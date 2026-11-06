from django.apps import apps as global_apps
from django.db import migrations

FLOW = 'COMMUNICATION_POST_APPROVAL'
PUBLISH_RIGHT = '221505'


def forwards(apps, schema_editor):
    """Post approval moves to the publish right; admin-edited flows are left alone."""
    try:
        ApprovalFlow = apps.get_model('approval', 'ApprovalFlow')
    except LookupError:
        return
    for flow in ApprovalFlow.objects.filter(code=FLOW, is_user_managed=False):
        config = flow.config or {}
        steps = config.get('steps') or []
        if [s.get('required_right') for s in steps] != ['220110']:
            continue
        config['steps'] = [{'code': 'PUBLISHER', 'label': 'Communications Manager', 'required_right': PUBLISH_RIGHT}]
        flow.config = config
        flow.save(update_fields=['config'])


class Migration(migrations.Migration):
    dependencies = [('communications', '0014_feed_view_for_all_roles')] + (
        [('approval', '0004_approvalstep_assigned_group_id')] if global_apps.is_installed('approval') else [])
    operations = [migrations.RunPython(forwards, migrations.RunPython.noop)]
