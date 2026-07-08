# openIMIS Communications Module (backend)

`openimis-be-communications_py` — Communication Activity management for TASAF / CoreMIS.
Module number **22** (rights `22xxxx`). Patterned on the `training` module and
`tasks_management`.

Provides: Communication Activities with a status workflow (Draft → Submitted →
Approved → Scheduled → Ongoing → Completed → Closed → Archived / Cancelled), multiple
channels per activity (with a dispatch/"blast" stub), measurable objectives (with
MIS-tracked achievement), staff assignments, file attachments, feedback, a calendar and
dashboard, and a library repository (templates, stakeholder lists, reusable assets).

GraphQL CRUD + status transitions; DRF endpoints for file upload/download. Rights and
reference data (categories, channels) are seeded idempotently on `post_migrate`.

## Developer Guide

Start with `communications/models.py` for the activity, audience, feed, library
and mutation-journal entities. Workflow rules and dashboard aggregation live in
`communications/services.py`; GraphQL mutations are in
`communications/gql_mutations.py`; upload/download endpoints are in
`communications/views.py`.

The module uses rights in the `22xxxx` range, defined in
`communications/apps.py::DEFAULT_CONFIG`. Keep those values aligned with the
frontend constants and menu filters.

The frontend companion is `openimis-fe-communications_js`. It expects the backend
GraphQL names and REST paths under `/api/communications/...` to remain stable.
Run `python manage.py makemigrations communications` only for schema changes, then
`python manage.py migrate`.
