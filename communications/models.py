"""Communications management models."""
from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _

from core.models import HistoryModel, UUIDModel, ObjectMutation, MutationLog
from location.models import Location


class ActivityStatus(models.TextChoices):
    DRAFT = 'DRAFT', _('Draft')
    SUBMITTED = 'SUBMITTED', _('Submitted')
    APPROVED = 'APPROVED', _('Approved')
    REJECTED = 'REJECTED', _('Rejected')
    SCHEDULED = 'SCHEDULED', _('Scheduled')
    ONGOING = 'ONGOING', _('Ongoing')
    COMPLETED = 'COMPLETED', _('Completed')
    CLOSED = 'CLOSED', _('Closed')
    ARCHIVED = 'ARCHIVED', _('Archived')
    CANCELLED = 'CANCELLED', _('Cancelled')


TERMINAL_STATUSES = (ActivityStatus.CANCELLED, ActivityStatus.REJECTED,
                     ActivityStatus.CLOSED, ActivityStatus.ARCHIVED)


class ChannelType(models.TextChoices):
    EMAIL = 'EMAIL', _('Email')
    SMS = 'SMS', _('SMS')
    SOCIAL = 'SOCIAL', _('Social Media')
    RADIO = 'RADIO', _('Radio')
    TV = 'TV', _('Television')
    PRINT = 'PRINT', _('Print')
    WEB = 'WEB', _('Website / Portal')
    EVENT = 'EVENT', _('Community Event')
    OTHER = 'OTHER', _('Other')


class DispatchStatus(models.TextChoices):
    PENDING = 'PENDING', _('Pending')
    QUEUED = 'QUEUED', _('Queued')
    SENT = 'SENT', _('Sent')
    FAILED = 'FAILED', _('Failed')
    SKIPPED = 'SKIPPED', _('Skipped')


class AssignmentRole(models.TextChoices):
    OWNER = 'OWNER', _('Owner')
    CONTRIBUTOR = 'CONTRIBUTOR', _('Contributor')
    REVIEWER = 'REVIEWER', _('Reviewer')
    APPROVER = 'APPROVER', _('Approver')
    SUPPORT = 'SUPPORT', _('Support')


class AssignmentStatus(models.TextChoices):
    ASSIGNED = 'ASSIGNED', _('Assigned')
    CONFIRMED = 'CONFIRMED', _('Confirmed')
    DECLINED = 'DECLINED', _('Declined')
    REPLACED = 'REPLACED', _('Replaced')


class AssetType(models.TextChoices):
    TEMPLATE = 'TEMPLATE', _('Template')
    BRAND = 'BRAND', _('Brand Asset')
    IMAGE = 'IMAGE', _('Image')
    VIDEO = 'VIDEO', _('Video')
    DOCUMENT = 'DOCUMENT', _('Document')
    OTHER = 'OTHER', _('Other')


class ActivityType(models.TextChoices):
    MEDIA_MISSION = 'MEDIA_MISSION', _('Media Mission')
    PRESS_RELEASE = 'PRESS_RELEASE', _('Press Release')
    PRESS_CONFERENCE = 'PRESS_CONFERENCE', _('Press Conference')
    IMPACT_CASE_STUDY = 'IMPACT_CASE_STUDY', _('Impact Case Study')
    NEWSLETTER = 'NEWSLETTER', _('Newsletter')
    ANNUAL_REPORT = 'ANNUAL_REPORT', _('Annual Report')
    COMMUNITY_AWARENESS = 'COMMUNITY_AWARENESS', _('Community Awareness Session')
    STAKEHOLDER_BRIEFING = 'STAKEHOLDER_BRIEFING', _('Stakeholder Briefing')
    OTHER = 'OTHER', _('Other')


class StakeholderLevel(models.TextChoices):
    NATIONAL = 'NATIONAL', _('National')
    REGIONAL = 'REGIONAL', _('Regional')
    PAA = 'PAA', _('PAA (Project Area Authority)')
    COMMUNITY = 'COMMUNITY', _('Community')
    OTHER = 'OTHER', _('Other')


class PostType(models.TextChoices):
    ANNOUNCEMENT = 'ANNOUNCEMENT', _('Announcement')
    UPDATE = 'UPDATE', _('Update')
    MEDIA_HIGHLIGHT = 'MEDIA_HIGHLIGHT', _('Media Highlight')
    NEWSLETTER = 'NEWSLETTER', _('Newsletter')


class ActivityCategory(HistoryModel):
    """Programme / communication area an activity belongs to (configurable)."""
    code = models.CharField(max_length=255, blank=False, null=False)
    name = models.CharField(max_length=255, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['code']), models.Index(fields=['is_active'])]

    def __str__(self):
        return f'{self.code} - {self.name}'


class Channel(HistoryModel):
    """A reusable communication channel (Email, SMS, Social Media, ...)."""
    code = models.CharField(max_length=255, blank=False, null=False)
    name = models.CharField(max_length=255, blank=False, null=False)
    channel_type = models.CharField(
        max_length=20, choices=ChannelType.choices, default=ChannelType.OTHER)
    config = models.JSONField(blank=True, default=dict)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['code']), models.Index(fields=['channel_type']),
                   models.Index(fields=['is_active'])]

    def __str__(self):
        return f'{self.name} ({self.channel_type})'


class CommunicationActivity(HistoryModel):
    """A communication activity with a status workflow (Save / Close / Archive)."""
    code = models.CharField(max_length=255, blank=False, null=False)
    title = models.CharField(max_length=255, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    objective_summary = models.TextField(blank=True, null=True)
    category = models.ForeignKey(
        ActivityCategory, on_delete=models.DO_NOTHING, blank=True, null=True,
        related_name='activities')
    activity_type = models.CharField(
        max_length=30, choices=ActivityType.choices, default=ActivityType.OTHER)
    start_datetime = models.DateTimeField(blank=False, null=False)
    end_datetime = models.DateTimeField(blank=False, null=False)
    venue = models.CharField(max_length=255, blank=True, null=True)
    virtual_platform = models.CharField(max_length=255, blank=True, null=True)
    location = models.ForeignKey(
        Location, on_delete=models.DO_NOTHING, blank=True, null=True,
        related_name='communication_activities')
    target_audience = models.TextField(blank=True, null=True)
    planned_audience_count = models.IntegerField(blank=True, null=True)
    actual_audience_count = models.IntegerField(blank=True, null=True)
    media_houses_invited = models.IntegerField(blank=True, null=True)
    media_houses_reported = models.IntegerField(blank=True, null=True)
    status = models.CharField(
        max_length=20, choices=ActivityStatus.choices, default=ActivityStatus.DRAFT)

    class Meta:
        indexes = [
            models.Index(fields=['code']),
            models.Index(fields=['status']),
            models.Index(fields=['activity_type']),
            models.Index(fields=['start_datetime']),
            models.Index(fields=['end_datetime']),
            models.Index(fields=['category']),
            models.Index(fields=['location']),
        ]

    def __str__(self):
        return f'{self.code} - {self.title}'


class ActivityCodeSequence(UUIDModel):
    prefix = models.CharField(max_length=16, unique=True)
    last_number = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'tblCommunicationActivityCodeSequence'

    def __str__(self):
        return f'{self.prefix}{self.last_number:08}'


class ActivityChannel(HistoryModel):
    """A channel attached to an activity, carrying its own dispatch ("blast") state."""
    activity = models.ForeignKey(
        CommunicationActivity, on_delete=models.DO_NOTHING, related_name='channels')
    channel = models.ForeignKey(
        Channel, on_delete=models.DO_NOTHING, related_name='activity_channels')
    target = models.CharField(max_length=255, blank=True, null=True)
    dispatch_status = models.CharField(
        max_length=20, choices=DispatchStatus.choices, default=DispatchStatus.PENDING)
    dispatch_detail = models.JSONField(blank=True, default=dict)
    sent_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=['activity']), models.Index(fields=['channel']),
                   models.Index(fields=['dispatch_status'])]

    def __str__(self):
        return f'{self.channel_id} @ {self.activity_id}'


class ActivityObjective(HistoryModel):
    """A measurable objective for an activity; ``achieved_value`` is MIS-tracked."""
    activity = models.ForeignKey(
        CommunicationActivity, on_delete=models.DO_NOTHING, related_name='objectives')
    description = models.TextField(blank=False, null=False)
    indicator = models.CharField(max_length=255, blank=True, null=True)
    unit = models.CharField(max_length=100, blank=True, null=True)
    target_value = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)
    achieved_value = models.DecimalField(max_digits=18, decimal_places=2, blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=['activity'])]

    def __str__(self):
        return f'{self.indicator or self.description[:30]} @ {self.activity_id}'


class ActivityAssignment(HistoryModel):
    """A staff member assigned to an activity in a given role."""
    activity = models.ForeignKey(
        CommunicationActivity, on_delete=models.DO_NOTHING, related_name='assignments')
    staff_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, blank=True, null=True,
        related_name='communication_assignments')
    role = models.CharField(
        max_length=20, choices=AssignmentRole.choices, default=AssignmentRole.CONTRIBUTOR)
    status = models.CharField(
        max_length=20, choices=AssignmentStatus.choices, default=AssignmentStatus.ASSIGNED)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=['activity']), models.Index(fields=['staff_user']),
                   models.Index(fields=['role']), models.Index(fields=['status'])]

    def __str__(self):
        return f'{self.staff_user_id} @ {self.activity_id} ({self.role})'


class ActivityAttachment(HistoryModel):
    """A material/asset attached to an activity (file)."""
    activity = models.ForeignKey(
        CommunicationActivity, on_delete=models.DO_NOTHING, related_name='attachments')
    file_name = models.CharField(max_length=255, blank=False, null=False)
    file_type = models.CharField(max_length=100, blank=True, null=True)
    file = models.FileField(upload_to='communications/attachments/%Y/%m/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=['activity']), models.Index(fields=['file_type'])]

    def __str__(self):
        return self.file_name


class ActivityFeedback(HistoryModel):
    """Feedback recorded against an activity (the feedback loop)."""
    activity = models.ForeignKey(
        CommunicationActivity, on_delete=models.DO_NOTHING, related_name='feedback')
    channel = models.ForeignKey(
        Channel, on_delete=models.DO_NOTHING, blank=True, null=True,
        related_name='feedback')
    source = models.CharField(max_length=255, blank=True, null=True)
    respondent = models.CharField(max_length=255, blank=True, null=True)
    rating = models.IntegerField(blank=True, null=True)
    comment = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=['activity']), models.Index(fields=['channel'])]

    def __str__(self):
        return f'feedback @ {self.activity_id}'


class StakeholderType(HistoryModel):
    """A stakeholder/audience type within the multi-level taxonomy (seeded, configurable)."""
    code = models.CharField(max_length=255, blank=False, null=False)
    name = models.CharField(max_length=255, blank=False, null=False)
    level = models.CharField(
        max_length=20, choices=StakeholderLevel.choices, default=StakeholderLevel.OTHER)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['code']), models.Index(fields=['level']),
                   models.Index(fields=['is_active'])]

    def __str__(self):
        return f'{self.name} ({self.level})'


class ActivityAudience(HistoryModel):
    """An audience (stakeholder type) targeted by an activity, with planned/actual reach."""
    activity = models.ForeignKey(
        CommunicationActivity, on_delete=models.DO_NOTHING, related_name='audiences')
    stakeholder_type = models.ForeignKey(
        StakeholderType, on_delete=models.DO_NOTHING, blank=True, null=True,
        related_name='activity_audiences')
    planned_count = models.IntegerField(blank=True, null=True)
    actual_count = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=['activity']), models.Index(fields=['stakeholder_type'])]

    def __str__(self):
        return f'{self.stakeholder_type_id} @ {self.activity_id}'


class CommunicationPost(HistoryModel):
    """An internal feed post (announcement, update, media highlight, newsletter)."""
    title = models.CharField(max_length=255, blank=False, null=False)
    body = models.TextField(blank=True, null=True)
    post_type = models.CharField(
        max_length=20, choices=PostType.choices, default=PostType.ANNOUNCEMENT)
    activity = models.ForeignKey(
        CommunicationActivity, on_delete=models.DO_NOTHING, blank=True, null=True,
        related_name='posts')
    is_published = models.BooleanField(default=False)
    is_pinned = models.BooleanField(default=False)
    published_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        indexes = [models.Index(fields=['post_type']), models.Index(fields=['is_published']),
                   models.Index(fields=['published_at'])]

    def __str__(self):
        return f'{self.post_type}: {self.title}'


class CommunicationPostAttachment(HistoryModel):
    """A file attached to an internal feed post (view/download in the feed).

    ``is_inline`` marks images embedded inside the post body HTML (referenced by
    download URL). Inline images have no ``post`` until the post is saved, and are
    kept out of the attachment-card strip shown below the post.
    """
    post = models.ForeignKey(
        CommunicationPost, on_delete=models.DO_NOTHING, related_name='attachments',
        blank=True, null=True)
    file_name = models.CharField(max_length=255, blank=False, null=False)
    file_type = models.CharField(max_length=100, blank=True, null=True)
    file_size = models.BigIntegerField(blank=True, null=True)
    file = models.FileField(upload_to='communications/posts/%Y/%m/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_inline = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=['post']), models.Index(fields=['file_type'])]

    def __str__(self):
        return self.file_name


class AnnouncementDismissal(HistoryModel):
    """Marks an announcement as read by a user, so it is shown only once."""
    post = models.ForeignKey(
        CommunicationPost, on_delete=models.DO_NOTHING, related_name='dismissals')
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.DO_NOTHING, related_name='announcement_dismissals')
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['post', 'user']),
            models.Index(fields=['user', 'dismissed_at']),
        ]
        unique_together = [['post', 'user']]

    def __str__(self):
        return f'{self.user.username} dismissed post {self.post.id}'


class CommunicationTemplate(HistoryModel):
    """A reusable message template for a channel type."""
    code = models.CharField(max_length=255, blank=False, null=False)
    name = models.CharField(max_length=255, blank=False, null=False)
    channel_type = models.CharField(
        max_length=20, choices=ChannelType.choices, default=ChannelType.OTHER)
    subject = models.CharField(max_length=255, blank=True, null=True)
    body = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['code']), models.Index(fields=['channel_type']),
                   models.Index(fields=['is_active'])]

    def __str__(self):
        return f'{self.code} - {self.name}'


class StakeholderList(HistoryModel):
    """A reusable list of stakeholders/recipients."""
    code = models.CharField(max_length=255, blank=False, null=False)
    name = models.CharField(max_length=255, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['code']), models.Index(fields=['is_active'])]

    def __str__(self):
        return f'{self.code} - {self.name}'


class StakeholderListEntry(HistoryModel):
    """A single stakeholder within a list."""
    stakeholder_list = models.ForeignKey(
        StakeholderList, on_delete=models.DO_NOTHING, related_name='entries')
    name = models.CharField(max_length=255, blank=False, null=False)
    organization = models.CharField(max_length=255, blank=True, null=True)
    email = models.CharField(max_length=255, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    location = models.ForeignKey(
        Location, on_delete=models.DO_NOTHING, blank=True, null=True,
        related_name='stakeholder_entries')

    class Meta:
        indexes = [models.Index(fields=['stakeholder_list'])]

    def __str__(self):
        return f'{self.name} @ {self.stakeholder_list_id}'


class LibraryAsset(HistoryModel):
    """A reusable communication asset (file) in the central library."""
    code = models.CharField(max_length=255, blank=False, null=False)
    name = models.CharField(max_length=255, blank=False, null=False)
    asset_type = models.CharField(
        max_length=20, choices=AssetType.choices, default=AssetType.DOCUMENT)
    file_name = models.CharField(max_length=255, blank=True, null=True)
    file_type = models.CharField(max_length=100, blank=True, null=True)
    file = models.FileField(upload_to='communications/library/%Y/%m/', blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        indexes = [models.Index(fields=['code']), models.Index(fields=['asset_type']),
                   models.Index(fields=['is_active'])]

    def __str__(self):
        return f'{self.code} - {self.name}'


class CommunicationActivityMutation(UUIDModel, ObjectMutation):
    communication_activity = models.ForeignKey(CommunicationActivity, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='communication_activities')


class ActivityCategoryMutation(UUIDModel, ObjectMutation):
    activity_category = models.ForeignKey(ActivityCategory, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='activity_categories')


class ChannelMutation(UUIDModel, ObjectMutation):
    channel = models.ForeignKey(Channel, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='channels')


class ActivityChannelMutation(UUIDModel, ObjectMutation):
    activity_channel = models.ForeignKey(ActivityChannel, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='activity_channels')


class ActivityObjectiveMutation(UUIDModel, ObjectMutation):
    activity_objective = models.ForeignKey(ActivityObjective, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='activity_objectives')


class ActivityAssignmentMutation(UUIDModel, ObjectMutation):
    activity_assignment = models.ForeignKey(ActivityAssignment, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='activity_assignments')


class ActivityAttachmentMutation(UUIDModel, ObjectMutation):
    activity_attachment = models.ForeignKey(ActivityAttachment, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='activity_attachments')


class ActivityFeedbackMutation(UUIDModel, ObjectMutation):
    activity_feedback = models.ForeignKey(ActivityFeedback, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='activity_feedback')


class CommunicationTemplateMutation(UUIDModel, ObjectMutation):
    communication_template = models.ForeignKey(CommunicationTemplate, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='communication_templates')


class StakeholderListMutation(UUIDModel, ObjectMutation):
    stakeholder_list = models.ForeignKey(StakeholderList, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='stakeholder_lists')


class StakeholderListEntryMutation(UUIDModel, ObjectMutation):
    stakeholder_list_entry = models.ForeignKey(StakeholderListEntry, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='stakeholder_list_entries')


class LibraryAssetMutation(UUIDModel, ObjectMutation):
    library_asset = models.ForeignKey(LibraryAsset, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='library_assets')


class StakeholderTypeMutation(UUIDModel, ObjectMutation):
    stakeholder_type = models.ForeignKey(StakeholderType, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='stakeholder_types')


class ActivityAudienceMutation(UUIDModel, ObjectMutation):
    activity_audience = models.ForeignKey(ActivityAudience, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='activity_audiences')


class CommunicationPostMutation(UUIDModel, ObjectMutation):
    communication_post = models.ForeignKey(CommunicationPost, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='communication_posts')


class CommunicationPostAttachmentMutation(UUIDModel, ObjectMutation):
    communication_post_attachment = models.ForeignKey(CommunicationPostAttachment, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='communication_post_attachments')


class AnnouncementDismissalMutation(UUIDModel, ObjectMutation):
    announcement_dismissal = models.ForeignKey(AnnouncementDismissal, models.DO_NOTHING, related_name='mutations')
    mutation = models.ForeignKey(MutationLog, models.DO_NOTHING, related_name='announcement_dismissals')
