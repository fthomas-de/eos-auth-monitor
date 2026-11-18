# Handover

Where the work stands and what is still open. `CLAUDE.md` holds the durable
rules for working on this app; this file holds the moment, and goes stale on
purpose - if a statement here contradicts the code, the code is right.

Last updated 2026-11-17 (0.0.34).

## Release

- **Unreleased** (2026-11-18): **Help mode remembered per user**. Model
  `HelpMode` (user as primary key, `on`; migration `0011`, applied to
  `aa_dev`), no row = on. `help.js` POSTs each change to `help_mode`
  (`help-mode/`, any app permission, POST only, 204); `_render` passes
  `help_mode`, `base.html` sets `checked` from it and carries the URL and the
  CSRF token as `data-*`. Tests: `TestHelpMode` 5 -> 8, three sabotages red.
  Seen in Chrome: off survives a reload and a switch to *My account*,
  back on likewise.
- Version **0.0.34** of 2026-11-17: **Help mode** (see `CHANGELOG.md` and
  the decisions of 2026-11-17 (help mode) below). A *Help mode* switch in
  the navbar (`base.html`, block `header_nav_collapse_right`, checked by
  default) and a question mark per area (`partials/help.html`, popover with
  `data-bs-trigger="focus"`); `static/eos_auth_monitor/js/help.js` starts the
  popovers, shows the switch only where the page has question marks and
  hides them while it is off. Tile texts on the new field `Row.help`
  (`report.py`: `SERVICE_HELP`, `ACTIVITY_HELP`, `REGISTERED_HELP`,
  `COCKPIT_GROUP_HELP`, `CORPORATION_GROUP_HELP` and inline ones); the rest
  in the templates via `{% translate ... as help_text %}`. On tiles
  (`gauge.html`, `spy-tile.html`, `gm-tile.html`, the account page's service
  tiles) `corner=True`, included **last** in the card body so the existing
  tile regexes in the tests stay untouched. 30 new messages, translated.
  Tests: `TestHelpMode` (5) in `test_views`; 506 in the suite. Seen in the
  browser on the overview and the Corporation page (switch, popover, off/on);
  the account pages only by tests.
- Version **0.0.33** of 2026-11-17: **GM transactions and spy markers for
  the CEO roles** of eos-tax (`eos_tax.basic_access`) and eos-spy-network
  (`eos_spy_network.view_own_corporation`): a viewer with such a role but
  without the app's full view sees that app's findings on the own main's
  Corporation only (tile, to-dos, card tags, CSV, account pages; no cockpit
  tile or overview column). Each app's own CEO filter decides the
  characters. See `CHANGELOG.md` and the decisions of 2026-11-17 (CEO roles)
  below. 12 new tests, 12 sabotages, 12 red; 501 in the suite. No
  migration, no message, no template, no static file. Not seen in a browser.
- **Next steps (0.0.33)**: log in as a CEO holding only `basic_access`,
  `eos_tax.basic_access` and `eos_spy_network.view_own_corporation` and look
  at *My Corporation* - GM and spy tiles linked to eos-tax's GM page and
  eos-spy-network's Corporation page, both showing that Corporation only;
  the Alliance overview (if `view_all`) without GM/spy tiles and columns.
  Production needs eos-spy-network **0.0.30** for the spy half; an older one
  shows a CEO no markers (no error).
- Version **0.0.32** of 2026-11-17: **Director crown per character** on Main
  details and My account (see `CHANGELOG.md` and the decisions of 2026-11-17
  (character crown) below). `Character.is_director`, set in `Report._account` from
  `Report._director_ids` (pairs Corporation id, character id of every row's
  `directors`): a Director of its own Corporation, not the main's. A crown
  (`fa-crown text-warning`, class `eos-auth-monitor-character-director`,
  tooltip the existing msgid "Director", context `EVE jargon`, so nothing new
  to translate) after the Main badge in `partials/character-cell.html` (only
  `account.html` uses it) and in the folded list of `account.html`. The
  Corporation page's account crown (`Account.directors`, main's Corporation)
  is unchanged. Tests: two in `TestAccountDirectors` (`test_report`),
  `TestCharacterDirectorIcon` (2, `test_views`); 4 sabotages, 4 red. No
  migration, no snapshot change, no static file. 489 tests in the suite.
  Not seen in a browser.
- Version **0.0.31** of 2026-11-17: **covered Directors warn, CharLink box
  *Full*** (see `CHANGELOG.md` and the decisions of 2026-11-17 (covered
  Directors) below).
  - `sources.corptools.character_problems(..., token_directors=set())` fills
    the Directors with a complete Corporation token; `snapshot.build` stores
    `corporation_token` per character. `report._account` collects the
    Corporations where a character of the account has it; `_is_warning`
    (third argument `covered`) turns `char_director_token_missing`
    (`report.DIRECTOR_CHECK`) into a warning there. Everything after that is
    the scope warnings' machinery; no template change. An older snapshot has
    no flag: red until rebuilt.
  - `charlink_hook.FIELD_LABEL` is `Corporation Audit (Full)`, `unique_id`
    stays `sovereignty`; the two hints in `checks.py` and the glossary keys
    renamed (translations: Sovereignty -> Full, otherwise unchanged).
  - Tests: `TestCoveredDirectors` in `test_report` (5), two in
    `test_sources_corptools`, one in `test_snapshot`; the CharLink texts in
    `test_views`; 485 in the suite. 4 sabotages, 4 red
    (`test_should_not_name_a_director_lacking_a_scope` not sabotaged). No
    migration, no static file. Not seen in a browser.
  - Where a covered Director's warning shows and where it no longer counts
    (explained to the user): the Character Audit shares (Corporation tile,
    cockpit tile, overview column and tile row) count him complete; the
    Corporation's Character Audit list shows him with a yellow tag among the
    fine ones; the Alliance-wide Character Audit list gives a main with this
    warning alone no tag; account page and My account show it yellow with
    the CharLink hint.
- **Next steps**:
  - Rebuild the dev snapshot and look at a covered Director on the
    Corporation page (yellow card, to-do group *Director token missing
    (warning)*) - nothing of 0.0.31 was seen in a browser.
  - Same rebuild: open Main details of an account with a Director (Ether
    Element has 14 by ESI) and My account, and check the per-character crown
    in the table and the folded list (0.0.32, not seen in a browser).
  - After the next aa-charlink release: check that the box shows as
    *Corporation Audit (Full)* on CharLink's page, and that an existing
    CharLink admin setting for the box (keyed by `unique_id` `sovereignty`)
    still applies.
  - Those of 0.0.28 below are still open.
- Version **0.0.30** of 2026-11-17: **Registered in Auth without a member
  list** (see `CHANGELOG.md` and the decisions of 2026-11-17 (Registered in
  Auth) below).
  - `snapshot._members`: where `corporation_members()` gives `None`, the
    characters with a `CharacterOwnership` whose `EveCharacter` is in the
    Corporation stand in for the list and run through the same loop
    (`other_mains`, `unregistered` with `in_auth: True`); `member_count`
    stays `None`, the new row key `member_list_unread` is `True`. With the
    ESI switch off nothing changes (`NO_MEMBERS`, no key).
  - `report.py`: `Corporation.member_list_unread`; `registered` counts
    `len(members) - len(unregistered)` then; `check_rows` adds *Registered
    in Auth* with `part` only and `Row.note` (new field, the message
    `MEMBER_LIST_UNREAD`, the same msgid as the Corporation page's notice);
    `Corporation.rows` (overview tiles and table, service pages' header)
    leaves rows with a `note` out.
  - Templates: `gauge.html`, `tile-row.html`, `row-title.html` show the
    count and the note instead of a share; `corporation_registered.html` a
    warning box; `corporation.html` shows the *Not registered in Auth*
    section whenever `unregistered` has entries (the to-do's anchor).
    `views.corporation_registered` opens wherever `registered` is not `None`.
  - Tests: 5 new (`test_snapshot` 1, `test_report` 2, `test_views` 2) plus
    two assertions; 477 in the suite. No migration, no static file, no new
    message. Not seen in a browser: it needs a rebuild with ESI.
- Version **0.0.29** of 2026-11-17: **numbered characters on Main details,
  wider Corporation column in the overview** (see `CHANGELOG.md` and the
  decisions of 2026-11-17 below). Templates only.
  - `account.html`: a `#` column (`forloop.counter`, `data-order` the same,
    class `eos-auth-monitor-number`) in the problem table; the folded
    *without problems* list goes on from `account.listed_characters|length`
    (`{% with offset=... %}` and `|add:offset`).
  - `index.html`: `style="min-width: 14rem"` on the Corporation `<th>` of the
    overview table.
  - Tests: one new in `test_views`
    (`test_should_number_the_characters_on_from_the_table_into_the_folded_list`,
    sabotaged red), `test_should_shorten_the_heads_of_the_table` now checks
    the min-width; 472 in the suite. No message, no migration, no static
    file.
  - Seen in the browser: the column at 224px in a 1024px window, names on
    one or two lines; own account 1-4 in the table. The folded list's
    numbers only by the test - the user's account has no problem-free
    character.

- Version **0.0.28** of 2026-11-17: **tile lists, Character Audit over all
  members, CharLink sovereignty box** (see `CHANGELOG.md` and the decisions
  of 2026-11-16 (CharLink box) and (tile lists) below).
  - The Corporation page's tiles *Registered in Auth* and *Character Audit*
    open pages of their own: `corporation_registered`
    (`corporation/<id>/registered/`) and `corporation_character_audit`
    (`corporation/<id>/character-audit/`), one view helper
    `views._corporation_list`; `Corporation.members` (new `report.Member`),
    `Corporation.audited_characters`; `Row.url` on both check rows, linked
    on the Corporation page only; partials `unknown-status.html` (shared
    with `unknown_characters.html`) and `audited-character.html`.
  - *Character Audit* counts members without a main as failing (`+
    len(unregistered)`), on the Corporation tiles, the overview and the
    cockpit. **Behaviour change**: shares drop where a member list was read.
  - `charlink_hook.py` adds *Corporation Audit (Sovereignty)* to aa-charlink
    (hook `charlink` in `auth_hooks.py`, only with corptools and charlink):
    CharLink's own Corporation Audit `LoginImport` with the sovereignty
    scope added. *Director token missing* always links to CharLink and names
    that box; `beyond_charlink` (check, problem, to-do) is gone.
  - Tests: `TestDirectorCharlink` (4, was `TestBeyondCharlink`),
    `TestCharlinkBox` (2), `TestTileLists` in `test_report` (4) and
    `test_views` (5); 20 sabotages, all red after one test fix. Three new
    messages, translated. No migration, no static file.
  - Seen in the browser (Corporation 98633815): tiles 4 of 283 and 0 of 283,
    both linked; 283 members, 4 registered; Character Audit 4 failing, then
    279 unknown; the box on CharLink's page (unticked by default); the
    Director hint linking to CharLink. No console errors.
- **Next steps**:
  - Have a Director log in through *Corporation Audit (Full)* (named
    *Sovereignty* until the Unreleased change), rebuild,
    and check that *Director token missing* clears - the CharLink login
    itself was not run.
  - After every aa-charlink upgrade, check `charlink_hook.py` against
    `charlink/imports/corptools.py` (it copies that `LoginImport`); drop the
    box once corptools' `views.CORP_REQUIRED_SCOPES` carries
    `esi-structures.read_corporation.v1`.
  - From 0.0.27: the account page's Mumble tile and `account_activity` not
    seen with real Mumble accounts; whether production writes
    `MumbleUser.last_disconnect` is unchecked (decisions of 2026-11-16
    (Active in Mumble)).

- Version **0.0.27** of 2026-11-16: **Active in Mumble day by day** (see
  `CHANGELOG.md` and the decisions of 2026-11-16 (day by day) below) - the
  account page's Mumble tile shows the main's share with its days ("Active
  in Mumble: 50 % (1 of 2)") and opens the new page `account_activity`
  (`account/<id>/activity/`, `account_activity.html`): every day of the
  window, today first. `activity.breakdown()`, `views._visible_account`
  (shared with `account`), `partials/activity-share.html`. 9 new tests in
  `tests/test_activity.py` (29 in the module; 13 sabotages, 13 red). Six
  new messages, translated; "Day" needs the `eos-auth-monitor` context (it
  clashed in ru and zh_Hans). No migration, no static file. Not seen in a
  browser: `aa_dev` has no Mumble account, so it would show only the
  "not linked" notice.
- Version **0.0.26** of 2026-11-16: **Active in Mumble** (see
  `CHANGELOG.md` and the decisions of 2026-11-16 (Active in Mumble) below) -
  of the days a main played EVE, the share it was in Mumble too.
  `activity.py` (`record()` for the task, `rates()` for the pages), model
  `ActivityDay` and setting `activity_days` (migration 0010), task
  `tasks.record_activity` (beat entry every 15 minutes, README),
  `sources.services.mumble_connections`, `sources.corptools.logins`,
  `Report.add_activity` (called for every page in `views._report`, not
  stored in the snapshot), `Row.average` and `Row.activity`,
  `partials/activity-cell.html`, `tests/test_activity.py` (20 tests; 19
  sabotages, 18 red, the green one fixed and not re-run). Three new
  messages, translated. Not seen in a browser, and never run on real data:
  `aa_dev` has no Mumble account.

- Version **0.0.25** of 2026-11-16: **Alliance join date in the
  Corporation header** (see `CHANGELOG.md` and the decisions of 2026-11-16
  below) - after *Characters*, "In the Alliance since: <Y-m-d> (<timesince>)"
  on every page with the header. The rebuild reads each Corporation's public
  alliance history from ESI without a token (`sources.members.alliance_joined`,
  the latest entry of the configured Alliance) into the snapshot row
  `alliance_joined` (ISO string; `Corporation.alliance_joined` a datetime).
  An ESI failure only logs and leaves the date out. `tests/base.py` now mocks
  `sources.members._client` in every test. No migration, one new message
  (de, ru, zh_Hans). 433 tests green, 6 new; no sabotage run. Not seen in a
  browser; the real ESI call was tried in the dev shell (Invidia
  Administrative: 2015-05-30).
- New in 0.0.24 (2026-11-13): **fixes from a code audit** for bugs and
  security (`docs/AUDIT.md`: what was found, why, and the fix with its test;
  `CHANGELOG.md`; the decisions of 2026-11-12 below). Five findings, no
  Critical or High: a rebuild fails when ESI does not answer instead of
  storing the outage as "no token" (AM-01, `sources/members.py`
  `_is_token_failure`); a Corporation's service list shows its own mains
  only (AM-02); settings saved during a running rebuild make it start over
  once (AM-03, `snapshot.update`); nothing missing when every scope is
  unticked (AM-04); a visiting main's card hides its service icons and crown
  from viewers without `view_all` (AM-05). No migration, no static file, no
  message. 427 tests green, 8 new, each seen red against the old code or
  without its guard. Not seen in a browser.
- New in 0.0.23 (2026-11-11): **overview order fixed** (see
  `CHANGELOG.md` and the decisions of 2026-11-11 below) - the Problems
  column, the tiles and the table's first order rank Corporations by
  accounts with problems (the number shown), then Corporation problems, then
  name; before they ranked by the sum of single problems. `report.py` and
  `index.html` only; no migration, no message. 419 tests green. Not seen in
  a browser.
- New in 0.0.22 (2026-11-10): **order of the main cards** on the
  Corporation page (see `CHANGELOG.md` and the decisions of 2026-11-10
  (0.0.22) below) - red borders before yellow; within each colour Directors
  (the crown) first, then GM transactions, then the rest by problems as
  before. `Corporation.card_accounts` only; no migration, no template, no
  message. 418 tests green. Not seen in a browser.
- New in 0.0.21 (2026-11-10): **spy and GM tags on the main cards**
  of the Corporation page (see `CHANGELOG.md` and the decisions of
  2026-11-10 (0.0.21) below) - a cyan tag per spy marker kind, a pink *GM
  transactions* tag, a red border for any such finding; a main with
  findings alone gets a card. No migration, no static file, no new
  message. 416 tests green. Not seen in a browser.
- New in 0.0.20 (2026-11-10): **colours** - spy markers cyan (badges
  `text-bg-info`, counts `text-info-emphasis`, 0 green), Corporation
  problems in the header red (`text-bg-danger`). Templates only.
- New in 0.0.19 (2026-11-09): **scope warnings** (see `CHANGELOG.md`
  and the decisions of 2026-11-09 below) - setting *Scopes missing: a problem
  from* (`critical_scope_count`, default 5, migration 0009); a *Scopes
  missing* with fewer missing scopes is a warning: yellow on the Corporation
  page (card, to-do group `char_scopes_missing_warning`), the account pages
  and the dashboard widgets, a problem nowhere. Four new messages,
  translated. **Behaviour change for existing installations**: one to four
  missing scopes turn from red to yellow after the next rebuild. Not seen in
  a browser.
- New in 0.0.18: a **Director crown** on the Corporation
  page (see `CHANGELOG.md` and the decisions of 2026-11-07 below) - a
  `fa-crown` icon top right on a main's card and before the service icons in
  the *Without problems* list when a character of the account (the main
  included) is a Director of the main's Corporation, the names as tooltip.
  `Account.directors` (filled in `Report._account` from the snapshot's
  `directors` of the main's Corporation), `partials/director-icon.html`. No
  migration, no snapshot change, no static file; one new message,
  translated. Not seen in a browser.
- New in 0.0.17: the account page's **GM transactions
  link** opens eos-tax's GM Transactions page searched for the main's name
  (`?search="<main>"`, see `CHANGELOG.md` and the decisions of 2026-11-06
  below). eos-tax reads `?search=` only from its own matching change (a
  separate eos-tax session); until that is released the link opens the page
  unfiltered. No migration, no static file, no new message. Not seen in a
  browser.
- New in 0.0.16: a **Spy network cockpit tile** on the
  overview (see `CHANGELOG.md` and the decisions of 2026-11-06 below) - the
  sum of the *Spies* column, linked to eos-spy-network's Corporations page,
  for viewers with both of its view permissions; the Corporation page's spy
  tile now comes from the same `partials/spy-tile.html`. No migration, no
  static file, no new message. Not seen in a browser.
- New in 0.0.15: **eos-tax GM transactions** (see
  `CHANGELOG.md` and the decisions of 2026-11-06 below) - cockpit tile,
  overview column *GM*, Corporation tile, pink to-do with the mains, pink
  marker on the account page, for viewers of eos-tax's GM Transactions tab.
  The overview table heads are shorter (*Corp*, *Chars*, *Char Audit*,
  *Spies*, *GM*; the whole name as tooltip, filter `abbreviate`). No
  migration, no static file; six new messages, translated. Not seen in a
  browser.
- New in 0.0.14: an internal clean-up the user asked for
  ("mit dem ponytail skill durch coding ... optimierungen"), every point
  chosen by the user, nothing visible changes - see `CHANGELOG.md`. One
  `report.Row` for tile lines and statistic tiles (`Gauge`, `service_gauges`
  and `check_gauges` are gone; the Corporation page uses `check_rows` and
  `service_counts`, `Row.url` links a tile), the Connections tile reads the
  cockpit's service tiles (`Report.connections()` gone), `charlink_url` set
  in `views._render` for every page, `sources.corptools._missing_scopes`,
  `snapshot.NO_MEMBERS`. The suite stays at 368; the Connections test now
  checks the count (sabotaged and seen red). No migration, no message.
- New in 0.0.13: the names in the *Spy network* to-do groups of a
  Corporation page link to the account page of their main
  (`SpyTodo.entries`), with the same rule as the other groups: a main
  elsewhere stays text unless the viewer has `view_all`. Not seen in a
  browser.
- New in 0.0.12:
  **eos-spy-network markers** per character for viewers with both
  `eos_spy_network.view_suspects` and `view_evidence` - a *Spy network*
  column in the overview table, a count tile and one to-do entry per marker
  on the Corporation page, the markers on the account page. Display only.
  Needs eos-spy-network **0.0.10** (released and pushed the same day, tag
  `v0.0.10`); an older one is ignored. No migration, no new permission, no
  static file; three new messages, translated.
- New in 0.0.11: service shares count mains only; *Members registered* opens
  `unknown_characters`; paging of every list longer than 25 rows; table
  first on the overview (six messages, `tables.js`/`view.js`).
- New in 0.0.10: *My account* greys out unlinked QQ and Telegram (`Service.
  grey_when_missing`, filter `link_colour`); Discord, Mumble and the
  account page others see stay red.
- New in 0.0.9: a *Director token missing* problem lacking the sovereignty
  scope links to *Add Token* in the corptools Corporation Audit instead of
  CharLink (`Check.beyond_charlink`), dashboard widgets green or red. New in
  0.0.8: dashboard widgets named *My account* and *My Corporation*, scope
  lists cut after two, the notice to members (migration 0008). New in 0.0.7:
  the smart filter `CharacterProblemsFilter` (migration 0007), the
  Corporation header linking to aa-charlink, the check tiles of the
  Corporation page, character names linking to the Character Audit, Discord,
  QQ and Telegram voluntary.
- Migrations **0001-0010** applied in `aa_dev` (0010 adds `ActivityDay` and `activity_days`; 0009 adds `critical_scope_count`; 0008 adds `member_notice`; 0007 adds
  `CharacterProblemsFilter`; 0006 adds `alliance_characters_only`; 0005
  dropped the empty old smart filter table - no filter rows, no securegroups
  bindings - and added `view_own`).
- 501 tests without the translation tests, 3 translation tests, all green;
  `test_should_find_the_page_of_the_installed_charlink` runs only with
  aa-charlink installed, `TestSpyNetwork` and the spy permission tests only
  with eos-spy-network installed, the source and view tests of
  `test_gm_transactions` only with eos-tax installed. Every check, access rule and feature was
  counter-checked against broken code (a sabotage that stays green means the
  test is too weak - it happened seven times and each was fixed; 0.0.2 went 34
  for 34, 0.0.3 31 for 31, 0.0.4 3 for 3, 0.0.5 11 for 11, 0.0.6 41 for 41,
  0.0.7 11 for 11, 0.0.8 16 for 16, 0.0.9 7 for 7, 0.0.10 4 for 4, 0.0.11
  13 for 13 after one fix: the status badges were counted, not tied to
  their rows; 0.0.12 20 for 20 after two fixes: the order by marker count
  and the to-do card opened by markers alone were untested; 0.0.15 6 for 6; 0.0.16 1 for 1;
  0.0.18 5 for 5; 0.0.19 24 for 24; 0.0.20 8 for 8; 0.0.21 6 for 6; 0.0.22's two order tests checked by
  reasoning against the old sort, no sabotage run; 0.0.23 1 for 1, run
  against the old `report.py`; 0.0.24 8 for 8; 0.0.25 not sabotaged; 0.0.26
  18 of 19, the green one strengthened; 0.0.27 13 for 13; 0.0.28 20 for 20
  after one fix: a marker class was part of another attribute; 0.0.30 6 for
  6 after one fix: the tile's count itself was not asserted; 0.0.31 4 for 4; 0.0.32 4 for 4; 0.0.33 12 for 12).
- Translated into de, ru and zh_Hans, machine-generated and marked so in the
  `.po` header; see `## Translations` in `CLAUDE.md`. The catalogues are only
  brought up to date at `/commit`.

## What the app does

| Page | Permission | What |
|---|---|---|
| Overview (`index`) | `view_all` | Cockpit (service shares, a Connections tile, audit shares; *Members registered* opens the unknown characters), then the Corporations, most accounts with problems first, as a table (the default since 0.0.11) or as tiles (`view.js`, remembered in `localStorage`), with a filter box and an *Only with problems* switch that act on both; each tile shows the number of accounts with problems, mains, characters, and each app with its share. `basic_access` alone is sent to its own Corporation, `manage_settings` alone to the settings |
| Corporation | `view_all`, or `basic_access` for the own main's Corporation | Tiles of the apps whose checks ran (`Corporation.check_rows`: Registered in Auth and Character Audit linked to their lists, Corporation Audit and Structures, which name their failed checks, without a link; Character Audit counts the members without a main as failing) and the service tiles, the header without rows (`hide_rows`), a to-do list (per failed character check the mains concerned - also mains elsewhere whose alts here fail it - with the check's hint, CharLink's where installed, plus the unregistered members; each with a copy button for an EVE mail and a CSV button, one more CSV button for the whole list), mains with problems, warnings, spy markers or GM transactions as cards (`Corporation.card_accounts`; a visiting main marked "Main in ...", linked and with its service icons and crown only for `view_all`), the others as a compact list, members whose main is elsewhere, members not registered in Auth as a compact list. The header gives each Corporation problem its hint |
| Registered in Auth (`corporation_registered`), Character Audit (`corporation_character_audit`) | as Corporation | Behind the Corporation page's tiles: every member with its main and *registered*, *not in Auth* or *no main*, those without a main first (`Corporation.members`); every character the tile rates with its main and failed checks (warnings yellow, *No problems* green), the failing first, then the members without a main, then the rest (`Corporation.audited_characters`). Where the member list was unreadable (`member_list_unread`), the characters Auth knows in the Corporation, with the reason as a warning box. 404 with the ESI switch off / without character checks |
| Corporation export (`corporation_export`) | as Corporation | CSV of `Corporation.todo_rows`: `?group=<check key>` or `?group=unregistered` one column Name, without `group` Problem and Name. UTF-8 with BOM, formula-like cells prefixed with `'`; 404 for an empty or unknown group |
| Account | as Corporation, by the account's main | One green/red tile per service (links to the Corporation's list of it; Mumble to `account_activity`, with the main's Active in Mumble below *linked*), the characters with problems (each problem with description, detail, hint and a link to aa-charlink, the check's app without it; the Corporation header's problems link to aa-charlink as well), the others folded away in a `<details>`, and the number of characters left out by *Only characters in the Alliance* |
| eos-spy-network markers (on Overview, Corporation, export, Account) | the page's own plus `eos_spy_network.view_suspects` and `view_evidence` (`sources.spy_network.can_view`) | Overview cockpit tile (`partials/spy-tile.html`, `Report.spy_characters`: the column's sum, linked to `eos_spy_network:corporations`, since 0.0.16); overview table column *Spy network* (characters with markers per Corporation, linked to `eos_spy_network:corporation`); Corporation page count tile (same link), one to-do entry per marker kind (`Corporation.spy_todos`, group `spy_<kind>` in the CSV) and a cyan tag per kind on the main cards (`Account.spy_markers`, red border); account page markers per character (`Account.listed_characters`). Read per page view by `views._report(user)` -> `Report.add_spy_markers`; never on *My account*, the dashboard widgets or the smart filter |
| eos-tax GM transactions (on Overview, Corporation, export, Account) | the page's own plus `eos_tax.admin_view` or `eos_tax.gm_bots_access` (`sources.gm_transactions.can_view`) | Cockpit tile (Alliance count) and Corporation tile (`partials/gm-tile.html`), both linked to `eos_tax:gm_transactions`; overview table column *GM* (count, no link); pink to-do with the mains (`Corporation.gm_accounts`, group `gm_transactions` in the CSV); a pink tag on the main cards (`Account.has_gm`, red border); pink marker per character with an eos-tax link on the account page (searched for the main's name, `?search="<main>"`). Read per page view by `views._report(user)` -> `Report.add_gm_transactions`; never on *My account*, the dashboard widgets or the smart filter |
| Active in Mumble of a main (`account_activity`) | as Account | Behind the account page's Mumble tile: the main's share in the card header, then every day of `activity_days` plus today, today first with a grey *today* badge (`activity.breakdown`, unnoted days as unsaved `ActivityDay`); *yes* green for EVE and Mumble, a red *no* for a whole day in EVE without Mumble, "-" otherwise. A notice without Mumble linked; 404 without the Mumble service |
| Corporation service | as Corporation | One row per main of the Corporation, linked yes/no, no problems; for Mumble a column *Active in Mumble* |
| Service | `view_all` | Every main of the Alliance, linked yes/no; for Mumble a column *Active in Mumble* |
| Active in Mumble (on Overview, Corporation, the Mumble lists) | the page's own | Per main with Mumble linked: days in EVE and in Mumble out of days in EVE over `activity_days` whole days (`activity.rates`, read per page view by `views._report` -> `Report.add_activity`). Below the linked share on the Mumble tile of cockpit and Corporation page (`Row.activity`), a row of each overview tile and a column of the overview table (`Corporation.rows`), a column per main in the Mumble lists (`partials/activity-cell.html`, days as tooltip). A tile is the mean of its mains (`report._mean_activity`); "-" without a share. Never a problem; not on My account or the dashboard. Nothing at all without the Mumble service |
| Character Audit list (`character_audit`) | `view_all` | Every main of the Alliance with a tag per failed character check (`Account.keyword_counts`, "×n" for n characters), most problems first; 404 without character checks |
| Director list (`directors/<group>`) | `view_all` | For `corptools_corporations` and `structures`: every Director of the Alliance's Corporations with Corporation, main (linked where the account is in the overview, *not in Auth* tag otherwise) and token yes/no, those without first; a notice without ESI (corptools' Directors only) or where roles were unreadable; 404 when no check of the group ran |
| Unknown characters (`unknown_characters`) | `view_all` | Behind *Members registered*: every `unregistered` member of the Alliance (`Report.unknown_characters`) with Corporation and status - *not in Auth*, *no main* (account without a main), "-" for a snapshot from before 0.0.11 -, by Corporation and name; a notice naming how many Corporations' member lists were unread; 404 without any member list |
| My account (`own_account`) | `view_own` | The viewer's own account on `account.html` with `own=True`: service tiles linking to Alliance Auth's `services:services`, no Corporation header, the problems with hints linking to aa-charlink (the check's app without it), the left-out count; a notice when the account is not in the snapshot. `view_own` alone is sent here from the index |
| Dashboard widgets (`views.dashboard_own`, `views.dashboard_corporation`) | `view_own` / `basic_access` | On Alliance Auth's dashboard, order 4 like eos-invoices, own before Corporation (registration order). Own: failed checks with the number of characters (`Account.keyword_counts`), service icons, link to My account. Corporation: its own problems, each to-do group with the number of mains, the unregistered count, link to the Corporation page. Red border with anything to do, green without. `""` without the permission or when the snapshot has nothing about the viewer |
| Settings | `manage_settings` | Alliance (Tom Select), stale limit, scope threshold (*Scopes missing: a problem from*), ESI member lists on/off (also switches the roles call), only characters in the Alliance on/off, check and service switches, corptools sections and scopes, the notice to members (saving only a changed notice starts no rebuild: `form.changed_data`) |
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
`execCommand` fallback for plain HTTP), `help.js` (Help mode switch and
popovers). Partials: `help.html` (a Help mode question mark, `corner=True`
on a tile), `gauge.html` (a statistic
tile), `corporation-rows.html`, `metrics.html`, `problem-count.html`,
`no-director.html`, `problem-hint.html`, `copy-button.html`, `csv-button.html`,
`service-icons.html`, `director-icon.html` (the crown, `corner=True` on a card),
`row-title.html` (tooltip of a tile row or table cell),
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
  **Reversed on 2026-10-09**, see there.
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
  tile (until 2026-10-09, see there) and the Corporation tile rows have no
  link of their own.
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
  kachel"): `Corporation.check_rows` before the service tiles, in the same
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
- **My account greys out unlinked QQ and Telegram** ("in my account färbe qq
  und telegram nicht rot, wenn sie fehlen sondern grau"): `Service.
  grey_when_missing`, filter `link_colour` (`border-secondary`,
  `text-secondary`). Only *My account* (`own`; the account view passes
  `own=False` explicitly, a filter argument must exist); Discord - voluntary
  too, but not named - and Mumble stay red, and so does every tile on the
  account page others see. The dashboard widget's icons were grey already.

2026-10-09:

- **Unknown characters apart** ("zähle charactere, die noch nicht im auth
  sind und noch keinem main zugehörig sind ... nicht mit in die gesamtsumme,
  sondern zeig sie separat an"): the service shares count mains only -
  `Corporation.service_total` is gone, `service_counts` and the cockpit use
  the mains. Asked where: the user chose **everywhere** (cockpit, Corporation
  tiles and table, Corporation page). The cockpit's *Members registered* tile,
  unlinked until now, opens `unknown_characters` (`view_all`, 404 without
  any member list): every `unregistered` member with Corporation and status,
  sortable. A tile *Unknown characters* of its own was built and dropped the
  same day ("die ist ja doppelt mit registered"). The snapshot keeps
  `in_auth` per unregistered member (False: not in Auth, True: account
  without a main); an older snapshot shows "-" until the next rebuild.
  The user reported that "-" as "status unknown" before rebuilding.
- **Paging on every list** ("bau eine pagination bei allen listen ein mit
  standard 100"): `tables.js` pages every sortable table longer than 25 rows,
  100 per page, 25-500 to choose, with DataTables' info line. Not the
  overview table (`eos-auth-monitor-no-search`): `filter.js` hides rows itself
  and would miss those on other pages. Not looked at in a browser.
- **Table first on the overview** ("mach die table ansicht in der alliance
  overview zum default"): `index.html` renders the table pane visible and
  the tiles hidden, the table button pressed; a choice stored by `view.js`
  still wins. Without a table line (no Corporation) the tiles stay visible,
  they carry the "No Corporation ..." notice.

2026-11-04 (0.0.12):

- **eos-spy-network integration** ("integration von eos spy network in den
  auth monitor"): for viewers with both `eos_spy_network.view_suspects` and
  `view_evidence` (`sources.spy_network.can_view`) on top of the page's own
  permission: a *Spy network* column in the overview **table** (not on the
  tiles - the user asked for a column), a count tile on the Corporation page
  linking to `eos_spy_network:corporation`, a to-do entry per marker kind
  (group `spy_<kind>`, copy and CSV like the others, also in the whole-list
  CSV), and on the **account page** (the user's "Main-Übersicht") each
  character's markers; a character with markers but no problem moves into
  the table (`Account.listed_characters`). Answers of the user: count
  **characters with markers** (column and tile alike), each character **in
  its own Corporation** like the checks; **display only** - no problem
  count, sorting, border, dashboard widget or smart filter; *My account*
  never shows them (`own_account` calls `_report()` without the user).
- The markers per character need eos-spy-network to store the characters
  behind each marker; the user had that done **in a separate session** in
  eos-spy-network (0.0.10: `character_ids` per stored marker,
  `eos_spy_network/api.py` with `character_markers()`, `label()`,
  `description()`, `KINDS`). The auth monitor reads that API on every page
  view (`views._report(user)` -> `Report.add_spy_markers`); nothing goes into
  its own snapshot. The Corporation and account objects share the
  `Character` instances, which is why setting `character.spy` once reaches
  every page.

2026-11-06 (0.0.15):

- **eos-tax GM transactions** ("integration von eos tax gm transactions"):
  `sources/gm_transactions.py` reads eos-tax's stored GM report on every page
  view through its own `get_gm_page` and keeps the rows with counterparty
  `FLAGGED_PARTY` ("GM X"), the user's definition of a finding: the rows
  shown with the "GM X" box ticked. `Report.add_gm_transactions` marks
  `Character.gm`, only for characters whose Corporation is in the overview
  ("noch in der corp der allianz"). Visible with `eos_tax.admin_view` or
  `gm_bots_access`, eos-tax's own rule for the tab. Cockpit tile and
  Corporation tile (`partials/gm-tile.html`) link to `eos_tax:gm_transactions`;
  the overview column *GM* has **no link** ("das macht die kachel oben ja
  schon"); a pink to-do with the **mains** (group `gm_transactions`), each
  linked to its account page; a pink marker with an eos-tax link on the
  account page. **Pink** (`var(--bs-pink)`, inline): first orange, then the
  user asked for a warning colour "nicht gelb oder orange", so it differs
  from the spy markers (yellow then, cyan since 2026-11-10). A spy count in the cockpit was left for a
  separate session (the user's choice). Display only, like the spy markers.
- **GM link searched for the main** (0.0.17): the account page's GM
  link carries `?search="<main name>"`, which eos-tax takes as the initial
  DataTables search (phrase match). Not the Corporation name too: alts in
  other Corporations would be hidden; not a filter on the Main column only:
  invisible and not clearable.
- **Spy cockpit tile** (0.0.16; "corporation overview
  braucht auch eine spy kachel mit link zur app"): beside the GM tile, the
  sum of the *Spies* column, linked to `eos_spy_network:corporations`; the
  Corporation page's tile keeps its link to `eos_spy_network:corporation`,
  both from `partials/spy-tile.html`. Same rule as the other spy displays:
  both view permissions. eos-spy-network's own pages stay as they are (its
  Corporations pages need `view_suspects` only - the user's choice).
- **Shorter overview table heads** ("die tabelle in corp overview wird
  langsam etwas groß"): "Corporation" -> "Corp", "Character" -> "Char" in
  the heads only (filter `abbreviate`, on the translated text - the jargon
  stays English in every catalogue), the whole name as tooltip; the spy
  column reads *Spies*, the GM column *GM*. Tiles and other pages keep the
  long names.

2026-11-07 (0.0.18):

- **Director crown on the main cards** ("zeige bei kacheln von mains in der
  oberen rechten ecke an, wenn sich ein corp director der haupt corp (corp
  des mains) unter den chars befindet"). The user's answers: on the problem
  cards **and** in the compact *Without problems* list (not the account
  page, the overview or the dashboard); **icon with tooltip** naming the
  characters; the **main counts** too; on the card of a main from another
  Corporation ("Main in ...") the check is against the main's own
  Corporation, with all the account's characters. **Data source as it is**:
  the snapshot's `directors`, which exist only while the Corporation Audit
  or Structures checks run (`director_lists`) - without them, or where no
  roles could be read, no crown and no hint. Display only, no problem.

2026-11-09 (0.0.19):

- **Scope warnings** ("erlaube ein setting für eine kritische anzahl scope
  fehler und weniger kritische ... in der corp details ansicht aber schon
  gelistet mit entsprechend eingefärbten rand"): setting
  `critical_scope_count` (migration 0009), copied into the snapshot;
  `report._is_warning` puts a *Scopes missing* below it into
  `Character.warnings` instead of `problems`, so every problem rule stays as
  it was and the overview ignores warnings by itself. The user's answers:
  **only Scopes missing** (`checks.WARNING_CHECK`; Director token missing
  stays a problem); **default 5**; a warned character counts as **complete**
  in the Character Audit percentages; the **dashboard widgets** turn yellow
  (`border-warning`) and the **smart filter** passes. Colour: Bootstrap's
  `warning`, the same as the spy markers then (the user asked for "standard
  warn farbe"; the spy markers turned cyan on 2026-11-10). Corporation page: card `border-warning` for a main with warnings
  and no problem, red as soon as it has one; to-do group
  `char_scopes_missing_warning` ("Scopes missing (warning)", `Todo.warning`,
  `Corporation.listed_todos`); the to-do card keeps its red border. A snapshot
  without the key rates every missing scope a problem (threshold 1) until
  rebuilt.

2026-11-10 (0.0.20):

- **Spy markers get a colour of their own**: yellow (`text-bg-warning`, the
  scope warnings' colour) on the badges and red (`text-danger`, a problem's)
  on the counts mixed them up with things they are not. Planned was
  `var(--bs-purple)`; as text it reads badly in AA's dark theme (about
  2.6:1), so the user asked for a Bootstrap standard colour and chose **info
  (cyan)**: badges `text-bg-info` (account page, Corporation to-do), counts
  `text-info-emphasis` (*Spies* column, both spy tiles - one partial; the
  user's choice: plain `text-info` on white is about 2:1, the emphasis dark
  teal in the light theme, light cyan in the dark one); a 0 stays green. No CSS file. Colours now: yellow warnings, pink GM transactions,
  cyan spy markers, red problems. Cyan is also the *No Director token*
  icon's and the notice boxes' colour (accepted). Counting, sorting, borders
  and the dashboard are unchanged; the to-do card keeps its red border.
  eos-spy-network followed in 0.0.21: its markers are Bootstrap info too
  (badges `text-bg-info`, tile borders `border-info`, no CSS of its own).
- **Corporation problems red in the header** (`partials/corporation-header.
  html`, `text-bg-danger`, yellow before): they count as problems
  (`Corporation.has_problems`) and already turn the tile red.

2026-11-10 (0.0.21):

- **Spy and GM tags on the main cards** ("zeige die eos spy und gm
  transactions tags auch auf den main kachel der corporation details
  ansicht"): `Account.spy_markers` (each kind once, in the order first met -
  not necessarily eos-spy-network's), `Account.has_gm`, `has_markers`;
  `Corporation.card_accounts` feeds the cards. The user's answers: a main
  with markers alone **gets a card** and leaves *Without problems*; a card
  with markers has a **red border** ("bei gm transactions oder spy findings
  roter rand, wenn diese keine warnungen sind") - neither app gives a
  severity (eos-spy-network's API drops cleared findings itself), so every
  marker is red, also over a warning; one tag
  **per marker kind**, no count (cyan `text-bg-info`, `fa-user-secret`; pink
  "GM transactions", `fa-sack-dollar`). A visiting main whose alt here has a
  marker gets a card too, as in the to-dos. Order, counts, dashboard and
  smart filter unchanged; marker-only cards came last (changed in 0.0.22).
  Tests helper `tests.test_views.main_cards`; 6 sabotages, 6 red.

2026-11-10 (0.0.22):

- **Main cards by border colour** ("sortiere die corp details ansich nach
  farbigem rahmen rot, dann gelb"): `Corporation.card_accounts` sorts red
  (problems or markers) before yellow (warnings alone), so a marker-only card
  no longer lands behind the warning cards.
- **Directors, then GM transactions, first within each colour** ("je gelbem
  oder rotem rahmen haben director char prio, dann mit gm transactions, dann
  rest"): the user chose the **crown's rule** (`Account.directors`: any
  character of the account a Director of the main's Corporation, alts
  included), not the main alone; a Director with GM transactions counts as
  Director. A GM transaction makes a card red, so the GM step only shows in
  red; for a viewer without eos-tax's permission it falls into the rest. A
  stable sort keeps `accounts_by_problems` order inside each step;
  `accounts_by_problems` itself (service lists, exports) is unchanged.

2026-11-11 (0.0.23):

- **Overview ranks Corporations by accounts with problems** ("in alliance
  overview wird die spalte problems nicht richtig sortiert, eine corp wird
  mit 1 angezeigt aber ist recht weit oben"): the user chose to sort by the
  number shown (option A, not to show the problem sum instead), and for
  **everything** - the Problems column's `data-order`, the tiles and the
  table's first order (`Report.corporations_by_problems`): accounts with
  problems, then the Corporation's own problems, then the name. Narrows the
  2026-09-29 rule "everything is sorted by number of problems" for the
  Corporations; accounts, characters and service lists still sort by
  problems. `Corporation.problem_count` is no longer used by app code, only
  by tests as the total; it could go.

2026-11-12 (0.0.24, from the audit in `docs/AUDIT.md`):

- **ESI down fails the run** ("ok wie empfohlen"): a server error, the
  error limit or no network leaves `sources.members` instead of moving on to
  the next token; the task fails and the last good snapshot stays. Only a
  token failure (`esi.errors.TokenError`, a 4xx `HTTPClientError`) moves on.
  Not chosen: carrying the member lists and Directors over from the previous
  snapshot, or leaving it.
- **A visiting main's card hides its services and crown** ("hide under that
  circumstance"): for a viewer without `view_all` - who may not open that
  account - the card of a main from another Corporation shows neither its
  service icons nor its Director crown. Read as both, since the question
  named both; if only the icons were meant, drop the condition around
  `director-icon.html` in `corporation.html` and the crown assertions in
  `TestAltsInAnotherCorporation`.
- The audit report stays in the repo as `docs/AUDIT.md` (the user's choice at
  the 0.0.24 commit); its *Checked and fine* list says what needs no second
  look.

2026-11-16 (0.0.25):

- **Alliance join date in the Corporation header** ("füge der corporation
  detail ansicht eine info zum allianz beitritt zur aktuellen allianz hinzu
  ... nach characters"): the user chose date plus duration and **every page
  with the header**, not only the Corporation page. They expected corptools
  to have it; it does not (only characters' Corporation history), so ESI's
  public alliance history it is, read at every rebuild, independent of the
  *ESI member lists* switch. Unlike the member lists (AM-01), an ESI failure
  here does not fail the run: the date is a nicety.

2026-11-16 (Active in Mumble):

- **What it is** ("aktivitätsübersicht ... je main: war einer der chars im
  mumble verbunden ... war einer der chars an dem tag eingeloggt"): per main
  and day two flags; the share is days with EVE and Mumble out of days with
  EVE. The user confirmed: EVE without Mumble lowers it, Mumble without EVE
  changes nothing.
- **Where** (the user's words): the Mumble tile of the Alliance overview and
  of the Corporation page - **both numbers**, the linked share stays and the
  activity goes below it; **also per Corporation** on the overview (tile row
  and table column); a column per main in the Mumble lists.
- **A tile shows the mean of the mains' shares** (the user's choice over
  pooled days), each main once; mains without a share stay out.
- **Only mains with Mumble linked are rated** ("die aktivität kann nur
  erfasst werden, wenn mumble verknüpft ist"): the others show "-" and are
  not noted. The user's second sentence - Mumble needs a clean character in
  the Character Audit - is how their Auth is set up, not something to check.
- **Window and retention one setting**, "letzte 30 tage einstellbar".
- **Characters as the settings count them** (*Only characters in the
  Alliance*): taken from the snapshot's accounts.
- **Mumble hangers**: "maximale verbindungsdauer von 24h ... da der server
  täglich neugestartet wird" - connected counts for 24 hours after the
  connect (`activity.CONNECTED_AT_MOST`).
- **From the review the user asked for and accepted** ("weiter"): the day
  comes from the timestamp, not from "today"; an online character counts for
  the day corptools read it; no `total_logins` bookkeeping; today is left
  out of the share; no own ESI call (corptools reads a character about once
  a day - `update_subset_of_characters`, every 30 minutes the oldest 1/48 -
  so a day in EVE shows late and some are lost; told and accepted for now,
  the remedy would be corptools' `subset` parameter).
- **Production writes the Mumble timestamps**: 823 `MumbleUser`, 335 with a
  `last_connect` within 7 days (the user's check, 2026-11-16). Whether
  `last_disconnect` is written as well was not checked.
- Shown, never rated - like the spy markers; it keeps `percent_class`'
  colours though (below 60 % red), as Mumble does.

2026-11-16 (day by day):

- **The Mumble tile of Main details opens the main's days** ("ein klick auf
  die mumble kachel des nutzers (main details) führt zur tageweisen
  aufschlüsselung der aktivität"). The user's answers: a **page of its own**,
  not a fold-out; **every day of the window**, days without anything as "-";
  **today shown, marked** as running and not counted; the tile shows the
  **share below *linked*** too; an unlinked Mumble tile **also leads there**
  (the page says Mumble is not linked); **not on *My account*** - its tile
  keeps leading to Auth's services page and shows no share.
- Today is never red: a missing Mumble day only lowers the share once the
  day is over.

2026-11-16 (CharLink box):

- **Director token missing to CharLink** ("director token missing linke zu
  charlink statt corptools"). Neither corptools 3.5.1 (also `master`) nor
  aa-charlink 1.15.0 puts the sovereignty scope into CharLink's Corporation
  Audit box. The user chose a **box of the monitor's own** through CharLink's
  `charlink` hook, under the label `eos_auth_monitor`, over replacing
  CharLink's corptools entry (a second hook with the label `corptools` would
  switch both off as duplicates) and over waiting for corptools. The monitor
  keeps demanding the scope. `charlink_hook.py` copies CharLink's
  `LoginImport` with `dataclasses.replace`: only label, id and scopes differ.

2026-11-16 (tile lists):

- **Why the totals differ** (the user asked): *Registered in Auth* counts the
  member list from ESI, *Character Audit* only characters Auth knows. The
  user chose to count **members without a main as failing** the Character
  Audit (`unregistered` added to the total), which the overview tiles, table
  and cockpit follow; the Alliance-wide Character Audit list, sorting, smart
  filter and dashboard are unchanged. The base is not the member count
  itself: alts outside the overview rated here and members whose main is
  elsewhere differ from it.
- **A page of its own per tile** (the user's choice over two tables or a
  fold-out), one line per character with its main, negatives first; same
  access as the Corporation page (`basic_access` for the own one). A main in
  another Corporation stays unlinked, as on the Corporation page's
  *Members whose main is in another Corporation*.

2026-11-17 (numbers and column width):

- **Corporation column at least 14rem** (over 18rem or no wrapping at
  all): long names may still take two lines; narrow screens scroll the
  table sideways.
- **Main details numbers both lists running on**, the folded list after the
  table, so the last number is the count shown. A number **stays with its
  character** when sorting (over renumbering 1..n after each sort in JS);
  sorting by `#` restores the server's order.

2026-11-17 (Registered in Auth):

- **The tile stays where no member list was read** ("zeige die registered
  in auth kachel in corporation details auch, wenn kein char registered
  ist"). The user's answers: **whenever the list is missing**, not only
  without any main; the tile shows **the number of registered characters
  Auth knows, no total, no share**, plus the reason; it **links to its
  list**, which shows those characters with the same notice; **Corporation
  pages only**, the Alliance overview keeps leaving the row out.
- **Characters on an account without a main count as unregistered**, as
  with a read list: to-do entry, failing in Character Audit, the unknown
  characters list - also on the overview's Character Audit shares.
- The notice is the existing "no member has a token with the membership
  scope", not the "no Director token" first proposed: reading the list needs
  any member's token, not a Director's.

2026-11-17 (covered Directors):

- **A Director only warns when the account covers the Corporation** ("wenn
  für einen main / account mindestens ein director der corp vollständige corp
  tokens abgegeben hat, dann zeige alle weiteren director chars/alts des
  mains nur als warnung"). The user's answers: **same Corporation only** (a
  Director of another Corporation stays red); **like the scope warnings**
  (to-do group, complete in the Character Audit, dashboard yellow, smart
  filter passes); the **Director lists stay** as they are (token yes/no of
  the Director himself). The warning shows the check's own hint with the
  CharLink link, no extra sentence why it is yellow.
- "Complete" is the Director check's rule: every Corporation-audit scope
  minus those left out in the settings.
- **CharLink box *Full*** ("nenne es statt (sov..) beispielsweise (full).
  sonst nimmt man an, dass es nur sov ist"): checked in the dev instance -
  the box carries all 17 scopes the check asks for, CharLink's own
  Corporation Audit all but `esi-structures.read_corporation.v1`.

2026-11-17 (character crown):

- **Director crown per character on the account pages** ("zeige in der my
  account und main details sicht per icon an, welche chars director rechte
  haben"). The user's answers: a character counts as Director of **its own
  Corporation**, any of the Alliance's (not the crown's main-Corporation
  rule); the crown sits **at each character** (problem table and folded
  list), no extra crown in the card header. Display only.

2026-11-17 (CEO roles of eos-tax and eos-spy-network):

- **The other apps' CEO roles open their markers for the own Corporation**
  ("es gibt neuerdings eine ceo rolle im spy network und in eos tax ...
  entweder nutzen wir diese beiden für unsere marker oder wir knüpfen es an
  die ceo rechte von auth monitor"). The user chose **the apps' own CEO
  roles**, not `basic_access`: each app keeps deciding who sees its findings,
  and the tiles' links open pages the CEO may open. Not chosen: giving CEOs
  the full permissions (they would see the whole Alliance there).
- **GM (0.0.33)**: `eos_tax.basic_access` without the full view gives
  `sources.gm_transactions.ceo_corporation_id` (the main's Corporation);
  `character_ids(corporation_id)` takes eos-tax's own CEO rows
  (`get_gm_page(stored, corporation_id=...)`: in the Corporation now, or
  booked while in it). `Report.add_gm_transactions(..., corporation_id)`
  sets `gm_shown` on that Corporation only and leaves `Report.gm_shown`
  off (no cockpit tile, no overview column, which would read 0 elsewhere).
  An eos-tax whose `get_gm_page` lacks `corporation_id` gives a CEO nothing.
  Tests: 6 new in `test_gm_transactions` (25 in the module), 6 sabotages, 6
  red. No migration, no message, no template. Not seen in a browser.
- **Spy (0.0.33)**: the user chose an exact match ("Erst Spy-API
  erweitern") over filtering by the monitor's own Corporation of a
  character, so eos-spy-network 0.0.30 (released 2026-11-17, tag `v0.0.30`)
  added `api.character_markers(*, corporation_id=None)`: the mains of that
  Corporation with all their characters, as its Corporation page. Here
  `view_own_corporation` without `view_suspects` + `view_evidence` gives
  `sources.spy_network.ceo_corporation_id`; `character_markers(corporation_id)`
  and `Report.add_spy_markers(..., corporation_id)` work as for GM (only
  that Corporation's `spy_kinds`, `Report.spy_shown` off). An API without
  `corporation_id` gives a CEO nothing. Tests: 1 in `test_report`, 3 in
  `test_sources_other`, 2 in `test_views`; 6 sabotages, 6 red.

2026-11-17 (help mode, 0.0.34; "könnte man sowas wie einen hilfe button
einbauen, der alle bereiche/container mit erklärenden texten versieht"):

- **Info icon with popover** per area, not visible text boxes.
- **Pages**: Alliance overview, Corporation page, Account and My account;
  **not** Settings (nor the lists or the dashboard).
- **All texts written new** for the help mode, not taken from
  `Check.description`. The user approved the English drafts before they were
  built; *My account* has its own second-person texts.
- After seeing the first version: the icon goes into the **top right corner
  of a tile**, and the navbar button became a **switch named "Help mode",
  on by default** ("mach aus dem hilfe icon einen schalter, der per default
  an ist"). First not remembered at all; on 2026-11-18 changed to
  **remembered per user on the server** ("speichert sich der help status
  session übergreifend nicht?"): offered per browser (localStorage) or per
  user, the user chose per user, so it follows them across devices.
- The icon stays small (about 12 px): asked whether to enlarge it, the user
  said no ("passt so").
- The switch is green while on (`bg-success`, toggled by `help.js`): the
  theme's primary colour vanished on the primary-coloured navbar. Claude's
  call, not asked.

## Pitfalls found

- A new file under `static/` needs `collectstatic` before the tests: the
  manifest storage of `sri_static` raises "Missing staticfiles manifest
  entry" and almost every view test errors.
- The view tests read tiles with regexes (`TestPages.gauge`,
  `TestOwnAccountServices.tile_colours`) that expect the label `<div>` to
  hold the bare label right after the icon. Anything new on a tile goes at
  the end of its card body.

- `eos-test` takes one test label only; a second one fails with
  "unrecognized arguments". Run several modules one after another.
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
- Short words may clash with Alliance Auth's catalogue ("View" did, "Day"
  in ru and zh_Hans too): the
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
- `sed` in Git Bash turns a `\n` in its replacement into a real line break:
  a Python string edited that way ends unterminated. Change scratch scripts
  with the Edit tool.
- A sabotage pattern must be unique in its file (`snapshot.py` builds
  `in_auth` for Directors too; the status template tests `in_auth` twice):
  the script asserts a single match and stops otherwise.
- `test_aa_dev` is shared by every app's test runs: on 2026-11-04 an
  eos-sig-checker run from another session broke the kept database mid-run
  (a foreign migration failing, then "Unknown database"), and a sabotage
  round showed "red" for that reason alone. Run with
  `EOS_TEST_DB=test_eam_<topic>` while other sessions may test; check that a
  red round failed in a test, not in the setup.
- A sabotage round on `test_views` costs about a minute for the whole module;
  scope it to the test class (`tests.test_views.TestSpyNetwork`) - seconds.
- A sabotage that only adds an attribute the tests never look at (`hidden`
  on a cell) proves nothing; break what a test can see.
- To fake an uninstalled module that was already imported, setting
  `sys.modules[name] = None` is not enough: `from package import api` takes
  the package attribute first - remove that too, and put it back
  (`test_should_ignore_a_release_without_the_read_api`).

- `{% translate "..." as var %}` gives a safe string: `{{ var }}` renders an
  apostrophe as `'`, not `&#x27;` - assert on the plain text.
- A marker class for a test must not be a substring of another attribute on
  the page: `eos-auth-monitor-failed` is part of `data-eos-auth-monitor-failed`
  in `partials/state.html`, so `content.index()` always found it.
- `assertRegex(text, pattern, re.DOTALL)` passes the flag as the failure
  *message*: compile the pattern (`re.compile(..., re.DOTALL)`).
- A settings test that posts only some fields leaves a required field out
  and the form invalid - it then "keeps" every state because nothing was
  saved, and stays green. Since 0.0.19 `critical_scope_count` is required:
  post it (or `TestSettings.unchanged`), and assert the redirect.
- `tests.test_views.main_cards` cuts the Corporation page at each
  `<div class="card h-100 `: the last card runs to the end of the page,
  where the unregistered card is `border-danger` too - assert the border
  with `startswith('border-danger"')`, not `assertIn`.
- django-esi's exceptions need their fields to be built in a test:
  `HTTPClientError(status_code=403, headers={}, data=None)`, the same for
  `HTTPServerError`; a `RuntimeError("403")` stands for neither since
  0.0.24 and would now end the run.
- A test that patches `snapshot.build` must call the real one through a
  reference taken before the patch (`real_build = snapshot.build`), or it
  recurses into the mock.
- `/commit` and `/push` cannot be started by Claude (`disable-model-
  invocation`): the user types them. A full-width `／commit` arrives as text,
  not as the command.
- From PowerShell, `wsl.exe ... bash -lc '...'` loses the double quotes
  inside (a `grep -E "^(...)"` becomes a bash syntax error): put such
  commands into a script file in the scratchpad and run it by path.
- `eos-test` takes one test label only: a second module name ends in
  "unrecognized arguments". Run the modules one by one or the whole app.
- A fixture with fixed user IDs in a snapshot (`account_row(33, ...)`) can
  collide with a user a test creates: MySQL does not reset the
  auto-increment on rollback, so pks depend on which modules ran first. It
  broke `test_dashboard` only in the full suite once `test_activity` came
  before it (0.0.26); a single-module run stayed green. Use `make_user(...).pk`.
- `MumbleUser.objects.create()` is Auth's own manager: it takes a user and
  sets a password, not model fields. A test row goes in with
  `MumbleUser(...).save()`.

## Open points / next steps

- **Help mode (0.0.34)**: look at *My account* and an account page in the
  browser (service tiles' corner icon, the question mark in the folded
  *characters without problems* summary must not fold it). A new area added
  later needs its own help text, or it simply has none. Production needs
  `collectstatic` for `help.js`.

- **Registered in Auth without a member list not seen in a browser**
  (0.0.30): after a rebuild with the 0.0.30 code, open a Corporation without
  a membership token (all but Ether Element in dev) and check the tile, its
  long notice under the gauge, and the list page. Expect new to-dos and
  lower Character Audit shares where such a Corporation has characters on
  accounts without a main.

- **Active in Mumble has never seen real data or a browser.** After
  deploying: add the beat entry `eos_auth_monitor_record_activity` (README),
  then look after a few days whether the shares are plausible - above all
  whether the 24-hour rule and production's `last_disconnect` hold, and how
  many EVE days corptools' daily read loses. Ideas offered, not asked for:
  the number of mains behind a tile's mean as tooltip; a minimum of days in
  EVE before a main counts; the red below 60 % may read as a problem.
- The dev `local.py` has the new beat entry, but no beat runs in dev.

- **Alliance join date not seen in a browser** (0.0.25): it shows only after
  a rebuild run by a worker with the 0.0.25 code. Check that the header line
  does not wrap badly on narrow screens; a Corporation whose history ESI does
  not return (or a snapshot from before 0.0.25) shows no date.

- **Scope warnings not seen in a browser**, nor the yellow in AA's dark
  theme. In dev they show only after *Rebuild now* (the stored snapshot has no
  threshold and rates every missing scope a problem). The to-do card of the
  Corporation page keeps its red border even when it holds only warnings
  (and spy or GM entries) - not asked; ask if it should turn yellow.

- **Director crown not seen in a browser**: a long main name may run under
  the corner crown on a card (no padding reserved); `text-warning` in AA's
  dark theme unchecked. In dev it shows only after *Rebuild now* fills the
  `directors` (Ether Element: 14 Directors by ESI).

- **eos-spy-network markers not seen in a browser**: covered by tests of the
  rendered HTML only. In the dev instance they show only after
  eos-spy-network's own snapshot was rebuilt with 0.0.10 (its button or
  `snapshot.update()`), and only for a user holding both of its view
  permissions. Their colour (cyan, 0.0.20) is the user's choice of
  2026-11-10; check in a browser, light and dark theme, that the cyan badges
  and the `text-info-emphasis` counts read well. eos-spy-network 0.0.21 uses
  the same colour; its "Mains with markers" count is to move from
  `text-info` to `text-info-emphasis` as here - in an eos-spy-network
  session.
- **Spy and GM tags on the main cards and their order not seen in a
  browser** (0.0.21, 0.0.22): check that the red marker cards read well
  beside the problem cards and that the order (red, yellow; Directors, GM,
  rest) reads as intended; the user may still want the marker-only cards set
  apart from real problems (they share the red border, the problem count
  does not include them).
- The overview **tiles** have no spy number - the user asked for a column;
  ask if the tiles should get it too.
- **eos-tax GM transactions not seen in a browser**, nor the pink in AA's
  dark theme. In dev they need eos-tax's GM report (its *Recalculate* on
  GM Transactions) and a user with `eos_tax.gm_bots_access` or `admin_view`.
  Once eos-tax reads `?search=`, check in a browser that the account page's
  GM link opens that page filtered to the main (and to its alts).
- `sources.gm_transactions.character_ids()` builds eos-tax's whole GM page
  per page view (`shortcut:` comment): if it gets slow, give eos-tax a small
  read API like eos-spy-network's `api.py` - in an eos-tax session.
- **Overview table still wide**; ideas offered, none chosen yet: services in
  one column as coloured icons (shares in the tooltip), Spies and GM in one
  *Flags* column, Mains and Chars as "12 / 40", icon-only heads, rare columns
  hidden on narrow screens.

- **Rebuild the dev snapshot** (*Rebuild now*, after starting a worker, see
  *Dev instance*): then the unknown characters list should show *not in Auth*
  or *no main* for every one of Ether Element's 275, and the paging (275 rows:
  three pages of 100) and the table-first overview can be looked at.

- **Calls into eos-tax and eos-spy-network are unguarded**: the audit could
  not read those repositories (one per session). `sources.gm_transactions`
  and `sources.spy_network` call their APIs on every page view of a viewer
  with their permissions, without a try/except - an exception there fails
  that page. The contracts are listed at the end of *Checked and fine* in
  `docs/AUDIT.md`; the sibling audit sessions got the same list.
- Production still runs 0.0.5: 0.0.6 to 0.0.30 are to be deployed, with
  migrations 0007 to 0010, `collectstatic` (for the spy markers also
  eos-spy-network 0.0.10) and the new beat entry
  `eos_auth_monitor_record_activity` in `local.py` (README, *Installation*;
  without it Active in Mumble stays empty). After deploying, *Rebuild now* (or the beat run) fills the
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
  (`filter.js`, `view.js`, `copy.js`, the paging in `tables.js`), the
  unknown characters list, the tiles (the new check tiles
  included), the table, the footer, the navbar tabs, the two dashboard
  widgets and their borders, the CSV download, the audit lists, the visiting
  cards, the notice box, the scope tooltip and the sovereignty hint are covered by tests of the rendered HTML (and of
  the CSV bytes) only.
- Discord is voluntary like QQ and Telegram but stays red on *My account*:
  the user named only QQ and Telegram. Asked after 0.0.10 whether Discord
  should go grey as well, not answered yet (one flag in `checks.SERVICES`).
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
  off, the notice empty, `critical_scope_count` 5 (the migration's
  default). **No Celery worker was running** on 2026-11-09 nor on 2026-11-13 (`ps` found none; not checked on 2026-11-16; a worker started now runs the 0.0.25 code):
  *Rebuild now* queues for nobody until one is started detached by a script
  (`setsid nohup ~/aa-dev/venv/bin/celery -A myauth worker -l info -P solo`
  in `~/aa-dev/working/myauth`, log in `/tmp/celery-eos.log`); one worker,
  check `ps` first. **No Celery beat runs** in the dev instance,
  so the beat entry never fires and the stored snapshot (2026-09-30 11:11 UTC,
  with `directors`, without `in_auth`: the unknown characters list shows
  "-" as status for all 275 of Ether Element) stays until *Rebuild now*. `runserver` reloads by itself.
  Rendered against `aa_dev`, the account's 3 problem links on *My account* go
  to `/charlink/`. Ether Element: 279 in the member list,
  290 in Auth's count, 14 Directors named by ESI; Nah vi is one of them and
  is flagged. The other Corporations have no token with the membership scope
  and carry "No Director token".
- `collectstatic` was run after `view.js` and `copy.js` were added.
- eos-spy-network is installed editable from `~/aa-dev/working/eos-spy-network`
  (0.0.30 on 2026-11-17, `character_markers(corporation_id=...)`), so the spy
  tests run here; eos-tax likewise (0.4.27, `get_gm_page(corporation_id=...)`).
- `eos-test` takes one test label per run; several modules need a loop.
- Installed: allianceauth 5.3.1, allianceauth-corptools 3.5.0, django-solo
  2.5.1, django-esi 9.10.0. Target production per checklist: AA 5.4.0,
  corptools 3.5.0, aa-structures 4.0.1.
