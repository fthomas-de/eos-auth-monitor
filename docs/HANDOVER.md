# Handover

Where the work stands and what is still open. `CLAUDE.md` holds the durable
rules for working on this app; this file holds the moment, and goes stale on
purpose - if a statement here contradicts the code, the code is right.

Last updated 2026-09-28.

## Release

- Version **0.0.1** in `eos_auth_monitor/__init__.py`, nothing committed yet
  beyond GitHub's initial commit (LICENSE, template `.gitignore`).
- Migrations **0001-0002** applied in `aa_dev`.
- 74 tests, all green; every check and access rule counter-checked against
  broken code (16 sabotages, each turned a test red).
- Installed editable into `~/aa-dev/venv` (`pip install --no-deps -e`), in
  `INSTALLED_APPS` of `~/aa-dev/working/myauth`, beat entry
  `eos_auth_monitor_update_snapshot` (every 30 min) in its `local.py`.
- No translations yet; all texts English.

## What the app does

| Page | Permission | What |
|---|---|---|
| Overview (`index`) | `view_all` | Cockpit and one tile per Corporation; `basic_access` alone is sent to its own Corporation, `manage_settings` alone to the settings |
| Corporation | `view_all`, or `basic_access` for the own main's Corporation | Tile per main with problem keywords; accounts with problems first |
| Account | as Corporation, by the account's main | Every character, each problem with description and detail |
| Corporation service | as Corporation | All characters of the Corporation's accounts, linked yes/no, problem characters marked |
| Service | `view_all` | Every main of the Alliance, linked yes/no |
| Settings | `manage_settings` | Alliance (Tom Select), stale limit, check and service switches |
| Rebuild (POST) | `view_all` or `manage_settings` | Starts the task |

Code layout: `checks.py` (registry of checks, groups, services),
`sources/` (one reader per foreign app, read only), `snapshot.py` (builds
the JSON, run by `tasks.update_snapshot`), `report.py` (labels, counts,
percentages for the templates), `views.py`, `forms.py`.

## Decisions the user made (2026-09-28)

- **Scope**: an account belongs to the overview when its main is in the
  configured Alliance; it sits on the main's Corporation tile. All its
  characters are checked, alts outside the Alliance included. First level
  shows the main with problem keywords, a click shows all characters with
  details.
- **Permissions**: `basic_access` (own main's Corporation), `view_all`
  (all Corporations), `manage_settings` (settings page). Plain members see
  nothing.
- **Computation**: Celery task plus stored result, not live on page load.
- **Stale after**: default follows corptools' `CT_CHAR_MAX_INACTIVE_DAYS`
  (stored as empty, resolved when the snapshot is built).
- **corptools Corporation audit** fails on: no audit, no token with the
  required scopes, **and** stale sections.
- **aa-structures** fails on: no owner, owner inactive, no enabled owner
  character, **and** `are_all_syncs_ok` false.
- **QQ** from aa-qqbot (`qqbot.Binding`), **Telegram** from
  aa-discord-telegram-bridge (`TelegramUser` with `telegram_user_id`),
  Discord and Mumble from Alliance Auth's own services.
- Install and register every new app in the dev instance, then run
  `migrate` and `collectstatic` (also in `/projekt-setup`).

## Pitfalls found

- `CharacterAudit.is_active()` **saves** the audit; the app reads the stored
  `active` flag instead.
- Alliance Auth wraps every `url_hook` view in `main_character_required`, so
  test users need a main character.
- `AuthUtils.add_main_character_2` creates no `CharacterOwnership`; deleting
  a main's ownership makes Auth clear the main. The snapshot keeps a main
  without ownership.
- `SOLO_CACHE = "default"` in the dev instance: tests must use
  `tests.base.MonitorTestCase` (`SOLO_CACHE=None`), or a test's configuration
  lands in the dev Redis. It happened once this session; cleared with
  `MonitorConfiguration.clear_cache()`.
- The running Celery worker (`-P solo`) has to be restarted to know the new
  task; until then *Rebuild now* queues a task nobody runs.

## Open points

- aa-structures, aa-qqbot and the Telegram bridge are not installed in the
  dev venv; their readers are tested with fakes of their models. Installing
  them would test against the real schema (ask first; pulls dependencies).
- Discord and Mumble services are not in the dev `INSTALLED_APPS` either.
- The wheel built by flit contains `eos_auth_monitor/tests`; the checklist
  (1.3.2) wants tests out of the package.
- Raise the `allianceauth` lower bound once the code relies on something
  newer than 5.0 - `framework/header/page-header.html` is used; check which
  release introduced it.
- Performance with a large Alliance is untested: the character check reads
  all tokens with their scopes in one query.

## Dev instance

- Repo `~/aa-dev/working/eos-auth-monitor`, remote
  `https://github.com/fthomas-de/eos-auth-monitor.git`, branch `main`.
- `MonitorConfiguration` in `aa_dev`: Alliance 99003995 (Invidia Gloriae
  Comes), nothing switched off; a snapshot is stored (32 Corporations,
  1 account).
- Installed: allianceauth 5.3.1, allianceauth-corptools 3.5.0, django-solo
  2.5.1. Target production per checklist: AA 5.4.0, corptools 3.5.0,
  aa-structures 4.0.1 (field names checked against the 4.0.1 tag).
