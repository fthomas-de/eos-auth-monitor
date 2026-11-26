# Decisions

The user's decisions on `eos-auth-monitor` that hold for good and cannot be
seen in the code, sorted by topic. No session dates: an entry says what holds
and why. When a decision changes, its entry is replaced; superseded entries
are deleted. Not read at session start - look things up with `grep` or by
section.

## Scope and counting

- An account belongs to the overview when its main is in the configured
  Alliance. All its characters are checked, alts outside the Alliance
  included, unless *Only characters in the Alliance* (off by default) is on:
  then those alts are left out altogether and the account pages say how many.
- Each character counts in the Corporation of the overview it is in, not in
  its main's ("ein account kann chars in mehreren corps der alli haben, das
  ist erlaubt"); outside the overview it counts with its main.
- Corporation page: every member, reduced to mains where Auth knows the
  account; an unknown member counts as a main.
- Service shares count mains only, everywhere (cockpit, Corporation tiles and
  table, Corporation page). Unknown characters are shown apart, behind the
  cockpit's *Members registered* tile. The Connections tile counts real links.
- Character count per Corporation from `EveCorporationInfo.member_count`; the
  member list wins where it was read.
- Corporation-level rows on a tile (Corporation Audit, Structures) show 100 %
  or 0 %.
- *Character Audit* counts members without a main as failing (overview,
  tiles, cockpit); the Alliance-wide Character Audit list, sorting, smart
  filter and dashboard do not. *Registered in Auth* counts the ESI member
  list, *Character Audit* only characters Auth knows - that is why the totals
  differ.
- Where no member list was read, the *Registered in Auth* tile still shows on
  Corporation pages (not the overview): the number of registered characters
  Auth knows, no total, no share, the reason as notice ("no member has a token
  with the membership scope" - reading the list needs any member's token), and
  it links to its list. Characters on an account without a main count as
  unregistered, as with a read list.
- Gua Zi 2nd hand (98827954), reported as outside the Alliance, is in it by ESI
  since 2026-08-20. No exclusion list was asked for.

## Checks

- Stale after: the default follows corptools' `CT_CHAR_MAX_INACTIVE_DAYS`.
  corptools checks can leave out single sections and scopes.
- aa-structures fails on: no owner, owner inactive, no enabled owner
  character, `are_all_syncs_ok` false.
- Director check (*Director token missing*): a Director without a token
  carrying every Corporation-audit scope (minus those left out in the
  settings). Directors come from corptools' roles and from ESI's roles call -
  corptools never reads the roles of a character without a token. Only inside
  the Alliance: such Corporations outside it are not asked.
- The monitor keeps demanding `esi-structures.read_corporation.v1`.
- **Scope warnings**: a *Scopes missing* below `critical_scope_count` (default
  5) is a warning, not a problem - only this check (Director token missing
  stays a problem). A warned character counts as complete in the Character
  Audit shares, the dashboard widget turns yellow, the smart filter passes.
  Corporation page: yellow card for warnings alone, red as soon as there is a
  problem; to-do group *Scopes missing (warning)*.
- **Covered Directors**: a Director only warns when a character of the same
  account holds a complete Corporation token for the same Corporation (a
  Director of another Corporation stays red); handled like the scope warnings.
  The Director lists stay as they are (token yes/no of the Director himself).
  The warning shows the check's own hint, no sentence why it is yellow.
- **Services**: QQ from aa-qqbot (`qqbot.Binding`), Telegram from
  aa-discord-telegram-bridge (`TelegramUser.telegram_user_id`), Discord and
  Mumble from Alliance Auth. Discord, QQ and Telegram are voluntary: grey on
  the overview's tiles and table only; cockpit, Corporation and account pages
  keep their colours. Mumble is mandatory, colour only. No service is ever a
  problem (no red border, problem count or sorting).
- "No Director token" (no Director's token could read the roles) is an info
  icon with tooltip, not a problem; set only while the ESI switch is on
  together with the Director check or a Director list.

## ESI

- Member lists and roles from ESI with tokens corptools already holds
  (corptools stores no member list). One switch, *Fetch data from ESI*, covers
  both.
- ESI down (server error, error limit, no network) fails the run and the last
  good snapshot stays; only a token failure (`TokenError`, a 4xx) moves on to
  the next token. Not chosen: carrying over the previous lists.
- The Alliance join date comes from ESI's public alliance history at every
  rebuild (corptools does not have it), independent of the ESI switch; a
  failure there does not fail the run.
- Failed ESI tokens are retried every run and spend the error limit: the user
  chose not to change it for now.

## Computation

- Celery task plus stored snapshot; progress bar while it runs.
- Members cannot rebuild ("kann so bleiben"): *Rebuild now* needs `view_all`
  or `manage_settings`; only the progress poll is open to every app
  permission.

## Permissions

- `basic_access` (own main's Corporation), `view_all` (all Corporations),
  `manage_settings` (settings), `view_own` (members: *My account* only).
- A logged-in user without the permission gets 403, in every eos app alike.
- A visiting main links to its account only for `view_all`: a CEO may not
  open another Corporation's account. For a viewer without `view_all` a
  visiting main's card hides its service icons and its Director crown. Read as
  both, since the question named both; if only the icons were meant, drop the
  condition around `director-icon.html` in `corporation.html` and the crown
  assertions in `TestAltsInAnotherCorporation`.
- Asked in the permission review and kept as they are: the Director crown of
  alts in other Corporations on the account pages; mains of visiting accounts
  named for a CEO without `view_all`; corptools-derived data (audit state,
  scopes, login days, roles) for `basic_access` without corptools' own
  permissions. Left as information: a CEO can tell "not in the overview" (404)
  from "another Corporation" (403) by user ID; the CEO's live main Corporation
  is compared with the snapshot's.
- The CEO roles of eos-tax (`eos_tax.basic_access`) and eos-spy-network
  (`view_own_corporation`) open that app's findings for the own main's
  Corporation only - each app keeps deciding who sees its findings, and the
  tiles' links open pages the CEO may open. No cockpit tile or overview
  column for them. On the account pages they show for alts elsewhere, as the
  source apps do. Not chosen: tying them to `basic_access`, or giving CEOs the
  full permissions.

## Pages and layout

- Aim: a compact overview for the Alliance's leadership and for each CEO.
  Overview as table (the default) or tiles, *Only with problems*; Corporation
  page with a to-do list (copy and CSV buttons), cards only for mains with
  something open, compact lists for the rest; account page with a hint per
  problem and the characters without problems folded away.
- Page header "Auth Monitor (version)", the page below it; a service list is
  named after its service.
- Navbar: *My account*, *My Corporation*, *Alliance overview*, then Settings.
- Paging on every sortable list longer than 25 rows, 100 per page - not the
  overview table, whose filter hides rows itself.
- Overview table heads shortened (*Corp*, *Chars*, *Spies*, *GM*; the whole
  name as tooltip), the Corporation column at least 14rem.
- The overview table keeps one column per service (2026-11-26: the services
  in one column as coloured icons was chosen, then dropped again). Not chosen
  either: a *Flags* column for Spies and GM, Mains and Chars as "12 / 40",
  icon-only heads, rare columns hidden on narrow screens.
- The overview's Corporation tiles show the spy and GM numbers like the
  table's columns, at the end of the tile, without links of their own.
- The Corporation page's to-do card is yellow with warnings only; a problem,
  unregistered members, a spy marker or a GM transaction keep it red, like the
  main cards.
- Everything is sorted by number of problems, most first, then by name -
  except the Corporations: by accounts with problems (the number shown), then
  the Corporation's own problems, then the name.
- Main cards on the Corporation page: red before yellow before nothing open;
  within red and yellow first Directors (the crown's rule), then GM
  transactions, then the rest.
- Corporation page: the checks' apps as tiles before the service tiles;
  *Registered in Auth* and *Character Audit* open lists of their own (one line
  per character with its main, negatives first, same access as the
  Corporation page). *Alts of mains in other Corporations* is one section
  after the own mains: every visiting main a card, sorted like the cards; the
  mains outside the Alliance from the member list named only.
- Cockpit audit tiles open lists of their own: Character Audit every main
  with a tag per failed check; Corporation Audit and Structures the Directors,
  those without the token first, Directors unknown to Auth tagged *not in
  Auth*.
- Service lists show mains only, without problem badges; table columns are
  left-aligned.
- CSV export per to-do group and for the whole list (Problem, Name).
- Scope lists cut after two ("a, b and N more", the whole list as tooltip);
  the settings page's checkboxes stay whole.
- Character names on the account pages link to their corptools Character
  Audit.
- Main details numbers the characters running on from the table into the
  folded list; a number stays with its character when sorting.
- Main details shows the account's Auth groups in brackets after the main's
  name, the groups a state hands out included (without them an account whose
  groups all come from a state showed nothing).
- The Corporation header shows "In the Alliance since" with date and duration
  on every page with the header.
- The account page shows the account's own service links as tiles, not the
  Corporation's shares.

## My account and dashboard

- *My account* speaks to the member, German with *du*; it asks whether
  characters are missing, linking to CharLink or `add_character`. Its
  service tiles link to Auth's services page; unlinked QQ and Telegram are
  grey there, every other tile red.
- Notice to members (settings): plain text, line breaks kept, links made
  clickable; on *My account* and on the Corporation page only as *My
  Corporation*. Empty: no box.
- Dashboard widgets at eos-invoices' order (4), named *My account* and *My
  Corporation* (no "Auth Monitor" in front), for `view_own` and `basic_access`
  - no new permissions, they follow the pages they link to. Green border
  without anything to do, yellow with warnings only, red otherwise.

## CharLink

- Every problem links to aa-charlink where installed: the account page with
  hints about the player in the third person, *My account* in the second, the
  Corporation page's to-do list, the Corporation header ("verlinke charlink in
  corporation details und nicht structures oder corp tools"). Without
  aa-charlink the check's app is the link. *Structure owner inactive* has no
  CharLink hint (an admin switches the owner on).
- *Director token missing* always links to CharLink, to a box of the
  monitor's own, *Corporation Audit (Full)*, added through CharLink's
  `charlink` hook: neither corptools nor aa-charlink puts the sovereignty
  scope into CharLink's Corporation Audit box. Not chosen: replacing
  CharLink's corptools entry (a second hook with the label `corptools` would
  switch both off as duplicates) or waiting for corptools. Named *Full*, not
  *Sovereignty*, so nobody takes it for the sovereignty scope alone.

## Director crowns

- On the Corporation page's cards and compact list: a crown when any
  character of the account, the main included, is a Director of the main's
  Corporation (for a visiting main: its own Corporation), names as tooltip.
  Not on the overview or the dashboard. Data as it is: no Director lists, no
  crown.
- On the account pages a crown at each character that is a Director of its
  own Corporation, any of the Alliance's; none in the card header.
- Display only, never a problem.

## eos-spy-network

- Markers per character for viewers with `view_suspects` (or the CEO role):
  a *Spies* column in the overview table and the number on the overview
  tiles, a cockpit tile and a Corporation tile linked to
  eos-spy-network, a to-do entry per marker kind, a cyan tag per kind on the
  main cards (a card for markers alone, red border - neither app gives a
  severity; not set apart from the problem cards, asked and kept), the
  markers on the account page. Counted as characters with markers, each in
  its own Corporation.
- Display only: no problem count, sorting, dashboard or smart filter; never on
  *My account*.
- Read from its API on every page view, nothing in the snapshot. An exception
  there leaves the markers out of that page, logged with its traceback and
  with a notice to the viewer (2026-11-26); likewise for eos-tax.
- Alts of mains outside the Alliance with markers: card, to-do, tile, CSV and
  overview column (eos-spy-network shows them to the CEO of the alt's
  Corporation).
- A CEO role's exact Corporation comes from eos-spy-network's API
  (`corporation_id`), not from the monitor's own view of a character.

## eos-tax GM transactions

- A finding is a row of eos-tax's stored GM report with counterparty
  `FLAGGED_PARTY` ("GM X"), read on every page view through
  `eos_tax.api.gm_x_character_ids`; an eos-tax without that API falls back to
  building its GM page (`get_gm_page`). Visible with `eos_tax.admin_view` or
  `gm_bots_access`, eos-tax's own rule for the tab - the API checks none.
- A GM transaction marks the whole account (any character, also outside the
  Alliance), for every viewer, on own and visiting cards and on cards of mains
  outside the Alliance. Counted by mains: Corporation tile and *GM* column
  count the mains, the cockpit sums the Corporations - an account with cards
  in two Corporations counts twice there (told, kept).
- The cockpit and Corporation tiles link to eos-tax; the *GM* column does not
  ("das macht die kachel oben ja schon").
- The account page's GM link searches eos-tax for the main's name
  (`?search="<main>"`): not the Corporation too (alts elsewhere would be
  hidden), not a column filter (invisible, not clearable).
- Display only, like the spy markers.

## Colours

- Yellow warnings, pink GM transactions (`var(--bs-pink)`; not yellow or
  orange), cyan spy markers (`text-bg-info`, counts `text-info-emphasis` -
  purple read badly in AA's dark theme), red problems; a 0 stays green.
- Corporation problems red in the header: they count as problems.
- The Help mode switch is green while on: the theme's primary colour vanished
  on the navbar.

## Active in Mumble

- Per main and day two flags: a character in EVE, a character in Mumble. The
  share is days with both out of days in EVE; Mumble without EVE changes
  nothing. Today is shown, marked, and not counted.
- Only mains with Mumble linked are rated; the others show "-".
- A tile pools the days of its mains (the sum of days with Mumble over the sum
  of days in EVE).
- Shown on the Mumble tiles of cockpit and Corporation page (below the linked
  share), per Corporation on the overview, as a column in the Mumble lists.
  The Main details tile opens a page of its own with every day of the window;
  an unlinked Mumble leads there too. Not on *My account* or the dashboard.
- Shown, never rated, but in `percent_class`' colours (below 60 % red).
- Window and retention are one setting ("letzte 30 tage einstellbar");
  characters as the settings count them.
- Connected counts for at most 24 hours after the connect: the Mumble server
  restarts daily.
- No ESI call of its own: corptools reads a character about once a day, so a
  day in EVE shows late and some are lost (told and accepted; the remedy
  would be corptools' `subset` parameter).

## Help mode

- A question mark per area with a popover, no visible text boxes; on the
  Alliance overview, the Corporation page, Main details and *My account*, not
  on Settings, the lists or the dashboard.
- All texts written new (not `Check.description`); *My account* has its own
  second-person texts. A new area needs its own text.
- On a tile the icon sits in the top right corner, small (about 12 px, "passt
  so"). The navbar switch "Help mode" is on by default and remembered per user
  on the server, so it follows the user across devices.

## Smart filter

- `CharacterProblemsFilter` (a new name, so a leftover binding of the dropped
  0.0.1 filter cannot attach to it) passes an account without character
  problems in the whole account; *Reversed logic* those with. Corporation
  problems do not count.
- Unknown fails always, chosen knowing the cost: without a snapshot everyone
  fails, so the README says to rebuild before binding it.

## Accepted as they are

Asked and settled; not to be raised as open points again:

- QQ and Telegram tiles on *My account* linking to Auth's services page.
- Service lists showing registered mains only.
- Directors nobody can read the roles of stay unfound ("No Director token").
- The `allianceauth>=5.1.4` floor derived from the tags, never run against
  5.1.4.
- Machine-generated translations; no CI.
- Performance with a large Alliance untested (the footer measures it); the
  queries and ESI calls stay as they are.
- The CharLink hints name the boxes as CharLink labels them ("Character
  Audit" is corptools' default `CORPTOOLS_APP_NAME`; a renamed one differs).
- CharLink shows *Corporation Audit* only to holders of a corptools
  Corporation permission and *Structures* only to holders of
  `structures.add_structure_owner`: a Director or Station Manager without
  them follows the link and finds no box.
- A GM to-do entry of a main outside the Alliance has no link, and its other
  characters outside the Alliance are unknown here.

## Working on the app

- Install and register every new app in the dev instance, then run `migrate`
  and `collectstatic`.
- No audit report in the repo: `docs/AUDIT.md` was removed (2026-11-26).
