"""AppConfig for the Communications module.

Loads configuration (rights + seed flags) from ``core.ModuleConfiguration`` and performs
idempotent ``post_migrate`` seeding of rights, default categories and default channels —
mirroring the ``training`` module. Module number = ``22`` (rights ``22xxxx``).
"""
import logging
import uuid

from django.apps import AppConfig
from django.db.models.signals import post_migrate

logger = logging.getLogger(__name__)

MODULE_NAME = 'communications'
IMIS_ADMINISTRATOR_SYSTEM = 64

DEFAULT_CATEGORIES = [
    ('MEDIA_ENGAGEMENT', 'Media Engagement'),
    ('CONTENT_REPORTING', 'Content & Reporting'),
    ('OUTREACH', 'Outreach'),
    ('GENERAL', 'General'),
]

# Multi-level stakeholder taxonomy (the "Who").
DEFAULT_STAKEHOLDER_TYPES = [
    ('MINISTER', 'Minister', 'NATIONAL'),
    ('MP', 'Member of Parliament', 'NATIONAL'),
    ('NATIONAL_DIRECTORATE', 'National Directorate', 'NATIONAL'),
    ('RC', 'Regional Commissioner', 'REGIONAL'),
    ('RAS', 'Regional Administrative Secretary', 'REGIONAL'),
    ('TMO', 'Town Municipal Officer', 'PAA'),
    ('DED', 'District Executive Director', 'PAA'),
    ('DAS', 'District Administrative Secretary', 'PAA'),
    ('VEO', 'Village Executive Officer', 'COMMUNITY'),
    ('VILLAGE_COUNCIL', 'Village Council', 'COMMUNITY'),
    ('CMC', 'Community Management Committee', 'COMMUNITY'),
    ('LSP', 'Local Service Provider', 'COMMUNITY'),
]

DEFAULT_CHANNELS = [
    ('EMAIL', 'Email', 'EMAIL'),
    ('SMS', 'SMS', 'SMS'),
    ('SOCIAL', 'Social Media', 'SOCIAL'),
    ('RADIO', 'Radio', 'RADIO'),
    ('TV', 'Television', 'TV'),
    ('PRINT', 'Print', 'PRINT'),
    ('WEB', 'Website / Portal', 'WEB'),
]

DEFAULT_CONFIG = {
    # Activity
    'gql_activity_search_perms': ['220101'],
    'gql_activity_create_perms': ['220102'],
    'gql_activity_update_perms': ['220103'],
    'gql_activity_delete_perms': ['220104'],
    'gql_activity_approve_perms': ['220110'],
    # Category
    'gql_category_search_perms': ['220201'],
    'gql_category_create_perms': ['220202'],
    'gql_category_update_perms': ['220203'],
    'gql_category_delete_perms': ['220204'],
    # Channel
    'gql_channel_search_perms': ['220301'],
    'gql_channel_create_perms': ['220302'],
    'gql_channel_update_perms': ['220303'],
    'gql_channel_delete_perms': ['220304'],
    'gql_channel_dispatch_perms': ['220305'],
    # Activity-channel
    'gql_activity_channel_search_perms': ['220401'],
    'gql_activity_channel_create_perms': ['220402'],
    'gql_activity_channel_update_perms': ['220403'],
    'gql_activity_channel_delete_perms': ['220404'],
    # Objective
    'gql_objective_search_perms': ['220501'],
    'gql_objective_create_perms': ['220502'],
    'gql_objective_update_perms': ['220503'],
    'gql_objective_delete_perms': ['220504'],
    # Assignment
    'gql_assignment_search_perms': ['220601'],
    'gql_assignment_create_perms': ['220602'],
    'gql_assignment_update_perms': ['220603'],
    'gql_assignment_delete_perms': ['220604'],
    # Attachment
    'gql_attachment_search_perms': ['220701'],
    'gql_attachment_upload_perms': ['220702'],
    'gql_attachment_delete_perms': ['220704'],
    # Feedback
    'gql_feedback_search_perms': ['220801'],
    'gql_feedback_create_perms': ['220802'],
    'gql_feedback_update_perms': ['220803'],
    'gql_feedback_delete_perms': ['220804'],
    # Template
    'gql_template_search_perms': ['220901'],
    'gql_template_create_perms': ['220902'],
    'gql_template_update_perms': ['220903'],
    'gql_template_delete_perms': ['220904'],
    # Stakeholder list (+ entries)
    'gql_stakeholder_search_perms': ['221001'],
    'gql_stakeholder_create_perms': ['221002'],
    'gql_stakeholder_update_perms': ['221003'],
    'gql_stakeholder_delete_perms': ['221004'],
    # Library asset
    'gql_library_search_perms': ['221101'],
    'gql_library_upload_perms': ['221102'],
    'gql_library_update_perms': ['221103'],
    'gql_library_delete_perms': ['221104'],
    # Dashboard / calendar
    'gql_dashboard_view_perms': ['221201'],
    # Stakeholder type (taxonomy)
    'gql_stakeholder_type_search_perms': ['221301'],
    'gql_stakeholder_type_create_perms': ['221302'],
    'gql_stakeholder_type_update_perms': ['221303'],
    'gql_stakeholder_type_delete_perms': ['221304'],
    # Activity audience
    'gql_audience_search_perms': ['221401'],
    'gql_audience_create_perms': ['221402'],
    'gql_audience_update_perms': ['221403'],
    'gql_audience_delete_perms': ['221404'],
    # Communication feed posts
    'gql_post_search_perms': ['221501'],
    'gql_post_create_perms': ['221502'],
    'gql_post_update_perms': ['221503'],
    'gql_post_delete_perms': ['221504'],
    'gql_post_publish_perms': ['221505'],
    # Conflict detection (staff double-booking) — configurable
    'conflict_check_enabled': True,
    'conflict_hard_types': ['STAFF'],
    'conflict_soft_types': ['LOCATION'],
    # Seeding
    'seed_categories': True,
    'seed_channels': True,
    'seed_stakeholder_types': True,
}

ALL_RIGHTS = [
    220101, 220102, 220103, 220104, 220110,
    220201, 220202, 220203, 220204,
    220301, 220302, 220303, 220304, 220305,
    220401, 220402, 220403, 220404,
    220501, 220502, 220503, 220504,
    220601, 220602, 220603, 220604,
    220701, 220702, 220704,
    220801, 220802, 220803, 220804,
    220901, 220902, 220903, 220904,
    221001, 221002, 221003, 221004,
    221101, 221102, 221103, 221104,
    221201,
    221301, 221302, 221303, 221304,
    221401, 221402, 221403, 221404,
    221501, 221502, 221503, 221504, 221505,
]


class CommunicationsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = MODULE_NAME

    # rights (populated from config)
    gql_activity_search_perms = []
    gql_activity_create_perms = []
    gql_activity_update_perms = []
    gql_activity_delete_perms = []
    gql_activity_approve_perms = []
    gql_category_search_perms = []
    gql_category_create_perms = []
    gql_category_update_perms = []
    gql_category_delete_perms = []
    gql_channel_search_perms = []
    gql_channel_create_perms = []
    gql_channel_update_perms = []
    gql_channel_delete_perms = []
    gql_channel_dispatch_perms = []
    gql_activity_channel_search_perms = []
    gql_activity_channel_create_perms = []
    gql_activity_channel_update_perms = []
    gql_activity_channel_delete_perms = []
    gql_objective_search_perms = []
    gql_objective_create_perms = []
    gql_objective_update_perms = []
    gql_objective_delete_perms = []
    gql_assignment_search_perms = []
    gql_assignment_create_perms = []
    gql_assignment_update_perms = []
    gql_assignment_delete_perms = []
    gql_attachment_search_perms = []
    gql_attachment_upload_perms = []
    gql_attachment_delete_perms = []
    gql_feedback_search_perms = []
    gql_feedback_create_perms = []
    gql_feedback_update_perms = []
    gql_feedback_delete_perms = []
    gql_template_search_perms = []
    gql_template_create_perms = []
    gql_template_update_perms = []
    gql_template_delete_perms = []
    gql_stakeholder_search_perms = []
    gql_stakeholder_create_perms = []
    gql_stakeholder_update_perms = []
    gql_stakeholder_delete_perms = []
    gql_library_search_perms = []
    gql_library_upload_perms = []
    gql_library_update_perms = []
    gql_library_delete_perms = []
    gql_dashboard_view_perms = []
    gql_stakeholder_type_search_perms = []
    gql_stakeholder_type_create_perms = []
    gql_stakeholder_type_update_perms = []
    gql_stakeholder_type_delete_perms = []
    gql_audience_search_perms = []
    gql_audience_create_perms = []
    gql_audience_update_perms = []
    gql_audience_delete_perms = []
    gql_post_search_perms = []
    gql_post_create_perms = []
    gql_post_update_perms = []
    gql_post_delete_perms = []
    gql_post_publish_perms = []
    # behaviour
    conflict_check_enabled = True
    conflict_hard_types = []
    conflict_soft_types = []
    seed_categories = True
    seed_channels = True
    seed_stakeholder_types = True

    def ready(self):
        from core.models import ModuleConfiguration
        cfg = ModuleConfiguration.get_or_default(MODULE_NAME, DEFAULT_CONFIG)
        self.__load_config(cfg)
        post_migrate.connect(on_post_migrate, sender=self)

    @classmethod
    def __load_config(cls, cfg):
        for field in cfg:
            if hasattr(CommunicationsConfig, field):
                setattr(CommunicationsConfig, field, cfg[field])


def on_post_migrate(sender, **kwargs):
    apps = kwargs.get('apps')
    try:
        _seed_admin_rights(apps)
    except Exception as exc:
        logger.warning("communications: rights seeding skipped (%s)", exc)
    try:
        if CommunicationsConfig.seed_categories:
            _seed_categories(apps)
        if CommunicationsConfig.seed_channels:
            _seed_channels(apps)
        if CommunicationsConfig.seed_stakeholder_types:
            _seed_stakeholder_types(apps)
    except Exception as exc:
        logger.warning("communications: reference-data seeding skipped (%s)", exc)


def _seed_admin_rights(apps):
    Role = apps.get_model('core', 'Role')
    RoleRight = apps.get_model('core', 'RoleRight')
    role = Role.objects.filter(is_system=IMIS_ADMINISTRATOR_SYSTEM, validity_to__isnull=True).first()
    if not role:
        return
    for right_id in ALL_RIGHTS:
        if not RoleRight.objects.filter(role=role, right_id=right_id, validity_to__isnull=True).exists():
            RoleRight.objects.create(role=role, right_id=right_id, audit_user_id=1)


def _seed_categories(apps):
    ActivityCategory = apps.get_model('communications', 'ActivityCategory')
    User = apps.get_model('core', 'User')
    admin = User.objects.order_by('id').first()
    if not admin:
        return
    for code, name in DEFAULT_CATEGORIES:
        if not ActivityCategory.objects.filter(code=code).exists():
            ActivityCategory.objects.create(
                id=uuid.uuid4(), code=code, name=name, is_active=True, version=1,
                user_created_id=admin.id, user_updated_id=admin.id)


def _seed_channels(apps):
    Channel = apps.get_model('communications', 'Channel')
    User = apps.get_model('core', 'User')
    admin = User.objects.order_by('id').first()
    if not admin:
        return
    for code, name, ctype in DEFAULT_CHANNELS:
        if not Channel.objects.filter(code=code).exists():
            Channel.objects.create(
                id=uuid.uuid4(), code=code, name=name, channel_type=ctype, config={},
                is_active=True, version=1, user_created_id=admin.id, user_updated_id=admin.id)


def _seed_stakeholder_types(apps):
    StakeholderType = apps.get_model('communications', 'StakeholderType')
    User = apps.get_model('core', 'User')
    admin = User.objects.order_by('id').first()
    if not admin:
        return
    for code, name, level in DEFAULT_STAKEHOLDER_TYPES:
        if not StakeholderType.objects.filter(code=code).exists():
            StakeholderType.objects.create(
                id=uuid.uuid4(), code=code, name=name, level=level, is_active=True,
                version=1, user_created_id=admin.id, user_updated_id=admin.id)
