"""GraphQL mutations for the Communications module.

CRUD mutations follow the openIMIS pattern (``BaseHistoryModel*MutationMixin +
BaseMutation`` with custom ``_validate_mutation`` / ``_mutate``), journaling through the
per-entity ``*Mutation`` link tables. Status-workflow mutations delegate to
``CommunicationActivityService.transition``. Patterned on the ``training`` module.
"""
import graphene
from django.core.exceptions import PermissionDenied
from django.utils.translation import gettext as _

from core.gql.gql_mutations.base_mutation import (
    BaseHistoryModelCreateMutationMixin, BaseHistoryModelUpdateMutationMixin,
    BaseHistoryModelDeleteMutationMixin, BaseMutation,
)
from core.schema import OpenIMISMutation

from communications.apps import CommunicationsConfig
from communications.models import (
    CommunicationActivity, ActivityCategory, Channel, ActivityChannel,
    ActivityObjective, ActivityAssignment, ActivityAttachment, ActivityFeedback,
    CommunicationTemplate, StakeholderList, StakeholderListEntry, LibraryAsset,
    StakeholderType, ActivityAudience, CommunicationPost, CommunicationPostAttachment,
    CommunicationActivityMutation, ActivityCategoryMutation, ChannelMutation,
    ActivityChannelMutation, ActivityObjectiveMutation, ActivityAssignmentMutation,
    ActivityAttachmentMutation, ActivityFeedbackMutation, CommunicationTemplateMutation,
    StakeholderListMutation, StakeholderListEntryMutation, LibraryAssetMutation,
    StakeholderTypeMutation, ActivityAudienceMutation, CommunicationPostMutation,
    ActivityStatus, ChannelType, DispatchStatus, AssignmentRole, AssignmentStatus, AssetType,
    ActivityType, StakeholderLevel, PostType,
)
from communications.services import (
    CommunicationActivityService, ActivityCategoryService, ChannelService,
    ActivityChannelService, ActivityObjectiveService, ActivityAssignmentService,
    ActivityAttachmentService, ActivityFeedbackService, CommunicationTemplateService,
    StakeholderListService, StakeholderListEntryService, LibraryAssetService,
    StakeholderTypeService, ActivityAudienceService, CommunicationPostService,
    CommunicationPostAttachmentService, ConflictService,
)


def _gql_enum(name, choices_cls):
    return graphene.Enum(name, [(c.value, c.value) for c in choices_cls])


ActivityStatusEnum = _gql_enum('CommActivityStatusInput', ActivityStatus)
ChannelTypeEnum = _gql_enum('CommChannelTypeInput', ChannelType)
DispatchStatusEnum = _gql_enum('CommDispatchStatusInput', DispatchStatus)
AssignmentRoleEnum = _gql_enum('CommAssignmentRoleInput', AssignmentRole)
AssignmentStatusEnum = _gql_enum('CommAssignmentStatusInput', AssignmentStatus)
AssetTypeEnum = _gql_enum('CommAssetTypeInput', AssetType)
ActivityTypeEnum = _gql_enum('CommActivityTypeInput', ActivityType)
StakeholderLevelEnum = _gql_enum('CommStakeholderLevelInput', StakeholderLevel)
PostTypeEnum = _gql_enum('CommPostTypeInput', PostType)


def _strip_client(data):
    data.pop('client_mutation_id', None)
    data.pop('client_mutation_label', None)


def _journal(mutation_model, fk_name, user, client_mutation_id, obj):
    if client_mutation_id and obj is not None:
        mutation_model.object_mutated(user, client_mutation_id=client_mutation_id, **{fk_name: obj})


def _crud_create(user, data, service_cls, model, mutation_model, fk_name):
    client_mutation_id = data.get('client_mutation_id')
    _strip_client(data)
    res = service_cls(user).create(data)
    if res['success']:
        obj = model.objects.get(id=res['data']['id'])
        _journal(mutation_model, fk_name, user, client_mutation_id, obj)
    return res if not res['success'] else None


def _crud_update(user, data, service_cls, model, mutation_model, fk_name):
    client_mutation_id = data.get('client_mutation_id')
    _strip_client(data)
    res = service_cls(user).update(data)
    if res['success']:
        obj = model.objects.get(id=data['id'])
        _journal(mutation_model, fk_name, user, client_mutation_id, obj)
    return res if not res['success'] else None


def _crud_delete(user, data, service_cls):
    _strip_client(data)
    service = service_cls(user)
    for identifier in data.get('ids', []):
        res = service.delete({'id': identifier})
        if not res['success']:
            return res
    return None


class _IdsInput(OpenIMISMutation.Input):
    ids = graphene.List(graphene.UUID)


# ===========================================================================
# CommunicationActivity
# ===========================================================================
class CreateActivityInput(OpenIMISMutation.Input):
    code = graphene.String(required=False)
    title = graphene.String(required=True)
    description = graphene.String(required=False)
    objective_summary = graphene.String(required=False)
    category_id = graphene.UUID(required=False)
    activity_type = graphene.Field(ActivityTypeEnum, required=False)
    start_datetime = graphene.DateTime(required=True)
    end_datetime = graphene.DateTime(required=True)
    venue = graphene.String(required=False)
    virtual_platform = graphene.String(required=False)
    location_id = graphene.Int(required=False)
    target_audience = graphene.String(required=False)
    planned_audience_count = graphene.Int(required=False)
    actual_audience_count = graphene.Int(required=False)
    media_houses_invited = graphene.Int(required=False)
    media_houses_reported = graphene.Int(required=False)
    status = graphene.Field(ActivityStatusEnum, required=False)
    ignore_conflicts = graphene.Boolean(required=False)
    conflict_staff_user_ids = graphene.List(graphene.UUID, required=False)


class UpdateActivityInput(CreateActivityInput):
    id = graphene.UUID(required=True)


def _enforce_activity_conflicts(user, data):
    data.pop('ignore_conflicts', False)
    staff_ids = data.pop('conflict_staff_user_ids', None)
    if not CommunicationsConfig.conflict_check_enabled:
        return None
    conflicts = ConflictService(user).check(
        start=data.get('start_datetime'), end=data.get('end_datetime'),
        activity_id=data.get('id'), location_id=data.get('location_id'),
        staff_user_ids=staff_ids)
    hard = [c for c in conflicts if c['hard']]
    if hard:
        return {"success": False, "message": _("communications.mutation.hard_conflict"),
                "detail": " | ".join(c['message'] for c in hard)}
    return None


class CreateActivityMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateActivityMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_activity_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        client_mutation_id = data.get('client_mutation_id')
        _strip_client(data)
        err = _enforce_activity_conflicts(user, data)
        if err:
            return err
        res = CommunicationActivityService(user).create(data)
        if res['success']:
            obj = CommunicationActivity.objects.get(id=res['data']['id'])
            _journal(CommunicationActivityMutation, 'communication_activity', user, client_mutation_id, obj)
        return res if not res['success'] else None

    class Input(CreateActivityInput):
        pass


class UpdateActivityMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateActivityMutation"
    _model = CommunicationActivity

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_activity_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        client_mutation_id = data.get('client_mutation_id')
        _strip_client(data)
        err = _enforce_activity_conflicts(user, data)
        if err:
            return err
        res = CommunicationActivityService(user).update(data)
        if res['success']:
            obj = CommunicationActivity.objects.get(id=data['id'])
            _journal(CommunicationActivityMutation, 'communication_activity', user, client_mutation_id, obj)
        return res if not res['success'] else None

    class Input(UpdateActivityInput):
        pass


class DeleteActivityMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteActivityMutation"
    _model = CommunicationActivity

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_activity_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, CommunicationActivityService)

    class Input(_IdsInput):
        pass


# --- status workflow -------------------------------------------------------
class TransitionInput(OpenIMISMutation.Input):
    id = graphene.UUID(required=True)
    reason = graphene.String(required=False)


class _TransitionLogic:
    """Plain mixin shared by status-workflow mutations. Must NOT be a graphene
    mutation itself, and must NOT call super()._validate_mutation (the only base is
    BaseMutation whose abstract method raises NotImplementedError)."""
    _action = None

    @classmethod
    def _validate_mutation(cls, user, **data):
        perms = (CommunicationsConfig.gql_activity_approve_perms
                 if cls._action in ('approve', 'reject')
                 else CommunicationsConfig.gql_activity_update_perms)
        if not user.has_perms(perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        _strip_client(data)
        res = CommunicationActivityService(user).transition(
            data.get('id'), cls._action, reason=data.get('reason'))
        return res if not res['success'] else None


def _make_transition(class_name, action):
    return type(class_name, (_TransitionLogic, BaseMutation), {
        '_mutation_module': 'communications',
        '_mutation_class': class_name,
        '_action': action,
        'Input': type('Input', (TransitionInput,), {}),
    })


SubmitActivityMutation = _make_transition('SubmitActivityMutation', 'submit')
ApproveActivityMutation = _make_transition('ApproveActivityMutation', 'approve')
RejectActivityMutation = _make_transition('RejectActivityMutation', 'reject')
ReviseActivityMutation = _make_transition('ReviseActivityMutation', 'revise')
ScheduleActivityMutation = _make_transition('ScheduleActivityMutation', 'schedule')
StartActivityMutation = _make_transition('StartActivityMutation', 'start')
CompleteActivityMutation = _make_transition('CompleteActivityMutation', 'complete')
CloseActivityMutation = _make_transition('CloseActivityMutation', 'close')
ArchiveActivityMutation = _make_transition('ArchiveActivityMutation', 'archive')
CancelActivityMutation = _make_transition('CancelActivityMutation', 'cancel')


# --- channel dispatch ("blast" stub) ---------------------------------------
class DispatchActivityChannelMutation(_TransitionLogic, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DispatchActivityChannelMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        if not user.has_perms(CommunicationsConfig.gql_channel_dispatch_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        _strip_client(data)
        res = CommunicationActivityService(user).dispatch_channel(data.get('id'))
        return res if not res['success'] else None

    class Input(OpenIMISMutation.Input):
        id = graphene.UUID(required=True)


# ===========================================================================
# Simple CRUD entities
# ===========================================================================
class CreateActivityCategoryInput(OpenIMISMutation.Input):
    code = graphene.String(required=True)
    name = graphene.String(required=True)
    description = graphene.String(required=False)
    is_active = graphene.Boolean(required=False)


class CreateActivityCategoryMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateActivityCategoryMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_category_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, ActivityCategoryService, ActivityCategory,
                            ActivityCategoryMutation, 'activity_category')

    class Input(CreateActivityCategoryInput):
        pass


class UpdateActivityCategoryMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateActivityCategoryMutation"
    _model = ActivityCategory

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_category_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, ActivityCategoryService, ActivityCategory,
                            ActivityCategoryMutation, 'activity_category')

    class Input(CreateActivityCategoryInput):
        id = graphene.UUID(required=True)


class DeleteActivityCategoryMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteActivityCategoryMutation"
    _model = ActivityCategory

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_category_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, ActivityCategoryService)

    class Input(_IdsInput):
        pass


class CreateChannelInput(OpenIMISMutation.Input):
    code = graphene.String(required=True)
    name = graphene.String(required=True)
    channel_type = graphene.Field(ChannelTypeEnum, required=False)
    is_active = graphene.Boolean(required=False)


class CreateChannelMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateChannelMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_channel_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, ChannelService, Channel, ChannelMutation, 'channel')

    class Input(CreateChannelInput):
        pass


class UpdateChannelMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateChannelMutation"
    _model = Channel

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_channel_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, ChannelService, Channel, ChannelMutation, 'channel')

    class Input(CreateChannelInput):
        id = graphene.UUID(required=True)


class DeleteChannelMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteChannelMutation"
    _model = Channel

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_channel_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, ChannelService)

    class Input(_IdsInput):
        pass


class CreateActivityChannelInput(OpenIMISMutation.Input):
    activity_id = graphene.UUID(required=True)
    channel_id = graphene.UUID(required=True)
    target = graphene.String(required=False)
    dispatch_status = graphene.Field(DispatchStatusEnum, required=False)


class CreateActivityChannelMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateActivityChannelMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_activity_channel_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, ActivityChannelService, ActivityChannel,
                            ActivityChannelMutation, 'activity_channel')

    class Input(CreateActivityChannelInput):
        pass


class UpdateActivityChannelMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateActivityChannelMutation"
    _model = ActivityChannel

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_activity_channel_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, ActivityChannelService, ActivityChannel,
                            ActivityChannelMutation, 'activity_channel')

    class Input(CreateActivityChannelInput):
        id = graphene.UUID(required=True)
        activity_id = graphene.UUID(required=False)
        channel_id = graphene.UUID(required=False)


class DeleteActivityChannelMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteActivityChannelMutation"
    _model = ActivityChannel

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_activity_channel_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, ActivityChannelService)

    class Input(_IdsInput):
        pass


class CreateActivityObjectiveInput(OpenIMISMutation.Input):
    activity_id = graphene.UUID(required=True)
    description = graphene.String(required=True)
    indicator = graphene.String(required=False)
    unit = graphene.String(required=False)
    target_value = graphene.Decimal(required=False)
    achieved_value = graphene.Decimal(required=False)


class CreateActivityObjectiveMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateActivityObjectiveMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_objective_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, ActivityObjectiveService, ActivityObjective,
                            ActivityObjectiveMutation, 'activity_objective')

    class Input(CreateActivityObjectiveInput):
        pass


class UpdateActivityObjectiveMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateActivityObjectiveMutation"
    _model = ActivityObjective

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_objective_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, ActivityObjectiveService, ActivityObjective,
                            ActivityObjectiveMutation, 'activity_objective')

    class Input(CreateActivityObjectiveInput):
        id = graphene.UUID(required=True)
        activity_id = graphene.UUID(required=False)
        description = graphene.String(required=False)


class DeleteActivityObjectiveMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteActivityObjectiveMutation"
    _model = ActivityObjective

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_objective_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, ActivityObjectiveService)

    class Input(_IdsInput):
        pass


class CreateActivityAssignmentInput(OpenIMISMutation.Input):
    activity_id = graphene.UUID(required=True)
    staff_user_id = graphene.UUID(required=False)
    role = graphene.Field(AssignmentRoleEnum, required=False)
    status = graphene.Field(AssignmentStatusEnum, required=False)
    notes = graphene.String(required=False)


class CreateActivityAssignmentMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateActivityAssignmentMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_assignment_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, ActivityAssignmentService, ActivityAssignment,
                            ActivityAssignmentMutation, 'activity_assignment')

    class Input(CreateActivityAssignmentInput):
        pass


class UpdateActivityAssignmentMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateActivityAssignmentMutation"
    _model = ActivityAssignment

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_assignment_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, ActivityAssignmentService, ActivityAssignment,
                            ActivityAssignmentMutation, 'activity_assignment')

    class Input(CreateActivityAssignmentInput):
        id = graphene.UUID(required=True)
        activity_id = graphene.UUID(required=False)


class DeleteActivityAssignmentMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteActivityAssignmentMutation"
    _model = ActivityAssignment

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_assignment_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, ActivityAssignmentService)

    class Input(_IdsInput):
        pass


class CreateActivityFeedbackInput(OpenIMISMutation.Input):
    activity_id = graphene.UUID(required=True)
    channel_id = graphene.UUID(required=False)
    source = graphene.String(required=False)
    respondent = graphene.String(required=False)
    rating = graphene.Int(required=False)
    comment = graphene.String(required=False)


class CreateActivityFeedbackMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateActivityFeedbackMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_feedback_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, ActivityFeedbackService, ActivityFeedback,
                            ActivityFeedbackMutation, 'activity_feedback')

    class Input(CreateActivityFeedbackInput):
        pass


class UpdateActivityFeedbackMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateActivityFeedbackMutation"
    _model = ActivityFeedback

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_feedback_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, ActivityFeedbackService, ActivityFeedback,
                            ActivityFeedbackMutation, 'activity_feedback')

    class Input(CreateActivityFeedbackInput):
        id = graphene.UUID(required=True)
        activity_id = graphene.UUID(required=False)


class DeleteActivityFeedbackMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteActivityFeedbackMutation"
    _model = ActivityFeedback

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_feedback_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, ActivityFeedbackService)

    class Input(_IdsInput):
        pass


class CreateTemplateInput(OpenIMISMutation.Input):
    code = graphene.String(required=True)
    name = graphene.String(required=True)
    channel_type = graphene.Field(ChannelTypeEnum, required=False)
    subject = graphene.String(required=False)
    body = graphene.String(required=False)
    is_active = graphene.Boolean(required=False)


class CreateTemplateMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateTemplateMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_template_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, CommunicationTemplateService, CommunicationTemplate,
                            CommunicationTemplateMutation, 'communication_template')

    class Input(CreateTemplateInput):
        pass


class UpdateTemplateMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateTemplateMutation"
    _model = CommunicationTemplate

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_template_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, CommunicationTemplateService, CommunicationTemplate,
                            CommunicationTemplateMutation, 'communication_template')

    class Input(CreateTemplateInput):
        id = graphene.UUID(required=True)


class DeleteTemplateMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteTemplateMutation"
    _model = CommunicationTemplate

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_template_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, CommunicationTemplateService)

    class Input(_IdsInput):
        pass


class CreateStakeholderListInput(OpenIMISMutation.Input):
    code = graphene.String(required=True)
    name = graphene.String(required=True)
    description = graphene.String(required=False)
    is_active = graphene.Boolean(required=False)


class CreateStakeholderListMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateStakeholderListMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_stakeholder_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, StakeholderListService, StakeholderList,
                            StakeholderListMutation, 'stakeholder_list')

    class Input(CreateStakeholderListInput):
        pass


class UpdateStakeholderListMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateStakeholderListMutation"
    _model = StakeholderList

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_stakeholder_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, StakeholderListService, StakeholderList,
                            StakeholderListMutation, 'stakeholder_list')

    class Input(CreateStakeholderListInput):
        id = graphene.UUID(required=True)


class DeleteStakeholderListMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteStakeholderListMutation"
    _model = StakeholderList

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_stakeholder_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, StakeholderListService)

    class Input(_IdsInput):
        pass


class CreateStakeholderEntryInput(OpenIMISMutation.Input):
    stakeholder_list_id = graphene.UUID(required=True)
    name = graphene.String(required=True)
    organization = graphene.String(required=False)
    email = graphene.String(required=False)
    phone = graphene.String(required=False)
    location_id = graphene.Int(required=False)


class CreateStakeholderEntryMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateStakeholderEntryMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_stakeholder_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, StakeholderListEntryService, StakeholderListEntry,
                            StakeholderListEntryMutation, 'stakeholder_list_entry')

    class Input(CreateStakeholderEntryInput):
        pass


class UpdateStakeholderEntryMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateStakeholderEntryMutation"
    _model = StakeholderListEntry

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_stakeholder_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, StakeholderListEntryService, StakeholderListEntry,
                            StakeholderListEntryMutation, 'stakeholder_list_entry')

    class Input(CreateStakeholderEntryInput):
        id = graphene.UUID(required=True)
        stakeholder_list_id = graphene.UUID(required=False)
        name = graphene.String(required=False)


class DeleteStakeholderEntryMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteStakeholderEntryMutation"
    _model = StakeholderListEntry

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_stakeholder_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, StakeholderListEntryService)

    class Input(_IdsInput):
        pass


class UpdateLibraryAssetInput(OpenIMISMutation.Input):
    id = graphene.UUID(required=True)
    code = graphene.String(required=False)
    name = graphene.String(required=False)
    asset_type = graphene.Field(AssetTypeEnum, required=False)
    description = graphene.String(required=False)
    is_active = graphene.Boolean(required=False)


class UpdateLibraryAssetMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateLibraryAssetMutation"
    _model = LibraryAsset

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_library_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, LibraryAssetService, LibraryAsset,
                            LibraryAssetMutation, 'library_asset')

    class Input(UpdateLibraryAssetInput):
        pass


class DeleteLibraryAssetMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteLibraryAssetMutation"
    _model = LibraryAsset

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_library_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, LibraryAssetService)

    class Input(_IdsInput):
        pass


# --- ActivityAttachment delete (create via DRF upload) ---------------------
class DeleteActivityAttachmentMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteActivityAttachmentMutation"
    _model = ActivityAttachment

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_attachment_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, ActivityAttachmentService)

    class Input(_IdsInput):
        pass


# ===========================================================================
# StakeholderType (taxonomy)
# ===========================================================================
class CreateStakeholderTypeInput(OpenIMISMutation.Input):
    code = graphene.String(required=True)
    name = graphene.String(required=True)
    level = graphene.Field(StakeholderLevelEnum, required=False)
    is_active = graphene.Boolean(required=False)


class CreateStakeholderTypeMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateStakeholderTypeMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_stakeholder_type_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, StakeholderTypeService, StakeholderType,
                            StakeholderTypeMutation, 'stakeholder_type')

    class Input(CreateStakeholderTypeInput):
        pass


class UpdateStakeholderTypeMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateStakeholderTypeMutation"
    _model = StakeholderType

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_stakeholder_type_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, StakeholderTypeService, StakeholderType,
                            StakeholderTypeMutation, 'stakeholder_type')

    class Input(CreateStakeholderTypeInput):
        id = graphene.UUID(required=True)


class DeleteStakeholderTypeMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteStakeholderTypeMutation"
    _model = StakeholderType

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_stakeholder_type_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, StakeholderTypeService)

    class Input(_IdsInput):
        pass


# ===========================================================================
# ActivityAudience (the "Who" + planned/actual reach)
# ===========================================================================
class CreateActivityAudienceInput(OpenIMISMutation.Input):
    activity_id = graphene.UUID(required=True)
    stakeholder_type_id = graphene.UUID(required=False)
    planned_count = graphene.Int(required=False)
    actual_count = graphene.Int(required=False)
    notes = graphene.String(required=False)


class CreateActivityAudienceMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreateActivityAudienceMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_audience_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, ActivityAudienceService, ActivityAudience,
                            ActivityAudienceMutation, 'activity_audience')

    class Input(CreateActivityAudienceInput):
        pass


class UpdateActivityAudienceMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdateActivityAudienceMutation"
    _model = ActivityAudience

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_audience_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, ActivityAudienceService, ActivityAudience,
                            ActivityAudienceMutation, 'activity_audience')

    class Input(CreateActivityAudienceInput):
        id = graphene.UUID(required=True)
        activity_id = graphene.UUID(required=False)


class DeleteActivityAudienceMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeleteActivityAudienceMutation"
    _model = ActivityAudience

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_audience_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, ActivityAudienceService)

    class Input(_IdsInput):
        pass


# ===========================================================================
# CommunicationPost (internal feed)
# ===========================================================================
class CreatePostInput(OpenIMISMutation.Input):
    title = graphene.String(required=True)
    body = graphene.String(required=False)
    post_type = graphene.Field(PostTypeEnum, required=False)
    activity_id = graphene.UUID(required=False)
    is_pinned = graphene.Boolean(required=False)


class CreatePostMutation(BaseHistoryModelCreateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "CreatePostMutation"

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_post_create_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_create(user, data, CommunicationPostService, CommunicationPost,
                            CommunicationPostMutation, 'communication_post')

    class Input(CreatePostInput):
        pass


class UpdatePostMutation(BaseHistoryModelUpdateMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UpdatePostMutation"
    _model = CommunicationPost

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_post_update_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_update(user, data, CommunicationPostService, CommunicationPost,
                            CommunicationPostMutation, 'communication_post')

    class Input(CreatePostInput):
        id = graphene.UUID(required=True)
        title = graphene.String(required=False)


class DeletePostMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeletePostMutation"
    _model = CommunicationPost

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_post_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, CommunicationPostService)

    class Input(_IdsInput):
        pass


class _PostPublishLogic:
    """Plain mixin — publish / unpublish a post. Does NOT call abstract super()."""
    _published = True

    @classmethod
    def _validate_mutation(cls, user, **data):
        if not user.has_perms(CommunicationsConfig.gql_post_publish_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        _strip_client(data)
        res = CommunicationPostService(user).set_published(data.get('id'), cls._published)
        return res if not res['success'] else None


class PublishPostMutation(_PostPublishLogic, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "PublishPostMutation"
    _published = True

    class Input(OpenIMISMutation.Input):
        id = graphene.UUID(required=True)


class UnpublishPostMutation(_PostPublishLogic, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "UnpublishPostMutation"
    _published = False

    class Input(OpenIMISMutation.Input):
        id = graphene.UUID(required=True)


# Post attachments are created via the DRF multipart upload endpoint (binary files);
# only delete needs a GraphQL mutation. Reuses the post rights band.
class DeletePostAttachmentMutation(BaseHistoryModelDeleteMutationMixin, BaseMutation):
    _mutation_module = "communications"
    _mutation_class = "DeletePostAttachmentMutation"
    _model = CommunicationPostAttachment

    @classmethod
    def _validate_mutation(cls, user, **data):
        super()._validate_mutation(user, **data)
        if not user.has_perms(CommunicationsConfig.gql_post_delete_perms):
            raise PermissionDenied(_("unauthorized"))

    @classmethod
    def _mutate(cls, user, **data):
        return _crud_delete(user, data, CommunicationPostAttachmentService)

    class Input(_IdsInput):
        pass
