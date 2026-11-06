"""Service layer for the Communications module.

Per-entity CRUD services extend ``core.services.BaseService`` (uniform
``{success, data, error}`` contract + service signals). ``CommunicationActivityService``
adds the status-workflow ``transition`` chokepoint and the channel ``dispatch`` ("blast")
stub. ``ConflictService`` / ``ActivitySummaryService`` are read services. Patterned on
the ``training`` module.
"""
import logging
import re
from datetime import timedelta

from django.db import transaction
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone
from django.utils.translation import gettext as _

from core.services import BaseService
from core.services.utils import (
    output_exception, output_result_success, model_representation, check_authentication,
)
from core.signals import register_service_signal

from communications.apps import CommunicationsConfig
from communications.sanitize import sanitize_post_html
from communications.models import (
    CommunicationActivity, ActivityCategory, Channel, ActivityChannel,
    ActivityObjective, ActivityAssignment, ActivityAttachment, ActivityFeedback,
    CommunicationTemplate, StakeholderList, StakeholderListEntry, LibraryAsset,
    StakeholderType, ActivityAudience, CommunicationPost, CommunicationPostAttachment,
    AnnouncementDismissal,
    MediaHouseCategory, MediaHouse, Journalist, ActivityMediaHouse, ActivityParticipant,
    AttendanceStatus,
    ActivityStatus, TERMINAL_STATUSES, AssignmentStatus, DispatchStatus,
    ActivityCodeSequence,
)
from communications.validations import (
    CommunicationActivityValidation, ActivityCategoryValidation, ChannelValidation,
    ActivityChannelValidation, ActivityObjectiveValidation, ActivityAssignmentValidation,
    ActivityAttachmentValidation, ActivityFeedbackValidation,
    CommunicationTemplateValidation, StakeholderListValidation,
    StakeholderListEntryValidation, LibraryAssetValidation,
    StakeholderTypeValidation, ActivityAudienceValidation, CommunicationPostValidation,
    CommunicationPostAttachmentValidation,
    MediaHouseCategoryValidation, MediaHouseValidation, JournalistValidation,
    ActivityMediaHouseValidation, ActivityParticipantValidation,
)

logger = logging.getLogger(__name__)
COMMUNICATION_CODE_PREFIX = 'COM'
MEDIA_HOUSE_CODE_PREFIX = 'MH'
JOURNALIST_CODE_PREFIX = 'MJ'
REGISTRY_CODE_WIDTH = 5


def _next_registry_code(prefix, width=REGISTRY_CODE_WIDTH):
    """Next ``<PREFIX><zero-padded>`` code, reusing the activity code-sequence table.

    ``prefix`` is unique on that table, so each registry gets its own counter. Caller must be
    inside a transaction: the row is locked for the read-modify-write.
    """
    sequence, _created = ActivityCodeSequence.objects.select_for_update().get_or_create(
        prefix=prefix, defaults={'last_number': 0})
    sequence.last_number += 1
    sequence.save()
    return f'{prefix}{sequence.last_number:0{width}}'


def _json_safe_save_instance(self, obj_):
    """``save_instance`` that stringifies a ``FileField`` before the result is JSON-encoded.

    ``BaseService.save_instance`` → ``output_result_success`` does
    ``json.dumps(model_representation(obj), cls=DjangoJSONEncoder)``; ``model_representation``
    (``model_to_dict``) includes the raw ``FieldFile``, which the encoder cannot serialize — the
    row saves but the ``create``/``update`` ``transaction.atomic`` then rolls back. Replacing the
    file value with its stored path (``.name``) keeps the representation JSON-safe. No-op for
    models without a ``file`` field.
    """
    obj_.save(user=self.user, username=self.user.username)
    dict_repr = model_representation(obj_)
    file_field = dict_repr.get('file')
    if file_field is not None:
        dict_repr['file'] = getattr(file_field, 'name', str(file_field))
    return output_result_success(dict_representation=dict_repr)


# Plan rows change only in Draft/Rejected; result rows until Archived/Cancelled; split rows keep result fields.
LOCK_PLANNING = 'planning'
LOCK_RESULTS = 'results'
LOCK_SPLIT = 'split'
PLANNING_OPEN_STATUSES = (ActivityStatus.DRAFT, ActivityStatus.REJECTED)
RESULTS_CLOSED_STATUSES = (ActivityStatus.ARCHIVED, ActivityStatus.CANCELLED)


def _locked(status):
    message = _("This activity is %(status)s, so this part can no longer be changed.") % {
        'status': str(status).lower()}
    return {"success": False, "message": message, "detail": status}


def _parent_activity_status(model, obj_data):
    activity_id = obj_data.get('activity_id')
    if not activity_id and obj_data.get('id'):
        row = model.objects.filter(id=obj_data['id']).only('activity_id').first()
        activity_id = row.activity_id if row else None
    if not activity_id:
        return None
    return CommunicationActivity.objects.filter(id=activity_id).values_list('status', flat=True).first()


def apply_activity_lock(model, obj_data, lock, operation, result_fields=()):
    """None when the write may go ahead, else an error result (may drop non-result fields)."""
    status = _parent_activity_status(model, obj_data)
    if status is None or status in PLANNING_OPEN_STATUSES:
        return None
    if lock == LOCK_PLANNING or status in RESULTS_CLOSED_STATUSES:
        return _locked(status)
    if lock == LOCK_SPLIT:
        if operation != 'update':
            return _locked(status)
        for key in list(obj_data):
            if key not in ('id', *result_fields):
                obj_data.pop(key)
    return None


def _crud_service(name, object_type, validation_class, signal_prefix, lock=None, result_fields=()):
    """Build a simple BaseService subclass with create/update/delete service signals."""
    def __init__(self, user, validation_class=validation_class):
        BaseService.__init__(self, user, validation_class)

    def _guard(obj_data, operation):
        if not lock:
            return None
        return apply_activity_lock(object_type, obj_data, lock, operation, result_fields)

    @register_service_signal(f'{signal_prefix}.create')
    def create(self, obj_data):
        return _guard(obj_data, 'create') or BaseService.create(self, obj_data)

    @register_service_signal(f'{signal_prefix}.update')
    def update(self, obj_data):
        return _guard(obj_data, 'update') or BaseService.update(self, obj_data)

    @register_service_signal(f'{signal_prefix}.delete')
    def delete(self, obj_data):
        return _guard(obj_data, 'delete') or BaseService.delete(self, obj_data)

    return type(name, (BaseService,), {
        'OBJECT_TYPE': object_type, '__init__': __init__,
        'create': create, 'update': update, 'delete': delete,
        'save_instance': _json_safe_save_instance,
    })


ActivityCategoryService = _crud_service(
    'ActivityCategoryService', ActivityCategory, ActivityCategoryValidation, 'communications_category_service')
ChannelService = _crud_service(
    'ChannelService', Channel, ChannelValidation, 'communications_channel_service')
ActivityChannelService = _crud_service(
    'ActivityChannelService', ActivityChannel, ActivityChannelValidation, 'communications_activity_channel_service',
    lock=LOCK_PLANNING)
ActivityObjectiveService = _crud_service(
    'ActivityObjectiveService', ActivityObjective, ActivityObjectiveValidation, 'communications_objective_service',
    lock=LOCK_SPLIT, result_fields=('achieved_value',))
ActivityAttachmentService = _crud_service(
    'ActivityAttachmentService', ActivityAttachment, ActivityAttachmentValidation, 'communications_attachment_service',
    lock=LOCK_RESULTS)
ActivityFeedbackService = _crud_service(
    'ActivityFeedbackService', ActivityFeedback, ActivityFeedbackValidation, 'communications_feedback_service',
    lock=LOCK_RESULTS)
CommunicationTemplateService = _crud_service(
    'CommunicationTemplateService', CommunicationTemplate, CommunicationTemplateValidation, 'communications_template_service')
StakeholderListService = _crud_service(
    'StakeholderListService', StakeholderList, StakeholderListValidation, 'communications_stakeholder_service')
StakeholderListEntryService = _crud_service(
    'StakeholderListEntryService', StakeholderListEntry, StakeholderListEntryValidation, 'communications_stakeholder_entry_service')
LibraryAssetService = _crud_service(
    'LibraryAssetService', LibraryAsset, LibraryAssetValidation, 'communications_library_service')
StakeholderTypeService = _crud_service(
    'StakeholderTypeService', StakeholderType, StakeholderTypeValidation, 'communications_stakeholder_type_service')
CommunicationPostAttachmentService = _crud_service(
    'CommunicationPostAttachmentService', CommunicationPostAttachment,
    CommunicationPostAttachmentValidation, 'communications_post_attachment_service')
MediaHouseCategoryService = _crud_service(
    'MediaHouseCategoryService', MediaHouseCategory, MediaHouseCategoryValidation,
    'communications_media_house_category_service')


class ActivityAssignmentService(BaseService):
    """Staff on an activity. Planning data, and a staff member cannot be double-booked."""
    OBJECT_TYPE = ActivityAssignment

    def __init__(self, user, validation_class=ActivityAssignmentValidation):
        super().__init__(user, validation_class)

    @register_service_signal('communications_assignment_service.create')
    def create(self, obj_data):
        return (apply_activity_lock(ActivityAssignment, obj_data, LOCK_PLANNING, 'create')
                or self._clash(obj_data) or super().create(obj_data))

    @register_service_signal('communications_assignment_service.update')
    def update(self, obj_data):
        return (apply_activity_lock(ActivityAssignment, obj_data, LOCK_PLANNING, 'update')
                or self._clash(obj_data) or super().update(obj_data))

    @register_service_signal('communications_assignment_service.delete')
    def delete(self, obj_data):
        return apply_activity_lock(ActivityAssignment, obj_data, LOCK_PLANNING, 'delete') or super().delete(obj_data)

    def _clash(self, obj_data):
        row = ActivityAssignment.objects.filter(id=obj_data.get('id')).first() if obj_data.get('id') else None
        staff_id = obj_data.get('staff_user_id') or (row.staff_user_id if row else None)
        status = obj_data.get('status') or (row.status if row else AssignmentStatus.ASSIGNED)
        activity = CommunicationActivity.objects.filter(
            id=obj_data.get('activity_id') or (row.activity_id if row else None)).first()
        if not staff_id or not activity or status not in ACTIVE_ASSIGNMENT_STATUSES:
            return None
        hard = [c for c in ConflictService(self.user).check(
            start=activity.start_datetime, end=activity.end_datetime, activity_id=activity.id,
            staff_user_ids=[staff_id]) if c['hard']]
        if hard:
            return {"success": False, "message": _("communications.validation.hard_conflict"),
                    "detail": " | ".join(c['message'] for c in hard)}
        return None


class MediaHouseService(BaseService):
    """Media-house registry. Codes are system-generated (``MH00001``), never user-supplied."""
    OBJECT_TYPE = MediaHouse

    def __init__(self, user, validation_class=MediaHouseValidation):
        super().__init__(user, validation_class)

    @register_service_signal('communications_media_house_service.create')
    @transaction.atomic
    def create(self, obj_data):
        if not obj_data.get('code'):
            obj_data['code'] = _next_registry_code(MEDIA_HOUSE_CODE_PREFIX)
        return super().create(obj_data)

    @register_service_signal('communications_media_house_service.update')
    def update(self, obj_data):
        return super().update(obj_data)

    @register_service_signal('communications_media_house_service.delete')
    def delete(self, obj_data):
        return super().delete(obj_data)


class JournalistService(BaseService):
    """Journalist registry. A person has no natural code, so one is generated (``MJ00001``)."""
    OBJECT_TYPE = Journalist

    def __init__(self, user, validation_class=JournalistValidation):
        super().__init__(user, validation_class)

    @register_service_signal('communications_journalist_service.create')
    @transaction.atomic
    def create(self, obj_data):
        if not obj_data.get('code'):
            obj_data['code'] = _next_registry_code(JOURNALIST_CODE_PREFIX)
        return super().create(obj_data)

    @register_service_signal('communications_journalist_service.update')
    def update(self, obj_data):
        return super().update(obj_data)

    @register_service_signal('communications_journalist_service.delete')
    def delete(self, obj_data):
        return super().delete(obj_data)


def recompute_media_counters(activity_id):
    """Derive an activity's media counters from its ActivityMediaHouse rows.

    Only overwrites while rows exist. With no rows the typed values stand, so activities
    captured before the registry existed keep their hand-entered numbers and no dashboard
    silently drops to zero.
    """
    rows = ActivityMediaHouse.objects.filter(activity_id=activity_id, is_deleted=False)
    if not rows.exists():
        return None
    invited = rows.filter(invited=True).count()
    reported = rows.filter(reported=True).count()
    CommunicationActivity.objects.filter(id=activity_id).update(
        media_houses_invited=invited, media_houses_reported=reported)
    return invited, reported


def recompute_planned_audience(activity_id):
    """Derive an activity's ``planned_audience_count`` from its Audience rows.

    The Audience tab already records planned reach per stakeholder type; a second free-typed
    total on the form could only ever disagree with it. Same rule as the other derived counters:
    only overwrites while rows exist, so activities without an audience breakdown keep the
    figure someone typed.
    """
    rows = ActivityAudience.objects.filter(activity_id=activity_id, is_deleted=False)
    if not rows.exists():
        return None
    planned = rows.aggregate(s=Sum('planned_count'))['s'] or 0
    CommunicationActivity.objects.filter(id=activity_id).update(planned_audience_count=planned)
    return planned


class ActivityAudienceService(BaseService):
    """Planned reach per stakeholder type. Every write re-derives the activity's planned total."""
    OBJECT_TYPE = ActivityAudience

    def __init__(self, user, validation_class=ActivityAudienceValidation):
        super().__init__(user, validation_class)

    @register_service_signal('communications_audience_service.create')
    @transaction.atomic
    def create(self, obj_data):
        err = apply_activity_lock(ActivityAudience, obj_data, LOCK_SPLIT, 'create')
        if err:
            return err
        res = super().create(obj_data)
        if res['success']:
            recompute_planned_audience(obj_data.get('activity_id'))
        return res

    @register_service_signal('communications_audience_service.update')
    @transaction.atomic
    def update(self, obj_data):
        err = apply_activity_lock(ActivityAudience, obj_data, LOCK_SPLIT, 'update', ('actual_count', 'notes'))
        if err:
            return err
        res = super().update(obj_data)
        if res['success']:
            self._recompute_for(obj_data.get('id'))
        return res

    @register_service_signal('communications_audience_service.delete')
    @transaction.atomic
    def delete(self, obj_data):
        err = apply_activity_lock(ActivityAudience, obj_data, LOCK_SPLIT, 'delete')
        if err:
            return err
        row = ActivityAudience.objects.filter(id=obj_data.get('id')).only('activity_id').first()
        activity_id = row.activity_id if row else None
        res = super().delete(obj_data)
        if res['success'] and activity_id:
            recompute_planned_audience(activity_id)
        return res

    @staticmethod
    def _recompute_for(row_id):
        row = ActivityAudience.objects.filter(id=row_id).only('activity_id').first()
        if row:
            recompute_planned_audience(row.activity_id)


def recompute_participant_count(activity_id):
    """Derive an activity's ``actual_audience_count`` from its attendance register.

    Same rule as the media counters: only overwrites while rows exist, so activities recorded
    before the register existed keep their hand-entered figure.
    """
    rows = ActivityParticipant.objects.filter(activity_id=activity_id, is_deleted=False)
    if not rows.exists():
        return None
    attended = rows.filter(attendance_status=AttendanceStatus.ATTENDED).count()
    CommunicationActivity.objects.filter(id=activity_id).update(actual_audience_count=attended)
    return attended


class ActivityParticipantService(BaseService):
    """Attendance register. Every write re-derives the parent activity's actual count."""
    OBJECT_TYPE = ActivityParticipant

    def __init__(self, user, validation_class=ActivityParticipantValidation):
        super().__init__(user, validation_class)

    @register_service_signal('communications_participant_service.create')
    @transaction.atomic
    def create(self, obj_data):
        err = apply_activity_lock(ActivityParticipant, obj_data, LOCK_RESULTS, 'create')
        if err:
            return err
        res = super().create(obj_data)
        if res['success']:
            recompute_participant_count(obj_data.get('activity_id'))
        return res

    @register_service_signal('communications_participant_service.update')
    @transaction.atomic
    def update(self, obj_data):
        err = apply_activity_lock(ActivityParticipant, obj_data, LOCK_RESULTS, 'update')
        if err:
            return err
        res = super().update(obj_data)
        if res['success']:
            self._recompute_for(obj_data.get('id'))
        return res

    @register_service_signal('communications_participant_service.delete')
    @transaction.atomic
    def delete(self, obj_data):
        err = apply_activity_lock(ActivityParticipant, obj_data, LOCK_RESULTS, 'delete')
        if err:
            return err
        row = ActivityParticipant.objects.filter(id=obj_data.get('id')).only('activity_id').first()
        activity_id = row.activity_id if row else None
        res = super().delete(obj_data)
        if res['success'] and activity_id:
            recompute_participant_count(activity_id)
        return res

    @staticmethod
    def _recompute_for(row_id):
        row = ActivityParticipant.objects.filter(id=row_id).only('activity_id').first()
        if row:
            recompute_participant_count(row.activity_id)

    @staticmethod
    def _person_key(name, organization, phone):
        digits = re.sub(r'\D', '', phone or '')
        if len(digits) >= 9:
            return ('phone', digits[-9:])
        return ('name', (name or '').strip().lower(), (organization or '').strip().lower())

    @transaction.atomic
    def add_from_stakeholder_list(self, activity_id, stakeholder_list_id):
        """Invite every member of a stakeholder list; people already on the register are skipped."""
        try:
            err = apply_activity_lock(ActivityParticipant, {'activity_id': activity_id}, LOCK_RESULTS, 'create')
            if err:
                return err
            if not CommunicationActivity.objects.filter(id=activity_id, is_deleted=False).exists():
                return {"success": False, "message": _("communications.validation.not_found"),
                        "detail": str(activity_id)}
            entries = StakeholderListEntry.objects.filter(
                stakeholder_list_id=stakeholder_list_id, is_deleted=False,
                stakeholder_list__is_deleted=False)
            seen = {
                self._person_key(p.full_name, p.organization, p.phone)
                for p in ActivityParticipant.objects.filter(activity_id=activity_id, is_deleted=False)
            }
            added = 0
            for e in entries:
                key = self._person_key(e.name, e.organization, e.phone)
                if key in seen:
                    continue
                seen.add(key)
                ActivityParticipant(
                    activity_id=activity_id, full_name=e.name, organization=e.organization,
                    phone=e.phone, email=e.email, location_id=e.location_id,
                    attendance_status=AttendanceStatus.INVITED,
                ).save(username=self.user.username)
                added += 1
            if added:
                recompute_participant_count(activity_id)
            return {"success": True, "message": "Ok", "data": {"added": added, "skipped": entries.count() - added}}
        except Exception as exc:
            return output_exception(model_name='ActivityParticipant', method="add_from_list", exception=exc)


class ActivityMediaHouseService(BaseService):
    """Per-activity media coverage. Every write re-derives the parent activity's counters."""
    OBJECT_TYPE = ActivityMediaHouse

    def __init__(self, user, validation_class=ActivityMediaHouseValidation):
        super().__init__(user, validation_class)

    @register_service_signal('communications_activity_media_house_service.create')
    @transaction.atomic
    def create(self, obj_data):
        err = apply_activity_lock(ActivityMediaHouse, obj_data, LOCK_RESULTS, 'create')
        if err:
            return err
        res = super().create(obj_data)
        if res['success']:
            recompute_media_counters(obj_data.get('activity_id'))
        return res

    @register_service_signal('communications_activity_media_house_service.update')
    @transaction.atomic
    def update(self, obj_data):
        err = apply_activity_lock(ActivityMediaHouse, obj_data, LOCK_RESULTS, 'update')
        if err:
            return err
        res = super().update(obj_data)
        if res['success']:
            self._recompute_for(obj_data.get('id'))
        return res

    @register_service_signal('communications_activity_media_house_service.delete')
    @transaction.atomic
    def delete(self, obj_data):
        err = apply_activity_lock(ActivityMediaHouse, obj_data, LOCK_RESULTS, 'delete')
        if err:
            return err
        # read the parent before the row is soft-deleted
        row = ActivityMediaHouse.objects.filter(id=obj_data.get('id')).only('activity_id').first()
        activity_id = row.activity_id if row else None
        res = super().delete(obj_data)
        if res['success'] and activity_id:
            recompute_media_counters(activity_id)
        return res

    @staticmethod
    def _recompute_for(row_id):
        row = ActivityMediaHouse.objects.filter(id=row_id).only('activity_id').first()
        if row:
            recompute_media_counters(row.activity_id)


class CommunicationPostService(BaseService):
    OBJECT_TYPE = CommunicationPost

    def __init__(self, user, validation_class=CommunicationPostValidation):
        super().__init__(user, validation_class)

    @register_service_signal('communications_post_service.create')
    @transaction.atomic
    def create(self, obj_data):
        obj_data = self._sanitize_body(obj_data)
        if not self._can_publish():
            obj_data.pop('is_pinned', None)
        res = super().create(obj_data)
        if res['success']:
            self._adopt_inline_images(res['data']['id'], obj_data.get('body'))
        return res

    @register_service_signal('communications_post_service.update')
    @transaction.atomic
    def update(self, obj_data):
        obj_data = self._sanitize_body(obj_data)
        if not self._can_publish():
            obj_data.pop('is_pinned', None)
            post = CommunicationPost.objects.filter(id=obj_data.get('id'), is_deleted=False).first()
            if post and post.is_published and any(
                    k in obj_data and obj_data[k] != getattr(post, k) for k in ('title', 'body', 'post_type')):
                obj_data['is_published'] = False
                obj_data['published_at'] = None
        res = super().update(obj_data)
        if res['success']:
            self._adopt_inline_images(obj_data.get('id'), obj_data.get('body'))
        return res

    def _can_publish(self):
        return bool(self.user) and self.user.has_perms(CommunicationsConfig.gql_post_publish_perms)

    @staticmethod
    def _adopt_inline_images(post_id, body):
        """Link the inline images a body embeds to its post, so they are not left orphaned."""
        ids = re.findall(r'/post-attachments/([0-9a-fA-F-]{36})/download', body or '')
        if post_id and ids:
            CommunicationPostAttachment.objects.filter(
                id__in=ids, is_inline=True, post__isnull=True).update(post_id=post_id)

    @staticmethod
    def _sanitize_body(obj_data):
        if isinstance(obj_data, dict) and 'body' in obj_data:
            obj_data['body'] = sanitize_post_html(obj_data['body'])
        return obj_data

    @register_service_signal('communications_post_service.delete')
    def delete(self, obj_data):
        return super().delete(obj_data)

    @register_service_signal('communications_post_service.publish')
    def set_published(self, post_id, published=True):
        try:
            post = CommunicationPost.objects.filter(id=post_id, is_deleted=False).first()
            if not post:
                return {"success": False, "message": _("communications.validation.not_found"),
                        "detail": str(post_id)}
            post.is_published = published
            post.published_at = timezone.now() if published else None
            post.save(username=self.user.username)
            return {"success": True, "message": _("communications.post.success"),
                    "data": model_representation(post)}
        except Exception as exc:
            return output_exception(model_name='CommunicationPost', method="set_published", exception=exc)

    @register_service_signal('communications_post_service.pin')
    def set_pinned(self, post_id, pinned=True):
        try:
            post = CommunicationPost.objects.filter(id=post_id, is_deleted=False).first()
            if not post:
                return {"success": False, "message": _("communications.validation.not_found"),
                        "detail": str(post_id)}
            post.is_pinned = pinned
            post.save(username=self.user.username)
            return {"success": True, "message": _("communications.post.success"),
                    "data": model_representation(post)}
        except Exception as exc:
            return output_exception(model_name='CommunicationPost', method="set_pinned", exception=exc)

    def submit_for_approval(self, post_id):
        """Start the approval flow for a post; True when the request was raised."""
        try:
            from approval.services import ApprovalService
        except Exception:
            return False
        from django.contrib.contenttypes.models import ContentType
        from approval.models import ApprovalRequest, RequestStatus
        post = CommunicationPost.objects.filter(id=post_id, is_deleted=False).first()
        if not post or not self.user or post.is_published:
            return False
        if ApprovalRequest.objects.filter(
                content_type=ContentType.objects.get_for_model(CommunicationPost), object_id=str(post.pk),
                status=RequestStatus.PENDING, is_deleted=False).exists():
            return False
        if (post.json_ext or {}).get('approval_rejection_reason'):
            json_ext = {k: v for k, v in post.json_ext.items() if k != 'approval_rejection_reason'}
            CommunicationPost.objects.filter(id=post.id).update(json_ext=json_ext)
        summary = {
            'title': post.title,
            'post_type': post.get_post_type_display() if hasattr(post, 'get_post_type_display') else post.post_type,
            'created_by': post.user_created.username if post.user_created else 'Unknown',
        }
        res = ApprovalService(self.user).request_approval(post, 'COMMUNICATION_POST_APPROVAL', summary=summary)
        return res.get('success', False) if res else False


ACTIVITY_RESULT_FIELDS = ('actual_audience_count', 'media_houses_invited', 'media_houses_reported')
MARK_SENT_STATUSES = (ActivityStatus.SCHEDULED, ActivityStatus.ONGOING, ActivityStatus.COMPLETED)

# Allowed status transitions: action -> (from-states, to-state)
STATUS_TRANSITIONS = {
    'submit': ((ActivityStatus.DRAFT, ActivityStatus.REJECTED), ActivityStatus.SUBMITTED),
    'approve': ((ActivityStatus.SUBMITTED,), ActivityStatus.APPROVED),
    'reject': ((ActivityStatus.SUBMITTED,), ActivityStatus.REJECTED),
    'revise': ((ActivityStatus.REJECTED,), ActivityStatus.DRAFT),
    'schedule': ((ActivityStatus.APPROVED,), ActivityStatus.SCHEDULED),
    'start': ((ActivityStatus.SCHEDULED,), ActivityStatus.ONGOING),
    'complete': ((ActivityStatus.ONGOING,), ActivityStatus.COMPLETED),
    'close': ((ActivityStatus.COMPLETED,), ActivityStatus.CLOSED),
    'archive': ((ActivityStatus.CLOSED, ActivityStatus.COMPLETED,
                 ActivityStatus.CANCELLED), ActivityStatus.ARCHIVED),
    'cancel': ((ActivityStatus.DRAFT, ActivityStatus.APPROVED,
                ActivityStatus.SCHEDULED, ActivityStatus.ONGOING), ActivityStatus.CANCELLED),
}


class CommunicationActivityService(BaseService):
    OBJECT_TYPE = CommunicationActivity

    def __init__(self, user, validation_class=CommunicationActivityValidation):
        super().__init__(user, validation_class)

    @register_service_signal('communications_activity_service.create')
    @transaction.atomic
    def create(self, obj_data):
        obj_data['status'] = ActivityStatus.DRAFT
        self._assign_code(obj_data)
        return super().create(obj_data)

    @register_service_signal('communications_activity_service.update')
    def update(self, obj_data):
        # status changes only through transition()
        obj_data.pop('status', None)
        current = CommunicationActivity.objects.filter(
            id=obj_data.get('id'), is_deleted=False).values_list('status', flat=True).first()
        if current in RESULTS_CLOSED_STATUSES:
            return _locked(current)
        if current and current not in PLANNING_OPEN_STATUSES:
            for key in list(obj_data):
                if key not in ('id', *ACTIVITY_RESULT_FIELDS):
                    obj_data.pop(key)
        return super().update(obj_data)

    @staticmethod
    def _assign_code(obj_data):
        sequence = ActivityCodeSequence.objects.select_for_update().get(prefix=COMMUNICATION_CODE_PREFIX)
        sequence.last_number += 1
        sequence.save()
        obj_data['code'] = f'{COMMUNICATION_CODE_PREFIX}{sequence.last_number:08}'

    @register_service_signal('communications_activity_service.delete')
    def delete(self, obj_data):
        return super().delete(obj_data)

    @register_service_signal('communications_activity_service.transition')
    def transition(self, activity_id, action, **ctx):
        """Guarded status transition (Save/Close/Archive lifecycle)."""
        try:
            if action not in STATUS_TRANSITIONS:
                return {"success": False, "message": _("communications.validation.unknown_action"),
                        "detail": action}
            activity = CommunicationActivity.objects.filter(id=activity_id, is_deleted=False).first()
            if not activity:
                return {"success": False, "message": _("communications.validation.not_found"),
                        "detail": str(activity_id)}
            from_states, to_state = STATUS_TRANSITIONS[action]
            if activity.status not in from_states:
                return {"success": False,
                        "message": _("communications.validation.invalid_status_transition"),
                        "detail": f"{activity.status} -> {to_state} ({action})"}
            if action in ('approve', 'reject') and activity.user_created_id == getattr(self.user, 'id', None):
                return {"success": False,
                        "message": _("You created this activity, so another person must approve or reject it.")}
            if (action == 'cancel' and activity.status != ActivityStatus.DRAFT
                    and not self.user.has_perms(CommunicationsConfig.gql_activity_approve_perms)):
                return {"success": False,
                        "message": _("Only an approver can cancel an activity after it has been approved.")}
            if action == 'schedule':
                conflicts = ConflictService(self.user).check_for_activity(activity)
                hard = [c for c in conflicts if c['hard']]
                if hard:
                    return {"success": False,
                            "message": _("communications.validation.hard_conflict"),
                            "detail": " | ".join(c['message'] for c in hard)}
            if action == 'reject' and ctx.get('reason'):
                activity.json_ext = {**(activity.json_ext or {}), 'reject_reason': ctx['reason']}
            activity.status = to_state
            activity.save(username=self.user.username)
            return {"success": True, "message": _("communications.transition.success"),
                    "data": model_representation(activity)}
        except Exception as exc:
            return output_exception(model_name=self.OBJECT_TYPE.__name__, method="transition", exception=exc)

    @register_service_signal('communications_activity_service.dispatch')
    def dispatch_channel(self, activity_channel_id, **ctx):
        """Records that a channel's message was sent outside the MIS."""
        try:
            ac = ActivityChannel.objects.filter(id=activity_channel_id, is_deleted=False).select_related(
                'activity').first()
            if not ac:
                return {"success": False, "message": _("communications.validation.not_found"),
                        "detail": str(activity_channel_id)}
            if ac.activity.status not in MARK_SENT_STATUSES:
                return {"success": False,
                        "message": _("A channel can be marked as sent only once the activity is scheduled."),
                        "detail": ac.activity.status}
            ac.dispatch_status = DispatchStatus.SENT
            ac.sent_at = timezone.now()
            ac.dispatch_detail = {**(ac.dispatch_detail or {}),
                                  'manual': True, 'by': self.user.username}
            ac.save(username=self.user.username)
            return {"success": True, "message": _("communications.dispatch.success"),
                    "data": model_representation(ac)}
        except Exception as exc:
            return output_exception(model_name='ActivityChannel', method="dispatch", exception=exc)


# ---------------------------------------------------------------------------
# Conflict detection (staff double-booking)
# ---------------------------------------------------------------------------
ACTIVE_ASSIGNMENT_STATUSES = (AssignmentStatus.ASSIGNED, AssignmentStatus.CONFIRMED)


class ConflictService:
    def __init__(self, user):
        self.user = user

    @check_authentication
    def check(self, *, start, end, activity_id=None, location_id=None, staff_user_ids=None):
        if not CommunicationsConfig.conflict_check_enabled or not start or not end:
            return []
        hard_types = set(CommunicationsConfig.conflict_hard_types or [])
        conflicts = []
        overlap = (CommunicationActivity.objects
                   .filter(is_deleted=False, start_datetime__lt=end, end_datetime__gt=start)
                   .exclude(status__in=TERMINAL_STATUSES))
        if activity_id:
            overlap = overlap.exclude(id=activity_id)
        if staff_user_ids:
            qs = (ActivityAssignment.objects
                  .filter(is_deleted=False, staff_user_id__in=staff_user_ids,
                          status__in=ACTIVE_ASSIGNMENT_STATUSES, activity__in=overlap)
                  .select_related('staff_user', 'activity'))
            for a in qs:
                label = getattr(a.staff_user, 'username', None)
                conflicts.append(self._mk('STAFF', 'STAFF' in hard_types, a.activity,
                                          subject_id=str(a.staff_user_id), subject_label=label,
                                          subject=_("Staff member %(n)s") % {'n': label or a.staff_user_id}))
        if location_id:
            for act in overlap.filter(location_id=location_id):
                conflicts.append(self._mk('LOCATION', 'LOCATION' in hard_types, act,
                                          subject_id=str(location_id), subject=_("Location")))
        return conflicts

    def check_for_activity(self, activity):
        active = (ActivityAssignment.objects
                  .filter(activity=activity, is_deleted=False, status__in=ACTIVE_ASSIGNMENT_STATUSES))
        staff_ids = [a.staff_user_id for a in active if a.staff_user_id]
        return self.check(start=activity.start_datetime, end=activity.end_datetime,
                          activity_id=activity.id, location_id=activity.location_id,
                          staff_user_ids=staff_ids or None)

    @staticmethod
    def _mk(ctype, hard, activity, subject=None, subject_id=None, subject_label=None):
        message = _("Conflict: %(subject)s is already on Activity %(code)s.") % {
            'subject': subject or ctype, 'code': activity.code}
        return {
            'type': ctype, 'hard': bool(hard), 'message': message,
            'conflicting_activity_id': str(activity.id),
            'conflicting_activity_code': activity.code,
            'subject_id': subject_id, 'subject_label': subject_label,
        }


# ---------------------------------------------------------------------------
# Dashboard summary
# ---------------------------------------------------------------------------
class ActivitySummaryService:
    def __init__(self, user):
        self.user = user

    @check_authentication
    def get_summary(self, *, date_from=None, date_to=None, location_id=None):
        now = timezone.now()
        week_start = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)
        qs = CommunicationActivity.objects.filter(is_deleted=False)
        if location_id:
            qs = qs.filter(Q(location_id=location_id) | Q(location__parent_id=location_id)
                           | Q(location__parent__parent_id=location_id)
                           | Q(location__parent__parent__parent_id=location_id))
        if date_from:
            qs = qs.filter(start_datetime__gte=date_from)
        if date_to:
            qs = qs.filter(start_datetime__lte=date_to)

        def count(**f):
            return qs.filter(**f).count()

        by_status = list(qs.values('status').order_by('status').annotate(count=Count('id')))
        by_category = list(qs.values('category_id', 'category__name')
                           .order_by('category__name').annotate(count=Count('id')))
        by_channel = list(ActivityChannel.objects
                          .filter(is_deleted=False, activity__in=qs)
                          .values('channel__channel_type')
                          .order_by('channel__channel_type').annotate(count=Count('id')))
        # Activity volume by type
        by_type = list(qs.values('activity_type').order_by('activity_type').annotate(count=Count('id')))
        # Media impact (houses invited vs reported)
        media = qs.aggregate(invited=Sum('media_houses_invited'), reported=Sum('media_houses_reported'))
        # Planned (ActivityAudience) vs attended (ActivityParticipant) share a StakeholderType FK.
        parts = ActivityParticipant.objects.filter(is_deleted=False, activity__in=qs)
        participants_total = parts.count()
        participants_attended = parts.filter(attendance_status=AttendanceStatus.ATTENDED).count()
        by_gender = list(parts.filter(attendance_status=AttendanceStatus.ATTENDED)
                         .values('gender').order_by('gender').annotate(count=Count('id')))
        attended_by_type = {
            r['stakeholder_type_id']: r['count'] for r in
            parts.filter(attendance_status=AttendanceStatus.ATTENDED)
                 .values('stakeholder_type_id').annotate(count=Count('id'))
        }
        planned_by_type = list(ActivityAudience.objects
                               .filter(is_deleted=False, activity__in=qs)
                               .values('stakeholder_type_id', 'stakeholder_type__name')
                               .order_by('stakeholder_type__name')
                               .annotate(planned=Sum('planned_count')))
        # Sourced from ActivityMediaHouse, so these reflect registry-using activities only.
        coverage = ActivityMediaHouse.objects.filter(is_deleted=False, activity__in=qs)
        invited_rows = coverage.filter(invited=True).count()
        reported_rows = coverage.filter(reported=True).count()
        by_medium = list(coverage.filter(reported=True)
                         .values('media_house__category__medium')
                         .order_by('media_house__category__medium').annotate(count=Count('id')))
        by_scope = list(coverage.filter(reported=True)
                        .values('media_house__category__scope')
                        .order_by('media_house__category__scope').annotate(count=Count('id')))
        avg_quality = coverage.filter(coverage_quality__isnull=False).aggregate(a=Avg('coverage_quality'))['a']
        # Audience reach aggregated by stakeholder level (planned vs actual)
        reach = list(ActivityAudience.objects
                     .filter(is_deleted=False, activity__in=qs)
                     .values('stakeholder_type__level')
                     .order_by('stakeholder_type__level')
                     .annotate(planned=Sum('planned_count'), actual=Sum('actual_count')))
        return {
            'total_activities': qs.count(),
            'activities_this_week': count(start_datetime__gte=week_start, start_datetime__lt=week_end),
            'upcoming_activities': count(start_datetime__gte=now,
                                         status__in=[ActivityStatus.SCHEDULED, ActivityStatus.APPROVED]),
            'ongoing_activities': count(status=ActivityStatus.ONGOING),
            'completed_activities': count(status=ActivityStatus.COMPLETED),
            'cancelled_activities': count(status=ActivityStatus.CANCELLED),
            'planned_audience_total': qs.aggregate(s=Sum('planned_audience_count'))['s'] or 0,
            'actual_audience_total': qs.aggregate(s=Sum('actual_audience_count'))['s'] or 0,
            'media_houses_invited': media['invited'] or 0,
            'media_houses_reported': media['reported'] or 0,
            'by_status': [{'status': r['status'], 'count': r['count']} for r in by_status],
            'by_category': [{'category_id': str(r['category_id']) if r['category_id'] else None,
                             'category_name': r['category__name'], 'count': r['count']} for r in by_category],
            'by_channel': [{'channel_type': r['channel__channel_type'], 'count': r['count']} for r in by_channel],
            'by_type': [{'activity_type': r['activity_type'], 'count': r['count']} for r in by_type],
            'participants_total': participants_total,
            'participants_attended': participants_attended,
            'attendance_rate': (round(participants_attended * 100.0 / participants_total, 1)
                                if participants_total else 0.0),
            'participants_by_gender': [{'gender': r['gender'], 'count': r['count']}
                                       for r in by_gender if r['gender']],
            'participants_by_stakeholder': [
                {'stakeholder_type_id': str(r['stakeholder_type_id']) if r['stakeholder_type_id'] else None,
                 'stakeholder_name': r['stakeholder_type__name'],
                 'planned': r['planned'] or 0,
                 'attended': attended_by_type.get(r['stakeholder_type_id'], 0)}
                for r in planned_by_type if r['stakeholder_type_id']],
            'coverage_invited': invited_rows,
            'coverage_reported': reported_rows,
            'coverage_rate': round(reported_rows * 100.0 / invited_rows, 1) if invited_rows else 0.0,
            'avg_coverage_quality': round(avg_quality, 2) if avg_quality is not None else None,
            'coverage_by_medium': [{'medium': r['media_house__category__medium'], 'count': r['count']}
                                   for r in by_medium if r['media_house__category__medium']],
            'coverage_by_scope': [{'scope': r['media_house__category__scope'], 'count': r['count']}
                                  for r in by_scope if r['media_house__category__scope']],
            'reach_by_level': [{'level': r['stakeholder_type__level'],
                                'planned': r['planned'] or 0, 'actual': r['actual'] or 0}
                               for r in reach if r['stakeholder_type__level']],
        }


class AnnouncementDismissalService(BaseService):
    OBJECT_TYPE = AnnouncementDismissal

    def __init__(self, user, validation_class=None):
        super().__init__(user, validation_class)

    @register_service_signal('communications_dismissal_service.dismiss')
    def dismiss(self, post_id):
        """Mark an announcement as dismissed by the current user."""
        try:
            post = CommunicationPost.objects.filter(id=post_id, is_deleted=False).first()
            if not post:
                return {"success": False, "message": _("communications.validation.not_found"),
                        "detail": str(post_id)}
            if not self.user or not self.user.username:
                return {"success": False, "message": _("communications.validation.user_required")}

            # HistoryModel needs save(username=...) for its pk + audit fields, so no get_or_create.
            dismissal = AnnouncementDismissal.objects.filter(
                post_id=post_id, user_id=self.user.id).first()
            if dismissal:
                dismissal.dismissed_at = timezone.now()
            else:
                dismissal = AnnouncementDismissal(post_id=post_id, user_id=self.user.id)
            dismissal.save(username=self.user.username)

            return {"success": True, "message": _("communications.dismissal.success"),
                    "data": model_representation(dismissal)}
        except Exception as exc:
            return output_exception(model_name='AnnouncementDismissal', method="dismiss", exception=exc)
