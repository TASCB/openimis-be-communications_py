"""Service layer for the Communications module.

Per-entity CRUD services extend ``core.services.BaseService`` (uniform
``{success, data, error}`` contract + service signals). ``CommunicationActivityService``
adds the status-workflow ``transition`` chokepoint and the channel ``dispatch`` ("blast")
stub. ``ConflictService`` / ``ActivitySummaryService`` are read services. Patterned on
the ``training`` module.
"""
import logging
from datetime import timedelta

from django.db import transaction
from django.db.models import Count, Sum
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
)

logger = logging.getLogger(__name__)
COMMUNICATION_CODE_PREFIX = 'COM'


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


def _crud_service(name, object_type, validation_class, signal_prefix):
    """Build a simple BaseService subclass with create/update/delete service signals."""
    def __init__(self, user, validation_class=validation_class):
        BaseService.__init__(self, user, validation_class)

    @register_service_signal(f'{signal_prefix}.create')
    def create(self, obj_data):
        return BaseService.create(self, obj_data)

    @register_service_signal(f'{signal_prefix}.update')
    def update(self, obj_data):
        return BaseService.update(self, obj_data)

    @register_service_signal(f'{signal_prefix}.delete')
    def delete(self, obj_data):
        return BaseService.delete(self, obj_data)

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
    'ActivityChannelService', ActivityChannel, ActivityChannelValidation, 'communications_activity_channel_service')
ActivityObjectiveService = _crud_service(
    'ActivityObjectiveService', ActivityObjective, ActivityObjectiveValidation, 'communications_objective_service')
ActivityAssignmentService = _crud_service(
    'ActivityAssignmentService', ActivityAssignment, ActivityAssignmentValidation, 'communications_assignment_service')
ActivityAttachmentService = _crud_service(
    'ActivityAttachmentService', ActivityAttachment, ActivityAttachmentValidation, 'communications_attachment_service')
ActivityFeedbackService = _crud_service(
    'ActivityFeedbackService', ActivityFeedback, ActivityFeedbackValidation, 'communications_feedback_service')
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
ActivityAudienceService = _crud_service(
    'ActivityAudienceService', ActivityAudience, ActivityAudienceValidation, 'communications_audience_service')
CommunicationPostAttachmentService = _crud_service(
    'CommunicationPostAttachmentService', CommunicationPostAttachment,
    CommunicationPostAttachmentValidation, 'communications_post_attachment_service')


class CommunicationPostService(BaseService):
    OBJECT_TYPE = CommunicationPost

    def __init__(self, user, validation_class=CommunicationPostValidation):
        super().__init__(user, validation_class)

    @register_service_signal('communications_post_service.create')
    def create(self, obj_data):
        return super().create(self._sanitize_body(obj_data))

    @register_service_signal('communications_post_service.update')
    def update(self, obj_data):
        return super().update(self._sanitize_body(obj_data))

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

    def submit_for_approval(self, post_id):
        """Start the approval flow for a post; True when the request was raised."""
        try:
            from approval.services import ApprovalService
        except Exception:
            return False
        post = CommunicationPost.objects.filter(id=post_id, is_deleted=False).first()
        if not post or not self.user:
            return False
        summary = {
            'title': post.title,
            'post_type': post.get_post_type_display() if hasattr(post, 'get_post_type_display') else post.post_type,
            'created_by': post.user_created.username if post.user_created else 'Unknown',
        }
        res = ApprovalService(self.user).request_approval(post, 'COMMUNICATION_POST_APPROVAL', summary=summary)
        return res.get('success', False) if res else False


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
        self._assign_code(obj_data)
        return super().create(obj_data)

    @register_service_signal('communications_activity_service.update')
    def update(self, obj_data):
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
        """Phase-1 "blast" stub: records dispatch state on an ActivityChannel.
        Real Email/SMS/social adapters plug in here (Phase 2)."""
        try:
            ac = ActivityChannel.objects.filter(id=activity_channel_id, is_deleted=False).first()
            if not ac:
                return {"success": False, "message": _("communications.validation.not_found"),
                        "detail": str(activity_channel_id)}
            ac.dispatch_status = DispatchStatus.SENT
            ac.sent_at = timezone.now()
            ac.dispatch_detail = {**(ac.dispatch_detail or {}),
                                  'stub': True, 'by': self.user.username}
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
            qs = qs.filter(location_id=location_id)
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

            dismissal, created = AnnouncementDismissal.objects.get_or_create(
                post_id=post_id,
                user_id=self.user.id,
                defaults={
                    'is_deleted': False,
                    'version': 1,
                    'user_created_id': self.user.id,
                    'user_updated_id': self.user.id,
                }
            )
            if not created:
                dismissal.dismissed_at = timezone.now()
                dismissal.user_updated_id = self.user.id
                dismissal.save(username=self.user.username)

            return {"success": True, "message": _("communications.dismissal.success"),
                    "data": model_representation(dismissal)}
        except Exception as exc:
            return output_exception(model_name='AnnouncementDismissal', method="dismiss", exception=exc)
