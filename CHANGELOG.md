# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

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

### Added

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
- Footer with the cost of the last rebuild for holders of `view_all` or
  `manage_settings`: duration and time per step, database queries with their
  time, Corporations, accounts and characters read, member lists read, size
  of the stored result. The figures are kept inside the snapshot; snapshots
  from before show no footer until the next run.

### Changed

- The build backend is hatchling instead of flit, so the wheel no longer
  contains `eos_auth_monitor/tests`; the sdist holds the package, the
  README, the LICENSE and the CHANGELOG only.

## [0.0.1] - 2026-09-28

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
