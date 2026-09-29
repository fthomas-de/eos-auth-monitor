# Handover

Where the work stands and what is still open. `CLAUDE.md` holds the durable
rules for working on this app; this file holds the moment, and goes stale on
purpose - if a statement here contradicts the code, the code is right.

Last updated 2026-09-29.

## Release

- Version **0.0.1**, the first release (see `CHANGELOG.md`, which holds
  everything done so far under 0.0.1: it was never pushed before, `origin`
  had only the initial commit). The tag `v0.0.1` is set on the release commit
  and pushed with it.
- Migrations **0001-0004** applied in `aa_dev` (0004 only renames the ESI
  switch, a no-op in SQL).
- 187 tests without the translation tests, 3 translation tests, all green.
  Every check, access rule and feature was counter-checked against broken
  code (a sabotage that stays green means the test is too weak - it happened
  five times and each was fixed; the latest features went nine for nine).
- Translated into de, ru and zh_Hans, machine-generated and marked so in the
  `.po` header; see `## Translations` in `CLAUDE.md`. The catalogues are only
  brought up to date at `/commit`.

## What the app does

| Page | Permission | What |
|---|---|---|
| Overview (`index`) | `view_all` | Cockpit (service shares, a Connections tile, audit shares) and one tile per Corporation, most problems first, with a filter box; each tile lists mains, characters, and each app with its share. `basic_access` alone is sent to its own Corporation, `manage_settings` alone to the settings |
| Corporation | `view_all`, or `basic_access` for the own main's Corporation | Service tiles, then own mains as cards (most problems first) with problem keywords, members whose main is elsewhere, members not registered in Auth as cards |
| Account | as Corporation, by the account's main | One green/red tile per service (links to the Corporation's list of it), every character, each problem with description and detail |
| Corporation service | as Corporation | All characters of the Corporation's accounts, linked yes/no, problem characters marked |
| Service | `view_all` | Every main of the Alliance, linked yes/no |
| Settings | `manage_settings` | Alliance (Tom Select), stale limit, ESI member lists on/off (also switches the roles call), check and service switches, corptools sections and scopes |
| Rebuild (POST) / progress (JSON) | `view_all` or `manage_settings` / any app permission | Start the task / state for the progress bar |

Every page has a footer with the cost of the last rebuild (`view_all` or
`manage_settings` only).

Code layout: `checks.py` (registry of checks, groups, services),
`sources/` (one reader per foreign app, read only; `members.py` holds the two
ESI calls: member list and roles), `snapshot.py` (builds the JSON, run by
`tasks.update_snapshot`), `metrics.py` (times and counts a build, stored under
`metrics` in the snapshot), `progress.py` (task state in the cache),
`report.py` (labels, counts, percentages, sort orders for the templates),
`smart_filters.py` + `models.AccountProblemsFilter` (securegroups),
`views.py`, `forms.py`. JS: `tables.js` (DataTables), `progress.js`,
`searchable.js` (Tom Select), `filter.js` (live filter of the overview tiles).
Partials: `gauge.html` (a statistic tile), `corporation-rows.html`,
`metrics.html`. Translations: `tools/glossary.py`, `tools/translate.py`.

## Decisions the user made

2026-09-28:

- **Scope**: an account belongs to the overview when its main is in the
  configured Alliance; it sits on the main's Corporation tile. All its
  characters are checked, alts outside the Alliance included.
- **Corporation page**: every member of the Corporation, reduced to mains
  where Auth knows the account; unknown counts as a main.
- **Member lists from ESI** with tokens corptools already has - corptools
  stores no member list. Can be switched off in the settings.
- **Permissions**: `basic_access` (own main's Corporation), `view_all`
  (all Corporations), `manage_settings` (settings page).
- **Computation**: Celery task plus stored result; progress bar while it runs.
- **Stale after**: default follows corptools' `CT_CHAR_MAX_INACTIVE_DAYS`.
- **corptools checks** can leave out single sections and scopes.
- **aa-structures** fails on: no owner, owner inactive, no enabled owner
  character, `are_all_syncs_ok` false.
- **QQ** from aa-qqbot (`qqbot.Binding`), **Telegram** from
  aa-discord-telegram-bridge (`TelegramUser` with `telegram_user_id`),
  Discord and Mumble from Alliance Auth's own services.
- Install and register every new app in the dev instance, then run
  `migrate` and `collectstatic` (also in `/projekt-setup`).
- Corporation-level rows on a tile (Corporation Audit, Structures) show
  100 % or 0 %.

2026-09-29:

- **Unknown members are mains that linked nothing**: the cockpit's and the
  tiles' service shares count them in the total wherever the member list
  could be read. The Connections tile still counts real links only.
- **Character count per Corporation** from `EveCorporationInfo.member_count`
  (Auth's own, no token); the member list wins where it was read.
- **Everything is sorted by number of problems**, most first, then by name:
  Corporation tiles, mains, characters, the service lists.
- **Director check** ("Director token missing"): a Director without a token
  carrying all Corporation-audit scopes. Directors come from corptools' roles
  and from ESI (`GET /corporations/{id}/roles`, token of a character corptools
  knows as Director) - corptools never reads the roles of a character without
  a token, so Nah vi in Ether Element was invisible to it.
- The account page shows the account's own service links as green/red tiles
  and no longer the Corporation's shares in the header.
- Translations in de, ru, zh_Hans at every `/commit`, like eos-invoices.
- **Cockpit tiles without a page of their own** (Character Audit, Corporation
  Audit, Structures) link to Auth's `/services/`. The Members registered tile
  and the Corporation tile rows have no link of their own.
- **"No Director token"** marks a Corporation where no Director's token could
  read the roles: a badge on the overview tile and the Corporation page, *not*
  a problem - no percentage, sorting or border colour changes. Set only while
  the ESI switch and the Director check are on; a Corporation of the Alliance
  without any account in Auth is asked as well.
- The ESI switch is called **Fetch data from ESI** (it also covers the roles).

## Pitfalls found

- `CharacterAudit.is_active()` **saves** the audit. "Audit inactive" is
  computed by `sources.corptools.character_sections()`, which repeats its
  conditions - compare after every corptools upgrade.
- Alliance Auth wraps every `url_hook` view in `main_character_required`, so
  test users need a main character.
- `AuthUtils.add_main_character_2` creates no `CharacterOwnership`; deleting
  a main's ownership makes Auth clear the main.
- The dev instance points `SOLO_CACHE` and the default cache at its Redis:
  tests use `tests.base.MonitorTestCase` (and must call `super().setUp()`).
- The running Celery worker (`-P solo`) does not reload code: after any change
  it has to be restarted, or *Rebuild now* builds with the old code, and a
  new task name is queued for nobody.
- A snapshot is a stored result: after installing an app or changing a check
  the pages show the old one until it is rebuilt.
- A new static file breaks every view test until `collectstatic` has run
  (`sri_static` reads the manifest); a new template partial does not.
- Test assertions on the overview or Corporation page must be specific: the
  header buttons and the tiles carry the same URL and the same percentage, so
  a loose `assertContains` stays green when the tile is gone.
- A full test run occasionally hangs for minutes; run sabotage rounds as a
  script in the background and never start a second run meanwhile, or a
  half-sabotaged file is left behind. Restore from a `cp` made just before.
- `eos-test` takes one test label per call; run several modules one after
  the other. A full run takes about 15 s; only a sabotage round of many
  reruns is long - start it in the background.
- Do not put a Python patch into `wsl.exe -e bash -lc '...'`: an apostrophe
  in `Auth's` ends the quoted string. Write the script with the Write tool
  into the scratchpad and run it by its `/mnt/c/...` path.
- `.git/CLAUDE_COMMIT_MSG` must be *read* before it is written again, or the
  Write tool refuses and `git commit -F` silently reuses the old message.

## Open points / next steps

- Nothing was looked at in a browser: the pages need a login. `filter.js`, the
  tiles and the footer are covered by tests of the rendered HTML only.
- The service lists behind a tile show the registered mains only, while the
  tile's total also counts unknown members.
- A Director whose roles neither corptools nor ESI (no Director token in the
  Corporation) could read is not found; such Corporations carry the marker
  "No Director token". In the dev instance 31 of 32 Corporations have it, so
  the badge is nearly everywhere there - the user has not yet judged whether
  it should be quieter (e.g. only where Auth knows mains).
- Performance with a large Alliance is untested; the footer with the build
  figures is there to measure it. The character check reads all tokens with
  their scopes in one query; the member lists and roles cost up to two ESI
  calls per Corporation per run (cached by django-esi).
- The `allianceauth>=5.0` bound was checked by reading the tags, never run
  against 5.0 itself.
- The translations are machine-generated: a native speaker should read them.

## Dev instance

- Repo `~/aa-dev/working/eos-auth-monitor`, remote
  `https://github.com/fthomas-de/eos-auth-monitor.git`, branch `main`.
- Installed editable into `~/aa-dev/venv`, in `INSTALLED_APPS` of
  `~/aa-dev/working/myauth`, beat entry `eos_auth_monitor_update_snapshot`
  (every 30 min) in its `local.py`. Also installed there (by the user):
  aa-structures 4.0.1, securegroups 0.10.2, aa-qqbot 1.0.0, the Telegram
  bridge 1.7.6, Discord and Mumble - the readers ran against the real schemas.
  The dev DB has one account and no service links: every service number is 0.
- `MonitorConfiguration` in `aa_dev`: Alliance 99003995 (Invidia Gloriae
  Comes), nothing switched off, ESI on. The Celery worker was restarted
  after the last code change (started from a shell, log in `/tmp/celery-eos.log`
  in WSL, not from a terminal tab) and the snapshot rebuilt by hand at 11:14
  (WSL clock): the code is current. Ether Element: 279 in the member list,
  290 in Auth's count, 14 Directors named by ESI; Nah vi is one of them and
  is flagged. The other Corporations have no token with the membership scope
  and carry "No Director token".
- `collectstatic` was run after `filter.js` was added.
- Installed: allianceauth 5.3.1, allianceauth-corptools 3.5.0, django-solo
  2.5.1, django-esi 9.10.0. Target production per checklist: AA 5.4.0,
  corptools 3.5.0, aa-structures 4.0.1.
