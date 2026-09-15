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
        # coverage first: it points at both houses and journalists
        cov = ActivityMediaHouse.objects.filter(json_ext___seed='demo').delete()[0]
        acts = CommunicationActivity.objects.filter(json_ext___seed='demo').delete()[0]
        self.stdout.write(self.style.SUCCESS(
            f'Purged demo rows - coverage: {cov}, activities: {acts}'))

    def _district(self, name):
        return Location.objects.filter(type='D', name__iexact=name, validity_to__isnull=True).first()

    def _seed(self, user):
        created_a, created_c = self._seed_coverage(user)
        self.stdout.write(self.style.SUCCESS(
            f'Activities created: {created_a}' + chr(10)
            + f'Coverage rows:      {created_c}'))


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
