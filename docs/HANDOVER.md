# Handover

Where the work stands and what is still open. `CLAUDE.md` holds the durable
rules for working on this app; this file holds the moment, and goes stale on
purpose - if a statement here contradicts the code, the code is right.

Last updated 2026-09-30.

## Release

- Version **0.0.9** of 2026-09-30, tagged `v0.0.9` (annotated, like every
  release tag) on the release commit and pushed with it. New in 0.0.9, see
  `CHANGELOG.md`:
  - **Sovereignty scope to corptools**: a *Director token missing* problem
    lacking `esi-structures.read_corporation.v1` shows the corptools hint
    (*Add Token*, every box ticked) and links to the Corporation Audit
    instead of CharLink (`Check.beyond_charlink`, `Problem.beyond_charlink`,
    `Todo.beyond_charlink`); the link without CharLink reads *corptools -
    Corporation Audit* (`Check.fix_group`).
  - **Dashboard widgets green or red** (`border-success` / `border-danger`).
  No migration, no new permission, no new static file.
- New in 0.0.8: dashboard widgets named *My account* and *My Corporation*,
  scope lists cut after two, the notice to members (migration 0008). New in
  0.0.7: the smart filter `CharacterProblemsFilter` (migration 0007), the
  Corporation header linking to aa-charlink, the check tiles of the
  Corporation page, character names linking to the Character Audit, Discord,
  QQ and Telegram voluntary.
- Migrations **0001-0008** applied in `aa_dev` (0008 adds `member_notice`; 0007 adds
  `CharacterProblemsFilter`; 0006 adds `alliance_characters_only`; 0005
  dropped the empty old smart filter table - no filter rows, no securegroups
  bindings - and added `view_own`).
- 335 tests without the translation tests, 4 translation tests, all green;
  one of them (`test_should_find_the_page_of_the_installed_charlink`) runs
  only with aa-charlink installed. Every check, access rule and feature was
  counter-checked against broken code (a sabotage that stays green means the
  test is too weak - it happened six times and each was fixed; 0.0.2 went 34
  for 34, 0.0.3 31 for 31, 0.0.4 3 for 3, 0.0.5 11 for 11, 0.0.6 41 for 41,
  0.0.7 11 for 11, 0.0.8 16 for 16, 0.0.9 7 for 7).
- Translated into de, ru and zh_Hans, machine-generated and marked so in the
  `.po` header; see `## Translations` in `CLAUDE.md`. The catalogues are only
  brought up to date at `/commit`.

## What the app does

| Page | Permission | What |
|---|---|---|
| Overview (`index`) | `view_all` | Cockpit (service shares, a Connections tile, audit shares), then the Corporations, most problems first, as tiles or as a table (`view.js`, remembered in `localStorage`), with a filter box and an *Only with problems* switch that act on both; each tile shows the number of accounts with problems, mains, characters, and each app with its share. `basic_access` alone is sent to its own Corporation, `manage_settings` alone to the settings |
| Corporation | `view_all`, or `basic_access` for the own main's Corporation | Tiles of the apps whose checks ran (`Corporation.check_gauges`: Registered in Auth, Character Audit, Corporation Audit, Structures; a Corporation-level one names its failed checks, without a link) and the service tiles, the header without rows (`hide_rows`), a to-do list (per failed character check the mains concerned - also mains elsewhere whose alts here fail it - with the check's hint, CharLink's where installed, plus the unregistered members; each with a copy button for an EVE mail and a CSV button, one more CSV button for the whole list), mains with problems as cards (a visiting main marked "Main in ...", linked only for `view_all`), the others as a compact list, members whose main is elsewhere, members not registered in Auth as a compact list. The header gives each Corporation problem its hint |
| Corporation export (`corporation_export`) | as Corporation | CSV of `Corporation.todo_rows`: `?group=<check key>` or `?group=unregistered` one column Name, without `group` Problem and Name. UTF-8 with BOM, formula-like cells prefixed with `'`; 404 for an empty or unknown group |
| Account | as Corporation, by the account's main | One green/red tile per service (links to the Corporation's list of it), the characters with problems (each problem with description, detail, hint and a link to aa-charlink, the check's app without it; the Corporation header's problems link to aa-charlink as well), the others folded away in a `<details>`, and the number of characters left out by *Only characters in the Alliance* |
| Corporation service | as Corporation | One row per main of the Corporation, linked yes/no, no problems |
| Service | `view_all` | Every main of the Alliance, linked yes/no |
| Character Audit list (`character_audit`) | `view_all` | Every main of the Alliance with a tag per failed character check (`Account.keyword_counts`, "×n" for n characters), most problems first; 404 without character checks |
| Director list (`directors/<group>`) | `view_all` | For `corptools_corporations` and `structures`: every Director of the Alliance's Corporations with Corporation, main (linked where the account is in the overview, *not in Auth* tag otherwise) and token yes/no, those without first; a notice without ESI (corptools' Directors only) or where roles were unreadable; 404 when no check of the group ran |
| My account (`own_account`) | `view_own` | The viewer's own account on `account.html` with `own=True`: service tiles linking to Alliance Auth's `services:services`, no Corporation header, the problems with hints linking to aa-charlink (the check's app without it), the left-out count; a notice when the account is not in the snapshot. `view_own` alone is sent here from the index |
| Dashboard widgets (`views.dashboard_own`, `views.dashboard_corporation`) | `view_own` / `basic_access` | On Alliance Auth's dashboard, order 4 like eos-invoices, own before Corporation (registration order). Own: failed checks with the number of characters (`Account.keyword_counts`), service icons, link to My account. Corporation: its own problems, each to-do group with the number of mains, the unregistered count, link to the Corporation page. Red border with anything to do, green without. `""` without the permission or when the snapshot has nothing about the viewer |
| Settings | `manage_settings` | Alliance (Tom Select), stale limit, ESI member lists on/off (also switches the roles call), only characters in the Alliance on/off, check and service switches, corptools sections and scopes, the notice to members (saving only a changed notice starts no rebuild: `form.changed_data`) |
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
`smart_filters.py` + `models.CharacterProblemsFilter` (securegroups),
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
`service-icons.html`, `row-title.html` (tooltip of a tile row or table cell),
`missing-characters.html` (My account's question).
The hints of each check live in `checks.py`: `Check.hint` with `Check.fix_url`
(a URL name, dropped when it does not resolve) about the player,
`charlink_hint` about the player where aa-charlink links, `own_hint` and
`own_app_hint` to the member on My account (with and without aa-charlink);
`problem-hint.html` picks by `charlink` and `own`. Translations:
`tools/glossary.py`, `tools/translate.py`.

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
  without a snapshot. Back on 2026-09-30, see there.
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
  ("The player ticks Character Audit in CharLink ..."). The Corporation
  page's to-do list names CharLink as well (see below). The Corporation
  header kept its apps until 2026-09-30, see there.
- Claude may apply this app's migrations to `aa_dev` and restart the dev
  Celery worker without asking.

2026-09-30:

- **Character names link to their corptools Character Audit** on the account
  page and *My account* (`partials/character-name.html`,
  `corptools:reactmain`; plain text without corptools), both in the problem
  table and in the folded list.
- **Discord, QQ and Telegram are voluntary** (`Service.voluntary`): on the
  overview's Corporation tiles and in its table their share is grey
  (`row_class` filter) instead of green/yellow/red. The user chose *only
  there*: the cockpit, the Corporation page and the account page keep their
  colours. **Mumble is mandatory, colour only**: it keeps its colours but, like
  every service, is no problem (no red border, problem count or sorting).
- **The Corporation header links its problems to aa-charlink** ("verlinke
  charlink in corporation details und nicht structures oder corp tools"),
  on every page that shows it (Corporation, Corporation service, account),
  with a `Check.charlink_hint` per Corporation check: Director ticks
  *Corporation Audit*, Station Manager ticks *Structures*. `problem-hint.html`
  takes CharLink only for a check with a `charlink_hint`: *Structure owner
  inactive* has none (an admin switches the owner on) and keeps its hint
  without a link. Without aa-charlink the apps stay the links.
- **Corporation page: the checks' apps as tiles** ("mache aus den drei
  buttons char audit corp audit und structures, jeweils mit prozentzahl eine
  kachel"): `Corporation.check_gauges` before the service tiles, in the same
  grid; *Registered in Auth* goes along, being a line of the same kind. The
  tiles have no link (the Alliance-wide lists need `view_all`). The account
  page and the service lists keep the lines in the header.
- **Smart filter back** ("erstelle einen smartfilter, der prüft, ob man
  probleme auf seinem char hat"): `models.CharacterProblemsFilter` +
  `smart_filters.audit_accounts`, hook `secure_group_filters`, admin in
  `admin.py`, migration 0007. A new name, not the `AccountProblemsFilter`
  0005 dropped, so a leftover 0.0.1 binding cannot attach to it. Passes an
  account without character problems (`Account.keywords` of the whole
  account from `Report.account()`, alts elsewhere included), *Reversed
  logic* those with; Corporation problems do not count (the old
  `include_corporation` is gone: the user asked about the characters).
  **Unknown fails always**, asked and chosen by the user knowing the cost:
  outside the overview fails either way, and without a snapshot everyone
  fails ("No Auth Monitor result yet") - a smart group empties until the
  next rebuild. The README says to rebuild before binding it.
- **Dashboard widgets named after their tabs** ("benenne die main account und
  corp kachel auf dem dashboard mit passenden namen um"): *My account* and
  *My Corporation*, the msgids of the navbar tabs. First "Auth Monitor - ..."
  in front; the user struck that ("streiche das auth monitor vor den
  kacheln").
- **Scope lists cut after two** ("überall wo scopes gelistet sind, kürze nach
  zwei scopes ab"): the details of *Scopes missing* and *Director token
  missing* read "a, b and N more", the whole list as tooltip. The settings
  page's scope checkboxes are a choice, not a listing, and stay whole.
- **Notice to members** ("textbox in den settings ... als infomeldung in my
  account und my corp"): plain text, escaped, line breaks kept, addresses
  linked (`urlize`); on *My account* (with or without an account in the
  snapshot) and on the Corporation page only when it is *My Corporation*
  (`nav == "corporation"`), not on the account or service pages of that
  Corporation. Empty or blanks only: no box.
- **Members cannot rebuild** (asked and settled: "kann so bleiben"): *Rebuild
  now* stays with `view_all` and `manage_settings`; `view_own` and
  `basic_access` wait for the beat run or an admin's rebuild. Only the
  progress poll is open to every app permission.
- **Sovereignty scope goes to corptools, not CharLink** ("wenn das scope fehlt
  soll corp audit angezeigt werden, sonst charlink ... mit allen checkmarks
  bei add token"): a *Director token missing* problem whose scopes include
  `esi-structures.read_corporation.v1` (`checks.SOVEREIGNTY_SCOPE`,
  `Check.beyond_charlink`, `Problem.beyond_charlink`) shows the corptools hint
  ("clicks Add Token ..., ticks every box") and links to
  `corptools:corp_react`, labelled *corptools - Corporation Audit*
  (`Check.fix_group`). Other scopes keep CharLink. The to-do group turns to
  corptools as soon as one of its problems lacks the scope
  (`Todo.beyond_charlink`), since that way fixes the others too. The monitor
  keeps demanding the scope (the user: "erstmal nichts ändern").
- **Dashboard widgets green or red** ("grünen rahmen im dashboard, wenn alles
  passt und einen roten sonst"): `border-success` without problems,
  `border-danger` otherwise, by the same rule as before (own: any character
  problem; Corporation: its problems, a to-do or an unregistered member).

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
- `pkill -f "celery ..."` inside `wsl.exe -e bash -lc '...'` matches its own
  shell's command line and kills it (exit 15) - the worker dies, the restart
  after it never runs. Stop and start the worker from a script file.
- With `--keepdb` the test users' pks, and so the main characters' IDs
  (`pk + 1000`), grow from run to run: an assertion that compares a sorted
  list with a literal one breaks once they pass the fixed alt IDs (9002).
  Sort both sides.
- A test fixture's `character_row` defaults to Corporation 2001: since each
  character counts in its own Corporation, a character on another
  Corporation's account needs its `corporation_id`, or it moves to 2001.
- The Corporation page's to-do tooltips carry the check's description, which
  names corptools too: assert on the hint text itself, not on "corptools".
- A test that cuts a page into parts must end each part at a marker that
  is there on that page: the Corporation page's header has no rows since
  0.0.7, so a slice up to them runs far past the header. And a check's
  description can hold the words of its old hint ("not set up as an owner
  in aa-structures"): assert on the hint's own sentence.
- A release can stay local: 0.0.7 was committed and tagged, the handover
  said "pushed", and `origin/main` was still at 0.0.6. Before a push, compare
  `git ls-remote origin main` with `@{u}` rather than trust the handover.
- The settings form's `changed_data` compares with the form's initial
  values, so a test that posts only some fields changes every check and
  service switch it leaves out: post the whole form as the page does
  (`TestSettings.unchanged`).
- `eos-test ... | tail -4` can end on the system-check lines printed after
  the result: grep for `^(Ran|OK|FAILED)` instead.
- corptools 3.5.0 has **two `CORP_REQUIRED_SCOPES`**: `corptools.views`
  (its plain *add_corp* and CharLink's *Corporation Audit* box; no
  `esi-structures.read_corporation.v1`, with `read_starbases`) and
  `corptools.app_settings` (used by nobody in corptools but by this app's
  `sources.corptools.corporation_scopes()`; with the sovereignty scope,
  without `read_starbases`). Only *Add Token* with options
  (`add_corp_options`, Sovereignty ticked) asks for the sovereignty scope.
  `add_corp_section` also grows `_corp_scopes_base` in place with `+=` - an
  upstream bug, not reported yet.
- django-esi's `Token.created` is overwritten on every refresh: a token
  refreshed by the rebuild looks newer than the snapshot that used it.

## Open points / next steps

- Production still runs 0.0.5: 0.0.6 to 0.0.9 are to be deployed, with
  migrations 0007 and 0008. After deploying, *Rebuild now* (or the beat run) fills the
  Director lists, and only then should the smart filter be bound to a group:
  without a snapshot it fails everyone.
- **A CEO does not see the *My Corporation* widget** (reported for
  production, cause not found). The dev instance renders it (for `E_o`, a
  superuser). The widget hides silently, with no error, when the viewer lacks
  `basic_access` - with `view_all` alone the navbar tab shows but the widget
  does not -, has no main, or the main's Corporation is not in the snapshot
  (not in the Alliance, or joined after the last rebuild). Next step: ask how
  that CEO gets their permissions and whether the tab and the Corporation page
  work for them, or run a diagnosis for that user in production.
- BigBlackout C (2115475367, Ether Element, account 2) was added through
  CharLink at 10:32 UTC: token 19 has 48 scopes, all but
  `esi-structures.read_corporation.v1`. The stored snapshot is older, so the
  page does not show it yet. Next step: *Rebuild now*, check that the problem
  links to the Corporation Audit, then add the token there with *Add Token*
  and every box ticked, and rebuild again.
- The two corptools bugs under *Pitfalls found* (two `CORP_REQUIRED_SCOPES`,
  `_corp_scopes_base` grown in place) are not reported upstream; the user
  may want an issue text.
- The smart filter was never created in the admin nor bound to a smart group,
  in dev or production; only its `audit_filter`/`process_filter` are tested.
- The Director lists have data now (dev snapshot of 2026-09-30 10:07 UTC: E
  'o with both tokens) but were never looked at in a browser.
- The CharLink hints name the boxes as CharLink labels them. "Character
  Audit" is corptools' default `CORPTOOLS_APP_NAME` (an installation that
  renames it sees another box). CharLink shows *Corporation Audit* only to
  holders of one of corptools' Corporation permissions and *Structures* only
  to holders of `structures.add_structure_owner`: a Director or Station
  Manager without them follows the link and finds no box.
- Nothing was looked at in a browser: the pages need a login. The JS files
  (`filter.js`, `view.js`, `copy.js`), the tiles (the new check tiles
  included), the table, the footer, the navbar tabs, the two dashboard
  widgets and their borders, the CSV download, the audit lists, the visiting
  cards, the notice box, the scope tooltip and the sovereignty hint are covered by tests of the rendered HTML (and of
  the CSV bytes) only.
- The notice to members was never filled in, in dev or production: the
  settings card is empty, so no box shows yet.
- Checklist review of 2026-09-29 (working tree after 0.0.1): README
  mismatches, the AA floor, the Members registered link, the broker outage
  (now a message, `progress.withdrawn()`) and the member tier (`view_own`)
  are done; the smart filter came back in 0.0.7 with the user's choice to
  fail unknown accounts. Still open, the user chose not to do it for now:
  failed ESI tokens are retried every run and spend the error limit.

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
  off, the notice empty. The Celery worker runs the 0.0.8 code since
  2026-09-30 (restarted after migration 0008, not after 0.0.9: its changes
  are rendering only and build the same snapshot - restart it before the
  next change to the build), started detached by a script (`setsid nohup
  ~/aa-dev/venv/bin/celery -A myauth worker -l info -P solo` in
  `~/aa-dev/working/myauth`, log in `/tmp/celery-eos.log`); one worker, check
  `ps` before the next restart. **No Celery beat runs** in the dev instance,
  so the beat entry never fires and the stored snapshot (2026-09-30 10:07 UTC,
  with `directors`) stays until *Rebuild now*. `runserver` reloads by itself.
  Rendered against `aa_dev`, the account's 3 problem links on *My account* go
  to `/charlink/`. Ether Element: 279 in the member list,
  290 in Auth's count, 14 Directors named by ESI; Nah vi is one of them and
  is flagged. The other Corporations have no token with the membership scope
  and carry "No Director token".
- `collectstatic` was run after `view.js` and `copy.js` were added.
- Installed: allianceauth 5.3.1, allianceauth-corptools 3.5.0, django-solo
  2.5.1, django-esi 9.10.0. Target production per checklist: AA 5.4.0,
  corptools 3.5.0, aa-structures 4.0.1.
