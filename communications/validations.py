"""Validation classes for Communications entities (openIMIS core validation mixins)."""
from django.core.exceptions import ValidationError
from django.db.models import Q
from django.utils.translation import gettext as _

from core.validation import BaseModelValidation, UniqueCodeValidationMixin, ObjectExistsValidationMixin
from core.validation.stringFieldValidationMixin import StringFieldValidationMixin

from communications.models import (
    CommunicationActivity, ActivityCategory, Channel, ActivityChannel,
    ActivityObjective, ActivityAssignment, ActivityAttachment, ActivityFeedback,
    CommunicationTemplate, StakeholderList, StakeholderListEntry, LibraryAsset,
    StakeholderType, ActivityAudience, CommunicationPost, CommunicationPostAttachment,
    MediaHouseCategory, MediaHouse, Journalist, ActivityMediaHouse, ActivityParticipant,
    RATING_MIN, RATING_MAX,
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
        code = data.get('code', None)
        if code:
            cls.validate_empty_string(code)
            cls.validate_unique_code_name(code)
        cls._validate_dates(data)

    @classmethod
    def validate_update(cls, user, **data):
        id_ = data.get('id', None)
        cls.validate_object_exists(id_)
        if 'code' in data:
            existing = CommunicationActivity.objects.filter(id=id_).only('code').first()
            if existing and data.get('code') != existing.code:
                raise ValidationError(_("communications.validation.code_immutable"))
            if data.get('code'):
                cls.validate_unique_code_name(data.get('code'), id_)
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


def _validate_affiliation(journalist_id, media_house_id, error_key):
    """A journalist may only be linked to a house they actually work for.

    Freelancers (no affiliation recorded) are allowed anywhere — that is the point of the
    freelance flag. Only a *conflicting* affiliation is rejected: crediting Clouds FM's reporter
    with Mwananchi's story would silently corrupt both the house's and the person's derived stats.
    """
    if not journalist_id or not media_house_id:
        return
    journalist = Journalist.objects.filter(id=journalist_id, is_deleted=False).first()
    if not journalist or journalist.media_house_id is None:
        return
    if str(journalist.media_house_id) != str(media_house_id):
        raise ValidationError(_(error_key))


def _validate_rating(value, field='rating'):
    """Ratings are 1..RATING_MAX. A plain nullable IntegerField accepts 0, -3 or 99 silently,
    which then poisons any average computed over it."""
    if value is None:
        return
    if not isinstance(value, int) or isinstance(value, bool) or not RATING_MIN <= value <= RATING_MAX:
        raise ValidationError(_("communications.validation.rating_out_of_range"))


class _GeneratedCodeValidation(_CodedValidation):
    """For registries whose ``code`` the service generates (MH00001 / MJ00001).

    The code is absent on create and must not be edited afterwards — a hand-edited code would
    collide with a later sequence value.
    """

    @classmethod
    def validate_create(cls, user, **data):
        code = data.get('code', None)
        if code:
            cls.validate_empty_string(code)
            cls.validate_unique_code_name(code)

    @classmethod
    def validate_update(cls, user, **data):
        id_ = data.get('id', None)
        cls.validate_object_exists(id_)
        if 'code' in data and data.get('code'):
            existing = cls.OBJECT_TYPE.objects.filter(id=id_).only('code').first()
            if existing and data.get('code') != existing.code:
                raise ValidationError(_("communications.validation.code_immutable"))


class MediaHouseCategoryValidation(_CodedValidation):
    OBJECT_TYPE = MediaHouseCategory


class MediaHouseValidation(_GeneratedCodeValidation):
    OBJECT_TYPE = MediaHouse

    @classmethod
    def validate_create(cls, user, **data):
        super().validate_create(user, **data)
        cls._validate_primary_contact(data)

    @classmethod
    def validate_update(cls, user, **data):
        super().validate_update(user, **data)
        cls._validate_primary_contact(data, house_id=data.get('id'))

    @staticmethod
    def _validate_primary_contact(data, house_id=None):
        _validate_affiliation(data.get('primary_contact_id'), house_id,
                              "communications.validation.contact_not_at_house")


class JournalistValidation(_GeneratedCodeValidation):
    """Coded validation plus a duplicate-person guard.

    The same stringer gets entered by officers in several regions, so a match on full name
    *and* a contact detail is rejected. Name alone is not enough (namesakes) and a contact
    detail alone is not enough (newsrooms share a desk phone and a generic inbox).
    """
    OBJECT_TYPE = Journalist

    @classmethod
    def validate_create(cls, user, **data):
        super().validate_create(user, **data)
        cls._validate_not_duplicate(data)

    @classmethod
    def validate_update(cls, user, **data):
        super().validate_update(user, **data)
        cls._validate_not_duplicate(data, exclude_id=data.get('id', None))

    @staticmethod
    def _validate_not_duplicate(data, exclude_id=None):
        first, last = data.get('first_name'), data.get('last_name')
        if not first or not last:
            return
        contacts = [c for c in (data.get('phone'), data.get('email')) if c]
        if not contacts:
            return
        qs = Journalist.objects.filter(
            first_name__iexact=first, last_name__iexact=last,
            is_deleted=False, is_active=True)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        match = Q()
        for contact in contacts:
            match |= Q(phone__iexact=contact) | Q(email__iexact=contact)
        if qs.filter(match).exists():
            raise ValidationError(_("communications.validation.duplicate_journalist"))


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


class ActivityParticipantValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = ActivityParticipant

    @classmethod
    def validate_create(cls, user, **data):
        cls._validate_not_duplicate(data)

    @classmethod
    def validate_update(cls, user, **data):
        cls.validate_object_exists(data.get('id', None))
        cls._validate_not_duplicate(data, exclude_id=data.get('id', None))

    @staticmethod
    def _validate_not_duplicate(data, exclude_id=None):
        """One person, one row per activity.

        Name alone would reject genuine namesakes on a 100-person register, so a contact detail
        must match too — the same rule the journalist registry uses.
        """
        activity_id, name = data.get('activity_id'), data.get('full_name')
        if not activity_id or not name:
            return
        contacts = [c for c in (data.get('phone'), data.get('email')) if c]
        if not contacts:
            return
        qs = ActivityParticipant.objects.filter(
            activity_id=activity_id, full_name__iexact=name, is_deleted=False)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        match = Q()
        for c in contacts:
            match |= Q(phone__iexact=c) | Q(email__iexact=c)
        if qs.filter(match).exists():
            raise ValidationError(_("communications.validation.duplicate_participant"))


class ActivityMediaHouseValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = ActivityMediaHouse

    @classmethod
    def validate_create(cls, user, **data):
        _validate_rating(data.get('coverage_quality'), 'coverage_quality')
        cls._validate_not_already_linked(data)
        _validate_affiliation(data.get('journalist_id'), data.get('media_house_id'),
                              "communications.validation.journalist_not_at_house")

    @classmethod
    def validate_update(cls, user, **data):
        cls.validate_object_exists(data.get('id', None))
        _validate_rating(data.get('coverage_quality'), 'coverage_quality')
        cls._validate_not_already_linked(data, exclude_id=data.get('id', None))
        _validate_affiliation(data.get('journalist_id'), data.get('media_house_id'),
                              "communications.validation.journalist_not_at_house")

    @staticmethod
    def _validate_not_already_linked(data, exclude_id=None):
        activity_id, house_id = data.get('activity_id'), data.get('media_house_id')
        if not activity_id or not house_id:
            return
        qs = ActivityMediaHouse.objects.filter(
            activity_id=activity_id, media_house_id=house_id, is_deleted=False)
        if exclude_id:
            qs = qs.exclude(id=exclude_id)
        if qs.exists():
            raise ValidationError(_("communications.validation.media_house_already_linked"))


class ActivityFeedbackValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = ActivityFeedback

    @classmethod
    def validate_create(cls, user, **data):
        _validate_rating(data.get('rating'))

    @classmethod
    def validate_update(cls, user, **data):
        cls.validate_object_exists(data.get('id', None))
        _validate_rating(data.get('rating'))


class StakeholderListEntryValidation(BaseModelValidation, ObjectExistsValidationMixin):
    OBJECT_TYPE = StakeholderListEntry

    @classmethod
    def validate_update(cls, user, **data):
        cls.validate_object_exists(data.get('id', None))
