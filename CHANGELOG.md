# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- *My account* shows an unlinked QQ or Telegram tile in grey instead of red:
  nobody has to use them. Discord and Mumble stay red, and the account page
  seen by a CEO or the Alliance's leadership keeps every service red.

## [0.0.9] - 2026-09-30

### Changed

- *Director token missing* sends the Director to *Add Token* in the corptools
  Corporation Audit, with every box ticked, where the token lacks
  `esi-structures.read_corporation.v1`: aa-charlink asks for corptools' fixed
  list of Corporation scopes, which leaves it out. Other missing scopes keep
  the link to aa-charlink; the to-do list on the Corporation page follows the
  same rule.
- Both dashboard widgets have a green border when nothing is wrong, and keep
  the red one otherwise; before, a widget without problems had none.

### Fixed

- Without aa-charlink, the link of *Director token missing* is labelled
  *corptools - Corporation Audit*, the page it opens, instead of *Character
  Audit*.

## [0.0.8] - 2026-09-30

### Added

- *Notice to members* on the settings page: a text shown as an info box on
  *My account* and *My Corporation*; while it is empty no box is shown.
  Saving only a changed notice starts no rebuild. Migration 0008.

### Changed

- The two dashboard widgets are named *My account* and *My Corporation*
  instead of both *Auth Monitor*.
- A list of missing scopes (*Scopes missing*, *Director token missing*) names
  the first two and how many more; the whole list is the tooltip.

## [0.0.7] - 2026-09-30

### Added

- On the account page and on *My account* each character's name links to its
  corptools Character Audit.
- Smart filter for allianceauth-securegroups, *Smart Filter: Auth Monitor
  character problems*: passes an account none of whose characters has a
  problem, or with *Reversed logic* one that has; the audit names the failed
  checks. It reads the last result: an account outside the overview fails
  either way, and so does everyone before the first result is stored.
  Created in the Django admin; migration 0007 adds its table.

### Changed

- Discord, QQ and Telegram are voluntary: on the overview's Corporation tiles
  and in its table their share is shown in grey instead of green, yellow or
  red. Mumble keeps its colours, and so do the cockpit, the Corporation page
  and the account page. None of the services ever counted as a problem.
- The Corporation's own problems in the header of the Corporation pages and
  the account page link to aa-charlink where it is installed, with a hint
  saying which box a Director or Station Manager ticks, instead of to
  corptools or aa-structures. *Structure owner inactive* keeps its hint
  without a link: an admin switches the owner on in aa-structures.
- On the Corporation page *Registered in Auth*, *Character Audit*,
  *Corporation Audit* and *Structures* are tiles with their percentage, before
  the service tiles, instead of lines in the header. A Corporation-level tile
  names the failed checks below its percentage.

## [0.0.6] - 2026-09-30

### Added

- Lists behind the audit tiles of the cockpit: *Character Audit* shows every
  main of the Alliance with a tag per failed character check; *Corporation
  Audit* and *Structures* show every Director of the Alliance's Corporations
  with its main and whether it has a Corporation-audit token or fetches data
  for the aa-structures owner, those without first. Directors unknown to
  Auth are tagged *not in Auth*. The lists appear after the next rebuild.

- *My account* asks whether one of the member's characters is missing and
  links to aa-charlink, or to Alliance Auth's *Add Character* without it.

### Changed

- *My account* speaks to the member throughout: the hints, the line when
  nothing is wrong and the count of characters left out (German with *du*),
  also without aa-charlink.
- A character counts in the Corporation of the Alliance it is in, not in its
  main's: an alt in another Corporation of the Alliance turns that
  Corporation's tile and page red, shows there as a card with "Main in ..."
  and puts its main into that page's to-do list. A character in a
  Corporation outside the overview still counts with its main. The account
  page and the Alliance-wide lists keep the whole account. On the
  Corporation page, a CEO sees such a main without a link to its account.
- With aa-charlink installed, the to-do list of the Corporation page says
  what to do in aa-charlink instead of naming the corptools pages.
- The Character Audit, Corporation Audit and Structures tiles of the cockpit
  open these lists instead of corptools and aa-structures.
- With *Fetch data from ESI* on, the Director roles are also read when the
  Director check is off but a Director list needs them, and *No Director
  token* marks a Corporation in that case too.

- With aa-charlink installed, the problems of the characters on the account
  page link to aa-charlink as well, like on *My account*. The hints on both
  pages say what to do there - which app to tick before logging in with the
  character - instead of naming the corptools pages. The Corporation's own
  problems in the header, the Corporation page and every page without
  aa-charlink keep the link to the app of the check.

## [0.0.5] - 2026-09-29

### Added

- With *Only characters in the Alliance* on, the account page and *My
  account* say how many characters of the account are outside the Alliance
  and neither shown nor checked there. A snapshot built before this release
  shows no such line until it is rebuilt.

### Changed

- The problems on *My account* link to aa-charlink, where members add a
  character to every app at once; without aa-charlink they keep the link to
  the app of the check. Every other page keeps linking to that app.

### Fixed

- *Director token missing* flagged a main whose alt is a Director of a
  Corporation outside the Alliance. Only Directors in the Alliance count
  now, whatever *Only characters in the Alliance* says, and the roles are
  no longer asked for Corporations outside the Alliance - which also spares
  those ESI calls.

## [0.0.4] - 2026-09-29

### Added

- Setting *Only characters in the Alliance* (off by default): with it on,
  the characters of an account outside the Alliance are left out of every
  check, page and count, and their Corporations are no longer asked for
  Director roles. Migration `0006`.

## [0.0.3] - 2026-09-29

### Added

- The app navbar has a tab per view, from the narrowest to the widest:
  *My account* (`view_own`), *My Corporation* (the Corporation of the own
  main, for `basic_access` and `view_all`), *Alliance overview* (`view_all`),
  then *Settings*. A Corporation page marks *My Corporation* only for the own
  Corporation; any other one belongs to the Alliance overview.
- Two widgets on Alliance Auth's dashboard, at the same place as eos-invoices'
  (order 4): the own account in short - each failed check with the number of
  characters, the linked services - with a link to *My account*
  (`view_own`), and the own main's Corporation in short - its own problems,
  each to-do group with the number of mains, the members not registered in
  Auth - with a link to the Corporation page (`basic_access`). Both stay
  hidden when the snapshot has nothing about the viewer.
- CSV export of the to-do list on the Corporation page: a button beside each
  *Copy names* for that group (one name per line) and one for the whole list
  (problem and name per line). Excel opens the file as UTF-8, and a name that
  a spreadsheet would run as a formula is written as text.

### Changed

- The service tiles of *My account* open Alliance Auth's services page, where
  a member links the service.
- The navbar tab *Overview* is called *Alliance overview* and comes after
  *My account* and *My Corporation*.

## [0.0.2] - 2026-09-29

### Added

- The page header names the page under the app's name: Corporation overview,
  Corporation details, Main details, the settings; a service list is named
  after its service (Discord, Mumble, QQ, Telegram).
- The overview shows the Corporations as tiles or as a sortable table, one
  line per Corporation; the browser remembers the choice.
- A switch above the overview shows only the Corporations with problems.
- Each Corporation tile shows the number of accounts with problems, and the
  Corporation's own problems beside it.
- The Corporation page starts with a to-do list: per failed check the mains
  it concerns and what they have to do, and the members not registered in
  Auth. A button per group copies the names for an EVE mail.
- Every check has a hint what to do about it, with a link to the app where it
  is done, on the account page and for the Corporation's own problems.
- Permission `view_own` and the page *My account*: a member sees their own
  account - characters, problems, what to do - and nothing about others.
- Saving the settings or *Rebuild now* while the task queue is unreachable
  says so instead of failing with an error page; the progress bar is not left
  waiting.

### Changed

- On the Corporation page only the mains with problems get a card; the
  others, and the members not registered in Auth, are a compact list.
- The account page lists the characters with problems; those without are
  folded away below it.
- *No Director token* is a small info mark with a tooltip beside the name
  instead of a badge.
- Alliance Auth 5.1.4 is the minimum: migration 0002 needs `eveonline` 0025,
  which 5.0.0 to 5.1.3 lack.
- The README describes what the ESI calls use and cost, what `basic_access`
  reveals, installing a tag, and a complete uninstall.

### Removed

- The smart filter for allianceauth-securegroups. Without a result every
  account failed it, and a smart group would have removed all its members.
  Migration 0005 drops its table: remove the filter from every smart group and
  delete it before upgrading.

- The cockpit tiles Character Audit complete and Corporation Audit working
  link to corptools, Structures working to aa-structures, instead of Auth's
  services page. A tile whose app is not installed has no link.
- The version stands in brackets beside the app's name.
- The service list of a Corporation shows one row per main, as a service
  links an account and not each character, and no longer shows problems.
- Every table column is left-aligned; DataTables put the service and
  problem columns to the right.

### Fixed

- The Members registered tile of the cockpit linked to the list of the
  service tile before it.

## [0.0.1] - 2026-09-29

### Added

- Project skeleton: package metadata (flit), the `testauth` test project.
- Permissions `basic_access` (own Corporation), `view_all` (whole Alliance)
  and `manage_settings` (settings page), and a menu entry "Auth Monitor" for
  anyone holding one of them.
- Overview with a cockpit of percentages - linked Discord, Mumble, QQ and
  Telegram per main, members registered in Auth, complete Character Audits,
  working Corporation Audits and structure owners - a tile with the number
  of connections per service, and one tile per Corporation listing each app
  with its share of complete entries.
- Corporation page with every member reduced to mains: the Corporation's
  mains as tiles with keywords for their problems, members whose main is in
  another Corporation, and members not registered in Auth.
- Member lists of the Corporations read from ESI with tokens corptools
  already holds - the app's only ESI call; can be switched off.
- Account page with every character and the details of each problem.
- Service lists per Corporation, with problem characters marked, and per
  Alliance. All tables are sortable.
- Checks from corptools (Character Audit missing, scopes missing, audit
  inactive; Corporation Audit missing, token missing, data stale) and
  aa-structures (no owner, owner inactive, no owner character, sync failing).
- Settings page: Alliance as a searchable dropdown, the limit for stale
  Corporation data, a switch per check grouped by app and a switch per
  service, and which corptools sections and scopes the checks count.
- Periodic task `eos_auth_monitor.tasks.update_snapshot` that builds the
  overview, also started after saving the settings and by "Rebuild now",
  with a progress bar while it runs.
- Smart filter for allianceauth-securegroups: does an account have problems?
- Translations into German, Russian and Simplified Chinese (machine-generated),
  kept in `tools/glossary.py` and written into the catalogues by
  `tools/translate.py`. EVE jargon (Corporation, Alliance, Character, Main)
  stays English.
- Number of characters per Corporation on the overview and on the Corporation
  page, from the member count Auth stores (no token needed); the member list
  wins where it could be read.
- The roles of a Corporation are read from ESI with a Director's token
  (`GET /corporations/{id}/roles`), so the Director check also finds
  Directors corptools never read the roles of. Runs with the member lists
  switch.
- Check "Director token missing" (corptools Character Audit group): a
  character that is a Director of its Corporation and has no token with all
  scopes of the Corporation audit. It shows as a keyword on the main's tile
  and as a problem of the character. Switchable like the other checks.
- Filter above the Corporation tiles of the overview, by name or ticker.
- Statistic tiles for the linked services (Discord, Mumble, QQ, Telegram) on
  the Corporation page: the share of the Corporation's mains that linked
  each one, linking to the Corporation's service list. They replace the
  service buttons in the header of that page (the other Corporation pages keep
  the buttons). The overview had them for the whole Alliance already; both use
  the same tile now.
- Corporations where no Director's token could read the roles are marked
  "No Director token" on the overview tile and on the Corporation page: the
  check *Director token missing* cannot see their Directors. It is a marker,
  not a problem, and does not count in the percentages.
- Footer with the cost of the last rebuild for holders of `view_all` or
  `manage_settings`: duration and time per step, database queries with their
  time, Corporations, accounts and characters read, member lists read, size
  of the stored result. The figures are kept inside the snapshot; snapshots
  from before show no footer until the next run.

### Changed

- The cockpit tiles Character Audit, Corporation Audit and Structures link to
  Alliance Auth's services page.
- The settings switch *Fetch member lists from ESI* is now called *Fetch data
  from ESI*, as it also covers the roles call (migration 0004, help text only).
- The cockpit's and the Corporation tiles' service shares count members Auth
  does not know as mains that linked nothing (before: only the registered
  mains, so 0 of 1 for a Corporation of 279 members).
- Corporation tiles, mains, characters and the service lists are ordered by
  the number of problems, most first, then by name (before: by name, on the
  Corporation page problem accounts first).
- The account page shows one tile per service for the main, green when the
  account linked it and red when not, linking to the Corporation's list of
  that service; the header's service buttons and the badges are gone there.
- Members not registered in Auth are listed on the Corporation page as cards
  like the mains, each marked "Not registered in Auth", instead of a table.
- The build backend is hatchling instead of flit, so the wheel no longer
  contains `eos_auth_monitor/tests`; the sdist holds the package, the
  README, the LICENSE and the CHANGELOG only.
