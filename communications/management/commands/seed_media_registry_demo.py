"""Seed demonstration data for the media-house and journalist registries.

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

# (name, category_code, district_name_or_None, frequency_or_channel, language)
# Codes are NOT listed: MediaHouseService generates them (MH00001, ...).
MEDIA_HOUSES = [
    # --- Newspapers -------------------------------------------------------
    ('Mwananchi', 'NEWSPAPER', 'Ilala MC', 'Daily', 'Swahili'),
    ('The Citizen', 'NEWSPAPER', 'Ilala MC', 'Daily', 'English'),
    ('Daily News', 'NEWSPAPER', 'Ilala MC', 'Daily', 'English'),
    ('HabariLeo', 'NEWSPAPER', 'Ilala MC', 'Daily', 'Swahili'),
    ('Nipashe', 'NEWSPAPER', 'Kinondoni MC', 'Daily', 'Swahili'),
    ('Mtanzania', 'NEWSPAPER', 'Kinondoni MC', 'Daily', 'Swahili'),
    ('The Guardian', 'NEWSPAPER', 'Kinondoni MC', 'Daily', 'English'),
    # --- National / general radio ----------------------------------------
    ('TBC Taifa', 'RADIO_GENERAL', 'Kinondoni MC', '89.9 FM', 'Swahili'),
    ('Radio One', 'RADIO_GENERAL', 'Kinondoni MC', '95.2 FM', 'Swahili'),
    ('Clouds FM', 'RADIO_GENERAL', 'Kinondoni MC', '88.6 FM', 'Swahili'),
    ('Radio Free Africa', 'RADIO_GENERAL', 'Mwanza CC', '89.3 FM', 'Swahili'),
    ('East Africa Radio', 'RADIO_GENERAL', 'Kinondoni MC', '91.6 FM', 'Swahili'),
    ('Times FM', 'RADIO_GENERAL', 'Ilala MC', '98.0 FM', 'Swahili'),
    ('Wasafi FM', 'RADIO_GENERAL', 'Kinondoni MC', '88.9 FM', 'Swahili'),
    # --- Community radio (district-anchored) ------------------------------
    ('Sengerema Community Radio', 'RADIO_COMMUNITY', 'Sengerema', '99.6 FM', 'Swahili'),
    ('Orkonerei Radio Service (ORS FM)', 'RADIO_COMMUNITY', 'Simanjiro', '90.4 FM', 'Maa / Swahili'),
    ('FADECO Community Radio', 'RADIO_COMMUNITY', 'Karagwe', '99.0 FM', 'Swahili / Haya'),
    ('Radio Kwizera', 'RADIO_COMMUNITY', 'Ngara', '92.5 FM', 'Swahili / Kirundi'),
    # Generic district stations - placeholder names, not claims about specific stations.
    ('Kyela Community Radio', 'RADIO_COMMUNITY', 'Kyela', '101.2 FM', 'Swahili / Nyakyusa'),
    ('Njombe Community Radio', 'RADIO_COMMUNITY', 'Njombe', '102.4 FM', 'Swahili / Bena'),
    ('Tarime Community Radio', 'RADIO_COMMUNITY', 'Tarime DC', '103.8 FM', 'Swahili / Kuria'),
    ('Kondoa Community Radio', 'RADIO_COMMUNITY', 'Kondoa', '104.6 FM', 'Swahili / Rangi'),
    # --- Television -------------------------------------------------------
    ('TBC1', 'TV_GENERAL', 'Kinondoni MC', 'Channel 1', 'Swahili'),
    ('ITV', 'TV_GENERAL', 'Kinondoni MC', 'Channel 3', 'Swahili'),
    ('Channel Ten', 'TV_GENERAL', 'Kinondoni MC', 'Channel 10', 'Swahili'),
    ('Star TV', 'TV_GENERAL', 'Mwanza CC', 'Channel 5', 'Swahili'),
    ('Azam TV', 'TV_GENERAL', 'Ilala MC', 'Channel 2', 'Swahili'),
    # --- Online / digital -------------------------------------------------
    ('Mwananchi Digital', 'ONLINE', 'Ilala MC', 'Web', 'Swahili / English'),
    ('The Chanzo', 'ONLINE', 'Kinondoni MC', 'Web', 'Swahili / English'),
    ('JamiiForums', 'ONLINE', 'Kinondoni MC', 'Web', 'Swahili'),
    ('Michuzi Blog', 'ONLINE', 'Kinondoni MC', 'Web', 'Swahili'),
]

# (first, last, media_house_name or None, is_freelance, role, beat, district, accreditation)
JOURNALISTS = [
    ('Asha', 'Mwinyi', 'Mwananchi', False, 'REPORTER', 'Social protection', 'Ilala MC', 'ACC-2026-0101'),
    ('Baraka', 'Shirima', 'The Citizen', False, 'EDITOR', 'Economy', 'Ilala MC', 'ACC-2026-0102'),
    ('Neema', 'Kalinga', 'Daily News', False, 'REPORTER', 'Health', 'Kinondoni MC', 'ACC-2026-0103'),
    ('Juma', 'Mahenge', 'HabariLeo', False, 'CORRESPONDENT', 'Rural development', 'Dodoma CC', 'ACC-2026-0104'),
    ('Zainabu', 'Ngassa', 'Nipashe', False, 'REPORTER', 'Education', 'Kinondoni MC', None),
    ('Emmanuel', 'Mwaikambo', 'TBC Taifa', False, 'PRESENTER', 'Current affairs', 'Kinondoni MC', 'ACC-2026-0105'),
    ('Rehema', 'Lyimo', 'TBC Taifa', False, 'PRODUCER', 'Documentary', 'Kinondoni MC', 'ACC-2026-0106'),
    ('Salum', 'Kachenje', 'Clouds FM', False, 'PRESENTER', 'Youth affairs', 'Kinondoni MC', None),
    ('Fatuma', 'Nyoni', 'Radio Free Africa', False, 'REPORTER', 'Agriculture', 'Mwanza CC', 'ACC-2026-0107'),
    ('Godfrey', 'Msigwa', 'Sengerema Community Radio', False, 'REPORTER', 'Community development', 'Sengerema', None),
    ('Upendo', 'Sanga', 'Orkonerei Radio Service (ORS FM)', False, 'PRESENTER', 'Pastoralist affairs', 'Simanjiro', None),
    ('Deo', 'Rwegasira', 'FADECO Community Radio', False, 'REPORTER', 'Livelihoods', 'Karagwe', None),
    ('Grace', 'Mollel', 'Radio Kwizera', False, 'CORRESPONDENT', 'Refugees and migration', 'Ngara', 'ACC-2026-0108'),
    ('Hamisi', 'Chande', 'TBC1', False, 'CAMERA', 'Field production', 'Kinondoni MC', None),
    ('Lilian', 'Mtei', 'ITV', False, 'REPORTER', 'Social protection', 'Kinondoni MC', 'ACC-2026-0109'),
    ('Peter', 'Kimaro', 'The Chanzo', False, 'EDITOR', 'Investigations', 'Kinondoni MC', 'ACC-2026-0110'),
    ('Sophia', 'Mrutu', 'Mwananchi Digital', False, 'PHOTOGRAPHER', 'Photojournalism', 'Ilala MC', None),
    # Freelancers: no house, which is exactly the case a house-child model could not represent.
    ('Ibrahim', 'Nassoro', None, True, 'CORRESPONDENT', 'Social protection', 'Mtwara MC', 'ACC-2026-0111'),
    ('Consolata', 'Mushi', None, True, 'REPORTER', 'Gender and inclusion', 'Moshi MC', None),
    ('Frank', 'Mbwilo', None, True, 'PHOTOGRAPHER', 'Documentary', 'Njombe', None),
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

# (activity_index, media_house, journalist or None, invited, attended, reported, quality, coverage_type, day_offset)
# Journalists must work for the house (or be freelance) - the affiliation guard enforces it.
DEMO_COVERAGE = [
    # 0 - National launch: broad turnout, mostly covered
    (0, 'Mwananchi', 'Asha Mwinyi', True, True, True, 5, 'NEWS_ARTICLE', 1),
    (0, 'The Citizen', 'Baraka Shirima', True, True, True, 4, 'FEATURE', 1),
    (0, 'Daily News', 'Neema Kalinga', True, True, True, 4, 'NEWS_ARTICLE', 1),
    (0, 'HabariLeo', 'Juma Mahenge', True, True, True, 3, 'NEWS_ARTICLE', 2),
    (0, 'TBC Taifa', 'Emmanuel Mwaikambo', True, True, True, 5, 'BULLETIN', 0),
    (0, 'TBC1', 'Hamisi Chande', True, True, True, 4, 'BULLETIN', 0),
    (0, 'ITV', 'Lilian Mtei', True, True, True, 4, 'BULLETIN', 0),
    (0, 'Clouds FM', 'Salum Kachenje', True, True, False, None, None, None),
    (0, 'Nipashe', 'Zainabu Ngassa', True, False, False, None, None, None),
    (0, 'The Chanzo', 'Peter Kimaro', True, True, True, 5, 'FEATURE', 4),
    # 1 - Annual report: fewer houses, solid coverage
    (1, 'Daily News', 'Neema Kalinga', True, True, True, 4, 'NEWS_ARTICLE', 1),
    (1, 'HabariLeo', 'Juma Mahenge', True, True, True, 3, 'NEWS_ARTICLE', 1),
    (1, 'Mwananchi Digital', 'Sophia Mrutu', True, True, True, 4, 'SOCIAL_POST', 0),
    (1, 'TBC Taifa', 'Rehema Lyimo', True, True, True, 5, 'FEATURE', 3),
    (1, 'Mtanzania', None, True, False, False, None, None, None),
    # 2 - Kagera mission: community-heavy
    (2, 'FADECO Community Radio', 'Deo Rwegasira', True, True, True, 5, 'TALK_SHOW', 1),
    (2, 'Radio Kwizera', 'Grace Mollel', True, True, True, 4, 'INTERVIEW', 2),
    (2, 'Mwananchi', 'Asha Mwinyi', True, True, True, 4, 'FEATURE', 3),
    (2, 'Radio Free Africa', 'Fatuma Nyoni', True, True, True, 3, 'BULLETIN', 1),
    (2, 'JamiiForums', None, True, False, False, None, None, None),
    # 3 - Njombe awareness: local radio + a freelancer
    (3, 'Njombe Community Radio', None, True, True, True, 4, 'TALK_SHOW', 0),
    (3, 'Kyela Community Radio', None, True, True, False, None, None, None),
    (3, 'Mwananchi', 'Asha Mwinyi', True, True, True, 5, 'NEWS_ARTICLE', 2),
    (3, 'The Citizen', 'Frank Mbwilo', True, True, True, 3, 'FEATURE', 5),
    # 4 - Simanjiro briefing
    (4, 'Orkonerei Radio Service (ORS FM)', 'Upendo Sanga', True, True, True, 5, 'TALK_SHOW', 0),
    (4, 'ITV', 'Lilian Mtei', True, True, True, 3, 'BULLETIN', 1),
    (4, 'Radio Free Africa', 'Fatuma Nyoni', True, True, True, 2, 'BULLETIN', 2),
    (4, 'Daily News', 'Consolata Mushi', True, False, False, None, None, None),
    # 5 - Mwanza case study
    (5, 'Star TV', None, True, True, True, 4, 'FEATURE', 1),
    (5, 'Radio Free Africa', 'Fatuma Nyoni', True, True, True, 3, 'INTERVIEW', 1),
    (5, 'Sengerema Community Radio', 'Godfrey Msigwa', True, True, True, 5, 'TALK_SHOW', 2),
    (5, 'The Chanzo', 'Ibrahim Nassoro', True, True, True, 4, 'FEATURE', 6),
    (5, 'Azam TV', None, True, True, False, None, None, None),
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
        j = Journalist.objects.filter(json_ext___seed='demo').delete()[0]
        h = MediaHouse.objects.filter(json_ext___seed='demo').delete()[0]
        c = MediaHouseCategory.objects.filter(json_ext___seed='demo').delete()[0]
        self.stdout.write(self.style.SUCCESS(
            f'Purged demo rows - coverage: {cov}, activities: {acts}, '
            f'journalists: {j}, media houses: {h}, categories: {c}'))

    def _district(self, name):
        return Location.objects.filter(type='D', name__iexact=name, validity_to__isnull=True).first()

    def _seed(self, user):
        cat_service = MediaHouseCategoryService(user)
        for code, name, medium, scope in EXTRA_CATEGORIES:
            if MediaHouseCategory.objects.filter(code=code, is_deleted=False).exists():
                continue
            res = cat_service.create({'code': code, 'name': name, 'medium': medium,
                                      'scope': scope, 'is_active': True, 'json_ext': dict(DEMO)})
            if not res['success']:
                self.stderr.write(f'category {code}: {res.get("message")}')

        categories = {c.code: c for c in MediaHouseCategory.objects.filter(is_deleted=False)}
        house_service = MediaHouseService(user)
        created_h = skipped_h = 0
        for name, cat_code, district, freq, language in MEDIA_HOUSES:
            if MediaHouse.objects.filter(name=name, is_deleted=False).exists():
                skipped_h += 1
                continue
            category = categories.get(cat_code)
            if not category:
                self.stderr.write(f'{name}: category {cat_code} missing, skipped')
                continue
            loc = self._district(district) if district else None
            if district and not loc:
                self.stdout.write(f'  {name}: district "{district}" not found, left unset')
            # Placeholder contacts only - see the module docstring.
            slug = re.sub(r'[^a-z0-9]', '', name.lower())
            res = house_service.create({
                'name': name, 'category_id': category.id,
                'location_id': loc.id if loc else None,
                'frequency_or_channel': freq, 'language': language,
                'contact_person': 'News Desk',
                'phone': f'+255 700 000 {created_h % 100:03d}',
                'email': f'newsdesk@{slug}.example',
                'website': f'https://www.{slug}.example',
                'address': f'{district or "Dar es Salaam"}, Tanzania',
                'notes': 'Demo record - contact details are placeholders.',
                'is_active': True, 'json_ext': dict(DEMO),
            })
            if res['success']:
                created_h += 1
            else:
                self.stderr.write(f'{name}: {res.get("message")} {res.get("detail", "")}')

        houses = {h.name: h for h in MediaHouse.objects.filter(is_deleted=False)}
        j_service = JournalistService(user)
        created_j = skipped_j = 0
        for first, last, house_name, freelance, role, beat, district, accreditation in JOURNALISTS:
            if Journalist.objects.filter(first_name=first, last_name=last, is_deleted=False).exists():
                skipped_j += 1
                continue
            house = houses.get(house_name) if house_name else None
            loc = self._district(district) if district else None
            res = j_service.create({
                'first_name': first, 'last_name': last,
                'media_house_id': house.id if house else None,
                'is_freelance': freelance, 'role': role, 'beat': beat,
                'location_id': loc.id if loc else None,
                'phone': f'+255 715 000 {created_j % 100:03d}',
                'email': f'{first.lower()}.{last.lower()}@example.org',
                'languages': 'Swahili, English',
                'accreditation_no': accreditation,
                'notes': 'Demo record - fictional person, placeholder contacts.',
                'is_active': True, 'json_ext': dict(DEMO),
            })
            if res['success']:
                created_j += 1
            else:
                self.stderr.write(f'{first} {last}: {res.get("message")} {res.get("detail", "")}')

        created_a, created_c = self._seed_coverage(user)
        self.stdout.write(self.style.SUCCESS(
            f'Media houses created: {created_h} (skipped existing: {skipped_h})\n'
            f'Journalists created:  {created_j} (skipped existing: {skipped_j})\n'
            f'Activities created:   {created_a}\n'
            f'Coverage rows:        {created_c}'))

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
        journalists = {f'{j.first_name} {j.last_name}': j
                       for j in Journalist.objects.filter(is_deleted=False)}
        cov_service = ActivityMediaHouseService(user)
        created_c = 0
        for (idx, house_name, jname, invited, attended, reported,
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
            journalist = journalists.get(jname) if jname else None
            if jname and not journalist:
                self.stderr.write(f'coverage: journalist "{jname}" not found, left unattributed')
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
