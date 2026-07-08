"""Validation classes for Communications entities (openIMIS core validation mixins)."""
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from core.validation import BaseModelValidation, UniqueCodeValidationMixin, ObjectExistsValidationMixin
from core.validation.stringFieldValidationMixin import StringFieldValidationMixin

from communications.models import (
    CommunicationActivity, ActivityCategory, Channel, ActivityChannel,
    ActivityObjective, ActivityAssignment, ActivityAttachment, ActivityFeedback,
    CommunicationTemplate, StakeholderList, StakeholderListEntry, LibraryAsset,
    StakeholderType, ActivityAudience, CommunicationPost, CommunicationPostAttachment,
)


class _CodedValidation(BaseModelValidation, UniqueCodeValidationMixin,
                       ObjectExistsValidationMixin, StringFieldValidationMixin):
    """Shared create/update validation for entities carrying a unique ``code``."""

    @classmethod
    def validate_create(cls, user, **data):
        code = data.get('code', None)
        cls.validate_empty_string(code)
        cls.validate_unique_code_name(code)

    @classmethod
    def validate_update(cls, user, **data):
        id_ = data.get('id', None)
        cls.validate_object_exists(id_)
        code = data.get('code', None)
        if code:
            cls.validate_unique_code_name(code, id_)


class CommunicationActivityValidation(_CodedValidation):
    OBJECT_TYPE = CommunicationActivity

    @classmethod
    def validate_create(cls, user, **data):
        super().validate_create(user, **data)
        cls._validate_dates(data)

    @classmethod
    def validate_update(cls, user, **data):
        super().validate_update(user, **data)
        cls._validate_dates(data)

    @staticmethod
    def _validate_dates(data):
        start = data.get('start_datetime')
        end = data.get('end_datetime')
        if start and end and end < start:
            raise ValidationError(_("communications.validation.end_before_start"))


class ActivityCategoryValidation(_CodedValidation):
    OBJECT_TYPE = ActivityCategory


class ChannelValidation(_CodedValidation):
    OBJECT_TYPE = Channel


class CommunicationTemplateValidation(_CodedValidation):
    OBJECT_TYPE = CommunicationTemplate


class StakeholderListValidation(_CodedValidation):
    OBJECT_TYPE = StakeholderList


class LibraryAssetValidation(_CodedValidation):
    OBJECT_TYPE = LibraryAsset


class StakeholderTypeValidation(_CodedValidation):
    OBJECT_TYPE = StakeholderType


class ActivityAudienceValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = ActivityAudience

    @classmethod
    def validate_update(cls, user, **data):
        cls.validate_object_exists(data.get('id', None))


class CommunicationPostValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = CommunicationPost

    @classmethod
    def validate_update(cls, user, **data):
        cls.validate_object_exists(data.get('id', None))


class ActivityChannelValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = ActivityChannel

    @classmethod
    def validate_update(cls, user, **data):
        cls.validate_object_exists(data.get('id', None))


class ActivityObjectiveValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = ActivityObjective

    @classmethod
    def validate_update(cls, user, **data):
        cls.validate_object_exists(data.get('id', None))


class ActivityAssignmentValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = ActivityAssignment

    @classmethod
    def validate_create(cls, user, **data):
        if not data.get('staff_user_id') and not data.get('staff_user'):
            raise ValidationError(_("communications.validation.assignment_requires_staff"))

    @classmethod
    def validate_update(cls, user, **data):
        cls.validate_object_exists(data.get('id', None))


class ActivityAttachmentValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = ActivityAttachment


class CommunicationPostAttachmentValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = CommunicationPostAttachment


class ActivityFeedbackValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = ActivityFeedback

    @classmethod
    def validate_update(cls, user, **data):
        cls.validate_object_exists(data.get('id', None))


class StakeholderListEntryValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = StakeholderListEntry

    @classmethod
    def validate_update(cls, user, **data):
        cls.validate_object_exists(data.get('id', None))
