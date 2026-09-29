# Handover

Where the work stands and what is still open. `CLAUDE.md` holds the durable
rules for working on this app; this file holds the moment, and goes stale on
purpose - if a statement here contradicts the code, the code is right.

Last updated 2026-09-29.

## Release

- Version **0.0.1**, the first release (see `CHANGELOG.md`). Pushed to
  `origin/main`. Tag `v0.0.1` exists **locally** on the release commit
  0b472f6, not pushed yet (`git push origin v0.0.1`).
- Migrations **0001-0003** applied in `aa_dev`.
- 175 tests, all green (`eos-test eos_auth_monitor --exclude-tag
  translations`); every check, access rule and new feature counter-checked
  against broken code (37 sabotages over the session, each turned a test red).
- No translations yet; all texts English (`## Release` says "none yet").

## What the app does

| Page | Permission | What |
|---|---|---|
| Overview (`index`) | `view_all` | Cockpit (percentages, a Connections tile) and one tile per Corporation listing each app with its share; `basic_access` alone is sent to its own Corporation, `manage_settings` alone to the settings |
| Corporation | `view_all`, or `basic_access` for the own main's Corporation | Every member reduced to mains: own mains as tiles with problem keywords, members whose main is elsewhere, members not registered (sortable table) |
| Account | as Corporation, by the account's main | Every character, each problem with description and detail |
| Corporation service | as Corporation | All characters of the Corporation's accounts, linked yes/no, problem characters marked |
| Service | `view_all` | Every main of the Alliance, linked yes/no |
| Settings | `manage_settings` | Alliance (Tom Select), stale limit, ESI member lists on/off, check and service switches, corptools sections and scopes |
| Rebuild (POST) / progress (JSON) | `view_all` or `manage_settings` / any app permission | Start the task / state for the progress bar |

Code layout: `checks.py` (registry of checks, groups, services),
`sources/` (one reader per foreign app, read only; `members.py` is the one
ESI call), `snapshot.py` (builds the JSON, run by `tasks.update_snapshot`),
`progress.py` (task state in the cache), `metrics.py` (times and counts a build,
stored under `metrics` in the snapshot, footer `partials/metrics.html`), `report.py` (labels, counts,
percentages for the templates), `smart_filters.py` + `models.AccountProblemsFilter`
(securegroups), `views.py`, `forms.py`. JS: `tables.js` (DataTables),
`progress.js`, `searchable.js` (Tom Select).

## Decisions the user made (2026-09-28)

- **Scope**: an account belongs to the overview when its main is in the
  configured Alliance; it sits on the main's Corporation tile. All its
  characters are checked, alts outside the Alliance included.
- **Corporation page**: every member of the Corporation, reduced to mains
  where Auth knows the account; unknown counts as a main.
- **Member lists from ESI** (`GET /corporations/{id}/members/` plus
  `/universe/names/`) with tokens corptools already has - corptools stores no
  member list. Can be switched off in the settings.
- **Permissions**: `basic_access` (own main's Corporation), `view_all`
  (all Corporations), `manage_settings` (settings page).
- **Computation**: Celery task plus stored result; progress bar while it runs.
- **Stale after**: default follows corptools' `CT_CHAR_MAX_INACTIVE_DAYS`.
- **corptools checks** can leave out single sections and scopes (e.g. Moon
  Observations) - four checkbox lists in the settings.
- **aa-structures** fails on: no owner, owner inactive, no enabled owner
  character, `are_all_syncs_ok` false.
- **QQ** from aa-qqbot (`qqbot.Binding`), **Telegram** from
  aa-discord-telegram-bridge (`TelegramUser` with `telegram_user_id`),
  Discord and Mumble from Alliance Auth's own services.
- Install and register every new app in the dev instance, then run
  `migrate` and `collectstatic` (also in `/projekt-setup`).
- Corporation-level rows on a tile (Corporation Audit, Structures) show
  100 % or 0 %: the checks pass or fail as a whole; the failed checks are the
  tooltip.

## Pitfalls found

- `CharacterAudit.is_active()` **saves** the audit. "Audit inactive" is
  computed by `sources.corptools.character_sections()`, which repeats its
  conditions - compare after every corptools upgrade.
- Alliance Auth wraps every `url_hook` view in `main_character_required`, so
  test users need a main character.
- `AuthUtils.add_main_character_2` creates no `CharacterOwnership`; deleting
  a main's ownership makes Auth clear the main.
- The dev instance points `SOLO_CACHE` and the default cache at its Redis:
  tests use `tests.base.MonitorTestCase` (and must call `super().setUp()`),
  which switches the solo cache off and uses a memory cache. A leak happened
  once; cleared with `MonitorConfiguration.clear_cache()`.
- The running Celery worker (`-P solo`) has to be restarted to know
  `eos_auth_monitor.tasks.update_snapshot`; until then *Rebuild now* queues a
  task nobody runs and the bar waits.
- A test module takes ~30 s (test database); a full sabotage round of 20
  cases runs about 10 minutes - start it in the background.

## Open points / next steps

- Push the tag `v0.0.1` (checklist 1.2.2); it only exists locally.
- Since 2026-09-29 the dev instance has aa-structures 4.0.1, securegroups
  0.10.2, aa-qqbot 1.0.0, the Telegram bridge 1.7.6, Discord and Mumble in
  `INSTALLED_APPS`, so the readers ran against the real schemas (`user`
  one-to-one in each service model). The dev DB has one account and no
  links yet: every service number is 0, and aa-structures' own tables hold
  no owner. Tests that assumed aa-structures absent were made independent
  of what is installed. Not checked: that the snapshot of a large,
  really linked Alliance counts right - only fakes and the empty dev data.
- The `allianceauth>=5.0` bound was checked by reading the tags (page-header,
  DataTables 2 bundles and template tags exist in 5.0.0; its django-esi 9.0
  has the ESI client calls used). Never run against 5.0 itself.
- Performance with a large Alliance is untested (the footer with the build
  figures - seconds per step, queries, sizes - is there to measure it): the character check reads
  all tokens with their scopes in one query; the member lists cost one ESI
  call per Corporation per run (cached by django-esi).
- Translations (de, ru, zh_Hans like the sister apps) once the texts settle.

## Dev instance

- Repo `~/aa-dev/working/eos-auth-monitor`, remote
  `https://github.com/fthomas-de/eos-auth-monitor.git`, branch `main`.
- Installed editable into `~/aa-dev/venv` (`pip install --no-deps -e`), in
  `INSTALLED_APPS` of `~/aa-dev/working/myauth`, beat entry
  `eos_auth_monitor_update_snapshot` (every 30 min) in its `local.py`.
- `MonitorConfiguration` in `aa_dev`: Alliance 99003995 (Invidia Gloriae
  Comes), nothing switched off, member lists on. A snapshot is stored:
  32 Corporations, member list read for Ether Element only (279 members,
  277 not registered) - the other Corporations have no token with the
  membership scope.
- Installed: allianceauth 5.3.1, allianceauth-corptools 3.5.0, django-solo
  2.5.1. Target production per checklist: AA 5.4.0, corptools 3.5.0,
  aa-structures 4.0.1 (field names checked against the 4.0.1 tag).
