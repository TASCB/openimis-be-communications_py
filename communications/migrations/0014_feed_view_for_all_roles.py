from django.db import migrations

FEED_VIEW = 221501


def grant(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            INSERT INTO "tblRoleRight" ("RoleID", "RightID", "ValidityFrom", "AuditUserId")
            SELECT r."RoleID", %s, NOW(), 1
            FROM "tblRole" r
            WHERE r."ValidityTo" IS NULL
              AND NOT EXISTS (
                  SELECT 1 FROM "tblRoleRight" x
                  WHERE x."RoleID" = r."RoleID" AND x."RightID" = %s AND x."ValidityTo" IS NULL
              )
            """,
            [FEED_VIEW, FEED_VIEW],
        )


def revoke(apps, schema_editor):
    with schema_editor.connection.cursor() as cursor:
        cursor.execute(
            """
            DELETE FROM "tblRoleRight" rr
            WHERE rr."RightID" = %s
              AND NOT EXISTS (
                  SELECT 1 FROM "tblRoleRight" x
                  WHERE x."RoleID" = rr."RoleID" AND x."ValidityTo" IS NULL
                    AND x."RightID" BETWEEN 220000 AND 229999 AND x."RightID" <> %s
              )
            """,
            [FEED_VIEW, FEED_VIEW],
        )


class Migration(migrations.Migration):

    dependencies = [
        ('communications', '0013_activity_event_type'),
    ]

    operations = [migrations.RunPython(grant, revoke)]
