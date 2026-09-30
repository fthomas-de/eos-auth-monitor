# Handover

Where the work stands and what is still open. `CLAUDE.md` holds the durable
rules for working on this app; this file holds the moment, and goes stale on
purpose - if a statement here contradicts the code, the code is right.

Last updated 2026-09-29.

## Release

- Version **0.0.5** of 2026-09-29, tagged `v0.0.5` on the release commit and
  pushed with it, like `v0.0.1` to `v0.0.4`. New in 0.0.5, see
  `CHANGELOG.md`:
  - *Director token missing* counts only characters in the Alliance
    (`director_ids` of `sources.corptools.character_problems`), whatever
    *Only characters in the Alliance* says, and roles are asked only for
    Corporations of the Alliance.
  - *My account* links each problem to `charlink:index`
    (`views._charlink_url`, now `charlink` in `problem-hint.html`), the
    check's app without aa-charlink; label "CharLink", untranslated.
  - With *Only characters in the Alliance* on, the account pages say how many
    characters were left out (`left_out` per account in the snapshot,
    `Account.left_out`; an older snapshot shows nothing until rebuilt).
  No migration, no new permission.
- Migrations **0001-0006** applied in `aa_dev` (0006 adds
  `alliance_characters_only`; 0005 dropped the empty smart filter table - no
  filter rows, no securegroups bindings - and added `view_own`).
- 261 tests without the translation tests, 3 translation tests, all green;
  one of them (`test_should_find_the_page_of_the_installed_charlink`) runs
  only with aa-charlink installed. Every check, access rule and feature was
  counter-checked against broken code (a sabotage that stays green means the
  test is too weak - it happened six times and each was fixed; 0.0.2 went 34
  for 34, 0.0.3 31 for 31, 0.0.4 3 for 3, 0.0.5 11 for 11).
- Translated into de, ru and zh_Hans, machine-generated and marked so in the
  `.po` header; see `## Translations` in `CLAUDE.md`. The catalogues are only
  brought up to date at `/commit`.

## What the app does

| Page | Permission | What |
|---|---|---|
| Overview (`index`) | `view_all` | Cockpit (service shares, a Connections tile, audit shares), then the Corporations, most problems first, as tiles or as a table (`view.js`, remembered in `localStorage`), with a filter box and an *Only with problems* switch that act on both; each tile shows the number of accounts with problems, mains, characters, and each app with its share. `basic_access` alone is sent to its own Corporation, `manage_settings` alone to the settings |
| Corporation | `view_all`, or `basic_access` for the own main's Corporation | Service tiles, a to-do list (per failed character check the mains concerned with the check's hint, plus the unregistered members; each with a copy button for an EVE mail and a CSV button, one more CSV button for the whole list), mains with problems as cards, the others as a compact list, members whose main is elsewhere, members not registered in Auth as a compact list. The header gives each Corporation problem its hint |
| Corporation export (`corporation_export`) | as Corporation | CSV of `Corporation.todo_rows`: `?group=<check key>` or `?group=unregistered` one column Name, without `group` Problem and Name. UTF-8 with BOM, formula-like cells prefixed with `'`; 404 for an empty or unknown group |
| Account | as Corporation, by the account's main | One green/red tile per service (links to the Corporation's list of it), the characters with problems (each problem with description, detail, hint and a link to aa-charlink, the check's app without it; the Corporation header's problems keep their app), the others folded away in a `<details>`, and the number of characters left out by *Only characters in the Alliance* |
| Corporation service | as Corporation | One row per main of the Corporation, linked yes/no, no problems |
| Service | `view_all` | Every main of the Alliance, linked yes/no |
| Character Audit list (`character_audit`) | `view_all` | Every main of the Alliance with a tag per failed character check (`Account.keyword_counts`, "×n" for n characters), most problems first; 404 without character checks |
| Director list (`directors/<group>`) | `view_all` | For `corptools_corporations` and `structures`: every Director of the Alliance's Corporations with Corporation, main (linked where the account is in the overview, *not in Auth* tag otherwise) and token yes/no, those without first; a notice without ESI (corptools' Directors only) or where roles were unreadable; 404 when no check of the group ran |
| My account (`own_account`) | `view_own` | The viewer's own account on `account.html` with `own=True`: service tiles linking to Alliance Auth's `services:services`, no Corporation header, the problems with hints linking to aa-charlink (the check's app without it), the left-out count; a notice when the account is not in the snapshot. `view_own` alone is sent here from the index |
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
  on: then those alts are left out altogether (not checked, shown or
  counted), filtered on the ownerships in `snapshot.build`; the account pages
  say how many.
- **Each character counts where it is** (2026-09-29, after 0.0.5; "ein
  account kann chars in mehreren corps der alli haben, das ist erlaubt und
  soll normal bewertet werden"): a character is rated in the Corporation of
  the overview it is in, not in its main's; outside the overview it counts
  with its main. Worked out in `Report._characters_by_corporation` from the
  snapshot as it is: `Corporation.accounts` are the own mains with the
  characters counted here, `Corporation.visiting` the accounts of mains
  elsewhere with their characters here (`Account.visiting`,
  `main_corporation_name`), `evaluated_accounts` both - problem count, cards,
  to-dos, the Character Audit row. `Report.accounts` and `Report.account()`
  keep the whole accounts (account pages, Alliance-wide lists, cockpit). On
  the Corporation page a visiting main links to its account only for
  `view_all` (`can_view_all`): a CEO may not open another Corporation's
  account.
- **Corporation page to-do list** names CharLink (`Check.charlink_hint`) where
  aa-charlink is installed (2026-09-29).
- **My account "du-zt"** (2026-09-29): every text of its own speaks to the
  member - `Check.own_hint` with aa-charlink, `Check.own_app_hint` without,
  "None of your characters has a problem.", "N of your characters ...", and
  German with *du* (rule in `CLAUDE.md`, `## Translations`).
- **My account asks for missing characters** (2026-09-29, "ob chars in der
  übersicht fehlen und noch ergänzt werden müssen"): `partials/
  missing-characters.html`, shown on My account with or without an account in
  the overview, linking to CharLink or to `authentication:add_character`.
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
- **Cockpit audit tiles open lists of their own** (2026-09-29, after 0.0.5;
  before, they linked to corptools and aa-structures): Character Audit to
  `character_audit` - every main with a tag per failed character check and
  the number of its characters failing it, like a service list; Corporation
  Audit and Structures to `directors/<group>` - in both cases the
  **Directors** ("in beiden Fällen Directoren ohne Token"): all of them,
  those without the token first, Directors unknown to Auth included with the
  tag *not in Auth*. Corporation Audit asks for a token with every
  Corporation-audit scope (the Director check's rule), Structures for an
  enabled `OwnerCharacter` of the Corporation's owner. The Members registered
  tile and the Corporation tile rows have no link of their own.
- **Gua Zi 2nd hand** (98827954, production), reported as not in the
  Alliance, is in it according to ESI since 2026-08-20: the overview is right.
  No exclusion list was asked for.
- **Service lists show mains only** (one link per account), without problem
  badges; all table columns are left-aligned.
- **"No Director token"** marks a Corporation where no Director's token could
  read the roles: a small info icon with the explanation as tooltip beside the
  name (tile, table line, Corporation page; a badge until 2026-09-29), *not*
  a problem - no percentage, sorting or border colour changes. Set only while
  the ESI switch is on together with the Director check or a Director list
  (the latter since the audit lists); a Corporation of the Alliance
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
- **Accepted as they are** (asked again and settled on 2026-09-29, not to be
  raised as open points any more): the QQ and Telegram tiles on *My account*
  linking to Auth's services page - both apps link from there; the service
  lists showing registered mains only while the tile's total counts unknown
  members; Directors nobody can read the roles of staying unfound (marker
  "No Director token"); the `allianceauth>=5.1.4` floor derived from the tags
  without a run against 5.1.4; the machine-generated translations; no CI;
  performance with a large Alliance untested (the footer with the build
  figures is there to measure it; the token-by-scope query and the
  per-Corporation queries and ESI calls stay as they are).
- **Director check only inside the Alliance**: a Director of a Corporation
  outside the Alliance is no problem, with or without *Only characters in
  the Alliance*; such Corporations are not asked for roles.
- **My account links to aa-charlink** for every problem; without aa-charlink
  the check's app stays.
- **The account page links character problems to aa-charlink** too
  (2026-09-29, after 0.0.5), with hints about the player in the third person
  ("The player ticks Character Audit in CharLink ..."); the Corporation
  header's problems keep their app there and on the Corporation page. The
  Corporation page's to-do list names CharLink as well (see below).
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

- Uncommitted since 0.0.5: the four character checks carry two CharLink
  hints, `Check.own_hint` (to the player, My account: "Tick Character Audit
  in CharLink and log in with this character.") and `Check.charlink_hint`
  (about the player, account page). Both views pass `charlink_url`;
  `account.html` hands it to `problem-hint.html` as `charlink` for the
  character problems only, so the Corporation header keeps the check's app;
  `own` picks the text. The eight new messages go into `tools/glossary.py`
  at `/commit`. Sabotage 3 for 3 and 4 for 4. "Character Audit" is
  corptools' default `CORPTOOLS_APP_NAME`, which CharLink shows as the label;
  an installation that renames it sees a different box.
- Uncommitted since 0.0.5: the audit lists. `snapshot._directors` stores
  `directors` per Corporation (`id`, `name`, `in_auth`, `user_id` - only for
  an account of the overview -, `main_name`, `tokens` per group of
  `checks.DIRECTOR_GROUPS`), from the ESI roles kept per Corporation
  (`esi_directors_by_corporation`) and `corptools.known_directors`; tokens
  from `corptools.corporation_token_holders` and
  `structures.owner_characters`. The roles are asked when the Director check
  *or* a Director list needs them (`asked_roles`). `report.Director`,
  `Report.directors(group)`, `Report.accounts_by_problems()`, `Gauge.url`
  (replaces the `{% url %}` juggling in `index.html`). Templates
  `character_audit.html`, `directors.html`. The dev snapshot has no
  `directors` until the next rebuild; the Celery worker has to be restarted
  first. New messages for the glossary at `/commit`.
- Nothing was looked at in a browser: the pages need a login. The JS files
  (`filter.js`, `view.js`, `copy.js`), the tiles, the table, the footer, the
  navbar tabs, the two dashboard widgets and the CSV download are covered by
  tests of the rendered HTML (and of the CSV bytes) only.
- Checklist review of 2026-09-29 (working tree after 0.0.1): README
  mismatches, the AA floor, the Members registered link, the broker outage
  (now a message, `progress.withdrawn()`), the member tier (`view_own`) and the
  smart filter (removed) are done. Still open, the user chose not to do them
  for now: failed ESI tokens are retried every run and spend the error limit.
  (Roles for every Corporation any alt is in are gone with the Director fix.)

## Dev instance

- Repo `~/aa-dev/working/eos-auth-monitor`, remote
  `https://github.com/fthomas-de/eos-auth-monitor.git`, branch `main`.
- Installed editable into `~/aa-dev/venv`, in `INSTALLED_APPS` of
  `~/aa-dev/working/myauth`, beat entry `eos_auth_monitor_update_snapshot`
  (every 30 min) in its `local.py`. Also installed there (by the user):
  aa-structures 4.0.1, securegroups 0.10.2, aa-qqbot 1.0.0, the Telegram
  bridge 1.7.6, Discord and Mumble - the readers ran against the real schemas.
  aa-charlink 1.14.0 installed by Claude on the user's request (2026-09-29,
  `charlink` last in `INSTALLED_APPS`, its migrations 0001-0004 applied,
  `collectstatic` run; stays installed).
  The dev DB has one account and no service links: every service number is 0.
- `MonitorConfiguration` in `aa_dev`: Alliance 99003995 (Invidia Gloriae
  Comes), nothing switched off, ESI on, *Only characters in the Alliance*
  off. The Celery worker was restarted on the code after 0.0.5 (Director
  lists) at 22:43 (WSL clock; `pkill -f` from `bash -lc` kills its own shell -
  start it from a script), started detached from a
  shell (`setsid nohup ~/aa-dev/venv/bin/celery -A myauth worker -l info -P solo`
  in `~/aa-dev/working/myauth`, log in `/tmp/celery-eos.log`, not from a
  terminal tab); the two workers running before (one started outside a
  session) were both stopped, one runs now - check `ps` before the next
  restart. The stored snapshot (built 18:01 UTC) still renders; it lacks
  `left_out` and carries the Director flags of before the fix until the next
  beat run rebuilds it. Rendered against `aa_dev`, the account's 3 problem
  links on *My account* go to `/charlink/`. Ether Element: 279 in the member list,
  290 in Auth's count, 14 Directors named by ESI; Nah vi is one of them and
  is flagged. The other Corporations have no token with the membership scope
  and carry "No Director token".
- `collectstatic` was run after `view.js` and `copy.js` were added.
- Installed: allianceauth 5.3.1, allianceauth-corptools 3.5.0, django-solo
  2.5.1, django-esi 9.10.0. Target production per checklist: AA 5.4.0,
  corptools 3.5.0, aa-structures 4.0.1.
