# Media-house / journalist registries (hand-written: no local Django runtime).

import core.fields
import core.models.base_mutation
import core.utils
import datetime
import dirtyfields.dirtyfields
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import simple_history.models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('core', '0031_alter_mutationlog_client_mutation_id'),
        ('location', '0019_alter_location_code'),
        ('communications', '0006_announcementdismissal_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='MediaHouseCategory',
            fields=[
                ('id', models.UUIDField(db_column='UUID', default=None, editable=False, primary_key=True, serialize=False)),
                ('is_deleted', models.BooleanField(db_column='isDeleted', default=False)),
                ('json_ext', models.JSONField(blank=True, db_column='Json_ext', null=True)),
                ('date_created', core.fields.DateTimeField(db_column='DateCreated', default=datetime.datetime.now, null=True)),
                ('date_updated', core.fields.DateTimeField(db_column='DateUpdated', default=datetime.datetime.now, null=True)),
                ('version', models.IntegerField(default=1)),
                ('code', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('medium', models.CharField(choices=[('NEWSPAPER', 'Newspaper'), ('RADIO', 'Radio'), ('TV', 'Television'), ('ONLINE', 'Online / Digital'), ('SOCIAL', 'Social Media'), ('OTHER', 'Other')], default='OTHER', max_length=20)),
                ('scope', models.CharField(choices=[('NATIONAL', 'National'), ('REGIONAL', 'Regional'), ('PAA', 'PAA (Project Area Authority)'), ('COMMUNITY', 'Community'), ('OTHER', 'Other')], default='NATIONAL', max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            bases=(dirtyfields.dirtyfields.DirtyFieldsMixin, core.utils.CachedModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='MediaHouse',
            fields=[
                ('id', models.UUIDField(db_column='UUID', default=None, editable=False, primary_key=True, serialize=False)),
                ('is_deleted', models.BooleanField(db_column='isDeleted', default=False)),
                ('json_ext', models.JSONField(blank=True, db_column='Json_ext', null=True)),
                ('date_created', core.fields.DateTimeField(db_column='DateCreated', default=datetime.datetime.now, null=True)),
                ('date_updated', core.fields.DateTimeField(db_column='DateUpdated', default=datetime.datetime.now, null=True)),
                ('version', models.IntegerField(default=1)),
                ('code', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('frequency_or_channel', models.CharField(blank=True, max_length=100, null=True)),
                ('language', models.CharField(blank=True, max_length=100, null=True)),
                ('contact_person', models.CharField(blank=True, max_length=255, null=True)),
                ('phone', models.CharField(blank=True, max_length=50, null=True)),
                ('email', models.CharField(blank=True, max_length=255, null=True)),
                ('website', models.CharField(blank=True, max_length=255, null=True)),
                ('address', models.TextField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            bases=(dirtyfields.dirtyfields.DirtyFieldsMixin, core.utils.CachedModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='Journalist',
            fields=[
                ('id', models.UUIDField(db_column='UUID', default=None, editable=False, primary_key=True, serialize=False)),
                ('is_deleted', models.BooleanField(db_column='isDeleted', default=False)),
                ('json_ext', models.JSONField(blank=True, db_column='Json_ext', null=True)),
                ('date_created', core.fields.DateTimeField(db_column='DateCreated', default=datetime.datetime.now, null=True)),
                ('date_updated', core.fields.DateTimeField(db_column='DateUpdated', default=datetime.datetime.now, null=True)),
                ('version', models.IntegerField(default=1)),
                ('code', models.CharField(max_length=255)),
                ('first_name', models.CharField(max_length=255)),
                ('last_name', models.CharField(max_length=255)),
                ('is_freelance', models.BooleanField(default=False)),
                ('role', models.CharField(choices=[('REPORTER', 'Reporter'), ('EDITOR', 'Editor'), ('PRESENTER', 'Presenter / Anchor'), ('PRODUCER', 'Producer'), ('CAMERA', 'Camera Operator'), ('PHOTOGRAPHER', 'Photographer'), ('CORRESPONDENT', 'Correspondent'), ('OTHER', 'Other')], default='REPORTER', max_length=20)),
                ('beat', models.CharField(blank=True, max_length=255, null=True)),
                ('phone', models.CharField(blank=True, max_length=50, null=True)),
                ('alt_phone', models.CharField(blank=True, max_length=50, null=True)),
                ('email', models.CharField(blank=True, max_length=255, null=True)),
                ('languages', models.CharField(blank=True, max_length=255, null=True)),
                ('accreditation_no', models.CharField(blank=True, max_length=100, null=True)),
                ('accreditation_expiry', models.DateField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
            ],
            bases=(dirtyfields.dirtyfields.DirtyFieldsMixin, core.utils.CachedModelMixin, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalMediaHouseCategory',
            fields=[
                ('id', models.UUIDField(db_column='UUID', db_index=True, default=None, editable=False)),
                ('is_deleted', models.BooleanField(db_column='isDeleted', default=False)),
                ('json_ext', models.JSONField(blank=True, db_column='Json_ext', null=True)),
                ('date_created', core.fields.DateTimeField(db_column='DateCreated', default=datetime.datetime.now, null=True)),
                ('date_updated', core.fields.DateTimeField(db_column='DateUpdated', default=datetime.datetime.now, null=True)),
                ('version', models.IntegerField(default=1)),
                ('code', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('medium', models.CharField(choices=[('NEWSPAPER', 'Newspaper'), ('RADIO', 'Radio'), ('TV', 'Television'), ('ONLINE', 'Online / Digital'), ('SOCIAL', 'Social Media'), ('OTHER', 'Other')], default='OTHER', max_length=20)),
                ('scope', models.CharField(choices=[('NATIONAL', 'National'), ('REGIONAL', 'Regional'), ('PAA', 'PAA (Project Area Authority)'), ('COMMUNITY', 'Community'), ('OTHER', 'Other')], default='NATIONAL', max_length=20)),
                ('description', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
            ],
            options={
                'verbose_name': 'historical media house category',
                'verbose_name_plural': 'historical media house categorys',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalMediaHouse',
            fields=[
                ('id', models.UUIDField(db_column='UUID', db_index=True, default=None, editable=False)),
                ('is_deleted', models.BooleanField(db_column='isDeleted', default=False)),
                ('json_ext', models.JSONField(blank=True, db_column='Json_ext', null=True)),
                ('date_created', core.fields.DateTimeField(db_column='DateCreated', default=datetime.datetime.now, null=True)),
                ('date_updated', core.fields.DateTimeField(db_column='DateUpdated', default=datetime.datetime.now, null=True)),
                ('version', models.IntegerField(default=1)),
                ('code', models.CharField(max_length=255)),
                ('name', models.CharField(max_length=255)),
                ('frequency_or_channel', models.CharField(blank=True, max_length=100, null=True)),
                ('language', models.CharField(blank=True, max_length=100, null=True)),
                ('contact_person', models.CharField(blank=True, max_length=255, null=True)),
                ('phone', models.CharField(blank=True, max_length=50, null=True)),
                ('email', models.CharField(blank=True, max_length=255, null=True)),
                ('website', models.CharField(blank=True, max_length=255, null=True)),
                ('address', models.TextField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
            ],
            options={
                'verbose_name': 'historical media house',
                'verbose_name_plural': 'historical media houses',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='HistoricalJournalist',
            fields=[
                ('id', models.UUIDField(db_column='UUID', db_index=True, default=None, editable=False)),
                ('is_deleted', models.BooleanField(db_column='isDeleted', default=False)),
                ('json_ext', models.JSONField(blank=True, db_column='Json_ext', null=True)),
                ('date_created', core.fields.DateTimeField(db_column='DateCreated', default=datetime.datetime.now, null=True)),
                ('date_updated', core.fields.DateTimeField(db_column='DateUpdated', default=datetime.datetime.now, null=True)),
                ('version', models.IntegerField(default=1)),
                ('code', models.CharField(max_length=255)),
                ('first_name', models.CharField(max_length=255)),
                ('last_name', models.CharField(max_length=255)),
                ('is_freelance', models.BooleanField(default=False)),
                ('role', models.CharField(choices=[('REPORTER', 'Reporter'), ('EDITOR', 'Editor'), ('PRESENTER', 'Presenter / Anchor'), ('PRODUCER', 'Producer'), ('CAMERA', 'Camera Operator'), ('PHOTOGRAPHER', 'Photographer'), ('CORRESPONDENT', 'Correspondent'), ('OTHER', 'Other')], default='REPORTER', max_length=20)),
                ('beat', models.CharField(blank=True, max_length=255, null=True)),
                ('phone', models.CharField(blank=True, max_length=50, null=True)),
                ('alt_phone', models.CharField(blank=True, max_length=50, null=True)),
                ('email', models.CharField(blank=True, max_length=255, null=True)),
                ('languages', models.CharField(blank=True, max_length=255, null=True)),
                ('accreditation_no', models.CharField(blank=True, max_length=100, null=True)),
                ('accreditation_expiry', models.DateField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('history_id', models.AutoField(primary_key=True, serialize=False)),
                ('history_date', models.DateTimeField(db_index=True)),
                ('history_change_reason', models.CharField(max_length=100, null=True)),
                ('history_type', models.CharField(choices=[('+', 'Created'), ('~', 'Changed'), ('-', 'Deleted')], max_length=1)),
            ],
            options={
                'verbose_name': 'historical journalist',
                'verbose_name_plural': 'historical journalists',
                'ordering': ('-history_date', '-history_id'),
                'get_latest_by': ('history_date', 'history_id'),
            },
            bases=(simple_history.models.HistoricalChanges, models.Model),
        ),
        migrations.CreateModel(
            name='MediaHouseCategoryMutation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, core.models.base_mutation.ObjectMutation),
        ),
        migrations.CreateModel(
            name='MediaHouseMutation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, core.models.base_mutation.ObjectMutation),
        ),
        migrations.CreateModel(
            name='JournalistMutation',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
            ],
            options={
                'abstract': False,
            },
            bases=(models.Model, core.models.base_mutation.ObjectMutation),
        ),
        migrations.AddField(
            model_name='mediahouse',
            name='category',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='media_houses', to='communications.mediahousecategory'),
        ),
        migrations.AddField(
            model_name='mediahouse',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='media_houses', to='location.location'),
        ),
        migrations.AddField(
            model_name='journalist',
            name='media_house',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='journalists', to='communications.mediahouse'),
        ),
        migrations.AddField(
            model_name='journalist',
            name='location',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='journalists', to='location.location'),
        ),
        migrations.AddField(
            model_name='mediahousecategory',
            name='user_created',
            field=models.ForeignKey(db_column='UserCreatedUUID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(class)s_user_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='mediahousecategory',
            name='user_updated',
            field=models.ForeignKey(db_column='UserUpdatedUUID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(class)s_user_updated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='mediahouse',
            name='user_created',
            field=models.ForeignKey(db_column='UserCreatedUUID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(class)s_user_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='mediahouse',
            name='user_updated',
            field=models.ForeignKey(db_column='UserUpdatedUUID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(class)s_user_updated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='journalist',
            name='user_created',
            field=models.ForeignKey(db_column='UserCreatedUUID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(class)s_user_created', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='journalist',
            name='user_updated',
            field=models.ForeignKey(db_column='UserUpdatedUUID', on_delete=django.db.models.deletion.DO_NOTHING, related_name='%(class)s_user_updated', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalmediahouse',
            name='category',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='communications.mediahousecategory'),
        ),
        migrations.AddField(
            model_name='historicalmediahouse',
            name='location',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='location.location'),
        ),
        migrations.AddField(
            model_name='historicaljournalist',
            name='media_house',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='communications.mediahouse'),
        ),
        migrations.AddField(
            model_name='historicaljournalist',
            name='location',
            field=models.ForeignKey(blank=True, db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to='location.location'),
        ),
        migrations.AddField(
            model_name='historicalmediahousecategory',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalmediahousecategory',
            name='user_created',
            field=models.ForeignKey(blank=True, db_column='UserCreatedUUID', db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalmediahousecategory',
            name='user_updated',
            field=models.ForeignKey(blank=True, db_column='UserUpdatedUUID', db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalmediahouse',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalmediahouse',
            name='user_created',
            field=models.ForeignKey(blank=True, db_column='UserCreatedUUID', db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicalmediahouse',
            name='user_updated',
            field=models.ForeignKey(blank=True, db_column='UserUpdatedUUID', db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicaljournalist',
            name='history_user',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicaljournalist',
            name='user_created',
            field=models.ForeignKey(blank=True, db_column='UserCreatedUUID', db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='historicaljournalist',
            name='user_updated',
            field=models.ForeignKey(blank=True, db_column='UserUpdatedUUID', db_constraint=False, null=True, on_delete=django.db.models.deletion.DO_NOTHING, related_name='+', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='mediahousecategorymutation',
            name='media_house_category',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='mutations', to='communications.mediahousecategory'),
        ),
        migrations.AddField(
            model_name='mediahousecategorymutation',
            name='mutation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='media_house_categories', to='core.mutationlog'),
        ),
        migrations.AddField(
            model_name='mediahousemutation',
            name='media_house',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='mutations', to='communications.mediahouse'),
        ),
        migrations.AddField(
            model_name='mediahousemutation',
            name='mutation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='media_houses', to='core.mutationlog'),
        ),
        migrations.AddField(
            model_name='journalistmutation',
            name='journalist',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='mutations', to='communications.journalist'),
        ),
        migrations.AddField(
            model_name='journalistmutation',
            name='mutation',
            field=models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, related_name='journalists', to='core.mutationlog'),
        ),
        migrations.AddIndex(
            model_name='mediahousecategory',
            index=models.Index(fields=['code'], name='communicati_code_99a4ed_idx'),
        ),
        migrations.AddIndex(
            model_name='mediahousecategory',
            index=models.Index(fields=['medium'], name='communicati_medium_d47c48_idx'),
        ),
        migrations.AddIndex(
            model_name='mediahousecategory',
            index=models.Index(fields=['scope'], name='communicati_scope_b80200_idx'),
        ),
        migrations.AddIndex(
            model_name='mediahousecategory',
            index=models.Index(fields=['is_active'], name='communicati_is_acti_c76950_idx'),
        ),
        migrations.AddIndex(
            model_name='mediahouse',
            index=models.Index(fields=['code'], name='communicati_code_297b98_idx'),
        ),
        migrations.AddIndex(
            model_name='mediahouse',
            index=models.Index(fields=['category'], name='communicati_categor_0e46e3_idx'),
        ),
        migrations.AddIndex(
            model_name='mediahouse',
            index=models.Index(fields=['location'], name='communicati_locatio_486177_idx'),
        ),
        migrations.AddIndex(
            model_name='mediahouse',
            index=models.Index(fields=['is_active'], name='communicati_is_acti_71db0d_idx'),
        ),
        migrations.AddIndex(
            model_name='journalist',
            index=models.Index(fields=['code'], name='communicati_code_2556ce_idx'),
        ),
        migrations.AddIndex(
            model_name='journalist',
            index=models.Index(fields=['media_house'], name='communicati_media_h_8cb4df_idx'),
        ),
        migrations.AddIndex(
            model_name='journalist',
            index=models.Index(fields=['role'], name='communicati_role_5af796_idx'),
        ),
        migrations.AddIndex(
            model_name='journalist',
            index=models.Index(fields=['location'], name='communicati_locatio_851a19_idx'),
        ),
        migrations.AddIndex(
            model_name='journalist',
            index=models.Index(fields=['is_active'], name='communicati_is_acti_b10ee4_idx'),
        ),
    ]
