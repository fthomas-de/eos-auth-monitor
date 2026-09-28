# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
