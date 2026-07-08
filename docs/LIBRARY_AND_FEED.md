# Communications — Library consumption & Feed behaviour (current state + planned work)

> Status: **Phase 1 = built but not yet fully consumed.** This document records how the
> Library and the Communication Feed behave today, the gaps against the requirements,
> and the agreed next pass. See [[project_communications_module]] in memory.

## 1. Communication Library — where it is consumed

### Today (Phase 1)
The Library is a **standalone repository** with three tabs in `LibraryPage`:
- **Templates** (`CommunicationTemplate`: channel type, subject, body) — full CRUD.
- **Stakeholder Lists** (`StakeholderList` + `StakeholderListEntry`) — reusable recipient lists.
- **Assets** (`LibraryAsset`) — uploaded reusable files (logos, brand, media, docs).

These are created/managed, but **nothing else reads them yet** — they are not pulled
into the activity or dispatch flow.

### Planned consumption points (to build)
1. **Templates** → "Use template" picker that prefills:
   - the **Feed post / newsletter** composer (subject/body), and
   - a **channel message** in the Channels tab (for the dispatch/"blast").
2. **Stakeholder Lists** → "Add from stakeholder list" in the **Audience** tab, to bulk‑add
   `ActivityAudience` rows from a saved list (instead of picking types one by one).
3. **Assets** → "Attach from library" in the **Attachments** tab, to link an existing
   `LibraryAsset` to an activity without re‑uploading.

## 2. Communication Feed — publish behaviour

### Today (Phase 1)
- `publishCommunicationPost` → `CommunicationPostService.set_published(id, True)` sets
  `is_published = True` and stamps `published_at = now()`; `unpublish…` reverses it.
- The FeedPage chip flips **Draft ⇄ Published** and the icon toggles.

### Gaps (vs requirements)
- **Visibility is NOT gated on publish.** `resolve_communication_post` returns *all*
  non‑deleted posts (drafts included) to anyone with `gql_post_search_perms`. Publishing
  currently only changes the badge/timestamp, not *who can see* the post.
- **Newsletter** is only a `post_type` label — no "generate from activity/posts" or
  archive logic.
- **Posts cannot carry attachments yet.**

## 3. Planned next pass (agreed scope)

1. **Feed visibility gating** — general users see only `is_published = True` posts; drafts
   visible only to authors / `RIGHT_POST_MANAGE` holders, so publishing genuinely controls
   global visibility ("all users see published updates").
2. **Library consumption** — the three hooks in §1.
3. **Newsletter generation** — a "Generate newsletter" action composing a `NEWSLETTER`
   post from selected published activities/posts, then archived in the feed.
4. **Post attachments (NEW requirement)** — a post can include one or more attachments,
   with a mechanism to view/download them:
   - **Backend:** new `CommunicationPostAttachment` (HistoryModel: `post` FK, `file_name`,
     `file_type`, `file` FileField, `description`) + `*Mutation` journal; DRF upload/download
     endpoints (`/communications/posts/<id>/attachments/upload|<id>/download`); delete
     mutation; rights under the post band (e.g. `221506` upload / `221507` delete) or reuse
     `gql_post_*`; query `communicationPostAttachment(postId: ...)`.
   - **Frontend:** in the Feed composer, allow attaching files when creating a post; on
     each rendered post, list attachments with download links (and inline preview for
     images/PDF where feasible). Reuse the attachment upload/list pattern already used by
     `AttachmentsPanel` (activity attachments).

## 4. Notes / conventions to follow when building the above
- Files via **DRF multipart** endpoints (GraphQL = metadata + delete), like
  `ActivityAttachment` / `LibraryAsset`.
- FK **filters** need the encoded relay id (`encId`), mutation inputs need decoded pks
  (`decId`); datetimes naive (USE_TZ=False).
- New rights must be added to `apps.py` `ALL_RIGHTS` + `DEFAULT_CONFIG` and re‑seeded
  (log out/in to refresh session rights).
- New menu items must also be added to the DB `core_ModuleConfiguration` `fe-core`
  `menus[].submenus[]` (config‑driven menus) and `src/modules.js` regenerated via
  `yarn load-config` after `openimis.json` changes.
