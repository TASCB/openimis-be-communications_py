"""GraphQL schema (Query + Mutation) for the Communications module.

Concatenated into the global openIMIS schema by the assembly (same mechanism as
``training`` / ``payment_cycle``).
"""
import graphene
import graphene_django_optimizer as gql_optimizer
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.utils.translation import gettext as _

from core.schema import OrderedDjangoFilterConnectionField
from core.services import wait_for_mutation

from communications.apps import CommunicationsConfig
from communications.models import (
    CommunicationActivity, ActivityCategory, Channel, ActivityChannel,
    ActivityObjective, ActivityAssignment, ActivityAttachment, ActivityFeedback,
    CommunicationTemplate, StakeholderList, StakeholderListEntry, LibraryAsset,
    StakeholderType, ActivityAudience, CommunicationPost, CommunicationPostAttachment,
    AnnouncementDismissal, PostType,
)
from communications.gql_queries import (
    CommunicationActivityGQLType, ActivityCategoryGQLType, ChannelGQLType,
    ActivityChannelGQLType, ActivityObjectiveGQLType, ActivityAssignmentGQLType,
    ActivityAttachmentGQLType, ActivityFeedbackGQLType, CommunicationTemplateGQLType,
    StakeholderListGQLType, StakeholderListEntryGQLType, LibraryAssetGQLType,
    StakeholderTypeGQLType, ActivityAudienceGQLType, CommunicationPostGQLType,
    CommunicationPostAttachmentGQLType,
    ActivityConflictGQLType, ActivitySummaryGQLType,
    CommStatusCountGQLType, CommCategoryCountGQLType, CommChannelCountGQLType,
    CommTypeCountGQLType, CommReachGQLType,
)
from communications.services import ConflictService, ActivitySummaryService
from communications.gql_mutations import (
    CreateActivityMutation, UpdateActivityMutation, DeleteActivityMutation,
    SubmitActivityMutation, ApproveActivityMutation, RejectActivityMutation,
    ReviseActivityMutation, ScheduleActivityMutation, StartActivityMutation,
    CompleteActivityMutation, CloseActivityMutation, ArchiveActivityMutation,
    CancelActivityMutation, DispatchActivityChannelMutation,
    CreateActivityCategoryMutation, UpdateActivityCategoryMutation, DeleteActivityCategoryMutation,
    CreateChannelMutation, UpdateChannelMutation, DeleteChannelMutation,
    CreateActivityChannelMutation, UpdateActivityChannelMutation, DeleteActivityChannelMutation,
    CreateActivityObjectiveMutation, UpdateActivityObjectiveMutation, DeleteActivityObjectiveMutation,
    CreateActivityAssignmentMutation, UpdateActivityAssignmentMutation, DeleteActivityAssignmentMutation,
    CreateActivityFeedbackMutation, UpdateActivityFeedbackMutation, DeleteActivityFeedbackMutation,
    CreateTemplateMutation, UpdateTemplateMutation, DeleteTemplateMutation,
    CreateStakeholderListMutation, UpdateStakeholderListMutation, DeleteStakeholderListMutation,
    CreateStakeholderEntryMutation, UpdateStakeholderEntryMutation, DeleteStakeholderEntryMutation,
    UpdateLibraryAssetMutation, DeleteLibraryAssetMutation, DeleteActivityAttachmentMutation,
    CreateStakeholderTypeMutation, UpdateStakeholderTypeMutation, DeleteStakeholderTypeMutation,
    CreateActivityAudienceMutation, UpdateActivityAudienceMutation, DeleteActivityAudienceMutation,
    CreatePostMutation, UpdatePostMutation, DeletePostMutation,
    PublishPostMutation, UnpublishPostMutation, DeletePostAttachmentMutation,
    DismissAnnouncementMutation, SubmitPostForApprovalMutation,
)


def _check(user, perms):
    if type(user) is AnonymousUser or not user.id or not user.has_perms(perms):
        raise PermissionDenied(_("unauthorized"))


def _location_filter(parent_location, parent_location_level):
    from location.apps import LocationConfig
    query_key = "uuid"
    for _i in range(len(LocationConfig.location_types) - parent_location_level - 1):
        query_key = "parent__" + query_key
    query_key = "location__" + query_key
    return Q(**{query_key: parent_location})


class Query(graphene.ObjectType):
    communication_activity = OrderedDjangoFilterConnectionField(
        CommunicationActivityGQLType, orderBy=graphene.List(of_type=graphene.String),
        client_mutation_id=graphene.String(), show_deleted=graphene.Boolean(),
        parent_location=graphene.String(), parent_location_level=graphene.Int())
    activity_category = OrderedDjangoFilterConnectionField(
        ActivityCategoryGQLType, orderBy=graphene.List(of_type=graphene.String),
        show_deleted=graphene.Boolean())
    channel = OrderedDjangoFilterConnectionField(
        ChannelGQLType, orderBy=graphene.List(of_type=graphene.String),
        show_deleted=graphene.Boolean())
    activity_channel = OrderedDjangoFilterConnectionField(
        ActivityChannelGQLType, orderBy=graphene.List(of_type=graphene.String))
    activity_objective = OrderedDjangoFilterConnectionField(
        ActivityObjectiveGQLType, orderBy=graphene.List(of_type=graphene.String))
    activity_assignment = OrderedDjangoFilterConnectionField(
        ActivityAssignmentGQLType, orderBy=graphene.List(of_type=graphene.String))
    activity_attachment = OrderedDjangoFilterConnectionField(
        ActivityAttachmentGQLType, orderBy=graphene.List(of_type=graphene.String))
    activity_feedback = OrderedDjangoFilterConnectionField(
        ActivityFeedbackGQLType, orderBy=graphene.List(of_type=graphene.String),
        show_deleted=graphene.Boolean(),
        parent_location=graphene.String(), parent_location_level=graphene.Int())
    communication_template = OrderedDjangoFilterConnectionField(
        CommunicationTemplateGQLType, orderBy=graphene.List(of_type=graphene.String),
        show_deleted=graphene.Boolean())
    stakeholder_list = OrderedDjangoFilterConnectionField(
        StakeholderListGQLType, orderBy=graphene.List(of_type=graphene.String),
        show_deleted=graphene.Boolean())
    stakeholder_list_entry = OrderedDjangoFilterConnectionField(
        StakeholderListEntryGQLType, orderBy=graphene.List(of_type=graphene.String))
    library_asset = OrderedDjangoFilterConnectionField(
        LibraryAssetGQLType, orderBy=graphene.List(of_type=graphene.String),
        show_deleted=graphene.Boolean())
    stakeholder_type = OrderedDjangoFilterConnectionField(
        StakeholderTypeGQLType, orderBy=graphene.List(of_type=graphene.String),
        show_deleted=graphene.Boolean())
    activity_audience = OrderedDjangoFilterConnectionField(
        ActivityAudienceGQLType, orderBy=graphene.List(of_type=graphene.String))
    communication_post = OrderedDjangoFilterConnectionField(
        CommunicationPostGQLType, orderBy=graphene.List(of_type=graphene.String),
        client_mutation_id=graphene.String(), show_deleted=graphene.Boolean())
    communication_posts_unread = graphene.List(CommunicationPostGQLType)
    communication_post_attachment = OrderedDjangoFilterConnectionField(
        CommunicationPostAttachmentGQLType, orderBy=graphene.List(of_type=graphene.String))

    activity_calendar = graphene.List(
        CommunicationActivityGQLType,
        date_from=graphene.DateTime(required=True),
        date_to=graphene.DateTime(required=True),
        status=graphene.String(),
        category_id=graphene.UUID(),
        location_id=graphene.Int(),
    )
    activity_conflicts = graphene.List(
        ActivityConflictGQLType,
        start_datetime=graphene.DateTime(required=True),
        end_datetime=graphene.DateTime(required=True),
        activity_id=graphene.UUID(),
        location_id=graphene.Int(),
        staff_user_ids=graphene.List(graphene.UUID),
    )
    activity_summary = graphene.Field(
        ActivitySummaryGQLType,
        date_from=graphene.DateTime(), date_to=graphene.DateTime(), location_id=graphene.Int())

    # -- resolvers ----------------------------------------------------------
    def resolve_communication_activity(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_activity_search_perms)
        filters = [] if kwargs.get('show_deleted') else [Q(is_deleted=False)]
        client_mutation_id = kwargs.get("client_mutation_id")
        if client_mutation_id:
            wait_for_mutation(client_mutation_id)
            filters.append(Q(mutations__mutation__client_mutation_id=client_mutation_id))
        pl, pll = kwargs.get('parent_location'), kwargs.get('parent_location_level')
        if pl is not None and pll is not None:
            filters.append(_location_filter(pl, pll))
        return gql_optimizer.query(CommunicationActivity.objects.filter(*filters).distinct(), info)

    def resolve_activity_category(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_category_search_perms)
        filters = [] if kwargs.get('show_deleted') else [Q(is_deleted=False)]
        return gql_optimizer.query(ActivityCategory.objects.filter(*filters), info)

    def resolve_channel(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_channel_search_perms)
        filters = [] if kwargs.get('show_deleted') else [Q(is_deleted=False)]
        return gql_optimizer.query(Channel.objects.filter(*filters), info)

    def resolve_activity_channel(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_activity_channel_search_perms)
        return gql_optimizer.query(ActivityChannel.objects.filter(is_deleted=False), info)

    def resolve_activity_objective(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_objective_search_perms)
        return gql_optimizer.query(ActivityObjective.objects.filter(is_deleted=False), info)

    def resolve_activity_assignment(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_assignment_search_perms)
        return gql_optimizer.query(ActivityAssignment.objects.filter(is_deleted=False), info)

    def resolve_activity_attachment(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_attachment_search_perms)
        return gql_optimizer.query(ActivityAttachment.objects.filter(is_deleted=False), info)

    def resolve_activity_feedback(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_feedback_search_perms)
        filters = [] if kwargs.get('show_deleted') else [Q(is_deleted=False)]
        pl, pll = kwargs.get('parent_location'), kwargs.get('parent_location_level')
        if pl is not None and pll is not None:
            # feedback has no location; traverse via the activity's location
            query_key = "uuid"
            from location.apps import LocationConfig
            for _i in range(len(LocationConfig.location_types) - pll - 1):
                query_key = "parent__" + query_key
            filters.append(Q(**{"activity__location__" + query_key: pl}))
        return gql_optimizer.query(ActivityFeedback.objects.filter(*filters).distinct(), info)

    def resolve_communication_template(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_template_search_perms)
        filters = [] if kwargs.get('show_deleted') else [Q(is_deleted=False)]
        return gql_optimizer.query(CommunicationTemplate.objects.filter(*filters), info)

    def resolve_stakeholder_list(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_stakeholder_search_perms)
        filters = [] if kwargs.get('show_deleted') else [Q(is_deleted=False)]
        return gql_optimizer.query(StakeholderList.objects.filter(*filters), info)

    def resolve_stakeholder_list_entry(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_stakeholder_search_perms)
        return gql_optimizer.query(StakeholderListEntry.objects.filter(is_deleted=False), info)

    def resolve_library_asset(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_library_search_perms)
        filters = [] if kwargs.get('show_deleted') else [Q(is_deleted=False)]
        return gql_optimizer.query(LibraryAsset.objects.filter(*filters), info)

    def resolve_stakeholder_type(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_stakeholder_type_search_perms)
        filters = [] if kwargs.get('show_deleted') else [Q(is_deleted=False)]
        return gql_optimizer.query(StakeholderType.objects.filter(*filters), info)

    def resolve_activity_audience(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_audience_search_perms)
        return gql_optimizer.query(ActivityAudience.objects.filter(is_deleted=False), info)

    def resolve_communication_post(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_post_search_perms)
        filters = [] if kwargs.get('show_deleted') else [Q(is_deleted=False)]
        client_mutation_id = kwargs.get("client_mutation_id")
        if client_mutation_id:
            wait_for_mutation(client_mutation_id)
            filters.append(Q(mutations__mutation__client_mutation_id=client_mutation_id))

        # Drafts (pending approval) are visible to approvers only.
        if not info.context.user.has_perms(CommunicationsConfig.gql_activity_approve_perms):
            filters.append(Q(is_published=True))
        return gql_optimizer.query(
            CommunicationPost.objects.filter(*filters).order_by('-is_pinned', '-published_at', '-date_created'), info)

    def resolve_communication_post_attachment(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_post_search_perms)
        return gql_optimizer.query(CommunicationPostAttachment.objects.filter(is_deleted=False), info)

    def resolve_communication_posts_unread(self, info, **kwargs):
        """Published announcements the current user has not dismissed yet."""
        if not info.context.user or info.context.user.is_anonymous:
            return []
        from django.db.models import Exists, OuterRef
        dismissed = AnnouncementDismissal.objects.filter(
            post_id=OuterRef('id'), user_id=info.context.user.id, is_deleted=False)
        qs = (CommunicationPost.objects
              .filter(is_deleted=False, is_published=True, post_type=PostType.ANNOUNCEMENT)
              .exclude(Exists(dismissed))
              .order_by('-published_at'))
        return gql_optimizer.query(qs, info)

    def resolve_activity_calendar(self, info, date_from, date_to, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_dashboard_view_perms)
        qs = (CommunicationActivity.objects.filter(is_deleted=False)
              .filter(start_datetime__lt=date_to, end_datetime__gt=date_from))
        if kwargs.get('status'):
            qs = qs.filter(status=kwargs['status'])
        if kwargs.get('category_id'):
            qs = qs.filter(category_id=kwargs['category_id'])
        if kwargs.get('location_id'):
            qs = qs.filter(location_id=kwargs['location_id'])
        return gql_optimizer.query(qs.distinct().order_by('start_datetime'), info)

    def resolve_activity_conflicts(self, info, start_datetime, end_datetime, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_activity_search_perms)
        conflicts = ConflictService(info.context.user).check(
            start=start_datetime, end=end_datetime, activity_id=kwargs.get('activity_id'),
            location_id=kwargs.get('location_id'), staff_user_ids=kwargs.get('staff_user_ids'))
        return [ActivityConflictGQLType(**c) for c in conflicts]

    def resolve_activity_summary(self, info, **kwargs):
        _check(info.context.user, CommunicationsConfig.gql_dashboard_view_perms)
        data = ActivitySummaryService(info.context.user).get_summary(
            date_from=kwargs.get('date_from'), date_to=kwargs.get('date_to'),
            location_id=kwargs.get('location_id'))
        return ActivitySummaryGQLType(
            total_activities=data['total_activities'],
            activities_this_week=data['activities_this_week'],
            upcoming_activities=data['upcoming_activities'],
            ongoing_activities=data['ongoing_activities'],
            completed_activities=data['completed_activities'],
            cancelled_activities=data['cancelled_activities'],
            planned_audience_total=data['planned_audience_total'],
            actual_audience_total=data['actual_audience_total'],
            media_houses_invited=data['media_houses_invited'],
            media_houses_reported=data['media_houses_reported'],
            by_status=[CommStatusCountGQLType(**r) for r in data['by_status']],
            by_category=[CommCategoryCountGQLType(**r) for r in data['by_category']],
            by_channel=[CommChannelCountGQLType(**r) for r in data['by_channel']],
            by_type=[CommTypeCountGQLType(**r) for r in data['by_type']],
            reach_by_level=[CommReachGQLType(**r) for r in data['reach_by_level']],
        )


class Mutation(graphene.ObjectType):
    create_communication_activity = CreateActivityMutation.Field()
    update_communication_activity = UpdateActivityMutation.Field()
    delete_communication_activity = DeleteActivityMutation.Field()
    submit_activity = SubmitActivityMutation.Field()
    approve_activity = ApproveActivityMutation.Field()
    reject_activity = RejectActivityMutation.Field()
    revise_activity = ReviseActivityMutation.Field()
    schedule_activity = ScheduleActivityMutation.Field()
    start_activity = StartActivityMutation.Field()
    complete_activity = CompleteActivityMutation.Field()
    close_activity = CloseActivityMutation.Field()
    archive_activity = ArchiveActivityMutation.Field()
    cancel_activity = CancelActivityMutation.Field()
    dispatch_activity_channel = DispatchActivityChannelMutation.Field()

    create_activity_category = CreateActivityCategoryMutation.Field()
    update_activity_category = UpdateActivityCategoryMutation.Field()
    delete_activity_category = DeleteActivityCategoryMutation.Field()

    create_channel = CreateChannelMutation.Field()
    update_channel = UpdateChannelMutation.Field()
    delete_channel = DeleteChannelMutation.Field()

    create_activity_channel = CreateActivityChannelMutation.Field()
    update_activity_channel = UpdateActivityChannelMutation.Field()
    delete_activity_channel = DeleteActivityChannelMutation.Field()

    create_activity_objective = CreateActivityObjectiveMutation.Field()
    update_activity_objective = UpdateActivityObjectiveMutation.Field()
    delete_activity_objective = DeleteActivityObjectiveMutation.Field()

    create_activity_assignment = CreateActivityAssignmentMutation.Field()
    update_activity_assignment = UpdateActivityAssignmentMutation.Field()
    delete_activity_assignment = DeleteActivityAssignmentMutation.Field()

    create_activity_feedback = CreateActivityFeedbackMutation.Field()
    update_activity_feedback = UpdateActivityFeedbackMutation.Field()
    delete_activity_feedback = DeleteActivityFeedbackMutation.Field()

    create_communication_template = CreateTemplateMutation.Field()
    update_communication_template = UpdateTemplateMutation.Field()
    delete_communication_template = DeleteTemplateMutation.Field()

    create_stakeholder_list = CreateStakeholderListMutation.Field()
    update_stakeholder_list = UpdateStakeholderListMutation.Field()
    delete_stakeholder_list = DeleteStakeholderListMutation.Field()

    create_stakeholder_entry = CreateStakeholderEntryMutation.Field()
    update_stakeholder_entry = UpdateStakeholderEntryMutation.Field()
    delete_stakeholder_entry = DeleteStakeholderEntryMutation.Field()

    update_library_asset = UpdateLibraryAssetMutation.Field()
    delete_library_asset = DeleteLibraryAssetMutation.Field()
    delete_activity_attachment = DeleteActivityAttachmentMutation.Field()

    create_stakeholder_type = CreateStakeholderTypeMutation.Field()
    update_stakeholder_type = UpdateStakeholderTypeMutation.Field()
    delete_stakeholder_type = DeleteStakeholderTypeMutation.Field()

    create_activity_audience = CreateActivityAudienceMutation.Field()
    update_activity_audience = UpdateActivityAudienceMutation.Field()
    delete_activity_audience = DeleteActivityAudienceMutation.Field()

    create_communication_post = CreatePostMutation.Field()
    update_communication_post = UpdatePostMutation.Field()
    delete_communication_post = DeletePostMutation.Field()
    publish_communication_post = PublishPostMutation.Field()
    unpublish_communication_post = UnpublishPostMutation.Field()
    delete_communication_post_attachment = DeletePostAttachmentMutation.Field()
    dismiss_announcement = DismissAnnouncementMutation.Field()
    submit_post_for_approval = SubmitPostForApprovalMutation.Field()
