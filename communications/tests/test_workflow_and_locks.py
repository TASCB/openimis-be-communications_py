from decimal import Decimal
from types import SimpleNamespace
from unittest import mock

from django.test import TestCase
from django.utils import timezone

from core.test_helpers import LogInHelper

from communications.models import (
    ActivityChannel, ActivityFeedback, ActivityObjective, ActivityStatus, Channel, CommunicationActivity,
    CommunicationPost, CommunicationPostAttachment, DispatchStatus,
)
from communications.services import (
    ActivityChannelService, ActivityFeedbackService, ActivityObjectiveService, CommunicationActivityService,
    CommunicationPostService,
)
from communications.views import upload_error


def _no_rights(user):
    return mock.patch.object(type(user), 'has_perms', lambda self, perms, *a, **k: False)


class ActivityLockTest(TestCase):
    """The plan freezes at Submit; results stay open until the activity is archived or cancelled."""

    @classmethod
    def setUpTestData(cls):
        cls.user = LogInHelper().get_or_create_user_api()
        now = timezone.now()
        cls.activity = CommunicationActivity(code='TST-LOCK', title='Plan', start_datetime=now, end_datetime=now)
        cls.activity.save(username=cls.user.username)
        cls.channel = Channel.objects.filter(is_deleted=False).first() or Channel(code='TST-CH', name='Radio')
        if not cls.channel.id:
            cls.channel.save(username=cls.user.username)

    def _status(self, status):
        CommunicationActivity.objects.filter(id=self.activity.id).update(status=status)

    def test_objective_result_can_be_recorded_after_submit_but_not_the_plan(self):
        res = ActivityObjectiveService(self.user).create(
            {'activity_id': self.activity.id, 'description': 'Reach editors', 'target_value': 10})
        self.assertTrue(res['success'], res)
        self._status(ActivityStatus.COMPLETED)
        res = ActivityObjectiveService(self.user).update(
            {'id': res['data']['id'], 'description': 'Changed', 'target_value': 99, 'achieved_value': 7})
        self.assertTrue(res['success'], res)
        objective = ActivityObjective.objects.get(activity=self.activity)
        self.assertEqual((objective.description, objective.target_value, objective.achieved_value),
                         ('Reach editors', Decimal('10'), Decimal('7')))
        res = ActivityObjectiveService(self.user).create({'activity_id': self.activity.id, 'description': 'Late'})
        self.assertFalse(res['success'])

    def test_feedback_open_after_the_event_closed_when_archived(self):
        self._status(ActivityStatus.COMPLETED)
        self.assertTrue(ActivityFeedbackService(self.user).create(
            {'activity_id': self.activity.id, 'comment': 'Useful', 'rating': 4})['success'])
        self._status(ActivityStatus.ARCHIVED)
        self.assertFalse(ActivityFeedbackService(self.user).create(
            {'activity_id': self.activity.id, 'comment': 'Too late'})['success'])
        self.assertEqual(ActivityFeedback.objects.filter(activity=self.activity).count(), 1)

    def test_channels_are_planning_data(self):
        self._status(ActivityStatus.APPROVED)
        res = ActivityChannelService(self.user).create({'activity_id': self.activity.id, 'channel_id': self.channel.id})
        self.assertFalse(res['success'])

    def test_activity_update_after_submit_keeps_the_plan_and_status(self):
        self._status(ActivityStatus.COMPLETED)
        res = CommunicationActivityService(self.user).update(
            {'id': self.activity.id, 'title': 'Renamed', 'actual_audience_count': 42, 'status': 'DRAFT'})
        self.assertTrue(res['success'], res)
        self.activity.refresh_from_db()
        self.assertEqual((self.activity.title, self.activity.actual_audience_count, self.activity.status),
                         ('Plan', 42, ActivityStatus.COMPLETED))


class TransitionRulesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.maker = LogInHelper().get_or_create_user_api()
        cls.checker = LogInHelper().get_or_create_user_api(username='tst_comms_checker')
        now = timezone.now()
        cls.activity = CommunicationActivity(code='TST-FLOW', title='Flow', start_datetime=now, end_datetime=now,
                                             status=ActivityStatus.SUBMITTED)
        cls.activity.save(username=cls.maker.username)
        channel = Channel.objects.filter(is_deleted=False).first()
        if channel is None:
            channel = Channel(code='TST-CH2', name='SMS')
            channel.save(username=cls.maker.username)
        cls.activity_channel = ActivityChannel(activity=cls.activity, channel=channel)
        cls.activity_channel.save(username=cls.maker.username)

    def test_creator_cannot_approve_own_activity(self):
        res = CommunicationActivityService(self.maker).transition(self.activity.id, 'approve')
        self.assertFalse(res['success'])
        res = CommunicationActivityService(self.checker).transition(self.activity.id, 'approve')
        self.assertTrue(res['success'], res)

    def test_cancel_after_approval_needs_an_approver(self):
        CommunicationActivity.objects.filter(id=self.activity.id).update(status=ActivityStatus.SCHEDULED)
        with _no_rights(self.maker):
            self.assertFalse(CommunicationActivityService(self.maker).transition(self.activity.id, 'cancel')['success'])
        self.assertTrue(CommunicationActivityService(self.maker).transition(self.activity.id, 'cancel')['success'])

    def test_channel_marked_sent_only_once_scheduled(self):
        service = CommunicationActivityService(self.maker)
        self.assertFalse(service.dispatch_channel(self.activity_channel.id)['success'])
        CommunicationActivity.objects.filter(id=self.activity.id).update(status=ActivityStatus.SCHEDULED)
        self.assertTrue(service.dispatch_channel(self.activity_channel.id)['success'])
        self.activity_channel.refresh_from_db()
        self.assertEqual(self.activity_channel.dispatch_status, DispatchStatus.SENT)
        self.assertTrue(self.activity_channel.dispatch_detail.get('manual'))


class PostRulesTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = LogInHelper().get_or_create_user_api()
        cls.post = CommunicationPost(title='Notice', body='<p>Old</p>', is_published=True,
                                     published_at=timezone.now())
        cls.post.save(username=cls.user.username)

    def test_writer_edit_of_published_post_goes_back_for_approval(self):
        with _no_rights(self.user):
            res = CommunicationPostService(self.user).update(
                {'id': self.post.id, 'title': 'Notice', 'body': '<p>New</p>', 'is_pinned': True})
        self.assertTrue(res['success'], res)
        self.post.refresh_from_db()
        self.assertEqual((self.post.is_published, self.post.is_pinned), (False, False))

    def test_publisher_edit_keeps_post_published(self):
        res = CommunicationPostService(self.user).update({'id': self.post.id, 'body': '<p>Fixed typo</p>'})
        self.assertTrue(res['success'], res)
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_published)

    def test_inline_images_are_linked_to_their_post(self):
        image = CommunicationPostAttachment(file_name='a.png', is_inline=True)
        image.save(username=self.user.username)
        body = f'<p><img src="/api/communications/post-attachments/{image.id}/download/?inline=1"></p>'
        self.assertTrue(CommunicationPostService(self.user).update({'id': self.post.id, 'body': body})['success'])
        image.refresh_from_db()
        self.assertEqual(image.post_id, self.post.id)

    def test_pin_and_unpin(self):
        service = CommunicationPostService(self.user)
        self.assertTrue(service.set_pinned(self.post.id, True)['success'])
        self.post.refresh_from_db()
        self.assertTrue(self.post.is_pinned)
        service.set_pinned(self.post.id, False)
        self.post.refresh_from_db()
        self.assertFalse(self.post.is_pinned)


class UploadCheckTest(TestCase):
    def test_type_and_size(self):
        self.assertIsNone(upload_error(SimpleNamespace(name='report.PDF', size=1024)))
        self.assertIn('not allowed', upload_error(SimpleNamespace(name='run.exe', size=10)))
        self.assertIn('larger than', upload_error(SimpleNamespace(name='video.mp4', size=500 * 1024 * 1024)))


class FeedVisibilityTest(TestCase):
    """A writer sees their own unpublished posts (to submit them); other people's drafts stay hidden."""

    @classmethod
    def setUpTestData(cls):
        cls.writer = LogInHelper().get_or_create_user_api(username='tst_comms_writer')
        cls.other = LogInHelper().get_or_create_user_api()
        for title, user, published in (('Mine', cls.writer, False), ('Theirs', cls.other, False),
                                       ('Public', cls.other, True)):
            CommunicationPost(title=title, is_published=published).save(username=user.username)

    def _titles(self, user):
        from graphene.test import Client
        from openIMIS.schema import schema
        from django.test import RequestFactory
        context = RequestFactory().post('/api/graphql')
        context.user = user
        with mock.patch.object(type(user), 'has_perms', lambda self, perms, *a, **k: '221505' not in perms):
            res = Client(schema).execute('{ communicationPost { edges { node { title } } } }', context_value=context)
        self.assertNotIn('errors', res, res)
        return {e['node']['title'] for e in res['data']['communicationPost']['edges']}

    def test_writer_sees_own_draft_only(self):
        titles = self._titles(self.writer)
        self.assertIn('Mine', titles)
        self.assertIn('Public', titles)
        self.assertNotIn('Theirs', titles)
