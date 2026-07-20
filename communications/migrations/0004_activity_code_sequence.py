from django.db import migrations, models
import uuid


def seed_communication_sequence(apps, schema_editor):
    CommunicationActivity = apps.get_model('communications', 'CommunicationActivity')
    ActivityCodeSequence = apps.get_model('communications', 'ActivityCodeSequence')
    prefix = 'COM'
    last_number = 0
    for code in CommunicationActivity.objects.filter(code__startswith=prefix).values_list('code', flat=True):
        suffix = code[len(prefix):]
        if suffix.isdigit():
            last_number = max(last_number, int(suffix))
    ActivityCodeSequence.objects.get_or_create(
        prefix=prefix,
        defaults={'id': uuid.uuid4(), 'last_number': last_number},
    )


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0003_communicationpostattachment_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityCodeSequence',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('prefix', models.CharField(max_length=16, unique=True)),
                ('last_number', models.PositiveIntegerField(default=0)),
            ],
            options={
                'db_table': 'tblCommunicationActivityCodeSequence',
            },
        ),
        migrations.RunPython(seed_communication_sequence, migrations.RunPython.noop),
    ]
