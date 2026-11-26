# Handover

Where the work on `eos-auth-monitor` stands, for the next session. Describes a
moment; where it contradicts the code, the code is right. At most 300 lines:
`/push` rewrites it and never appends.

Elsewhere: lasting rules and traps in `CLAUDE.md`, the history in
`CHANGELOG.md`, the user's lasting decisions in `docs/DECISIONS.md` - read
that one only when a task touches it (`grep -n <topic> docs/DECISIONS.md` or
one section), not at session start.

## State

- Version: `0.1.0`, 2026-11-26 (eos-spy-network and eos-tax guarded, GM
  transactions through eos-tax's read API, yellow to-do card for warnings
  only, spy and GM numbers on the overview tiles).
- Not deployed yet: `0.1.0` - production runs 0.0.42. Prod steps: install,
  restart the Celery workers and the web server; no migration, no
  `collectstatic` (no new static file), no rebuild needed. Works with the
  released eos-tax (falls back to its GM page) as with one that has
  `eos_tax.api`.
- What the app does today: it shows the problem accounts and Corporations of
  one Alliance - incomplete corptools audits, missing corptools and
  aa-structures tokens, Directors without a full Corporation token, linked
  Discord, Mumble, QQ and Telegram, Active in Mumble - read out of other apps'
  models into a snapshot built by a Celery task. On top it shows eos-spy-network
  markers and eos-tax GM transactions per page view, to viewers with those
  apps' permissions; a failure there leaves that part out with a notice.

## Pages

| Page | Permission | What |
|---|---|---|
| Overview (`index`) | `view_all` | Cockpit tiles, then the Corporations as table (default) or tiles |
| Corporation | `view_all`, or `basic_access` for the own main's | Check and service tiles, to-do list with copy/CSV, main cards, *Alts of mains in other Corporations*, unregistered members |
| `corporation_registered`, `corporation_character_audit` | as Corporation | The lists behind those two tiles |
| `corporation_export` | as Corporation | CSV of the to-do list, per group or whole |
| Account (Main details) | as Corporation, by the main | Service tiles, characters with problems, the rest folded |
| `account_activity` | as Account | Active in Mumble day by day |
| Corporation service / Service | as Corporation / `view_all` | Mains linked yes/no, Active in Mumble for Mumble |
| `character_audit`, `directors/<group>`, `unknown_characters` | `view_all` | Alliance-wide lists behind the cockpit tiles |
| My account (`own_account`) | `view_own` | The viewer's own account, second person |
| Dashboard widgets | `view_own` / `basic_access` | *My account*, *My Corporation* |
| Settings | `manage_settings` | Alliance, thresholds, switches, notice to members |
| Rebuild / progress / `help_mode` | `view_all` or `manage_settings` / any app permission | POST, JSON, POST |

Code layout: `checks.py` (checks, groups, services, hints),
`sources/` (one read-only reader per foreign app; `members.py` holds the ESI
calls), `snapshot.py` (builds the JSON, `tasks.update_snapshot`),
`activity.py` (Active in Mumble, `tasks.record_activity`), `report.py`
(labels, counts, sort orders), `views.py`, `forms.py`, `charlink_hook.py`,
`smart_filters.py`. JS in `static/eos_auth_monitor/js/`; partials in
`templates/eos_auth_monitor/partials/`. Translations: `tools/glossary.py`,
`tools/translate.py`.

## Open

- **403 in the other eos apps**: the user chose 403 everywhere; checked
  2026-11-26, none has it yet - eos-spy-network's `permissions._required`
  uses `user_passes_test`, eos-tax's `any_permission_required` defaults to
  `raise_exception=False`, eos-sig-checker and eos-invoices use Django's
  `permission_required` without `raise_exception`. In their own sessions;
  eos-tax has it in its working tree since (Unreleased, not committed).
- **eos-tax fallback**: `sources.gm_transactions` reads
  `eos_tax.api.gm_x_character_ids` (since 0.1.0) and falls back on
  `ImportError` to the old `get_gm_page` path, because eos-tax's API is in its
  working tree only (2026-11-26). Once production runs an eos-tax with
  `eos_tax.api`, drop the fallback, `_api()`'s `None` branch and the
  `inspect.signature` check in `ceo_corporation_id()` with their tests
  (`TestSource.paths`, `..._without_the_api...`).
- **Active in Mumble**: runs in production with plausible shares (the user,
  2026-11-26). Ideas offered, not asked for: the number of mains behind a
  tile's share as tooltip; a minimum of days in EVE before a main counts; the
  red below 60 % may read as a problem.

## Dev instance

- Repo `~/aa-dev/working/eos-auth-monitor`, remote
  `https://github.com/fthomas-de/eos-auth-monitor.git`, branch `main`.
  Installed editable into `~/aa-dev/venv`, beat entries
  `eos_auth_monitor_update_snapshot` and `eos_auth_monitor_record_activity`
  in `local.py` - but no Celery beat runs in dev.
- Installed (2026-11-26): allianceauth 5.5.0, corptools 3.5.0, aa-structures
  4.1.0, securegroups 0.10.2, aa-qqbot 1.0.0, aa-discord-telegram-bridge
  1.7.6, aa-charlink 1.14.0, django-esi 10.0.0, django-solo 2.5.1;
  eos-spy-network and eos-tax editable from their working trees.
- Migrations 0001-0012 applied in `aa_dev`.
- `MonitorConfiguration`: Alliance 99003995 (Invidia Gloriae Comes), nothing
  switched off, ESI on, *Only characters in the Alliance* off, the notice
  empty, `critical_scope_count` 5.
- The stored snapshot is of 2026-10-09 13:14 UTC: everything since (Alliance
  join date, scope warnings, covered Directors, *Registered in Auth* without a
  list, ...) shows only after *Rebuild now*. That needs a worker: check `ps`
  first, one worker only, started detached from a script
  (`setsid nohup ~/aa-dev/venv/bin/celery -A myauth worker -l info -P solo`
  in `~/aa-dev/working/myauth`, log `/tmp/celery-eos.log`).
- Data: one account, no service links, no Mumble account. Ether Element: 279
  in the member list, 14 Directors by ESI; the other Corporations have no
  token with the membership scope and carry "No Director token".
