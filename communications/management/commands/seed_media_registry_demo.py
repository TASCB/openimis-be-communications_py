"""Seed demonstration activities and media coverage.

Every row carries ``json_ext['_seed'] = 'demo'`` so ``--purge`` can remove the whole set
without touching real registry entries.

Data provenance — read before treating any of this as reference data:
  * Media-house **names** are real Tanzanian outlets (public knowledge).
  * Every **contact detail is a placeholder**. No phone number, address or inbox here belongs
    to the real organisation; they follow the +255 700 000 0xx / *.example reserved patterns.
  * **Journalists are entirely fictional.** Real named journalists are private individuals and
    do not belong in invented demo records.
"""
import re
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import transaction

from core.models import User
from location.models import Location
from communications.models import (
    MediaHouseCategory, MediaHouse, Journalist, ActivityMediaHouse, CommunicationActivity,
    ActivityCategory, ActivityObjective, ActivityAudience, StakeholderType,
)
from communications.services import (
    MediaHouseCategoryService, MediaHouseService, JournalistService,
    ActivityMediaHouseService, CommunicationActivityService,
)

DEMO = {'_seed': 'demo'}

# Categories beyond the three the client specified, so the demo exercises the whole medium axis.
EXTRA_CATEGORIES = [
    ('TV_GENERAL', 'Television - General', 'TV', 'NATIONAL'),
    ('ONLINE', 'Online / Digital', 'ONLINE', 'NATIONAL'),
]


# Demo activities to hang coverage on (the dev DB has only a couple of test drafts).
# (title, activity_type, district, days_ago, venue)
DEMO_ACTIVITIES = [
    ('National PSSN II Launch', 'PRESS_CONFERENCE', 'Ilala MC', 95, 'JNICC, Dar es Salaam'),
    ('Annual Report 2025 Launch', 'ANNUAL_REPORT', 'Dodoma CC', 70, 'TASAF HQ, Dodoma'),
    ('Kagera Media Mission', 'MEDIA_MISSION', 'Karagwe', 55, 'Karagwe District'),
    ('Njombe Community Awareness Drive', 'COMMUNITY_AWARENESS', 'Njombe', 40, 'Njombe Town'),
    ('Simanjiro Pastoralist Briefing', 'STAKEHOLDER_BRIEFING', 'Simanjiro', 28, 'Orkesumet'),
    ('Mwanza Impact Case Study Release', 'IMPACT_CASE_STUDY', 'Mwanza CC', 12, 'Mwanza City'),
]

# One activity per lifecycle status so the list, filters and previews have something to show.
# (title, type, category, status, district, start offset in days (negative = past), days, venue,
#  planned audience, actual audience, objectives [(description, indicator, unit, target, achieved)],
#  audiences [(stakeholder type, planned, actual)], description)
DEMO_PIPELINE = [
    ('Dodoma Regional Payment Awareness Tour', 'COMMUNITY_AWARENESS', 'PAYMENT_COMMS', 'DRAFT',
     'Dodoma CC', 45, 3, 'Dodoma Region PAAs', 600, None,
     [('Explain the e-payment channels to beneficiaries', 'Beneficiaries reached', 'people', 600, None)],
     [('BENEFICIARIES', 500, None), ('VEO', 60, None), ('CMC', 40, None)],
     'Village meetings on how payments move to mobile money and bank accounts.'),
    ('Enrollment Communication Radio Series', 'MEDIA_MISSION', 'ENROLLMENT_COMMS', 'SUBMITTED',
     'Ilala MC', 30, 5, 'TBC FM studios', 0, None,
     [('Air five radio episodes on enrollment', 'Episodes aired', 'episodes', 5, None),
      ('Answer listener questions live', 'Questions answered', 'questions', 50, None)],
     [('PUBLIC', 0, None), ('JOURNALIST', 6, None)],
     'Weekly radio programme explaining who qualifies and how enrollment works.'),
    ('Grievance Mechanism Stakeholder Briefing', 'STAKEHOLDER_BRIEFING', 'GRIEVANCE_COMMS', 'APPROVED',
     'Mwanza CC', 21, 1, 'Mwanza Regional Office', 80, None,
     [('Brief council officers on the GRM channels', 'Officers briefed', 'people', 80, None)],
     [('DED', 8, None), ('TMO', 20, None), ('DAS', 8, None)],
     'Half-day briefing on grievance intake, escalation and response timelines.'),
    ('Social Media Campaign: Mafanikio ya Kaya', 'SOCIAL_MEDIA', 'PUBLIC_RELATIONS', 'REJECTED',
     'Ilala MC', 14, 30, 'Online', 0, None,
     [('Publish beneficiary success stories', 'Posts published', 'posts', 20, None)],
     [('PUBLIC', 0, None)],
     'Month-long campaign of household success stories; returned for consent forms.'),
    ('Kigoma Community Awareness Sessions', 'COMMUNITY_AWARENESS', 'AWARENESS', 'SCHEDULED',
     'Kigoma MC', 7, 4, 'Kigoma District villages', 900, None,
     [('Hold awareness sessions in 12 villages', 'Villages covered', 'villages', 12, None),
      ('Register attendance at every session', 'Attendees', 'people', 900, None)],
     [('BENEFICIARIES', 700, None), ('VILLAGE_COUNCIL', 120, None), ('LSP', 80, None)],
     'Sessions on programme rules, co-responsibilities and the grievance channels.'),
    ('Arusha Media House Visits', 'MEDIA_HOUSE_VISIT', 'MEDIA_ENGAGEMENT', 'ONGOING',
     'Arusha CC', -1, 3, 'Arusha City', 25, 18,
     [('Visit the main Arusha newsrooms', 'Newsrooms visited', 'visits', 6, 4)],
     [('EDITOR', 8, 6), ('JOURNALIST', 17, 12)],
     'Newsroom visits to share the PSSN story pipeline and contact points.'),
    ('Economic Inclusion Newsletter Q2', 'NEWSLETTER', 'ECONOMIC_INCLUSION', 'COMPLETED',
     'Dodoma CC', -35, 1, 'TASAF HQ, Dodoma', 2000, 2350,
     [('Distribute the quarterly newsletter', 'Copies distributed', 'copies', 2000, 2350)],
     [('STAFF', 400, 450), ('NATIONAL_DIRECTORATE', 100, 90), ('PUBLIC', 1500, 1810)],
     'Quarterly newsletter on savings groups and livelihood grants.'),
    ('PCT Results Press Release', 'PRESS_RELEASE', 'CONTENT_REPORTING', 'CLOSED',
     'Dodoma CC', -80, 1, 'TASAF HQ, Dodoma', 30, 34,
     [('Issue the press release to national media', 'Outlets reached', 'outlets', 30, 34)],
     [('EDITOR', 30, 34)],
     'Release of the productive cash transfer results for the last cycle.'),
    ('Parliamentary Committee Field Visit', 'STAKEHOLDER_BRIEFING', 'STAKEHOLDER_ENGAGEMENT', 'ARCHIVED',
     'Morogoro MC', -180, 2, 'Morogoro Region', 25, 22,
     [('Show the committee three project sites', 'Sites visited', 'sites', 3, 3)],
     [('PARLIAMENTARY_COMMITTEE', 15, 13), ('MP', 10, 9)],
     'Committee visit to public works and livelihood sites.'),
    ('Tanga Branding Materials Rollout', 'BRANDING', 'GENERAL', 'CANCELLED',
     'Tanga', 10, 2, 'Tanga Region', 0, None,
     [('Install signboards at PAA offices', 'Signboards installed', 'signboards', 20, None)],
     [('TMO', 10, None)],
     'Cancelled: the new brand guidelines were not yet approved.'),
]

# (activity_index, media_house, invited, attended, reported, quality, coverage_type, day_offset)
DEMO_COVERAGE = [
    # 0 - National launch: broad turnout, mostly covered
    (0, 'Mwananchi', True, True, True, 5, 'NEWS_ARTICLE', 1),
    (0, 'The Citizen', True, True, True, 4, 'FEATURE', 1),
    (0, 'Daily News', True, True, True, 4, 'NEWS_ARTICLE', 1),
    (0, 'Habari Leo', True, True, True, 3, 'NEWS_ARTICLE', 2),
    (0, 'TBC FM', True, True, True, 5, 'BULLETIN', 0),
    (0, 'TBC', True, True, True, 4, 'BULLETIN', 0),
    (0, 'ITV', True, True, True, 4, 'BULLETIN', 0),
    (0, 'Clouds TV', True, True, False, None, None, None),
    (0, 'Nipashe', True, False, False, None, None, None),
    (0, 'Millardayo.com', True, True, True, 5, 'FEATURE', 4),
    # 1 - Annual report: fewer houses, solid coverage
    (1, 'Daily News', True, True, True, 4, 'NEWS_ARTICLE', 1),
    (1, 'Habari Leo', True, True, True, 3, 'NEWS_ARTICLE', 1),
    (1, 'Michuzi Blog', True, True, True, 4, 'SOCIAL_POST', 0),
    (1, 'TBC FM', True, True, True, 5, 'FEATURE', 3),
    (1, 'Majira', True, False, False, None, None, None),
    # 2 - Kagera mission: community-heavy
    (2, 'Radio Saut FM', True, True, True, 5, 'TALK_SHOW', 1),
    (2, 'Radio Kwizera', True, True, True, 4, 'INTERVIEW', 2),
    (2, 'Mwananchi', True, True, True, 4, 'FEATURE', 3),
    (2, 'Radio Free Africa', True, True, True, 3, 'BULLETIN', 1),
    (2, 'Full Shangwe Blog', True, False, False, None, None, None),
    # 3 - Njombe awareness: local radio + a freelancer
    (3, 'Radio Saut FM', True, True, True, 4, 'TALK_SHOW', 0),
    (3, 'Radio Kwizera', True, True, False, None, None, None),
    (3, 'Mwananchi', True, True, True, 5, 'NEWS_ARTICLE', 2),
    (3, 'The Citizen', True, True, True, 3, 'FEATURE', 5),
    # 4 - Simanjiro briefing
    (4, 'Radio Kwizera', True, True, True, 5, 'TALK_SHOW', 0),
    (4, 'ITV', True, True, True, 3, 'BULLETIN', 1),
    (4, 'Radio Free Africa', True, True, True, 2, 'BULLETIN', 2),
    (4, 'Daily News', True, False, False, None, None, None),
    # 5 - Mwanza case study
    (5, 'Star TV', True, True, True, 4, 'FEATURE', 1),
    (5, 'Radio Free Africa', True, True, True, 3, 'INTERVIEW', 1),
    (5, 'Radio Saut FM', True, True, True, 5, 'TALK_SHOW', 2),
    (5, 'Millardayo.com', True, True, True, 4, 'FEATURE', 6),
    (5, 'Azam TV', True, True, False, None, None, None),
]


class Command(BaseCommand):
    help = 'Seed (or purge) demonstration media houses and journalists for the Tanzania context.'

    def add_arguments(self, parser):
        parser.add_argument('--purge', action='store_true',
                            help='Delete every demo-tagged row instead of seeding.')

    def handle(self, *args, **options):
        user = User.objects.filter(username='Admin').first() or User.objects.order_by('id').first()
        if not user:
            self.stderr.write('No user available to attribute the seed to.')
            return
        if options['purge']:
            self._purge()
            return
        with transaction.atomic():
            self._seed(user)

    def _purge(self):
        # children first: coverage, objectives and audiences all point at the activities
        cov = ActivityMediaHouse.objects.filter(json_ext___seed='demo').delete()[0]
        demo_acts = CommunicationActivity.objects.filter(json_ext___seed='demo')
        ActivityObjective.objects.filter(activity__in=demo_acts).delete()
        ActivityAudience.objects.filter(activity__in=demo_acts).delete()
        acts = demo_acts.delete()[0]
        self.stdout.write(self.style.SUCCESS(
            f'Purged demo rows - coverage: {cov}, activities: {acts}'))

    def _district(self, name):
        return Location.objects.filter(type='D', name__iexact=name, validity_to__isnull=True).first()

    def _seed(self, user):
        created_a, created_c = self._seed_coverage(user)
        created_p = self._seed_pipeline(user)
        self.stdout.write(self.style.SUCCESS(
            f'Activities created: {created_a + created_p}' + chr(10)
            + f'Coverage rows:      {created_c}'))

    def _seed_pipeline(self, user):
        """Activities in every status, written straight to that status (demo data, not a workflow
        test), with objectives and audiences so the detail tabs are not empty."""
        act_service = CommunicationActivityService(user)
        categories = {c.code: c for c in ActivityCategory.objects.filter(is_deleted=False)}
        stakeholders = {t.code: t for t in StakeholderType.objects.filter(is_deleted=False)}
        today = timezone.now().replace(hour=9, minute=0, second=0, microsecond=0)
        created = 0
        for (title, atype, category, status, district, offset, days, venue, planned, actual,
             objectives, audiences, description) in DEMO_PIPELINE:
            if CommunicationActivity.objects.filter(title=title, is_deleted=False).exists():
                continue
            start = today + timedelta(days=offset)
            loc = self._district(district)
            cat = categories.get(category)
            res = act_service.create({
                'title': title, 'activity_type': atype, 'status': status,
                'category_id': cat.id if cat else None,
                'start_datetime': start, 'end_datetime': start + timedelta(days=days, hours=-1),
                'venue': venue, 'location_id': loc.id if loc else None,
                'planned_audience_count': planned or None, 'actual_audience_count': actual,
                'objective_summary': objectives[0][0], 'description': description,
                'json_ext': dict(DEMO),
            })
            if not res['success']:
                self.stderr.write(f'{title}: {res.get("message")} {res.get("detail", "")}')
                continue
            activity = CommunicationActivity.objects.get(id=res['data']['id'])
            for desc, indicator, unit, target, achieved in objectives:
                ActivityObjective(
                    activity=activity, description=desc, indicator=indicator, unit=unit,
                    target_value=target, achieved_value=achieved, json_ext=dict(DEMO),
                ).save(user=user)
            for code, planned_n, actual_n in audiences:
                if code in stakeholders:
                    ActivityAudience(
                        activity=activity, stakeholder_type=stakeholders[code],
                        planned_count=planned_n or None, actual_count=actual_n, json_ext=dict(DEMO),
                    ).save(user=user)
            created += 1
        return created


    def _seed_coverage(self, user):
        """Demo activities plus the coverage that makes the ratings visible.

        Activities are written straight to COMPLETED rather than walked through
        submit/approve/schedule/start/complete: this is demo data, not a workflow test, and the
        transition chokepoint stays the only path real activities take.
        """
        act_service = CommunicationActivityService(user)
        now = timezone.now()
        activities = []
        created_a = 0
        for title, atype, district, days_ago, venue in DEMO_ACTIVITIES:
            existing = CommunicationActivity.objects.filter(title=title, is_deleted=False).first()
            if existing:
                activities.append(existing)
                continue
            start = (now - timedelta(days=days_ago)).replace(hour=10, minute=0, second=0, microsecond=0)
            loc = self._district(district)
            res = act_service.create({
                'title': title, 'activity_type': atype, 'status': 'COMPLETED',
                'start_datetime': start, 'end_datetime': start + timedelta(hours=4),
                'venue': venue, 'location_id': loc.id if loc else None,
                'description': 'Demo activity seeded for media-coverage reporting.',
                'json_ext': dict(DEMO),
            })
            if not res['success']:
                self.stderr.write(f'{title}: {res.get("message")} {res.get("detail", "")}')
                activities.append(None)
                continue
            activities.append(CommunicationActivity.objects.get(id=res['data']['id']))
            created_a += 1

        houses = {h.name: h for h in MediaHouse.objects.filter(is_deleted=False)}
        # Attribute each story to an editor at that house when the registry has one; the
        # affiliation guard would reject anyone else.
        editors = {}
        for j in Journalist.objects.filter(is_deleted=False, media_house__isnull=False):
            editors.setdefault(j.media_house_id, j)
        cov_service = ActivityMediaHouseService(user)
        created_c = 0
        for (idx, house_name, invited, attended, reported,
             quality, ctype, day_offset) in DEMO_COVERAGE:
            activity = activities[idx] if idx < len(activities) else None
            house = houses.get(house_name)
            if not activity or not house:
                if not house:
                    self.stderr.write(f'coverage: media house "{house_name}" not found, skipped')
                continue
            if ActivityMediaHouse.objects.filter(activity=activity, media_house=house,
                                                 is_deleted=False).exists():
                continue
            journalist = editors.get(house.id)
            cov_date = (activity.start_datetime.date() + timedelta(days=day_offset)
                        if day_offset is not None else None)
            res = cov_service.create({
                'activity_id': activity.id, 'media_house_id': house.id,
                'journalist_id': journalist.id if journalist else None,
                'invited': invited, 'attended': attended, 'reported': reported,
                'coverage_quality': quality, 'coverage_type': ctype,
                'coverage_date': cov_date,
                'coverage_url': (f'https://www.example.tz/story/{activity.code.lower()}-'
                                 f'{re.sub(r"[^a-z0-9]", "", house_name.lower())}' if reported else None),
                'notes': 'Demo coverage record.',
                'json_ext': dict(DEMO),
            })
            if res['success']:
                created_c += 1
            else:
                self.stderr.write(f'coverage {house_name} @ {activity.code}: '
                                  f'{res.get("message")} {res.get("detail", "")}')
        return created_a, created_c
