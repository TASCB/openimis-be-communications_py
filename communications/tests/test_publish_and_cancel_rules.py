from unittest import mock

from django.core.exceptions import PermissionDenied
from django.test import TestCase
from django.utils import timezone

from core.test_helpers import LogInHelper

from communications.gql_mutations import CancelActivityMutation, ScheduleActivityMutation
from communications.models import ActivityStatus, CommunicationActivity, CommunicationPost
from communications.services import CommunicationActivityService, CommunicationPostService

FLOW = 'COMMUNICATION_POST_APPROVAL'


def _rights(user, held):
    return mock.patch.object(type(user), 'has_perms', lambda self, perms, *a, **k: all(str(p) in held for p in perms))


def _admin(user, value):
    return mock.patch.object(type(user), 'is_imis_admin', new_callable=mock.PropertyMock, return_value=value)


class PostPublishRuleTest(TestCase):
    """The publish button never skips the approval flow (except for the IMIS administrator)."""

    @classmethod
    def setUpTestData(cls):
        cls.writer = LogInHelper().get_or_create_user_api(username='tst_comms_post_writer')
        cls.publisher = LogInHelper().get_or_create_user_api()

    def setUp(self):
        self.post = CommunicationPost(title='Draft notice', body='<p>x</p>')
        self.post.save(username=self.writer.username)

    def _publish(self, user):
        return CommunicationPostService(user).set_published(self.post.id, True)

    def _submit(self):
        self.assertTrue(CommunicationPostService(self.writer).submit_for_approval(self.post.id))
        from approval.models import ApprovalRequest
        req = ApprovalRequest.objects.filter(object_id=str(self.post.id)).order_by('-date_created').first()
        return req, req.steps.filter(status='PENDING').first()

    def test_draft_never_submitted_cannot_be_published(self):
        with _admin(self.publisher, False):
            res = self._publish(self.publisher)
        self.assertFalse(res['success'])
        self.post.refresh_from_db()
        self.assertFalse(self.post.is_published)

    def test_administrator_may_publish_a_draft(self):
        with _admin(self.publisher, True):
            self.assertTrue(self._publish(self.publisher)['success'])

    def test_pending_post_is_refused_even_for_the_administrator(self):
        self._submit()
        with _admin(self.publisher, True):
            res = self._publish(self.publisher)
        self.assertFalse(res['success'])
        self.assertIn('waiting for approval', res['message'])

    def test_approved_post_can_be_republished_until_the_writer_edits_it(self):
        from approval.services import ApprovalService
        req, step = self._submit()
        self.assertTrue(ApprovalService(self.publisher).approve(req.id, step.id, comment='ok')['success'])
        service = CommunicationPostService(self.publisher)
        self.assertTrue(service.set_published(self.post.id, False)['success'])
        with _admin(self.publisher, False):
            self.assertTrue(self._publish(self.publisher)['success'])
            with _rights(self.writer, set()):
                CommunicationPostService(self.writer).update(
                    {'id': self.post.id, 'title': 'Draft notice', 'body': '<p>new wording</p>'})
            self.post.refresh_from_db()
            self.assertFalse(self.post.is_published)
            self.assertTrue(self.post.json_ext.get('needs_approval'))
            self.assertFalse(self._publish(self.publisher)['success'])

    def test_reject_comment_reaches_the_post(self):
        from approval.services import ApprovalService
        req, step = self._submit()
        self.assertTrue(ApprovalService(self.publisher).reject(req.id, step.id, comment='Fix the wording')['success'])
        self.post.refresh_from_db()
        self.assertEqual(self.post.json_ext.get('approval_rejection_reason'), 'Fix the wording')


class CancelAndLockRuleTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = LogInHelper().get_or_create_user_api()
        now = timezone.now()
        cls.activity = CommunicationActivity(code='TST-CANCEL', title='Plan', start_datetime=now, end_datetime=now,
                                             status=ActivityStatus.SCHEDULED)
        cls.activity.save(username=cls.user.username)

    def test_approver_without_edit_right_may_cancel(self):
        with _rights(self.user, {'220110'}):
            CancelActivityMutation._validate_mutation(self.user, id=self.activity.id)
            with self.assertRaises(PermissionDenied):
                ScheduleActivityMutation._validate_mutation(self.user, id=self.activity.id)
            self.assertTrue(CommunicationActivityService(self.user).transition(self.activity.id, 'cancel')['success'])

    def test_approver_without_edit_right_cannot_cancel_a_draft(self):
        CommunicationActivity.objects.filter(id=self.activity.id).update(status=ActivityStatus.DRAFT)
        with _rights(self.user, {'220110'}):
            self.assertFalse(CommunicationActivityService(self.user).transition(self.activity.id, 'cancel')['success'])

    def test_locked_edit_says_locked(self):
        CommunicationActivity.objects.filter(id=self.activity.id).update(status=ActivityStatus.SUBMITTED)
        res = CommunicationActivityService(self.user).update({'id': self.activity.id, 'title': 'Renamed'})
        self.assertFalse(res['success'])
        self.assertIn('submitted', res['message'])
