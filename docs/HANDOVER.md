# Handover

Where the work stands and what is still open. `CLAUDE.md` holds the durable
rules for working on this app; this file holds the moment, and goes stale on
purpose - if a statement here contradicts the code, the code is right.

Last updated 2026-09-29.

## Release

- Version **0.0.4** of 2026-09-29, tagged `v0.0.4` on the release commit and
  pushed with it, like `v0.0.1` to `v0.0.3`. New in 0.0.4, see
  `CHANGELOG.md`: the setting *Only characters in the Alliance*
  (`MonitorConfiguration.alliance_characters_only`, off by default, migration
  0006) - with it on, an account's characters outside the Alliance are left
  out of every check, page and count and their Corporations are not asked
  for roles. No new permission.
- Migrations **0001-0006** applied in `aa_dev` (0006 adds
  `alliance_characters_only`; 0005 dropped the empty smart filter table - no
  filter rows, no securegroups bindings - and added `view_own`).
- 248 tests without the translation tests, 3 translation tests, all green.
  Every check, access rule and feature was counter-checked against broken
  code (a sabotage that stays green means the test is too weak - it happened
  six times and each was fixed; 0.0.2 went 34 for 34, 0.0.3 31 for 31 once
  the view_own test of the own widget was sharpened, 0.0.4 3 for 3).
- Translated into de, ru and zh_Hans, machine-generated and marked so in the
  `.po` header; see `## Translations` in `CLAUDE.md`. The catalogues are only
  brought up to date at `/commit`.

## What the app does

| Page | Permission | What |
|---|---|---|
| Overview (`index`) | `view_all` | Cockpit (service shares, a Connections tile, audit shares), then the Corporations, most problems first, as tiles or as a table (`view.js`, remembered in `localStorage`), with a filter box and an *Only with problems* switch that act on both; each tile shows the number of accounts with problems, mains, characters, and each app with its share. `basic_access` alone is sent to its own Corporation, `manage_settings` alone to the settings |
| Corporation | `view_all`, or `basic_access` for the own main's Corporation | Service tiles, a to-do list (per failed character check the mains concerned with the check's hint, plus the unregistered members; each with a copy button for an EVE mail and a CSV button, one more CSV button for the whole list), mains with problems as cards, the others as a compact list, members whose main is elsewhere, members not registered in Auth as a compact list. The header gives each Corporation problem its hint |
| Corporation export (`corporation_export`) | as Corporation | CSV of `Corporation.todo_rows`: `?group=<check key>` or `?group=unregistered` one column Name, without `group` Problem and Name. UTF-8 with BOM, formula-like cells prefixed with `'`; 404 for an empty or unknown group |
| Account | as Corporation, by the account's main | One green/red tile per service (links to the Corporation's list of it), the characters with problems (each problem with description, detail, hint and a link to the app), the others folded away in a `<details>` |
| Corporation service | as Corporation | One row per main of the Corporation, linked yes/no, no problems |
| Service | `view_all` | Every main of the Alliance, linked yes/no |
| My account (`own_account`) | `view_own` | The viewer's own account on `account.html` with `own=True`: service tiles linking to Alliance Auth's `services:services`, no Corporation header, the problems with hints; a notice when the account is not in the snapshot. `view_own` alone is sent here from the index |
| Dashboard widgets (`views.dashboard_own`, `views.dashboard_corporation`) | `view_own` / `basic_access` | On Alliance Auth's dashboard, order 4 like eos-invoices, own before Corporation (registration order). Own: failed checks with the number of characters (`Account.keyword_counts`), service icons, link to My account. Corporation: its own problems, each to-do group with the number of mains, the unregistered count, link to the Corporation page. `""` without the permission or when the snapshot has nothing about the viewer |
| Settings | `manage_settings` | Alliance (Tom Select), stale limit, ESI member lists on/off (also switches the roles call), only characters in the Alliance on/off, check and service switches, corptools sections and scopes |
| Rebuild (POST) / progress (JSON) | `view_all` or `manage_settings` / any app permission | Start the task / state for the progress bar |

Every page has a footer with the cost of the last rebuild (`view_all` or
`manage_settings` only). The header reads "Auth Monitor (version)" with the
page's name below it (`views.LOCATIONS`, by template; the service lists
show the service's label instead).

The app navbar (`base.html`) has the tabs *My account* (`view_own`), *My
Corporation* (`nav_corporation_id`: the own main's Corporation, for
`basic_access` or `view_all`), *Alliance overview* (`view_all`, the index),
*Settings*. The active tab comes from the view (`_render(..., nav)`), not from
the URL name: the pages about one Corporation ask `_corporation_nav`, which
gives *My Corporation* for the own Corporation and *Alliance overview* for
any other. The sidebar keeps its one *Auth Monitor* entry.

Code layout: `checks.py` (registry of checks, groups, services),
`sources/` (one reader per foreign app, read only; `members.py` holds the two
ESI calls: member list and roles), `snapshot.py` (builds the JSON, run by
`tasks.update_snapshot`), `metrics.py` (times and counts a build, stored under
`metrics` in the snapshot), `progress.py` (task state in the cache),
`report.py` (labels, counts, percentages, sort orders for the templates),
`views.py`, `forms.py`. JS: `tables.js` (DataTables), `progress.js`,
`searchable.js` (Tom Select), `filter.js` (live filter and problems switch of
the overview), `view.js` (tiles or table), `copy.js` (copy buttons, with an
`execCommand` fallback for plain HTTP). Partials: `gauge.html` (a statistic
tile), `corporation-rows.html`, `metrics.html`, `problem-count.html`,
`no-director.html`, `problem-hint.html`, `copy-button.html`, `csv-button.html`,
`service-icons.html`, `row-title.html` (tooltip of a tile row or table cell).
The hint of each check is `Check.hint` with `Check.fix_url` (a URL name,
dropped when it does not resolve) in `checks.py`. Translations: `tools/glossary.py`, `tools/translate.py`.

## Decisions the user made

2026-09-28:

- **Scope**: an account belongs to the overview when its main is in the
  configured Alliance; it sits on the main's Corporation tile. All its
  characters are checked, alts outside the Alliance included - unless the
  setting *Only characters in the Alliance* (2026-09-29, off by default) is
  on: then those alts are left out altogether (not checked, shown, counted,
  nor their Corporations asked for roles), filtered on the ownerships in
  `snapshot.build`.
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
- **Cockpit tiles without a page of their own** link to the app they count:
  Character Audit to `corptools:react`, Corporation Audit to
  `corptools:corp_react`, Structures to `structures:index` (no longer Auth's
  `/services/`, changed 2026-09-29). A URL that does not resolve leaves the
  tile unlinked. The Members registered tile and the Corporation tile rows
  have no link of their own.
- **Service lists show mains only** (one link per account), without problem
  badges; all table columns are left-aligned.
- **"No Director token"** marks a Corporation where no Director's token could
  read the roles: a small info icon with the explanation as tooltip beside the
  name (tile, table line, Corporation page; a badge until 2026-09-29), *not*
  a problem - no percentage, sorting or border colour changes. Set only while
  the ESI switch and the Director check are on; a Corporation of the Alliance
  without any account in Auth is asked as well.
- The ESI switch is called **Fetch data from ESI** (it also covers the roles).
- **Readability** (the aim: a compact overview for the Alliance's leadership
  and for each CEO): overview as tiles or table, *Only with problems*,
  problem count per tile; on the Corporation page a to-do list with copy
  buttons, cards only for mains with problems, compact lists for the rest and
  the unregistered; on the account page a hint per problem and the
  characters without problems folded away. The Connections tile stays.
- **Page header**: "Auth Monitor (version)", below it the page; a service
  list is named after its service.
- **Smart filter removed** ("erstmal streichen"): it failed every account
  without a snapshot. It may come back later, then without that failure.
- **Members** get `view_own` and *My account* - their own account only.
- **Navbar**: one tab each for the own main, the own Corporation and the
  Alliance, in that order (main > Corporation > Alliance), then Settings.
- **Dashboard widgets** at eos-invoices' order (4): the own account in short
  with a link to *My account*, for members (`view_own`); the own Corporation
  in short with a link to its page, for CEOs (`basic_access`). No new
  permissions: the widgets follow the pages they link to.
- *My account*'s service tiles link to Alliance Auth's services page.
- **CSV export** on the Corporation page: per to-do group beside *Copy
  names*, and one for the whole list (Problem, Name).
- Claude may apply this app's migrations to `aa_dev` and restart the dev
  Celery worker without asking.

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
- A sabotage round needs `--keepdb` on `eos-test`: without it every round
  builds the test database and runs all migrations of the dev instance
  again (about 24 s instead of 4 s for a small module).
- The Edit tool writes `"\ufeff"` as the character itself, not as the
  escape: a BOM in Python source goes in through a patch script.
- `eos-test` takes one test label per call; run several modules one after
  the other. A full run takes about 15 s; only a sabotage round of many
  reruns is long - start it in the background.
- Do not put a Python patch into `wsl.exe -e bash -lc '...'`: an apostrophe
  in `Auth's` ends the quoted string. Write the script with the Write tool
  into the scratchpad and run it by its `/mnt/c/...` path.
- `.git/CLAUDE_COMMIT_MSG` must be *read* before it is written again, or the
  Write tool refuses and `git commit -F` silently reuses the old message.
- From Windows' Git Bash, `wsl.exe ... python3 /mnt/c/...` needs
  `MSYS_NO_PATHCONV=1`, or the path is mangled into `C:/Program Files/Git/...`.
  A heredoc in that shell broke on a long template as well: write patch
  scripts with the Write tool.
- `eos-test` is a login-shell function: a script that calls it must run under
  `bash -l` (or `bash -lc`), or every run silently finds nothing.
- A `pgrep -f name` wait loop inside `bash -lc '... name ...'` matches its own
  command line and never ends; match the full command (`python3 /mnt/c/.*name`).
- `{% url ... as var %}` inside `{% for %}` keeps `var` across iterations (one
  context for the whole loop): clear it in an `{% else %}` (`{% firstof "" as
  var %}`). A `{% url %}` that cannot resolve sets `var` to "" - that is how an
  uninstalled app's link disappears.
- DataTables 2 right-aligns any column whose `data-order` is numeric;
  `tables.js` sets `dt-left` on all columns. It also measures widths of a
  hidden table as zero, hence `autoWidth: false` (the overview table starts
  hidden).
- Short words may clash with Alliance Auth's catalogue ("View" did): the
  translation test names them; give them `context "eos-auth-monitor"`.

## Open points / next steps

- With *Only characters in the Alliance* on, the account page and *My
  account* do not say that characters were left out; a short notice there
  was offered to the user (2026-09-29), not asked for yet.

- Nothing was looked at in a browser: the pages need a login. The JS files
  (`filter.js`, `view.js`, `copy.js`), the tiles, the table, the footer, the
  navbar tabs, the two dashboard widgets and the CSV download are covered by
  tests of the rendered HTML (and of the CSV bytes) only.
- Whether the Telegram and QQ tiles on *My account* lead anywhere useful:
  they link to Auth's services page like Discord and Mumble, as asked, but
  aa-qqbot and the Telegram bridge may keep their linking on pages of their
  own.
- The service lists behind a tile show the registered mains only, while the
  tile's total also counts unknown members.
- A Director whose roles neither corptools nor ESI (no Director token in the
  Corporation) could read is not found; such Corporations carry the marker
  "No Director token". In the dev instance 31 of 32 Corporations have it; the
  user chose a quiet info icon over a badge (2026-09-29).
- Performance with a large Alliance is untested; the footer with the build
  figures is there to measure it. The character check reads all tokens with
  their scopes in one query; the member lists and roles cost up to two ESI
  calls per Corporation per run (cached by django-esi).
- The `allianceauth>=5.1.4` bound (migration 0002 needs `eveonline` 0025,
  first in 5.1.4) was checked by reading the tags, never run against 5.1.4.
- The translations are machine-generated: a native speaker should read them.
- Checklist review of 2026-09-29 (working tree after 0.0.1): README
  mismatches, the AA floor, the Members registered link, the broker outage
  (now a message, `progress.withdrawn()`), the member tier (`view_own`) and the
  smart filter (removed) are done. Still open, the user chose not to do them
  for now: failed ESI tokens are retried every run and spend the error limit,
  roles are asked for every Corporation any alt is in (unless *Only
  characters in the Alliance* is on); no CI; the
  token-by-scope query and per-Corporation queries at scale.

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
  Comes), nothing switched off, ESI on, *Only characters in the Alliance*
  off. The Celery worker was restarted on the code with
  `alliance_characters_only` at 20:50 (WSL clock), started detached from a
  shell (`setsid nohup ~/aa-dev/venv/bin/celery -A myauth worker -l info -P solo`
  in `~/aa-dev/working/myauth`, log in `/tmp/celery-eos.log`, not from a
  terminal tab); the two workers running before (one started outside a
  session) were both stopped, one runs now - check `ps` before the next
  restart. The snapshot format did not change in 0.0.2 or 0.0.3, so the
  stored one still renders; the next beat run rebuilds it. Ether Element: 279 in the member list,
  290 in Auth's count, 14 Directors named by ESI; Nah vi is one of them and
  is flagged. The other Corporations have no token with the membership scope
  and carry "No Director token".
- `collectstatic` was run after `view.js` and `copy.js` were added.
- Installed: allianceauth 5.3.1, allianceauth-corptools 3.5.0, django-solo
  2.5.1, django-esi 9.10.0. Target production per checklist: AA 5.4.0,
  corptools 3.5.0, aa-structures 4.0.1.
