from django.test import TestCase
from django.utils import timezone

from core.test_helpers import LogInHelper

from communications.models import (
    ActivityParticipant, AttendanceStatus, CommunicationActivity, StakeholderList, StakeholderListEntry,
)
from communications.services import ActivityParticipantService


class AddParticipantsFromListTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = LogInHelper().get_or_create_user_api()
        name = cls.user.username
        now = timezone.now()
        cls.activity = CommunicationActivity(code='TST-LIST', title='List import', start_datetime=now, end_datetime=now)
        cls.activity.save(username=name)
        cls.stakeholders = StakeholderList(code='TST-SL', name='Regional media')
        cls.stakeholders.save(username=name)
        for member in [
            {'name': 'Asha Juma', 'organization': 'TBC', 'phone': '+255 712 345 678', 'email': 'asha@tbc.go.tz'},
            {'name': 'Baraka Mollel', 'organization': 'Mwananchi', 'phone': ''},
            {'name': 'Asha J.', 'organization': 'TBC', 'phone': '0712345678'},
        ]:
            StakeholderListEntry(stakeholder_list=cls.stakeholders, **member).save(username=name)
        removed = StakeholderListEntry(stakeholder_list=cls.stakeholders, name='Gone')
        removed.save(username=name)
        removed.delete(username=name)

    def _add(self):
        return ActivityParticipantService(self.user).add_from_stakeholder_list(self.activity.id, self.stakeholders.id)

    def _register(self):
        return ActivityParticipant.objects.filter(activity=self.activity, is_deleted=False)

    def test_members_are_invited_once_per_person(self):
        res = self._add()
        self.assertTrue(res['success'], res)
        self.assertEqual(res['data'], {'added': 2, 'skipped': 1})
        asha = self._register().get(full_name='Asha Juma')
        self.assertEqual((asha.organization, asha.email, asha.attendance_status),
                         ('TBC', 'asha@tbc.go.tz', AttendanceStatus.INVITED))

    def test_people_already_on_the_register_are_skipped(self):
        ActivityParticipant(activity=self.activity, full_name='baraka mollel', organization='MWANANCHI') \
            .save(username=self.user.username)
        self.assertEqual(self._add()['data'], {'added': 1, 'skipped': 2})
        self.assertEqual(self._add()['data'], {'added': 0, 'skipped': 3})
        self.assertEqual(self._register().count(), 2)

    def test_unknown_activity_is_refused(self):
        res = ActivityParticipantService(self.user).add_from_stakeholder_list(
            '00000000-0000-0000-0000-000000000000', self.stakeholders.id)
        self.assertFalse(res['success'])
