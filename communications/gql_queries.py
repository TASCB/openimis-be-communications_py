"""GraphQL object types for the Communications module."""
import graphene
from graphene_django import DjangoObjectType

from core import ExtendedConnection
from communications.models import (
    CommunicationActivity, ActivityCategory, Channel, ActivityChannel,
    ActivityObjective, ActivityAssignment, ActivityAttachment, ActivityFeedback,
    CommunicationTemplate, StakeholderList, StakeholderListEntry, LibraryAsset,
    StakeholderType, ActivityAudience, CommunicationPost, CommunicationPostAttachment,
    MediaHouseCategory, MediaHouse, Journalist, ActivityMediaHouse, ActivityParticipant,
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
    # Whether the derived counters have a source yet. Resolved on the activity rather than read
    # from the FE store, because the child lists are only fetched when their tab is opened —
    # an unopened tab must not make a derived field look editable.
    participant_count = graphene.Int()
    coverage_count = graphene.Int()
    audience_count = graphene.Int()

    class Meta:
        model = CommunicationActivity
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "title": ["exact", "istartswith", "icontains", "iexact"],
            "status": ["exact", "in"],
            "activity_type": ["exact", "in"],
            "event_type": ["exact", "in"],
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

    def resolve_participant_count(self, info):
        return self.participants.filter(is_deleted=False).count()

    def resolve_coverage_count(self, info):
        return self.media_houses.filter(is_deleted=False).count()

    def resolve_audience_count(self, info):
        return self.audiences.filter(is_deleted=False).count()


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


class MediaHouseCategoryGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = MediaHouseCategory
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "name": ["exact", "istartswith", "icontains", "iexact"],
            "medium": ["exact", "in"],
            "scope": ["exact", "in"],
            "is_active": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class MediaHouseGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')
    # Derived on read from rated coverage rows, never a stored score.
    avg_coverage_quality = graphene.Float()
    coverage_count = graphene.Int()

    class Meta:
        model = MediaHouse
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "name": ["exact", "istartswith", "icontains", "iexact"],
            "category": ["exact"],
            "category__medium": ["exact", "in"],
            "category__scope": ["exact", "in"],
            "location": ["exact"],
            "primary_contact": ["exact"],
            "language": ["exact", "icontains"],
            "is_active": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class ActivityParticipantGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = ActivityParticipant
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            # `<fk>_id` to match the childFetch convention (`activityId:`)
            "activity_id": ["exact"],
            "full_name": ["exact", "istartswith", "icontains", "iexact"],
            "gender": ["exact", "in"],
            "stakeholder_type_id": ["exact"],
            "attendance_status": ["exact", "in"],
            "organization": ["exact", "icontains"],
            "individual_id": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection


class ActivityMediaHouseGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')

    class Meta:
        model = ActivityMediaHouse
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            # `<fk>_id`, not the relation name: childFetch sends `activityId:`
            "activity_id": ["exact"],
            "media_house_id": ["exact"],
            "media_house__category__medium": ["exact", "in"],
            "media_house__category__scope": ["exact", "in"],
            "journalist_id": ["exact"],
            "invited": ["exact"],
            "attended": ["exact"],
            "reported": ["exact"],
            "coverage_type": ["exact", "in"],
            "coverage_quality": ["exact", "gte", "lte"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection

    def resolve_avg_coverage_quality(self, info):
        from django.db.models import Avg
        return self.activity_coverage.filter(
            is_deleted=False, coverage_quality__isnull=False
        ).aggregate(a=Avg('coverage_quality'))['a']

    def resolve_coverage_count(self, info):
        return self.activity_coverage.filter(is_deleted=False, reported=True).count()


class JournalistGQLType(DjangoObjectType):
    uuid = graphene.String(source='uuid')
    full_name = graphene.String()
    # Derived from attributed coverage, never stored on the person. See the guide §12.
    stories_filed = graphene.Int()
    coverage_attributed = graphene.Int()
    avg_coverage_quality = graphene.Float()
    last_coverage_date = graphene.Date()

    class Meta:
        model = Journalist
        interfaces = (graphene.relay.Node,)
        filter_fields = {
            "id": ["exact"],
            "code": ["exact", "istartswith", "icontains", "iexact"],
            "first_name": ["exact", "istartswith", "icontains", "iexact"],
            "last_name": ["exact", "istartswith", "icontains", "iexact"],
            "gender": ["exact", "in"],
            "media_house": ["exact"],
            "media_house__category": ["exact"],
            "media_house__category__medium": ["exact", "in"],
            "is_freelance": ["exact"],
            "role": ["exact", "in"],
            "beat": ["exact", "icontains"],
            "location": ["exact"],
            "is_active": ["exact"],
            "is_deleted": ["exact"],
            "version": ["exact"],
        }
        connection_class = ExtendedConnection

    def resolve_full_name(self, info):
        return f'{self.first_name} {self.last_name}'.strip()

    def _coverage(self):
        return self.coverage.filter(is_deleted=False)

    def resolve_coverage_attributed(self, info):
        return JournalistGQLType._coverage(self).count()

    def resolve_stories_filed(self, info):
        return JournalistGQLType._coverage(self).filter(reported=True).count()

    def resolve_avg_coverage_quality(self, info):
        from django.db.models import Avg
        return JournalistGQLType._coverage(self).filter(
            coverage_quality__isnull=False).aggregate(a=Avg('coverage_quality'))['a']

    def resolve_last_coverage_date(self, info):
        row = (JournalistGQLType._coverage(self)
               .filter(reported=True, coverage_date__isnull=False)
               .order_by('-coverage_date').only('coverage_date').first())
        return row.coverage_date if row else None


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
    rejection_reason = graphene.String()
    approval_status = graphene.String()
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

    def resolve_rejection_reason(self, info):
        if not self.json_ext:
            return None
        return self.json_ext.get('approval_rejection_reason')

    def resolve_approval_status(self, info):
        if self.is_published:
            return None
        try:
            from django.contrib.contenttypes.models import ContentType
            from approval.models import ApprovalRequest
        except ImportError:
            return None
        request = ApprovalRequest.objects.filter(
            content_type=ContentType.objects.get_for_model(CommunicationPost),
            object_id=str(self.pk),
            is_deleted=False,
        ).order_by('-date_created').first()
        return request.status if request else None

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


# Comm-prefixed: graphene type names are global across every openIMIS module.
class CommMediumCountGQLType(graphene.ObjectType):
    medium = graphene.String()
    count = graphene.Int()


class CommScopeCountGQLType(graphene.ObjectType):
    scope = graphene.String()
    count = graphene.Int()


class CommGenderCountGQLType(graphene.ObjectType):
    gender = graphene.String()
    count = graphene.Int()


class CommStakeholderCountGQLType(graphene.ObjectType):
    stakeholder_type_id = graphene.String()
    stakeholder_name = graphene.String()
    planned = graphene.Int()
    attended = graphene.Int()


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
    coverage_invited = graphene.Int()
    coverage_reported = graphene.Int()
    coverage_rate = graphene.Float()
    avg_coverage_quality = graphene.Float()
    participants_total = graphene.Int()
    participants_attended = graphene.Int()
    attendance_rate = graphene.Float()
    participants_by_gender = graphene.List(CommGenderCountGQLType)
    participants_by_stakeholder = graphene.List(CommStakeholderCountGQLType)
    coverage_by_medium = graphene.List(CommMediumCountGQLType)
    coverage_by_scope = graphene.List(CommScopeCountGQLType)
    reach_by_level = graphene.List(CommReachGQLType)
