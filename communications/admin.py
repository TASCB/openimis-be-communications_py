from django.contrib import admin

from communications.models import (
    CommunicationActivity, ActivityCategory, Channel, ActivityChannel,
    ActivityObjective, ActivityAssignment, ActivityAttachment, ActivityFeedback,
    CommunicationTemplate, StakeholderList, StakeholderListEntry, LibraryAsset,
    StakeholderType, ActivityAudience, CommunicationPost,
)


@admin.register(ActivityCategory)
class ActivityCategoryAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active', 'is_deleted')
    search_fields = ('code', 'name')


@admin.register(Channel)
class ChannelAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'channel_type', 'is_active', 'is_deleted')
    search_fields = ('code', 'name')


@admin.register(CommunicationActivity)
class CommunicationActivityAdmin(admin.ModelAdmin):
    list_display = ('code', 'title', 'status', 'start_datetime', 'end_datetime', 'is_deleted')
    list_filter = ('status',)
    search_fields = ('code', 'title')


@admin.register(ActivityChannel)
class ActivityChannelAdmin(admin.ModelAdmin):
    list_display = ('activity', 'channel', 'dispatch_status', 'sent_at')


@admin.register(ActivityObjective)
class ActivityObjectiveAdmin(admin.ModelAdmin):
    list_display = ('activity', 'indicator', 'target_value', 'achieved_value')


@admin.register(ActivityAssignment)
class ActivityAssignmentAdmin(admin.ModelAdmin):
    list_display = ('activity', 'staff_user', 'role', 'status')


@admin.register(ActivityAttachment)
class ActivityAttachmentAdmin(admin.ModelAdmin):
    list_display = ('activity', 'file_name', 'file_type')


@admin.register(ActivityFeedback)
class ActivityFeedbackAdmin(admin.ModelAdmin):
    list_display = ('activity', 'channel', 'rating')


@admin.register(CommunicationTemplate)
class CommunicationTemplateAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'channel_type', 'is_active')
    search_fields = ('code', 'name')


@admin.register(StakeholderList)
class StakeholderListAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'is_active')
    search_fields = ('code', 'name')


@admin.register(StakeholderListEntry)
class StakeholderListEntryAdmin(admin.ModelAdmin):
    list_display = ('stakeholder_list', 'name', 'organization', 'email')
    search_fields = ('name', 'organization', 'email')


@admin.register(LibraryAsset)
class LibraryAssetAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'asset_type', 'is_active')
    search_fields = ('code', 'name')


@admin.register(StakeholderType)
class StakeholderTypeAdmin(admin.ModelAdmin):
    list_display = ('code', 'name', 'level', 'is_active')
    list_filter = ('level',)
    search_fields = ('code', 'name')


@admin.register(ActivityAudience)
class ActivityAudienceAdmin(admin.ModelAdmin):
    list_display = ('activity', 'stakeholder_type', 'planned_count', 'actual_count')


@admin.register(CommunicationPost)
class CommunicationPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'post_type', 'is_published', 'is_pinned', 'published_at')
    list_filter = ('post_type', 'is_published')
    search_fields = ('title',)
