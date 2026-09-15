"""Load the media houses and media personnel supplied by the communications team.

Source: MODULE doc shared 2026-09-15 ("Share a list of Media Houses at least a few with national
Coverage" and "Share Sample/List of Media houses, Name of Personnel, Tittle, Phone number, Email,
Gender").

This is REAL reference data, not demo data: rows are tagged ``json_ext['_seed'] = 'client'`` so the
demo seeder's --purge leaves them alone. Contact fields on houses are left empty rather than
invented; only the personnel details the client actually supplied are stored.
"""
from django.core.management.base import BaseCommand
from django.db import transaction

from core.models import User
from communications.models import MediaHouseCategory, MediaHouse, Journalist
from communications.services import MediaHouseService, JournalistService

CLIENT = {'_seed': 'client'}

# (name, category_code)  — coverage/reach is carried by the category's scope
MEDIA_HOUSES = [
    ('TBC', 'TV'), ('ITV', 'TV'), ('Azam TV', 'TV'), ('Channel 10', 'TV'),
    ('Star TV', 'TV'), ('EATV', 'TV'), ('Wasafi TV', 'TV'), ('Clouds TV', 'TV'), ('TVE', 'TV'),
    # Referenced by the personnel list but absent from the client's media table.
    ('ZBC', 'TV'),

    ('Mwananchi', 'NEWSPAPER'), ('Uhuru', 'NEWSPAPER'), ('Daily News', 'NEWSPAPER'),
    ('Habari Leo', 'NEWSPAPER'), ('The Guardian', 'NEWSPAPER'), ('Nipashe', 'NEWSPAPER'),
    ('The East African', 'NEWSPAPER'), ('Zanzibar Leo', 'NEWSPAPER'), ('The Citizen', 'NEWSPAPER'),
    ('Raia Mwema', 'NEWSPAPER'), ('Majira', 'NEWSPAPER'),

    ('TBC FM', 'RADIO_GENERAL'), ('Uhai FM', 'RADIO_GENERAL'), ('EFM', 'RADIO_GENERAL'),
    ('Radio Free Africa', 'RADIO_GENERAL'), ('East Africa Radio', 'RADIO_GENERAL'),
    ('Radio One', 'RADIO_GENERAL'),

    ('Radio Kwizera', 'RADIO_ZONAL'), ('Radio Saut FM', 'RADIO_ZONAL'),

    ('Millardayo.com', 'WEBSITE'),
    ('Michuzi Blog', 'BLOG'), ('Full Shangwe Blog', 'BLOG'),
]

# (first_name, last_name, media_house, gender, phone, email)
JOURNALISTS = [
    ('Vumilia', 'Mwasha', 'TBC', 'F', '0712318876', None),
    ('Ezekiel', 'Mwambopo', 'Channel 10', 'M', '0714421867', None),
    ('Amina', 'Juma Rashid', 'ZBC', 'F', '0656389196', None),
    ('Robert', 'Odundo', 'Daily News', 'M', '0735612645', 'Robert.odundo@yahoo.com'),
    ('Dickson', "Ng'hily", 'The Guardian', 'M', '0746304306', None),
    ('Samuel', 'Kamndaya', 'The Citizen', 'M', '0621183194', 'samueltkk@gmail.com'),
    ('Ibrahim', 'Yamola', 'Mwananchi', 'M', '0716386168', 'yamola2025@gmail.com'),
    ('Gloria', 'Tesha', 'Habari Leo', 'F', '0715022555', None),
    # Supplied as a single name.
    ('Chuwa', '', 'ITV', 'M', None, None),
    ('Richard', 'Ngaila', 'Azam TV', 'M', '0689338835', None),
]


class Command(BaseCommand):
    help = "Load the communications team's media-house and personnel list."

    def add_arguments(self, parser):
        parser.add_argument('--purge', action='store_true',
                            help='Delete every client-tagged row instead of loading.')

    def handle(self, *args, **options):
        user = User.objects.filter(username='Admin').first() or User.objects.order_by('id').first()
        if not user:
            self.stderr.write('No user available to attribute the load to.')
            return
        if options['purge']:
            j = Journalist.objects.filter(json_ext___seed='client').delete()[0]
            h = MediaHouse.objects.filter(json_ext___seed='client').delete()[0]
            self.stdout.write(self.style.SUCCESS(f'Purged client rows - journalists: {j}, houses: {h}'))
            return
        with transaction.atomic():
            self._load(user)

    def _load(self, user):
        categories = {c.code: c for c in MediaHouseCategory.objects.filter(is_deleted=False)}
        house_service = MediaHouseService(user)
        created_h = skipped_h = 0
        for name, cat_code in MEDIA_HOUSES:
            if MediaHouse.objects.filter(name=name, is_deleted=False).exists():
                skipped_h += 1
                continue
            category = categories.get(cat_code)
            if not category:
                self.stderr.write(f'{name}: category {cat_code} missing, skipped')
                continue
            res = house_service.create({
                'name': name, 'category_id': category.id, 'is_active': True,
                'json_ext': dict(CLIENT),
            })
            if res['success']:
                created_h += 1
            else:
                self.stderr.write(f'{name}: {res.get("message")} {res.get("detail", "")}')

        houses = {h.name: h for h in MediaHouse.objects.filter(is_deleted=False)}
        j_service = JournalistService(user)
        created_j = skipped_j = 0
        for first, last, house_name, gender, phone, email in JOURNALISTS:
            if Journalist.objects.filter(first_name=first, last_name=last, is_deleted=False).exists():
                skipped_j += 1
                continue
            house = houses.get(house_name)
            if not house:
                self.stderr.write(f'{first} {last}: house "{house_name}" not found, left unaffiliated')
            res = j_service.create({
                'first_name': first, 'last_name': last,
                'media_house_id': house.id if house else None,
                'role': 'EDITOR', 'gender': gender,
                'phone': phone, 'email': email,
                'is_active': True, 'json_ext': dict(CLIENT),
            })
            if res['success']:
                created_j += 1
            else:
                self.stderr.write(f'{first} {last}: {res.get("message")} {res.get("detail", "")}')

        self.stdout.write(self.style.SUCCESS(
            f'Media houses: {created_h} created, {skipped_h} already present\n'
            f'Journalists:  {created_j} created, {skipped_j} already present'))
