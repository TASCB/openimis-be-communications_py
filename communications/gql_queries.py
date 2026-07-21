"""GraphQL object types for the Communications module."""
import graphene
from graphene_django import DjangoObjectType

from core import ExtendedConnection
from communications.models import (
    CommunicationActivity, ActivityCategory, Channel, ActivityChannel,
    ActivityObjective, ActivityAssignment, ActivityAttachment, ActivityFeedback,
    CommunicationTemplate, StakeholderList, StakeholderListEntry, LibraryAsset,
    StakeholderType, ActivityAudience, CommunicationPost, CommunicationPostAttachment,
)


class ActivityCategoryGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = ActivityCategory
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "name": ["exact", "istartswith", "icontains", "iexact"],
            "is_active": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class ChannelGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = Channel
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "name": ["exact", "istartswith", "icontains", "iexact"],
            "channel_type": ["exact", "in"],
            "is_active": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class CommunicationActivityGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = CommunicationActivity
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "title": ["exact", "istartswith", "icontains", "iexact"],
            "status": ["exact", "in"],
            "activity_type": ["exact", "in"],
            "venue": ["exact", "icontains"],
            "category_id": ["exact"],
            "location_id": ["exact"],
            "start_datetime": ["exact", "lt", "lte", "gt", "gte"],
            "end_datetime": ["exact", "lt", "lte", "gt", "gte"],
            "planned_audience_count": ["exact", "lt", "lte", "gt", "gte"],
            "channels__channel__id": ["exact"],
            "assignments__staff_user__id": ["exact"],
            "audiences__stakeholder_type__id": ["exact"],
            "audiences__stakeholder_type__level": ["exact", "in"],
            "is_deleted": ["exact"],
            "date_created": ["exact", "lt", "lte", "gt", "gte"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class ActivityChannelGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = ActivityChannel
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "activity_id": ["exact"],
            "channel_id": ["exact"],
            "dispatch_status": ["exact", "in"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class ActivityObjectiveGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = ActivityObjective
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "activity_id": ["exact"],
            "indicator": ["exact", "icontains"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class ActivityAssignmentGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = ActivityAssignment
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "activity_id": ["exact"],
            "staff_user_id": ["exact"],
            "role": ["exact", "in"],
            "status": ["exact", "in"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class ActivityAttachmentGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')
    file_url = graphene.String()

    class Meta:
        model = ActivityAttachment
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "activity_id": ["exact"],
            "file_name": ["exact", "icontains"],
            "file_type": ["exact", "icontains"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection

    def resolve_file_url(self, info):
        try:
            return self.file.url if self.file else None
        except Exception:
            return None


class ActivityFeedbackGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = ActivityFeedback
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "activity_id": ["exact"],
            "channel_id": ["exact"],
            "rating": ["exact", "lt", "lte", "gt", "gte"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class CommunicationTemplateGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = CommunicationTemplate
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "name": ["exact", "istartswith", "icontains", "iexact"],
            "channel_type": ["exact", "in"],
            "is_active": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class StakeholderListGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = StakeholderList
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "name": ["exact", "istartswith", "icontains", "iexact"],
            "is_active": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class StakeholderListEntryGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = StakeholderListEntry
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "stakeholder_list_id": ["exact"],
            "name": ["exact", "istartswith", "icontains", "iexact"],
            "organization": ["exact", "icontains"],
            "location_id": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class LibraryAssetGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')
    file_url = graphene.String()

    class Meta:
        model = LibraryAsset
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "name": ["exact", "istartswith", "icontains", "iexact"],
            "asset_type": ["exact", "in"],
            "is_active": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection

    def resolve_file_url(self, info):
        try:
            return self.file.url if self.file else None
        except Exception:
            return None


class StakeholderTypeGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = StakeholderType
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "name": ["exact", "istartswith", "icontains", "iexact"],
            "level": ["exact", "in"],
            "is_active": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class ActivityAudienceGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = ActivityAudience
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "activity_id": ["exact"],
            "stakeholder_type_id": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class CommunicationPostAttachmentGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')
    file_url = graphene.String()

    class Meta:
        model = CommunicationPostAttachment
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "post_id": ["exact"],
            "file_name": ["exact", "icontains"],
            "file_type": ["exact", "icontains"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection

    def resolve_file_url(self, info):
        try:
            return self.file.url if self.file else None
        except Exception:
            return None


class CommunicationPostGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')
    attachments = graphene.List(CommunicationPostAttachmentGQLType)

    class Meta:
        model = CommunicationPost
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "title": ["exact", "istartswith", "icontains", "iexact"],
            "post_type": ["exact", "in"],
            "activity_id": ["exact"],
            "is_published": ["exact"],
            "is_pinned": ["exact"],
            "published_at": ["exact", "lt", "lte", "gt", "gte"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection

    def resolve_attachments(self, info):
        # Inline images live inside the post body HTML; keep them out of the card strip.
        return self.attachments.filter(is_deleted=False, is_inline=False).order_by('date_created')


# --- Non-model types -------------------------------------------------------
class ActivityConflictGQLType(graphene.ObjectType):
    type = graphene.String()
    hard = graphene.Boolean()
    message = graphene.String()
    conflicting_activity_id = graphene.String()
    conflicting_activity_code = graphene.String()
    subject_id = graphene.String()
    subject_label = graphene.String()


# NB: graphene type names are GLOBAL across the assembled schema — prefix with "Comm"
# to avoid collisions with identically-named helper types in other modules (e.g. the
# training module also defines StatusCountGQLType / CategoryCountGQLType).
class CommStatusCountGQLType(graphene.ObjectType):
    status = graphene.String()
    count = graphene.Int()


class CommCategoryCountGQLType(graphene.ObjectType):
    category_id = graphene.String()
    category_name = graphene.String()
    count = graphene.Int()


class CommChannelCountGQLType(graphene.ObjectType):
    channel_type = graphene.String()
    count = graphene.Int()


class CommTypeCountGQLType(graphene.ObjectType):
    activity_type = graphene.String()
    count = graphene.Int()


class CommReachGQLType(graphene.ObjectType):
    level = graphene.String()
    planned = graphene.Int()
    actual = graphene.Int()


class ActivitySummaryGQLType(graphene.ObjectType):
    total_activities = graphene.Int()
    activities_this_week = graphene.Int()
    upcoming_activities = graphene.Int()
    ongoing_activities = graphene.Int()
    completed_activities = graphene.Int()
    cancelled_activities = graphene.Int()
    planned_audience_total = graphene.Int()
    actual_audience_total = graphene.Int()
    media_houses_invited = graphene.Int()
    media_houses_reported = graphene.Int()
    by_status = graphene.List(CommStatusCountGQLType)
    by_category = graphene.List(CommCategoryCountGQLType)
    by_channel = graphene.List(CommChannelCountGQLType)
    by_type = graphene.List(CommTypeCountGQLType)
    reach_by_level = graphene.List(CommReachGQLType)
