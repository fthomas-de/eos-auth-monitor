# EOS Auth Monitor

An [Alliance Auth](https://gitlab.com/allianceauth/allianceauth) app that shows
which accounts and Corporations of an Alliance need attention: characters
whose corptools audit is incomplete, Corporations without a working corptools
or aa-structures token, members not registered in Auth, and how many members
have linked Discord, Mumble, QQ and Telegram.

The app reads what Alliance Auth and the installed apps already hold. Its
only ESI call is the member list of each Corporation, which no installed app
stores (see [ESI](#esi)). Every check can be switched off.

> **Status: in development.** No release has been tagged yet.

## Features

- **Cockpit**: percentages across the whole Alliance at a glance - share of
  mains with Discord, Mumble, QQ and Telegram linked, share of members
  registered in Auth, share of characters with a complete corptools
  Character Audit, share of Corporations with a working corptools
  Corporation Audit and aa-structures owner - and a tile with the number of
  connections per service
- **One tile per Corporation**: its name as the title, below it each app with
  its share of complete entries (registered members, Character Audit,
  Corporation Audit, Structures, every service)
- **Corporation detail**: every member of the Corporation, reduced to mains -
  the mains of the Corporation as tiles with keywords naming their problems,
  members whose main is in another Corporation under that main, and members
  unknown to Auth, each counting as a main of its own
- **Account detail**: every character of the account, with the full details
  of each problem - which scopes are missing, which sections are stale
- **Service lists**: per Corporation all characters of its accounts, with
  the problem characters marked; per service every main of the Alliance and
  whether it has linked that service
- **Rebuild now** with a progress bar while the task runs
- **Smart filter** for [allianceauth-securegroups](https://github.com/Solar-Helix-Independent-Transport/allianceauth-secure-groups):
  does an account have problems?
- **Settings page**: the Alliance, chosen from a searchable dropdown; a
  switch for every check, grouped by app, and for every service; which
  corptools sections and scopes the checks count
- Sortable tables; the pages work on a phone
- Checks and services of an app that is not installed are hidden
  automatically

## How accounts are counted

An account belongs to the overview when its **main character** is in a
Corporation of the configured Alliance. It appears on the tile of the main's
Corporation. All characters of the account are checked, including alts
outside the Alliance: a missing token on an alt is a problem of the account.

Services are linked per Auth account, not per character, so the service
figures count mains.

The tiles show every Corporation Auth knows as a member of the Alliance, and
the Corporation of every main on top of that.

On the Corporation page, a member from the ESI member list is shown under
its main when Auth knows its account. A member Auth does not know - or an
account without a main - counts as a main of its own, "Not registered in
Auth".

## Checks

A check only runs when its app is installed and it is switched on in the
settings.

### corptools - Character Audit

| Check | A character fails when |
|---|---|
| Audit missing | it has no `CharacterAudit` |
| Scopes missing | none of its tokens carries all scopes corptools asks for (`get_character_scopes()`), minus the scopes left out in the settings; the detail names the scopes the most complete token lacks |
| Audit inactive | a section corptools counts has not updated for longer than `CT_CHAR_MAX_INACTIVE_DAYS`, minus the sections left out in the settings; the detail names them |

"Audit inactive" follows the conditions of corptools'
`CharacterAudit.is_active()` - which sections count depends on corptools'
`CT_CHAR_*_MODULE` settings and its own configuration - but is worked out by
this app: `is_active()` saves the audit, and this app never writes to another
app's tables.

### corptools - Corporation Audit

| Check | A Corporation fails when |
|---|---|
| Corporation audit missing | it has no `CorporationAudit` |
| Corporation token missing | no character of the Corporation has one token with all scopes corptools needs for the Corporation audit (`CORP_REQUIRED_SCOPES` plus the roles scope), minus the scopes left out in the settings |
| Corporation data stale | a section of the Corporation audit (Assets, Wallet, Tracking, ...) has not updated for longer than *Stale after* on the settings page, usually because the character behind the token lost its roles; an audit that never updated at all counts too. Sections left out in the settings do not count |

A section corptools has never written a timestamp for is left alone: corptools
only writes one once the module has run, and some modules never apply to a
Corporation.

### aa-structures

| Check | A Corporation fails when |
|---|---|
| No structure owner | it is not set up as an owner |
| Structure owner inactive | the owner exists but is switched off; the other checks are skipped then |
| No structure owner character | the owner has no enabled character left to fetch data with |
| Structure sync failing | aa-structures reports a sync that is not up to date (`Owner.are_all_syncs_ok`); the detail names it: Structures, Notifications, Forwarding or Assets |

## Services

| Service | Source | A main counts as linked when |
|---|---|---|
| Discord | Alliance Auth service `allianceauth.services.modules.discord` | the account has a `DiscordUser` |
| Mumble | Alliance Auth service `allianceauth.services.modules.mumble` | the account has a `MumbleUser` |
| QQ | [aa-qqbot](https://github.com/yilifaer/aa-qqbot-plugin) | the account has a `Binding` (verified or trusted) |
| Telegram | [aa-discord-telegram-bridge](https://github.com/radioactive68/AUTH-Discord-Telegram-Bridge) | the account has a `TelegramUser` with a Telegram user ID |

## ESI

No installed app stores who is in a Corporation - corptools' member tracking
only updates characters it already audits. The task therefore reads, per
Corporation:

| Endpoint | Scope | Token |
|---|---|---|
| `GET /corporations/{corporation_id}/members/` | `esi-corporations.read_corporation_membership.v1` | any token corptools already holds of a character in that Corporation; corptools' Corporation audit requires the scope anyway. No in-game role needed |
| `POST /universe/names/` | none | for members Auth has no name for |

django-esi caches the responses and honours their expiry. The app asks for
no scopes of its own and adds no login step. *Fetch member lists from ESI*
in the settings switches the calls off; the Corporation page then shows the
registered accounts only.

## How the data is updated

A periodic task, `eos_auth_monitor.tasks.update_snapshot`, reads the other
apps and stores the result; the pages only show that result and say how old
it is. The task runs once at a time (`QueueOnce`), keeps a single row and
replaces it on every run.

The task also runs after the settings are saved, and on *Rebuild now*, which
holders of `view_all` or `manage_settings` find above every page. While it is
queued or running, a progress bar shows its step; the page reloads itself
once the task is done. The progress lives in the default cache for up to an
hour.

## Smart filter

With [allianceauth-securegroups](https://github.com/Solar-Helix-Independent-Transport/allianceauth-secure-groups)
installed, *Smart Filter: Auth Monitor problems* is offered as a filter.
Create one in the Django admin (*EOS Auth Monitor → Smart Filter: Auth
Monitor problems*), then add it to a smart group.

| Field | Meaning |
|---|---|
| Reversed logic | Off: accounts without problems pass. On: accounts with problems pass |
| Include corporation | Also count the problems of the main's Corporation |

The filter reads the last result of the task, so it is as current as that.
An account outside the overview - main not in the Alliance, or no result
yet - fails either way.

## Requirements

| | |
|---|---|
| Alliance Auth | 5.x |
| Python | 3.10 or newer |
| Optional | allianceauth-corptools, aa-structures, aa-qqbot, aa-discord-telegram-bridge, allianceauth-securegroups, the Discord and Mumble services of Alliance Auth |

None of the optional apps is a dependency of the package. `pip install` will
not pull them in, nor upgrade the ones you have.

## Installation

1. Install the package into the virtual environment of your Alliance Auth:

   ```bash
   pip install git+https://github.com/fthomas-de/eos-auth-monitor.git
   ```

2. Add `"eos_auth_monitor",` to `INSTALLED_APPS` in `local.py`, and the
   periodic task below it:

   ```python
   CELERYBEAT_SCHEDULE["eos_auth_monitor_update_snapshot"] = {
       "task": "eos_auth_monitor.tasks.update_snapshot",
       "schedule": crontab(minute="*/30"),
   }
   ```

3. Run migrations and collect static files:

   ```bash
   python manage.py migrate
   ```

   ```bash
   python manage.py collectstatic --noinput
   ```

4. Restart supervisor.

5. Give the permissions below to the groups or states that should see the
   app, then choose the Alliance on *Auth Monitor → Settings*. Until an
   Alliance is chosen, the overview stays empty.

The app creates no groups, states, permission assignments or periodic tasks
by itself.

## Permissions

| Permission | Who | What |
|---|---|---|
| `eos_auth_monitor.basic_access` | CEOs, directors | The Corporation of their own main: its members, accounts and service lists; the progress bar |
| `eos_auth_monitor.view_all` | Leadership | Cockpit and every Corporation of the Alliance, the Alliance-wide service lists, *Rebuild now* |
| `eos_auth_monitor.manage_settings` | Admins | The settings page: Alliance, checks, services, corptools sections and scopes; *Rebuild now* |

The menu entry shows for anyone holding one of them. Only the **main
character** counts for `basic_access`, and like every Alliance Auth app page,
the app needs a main character. Superusers hold every permission and see
everything.

The smart filter is maintained in the Django admin with Django's own
permissions on *Smart Filter: Auth Monitor problems*.

## Settings

Everything is set on the settings page in the app; there is nothing else to
put in `local.py`.

| Setting | Meaning |
|---|---|
| Alliance | The Alliance whose accounts and Corporations are monitored; a searchable dropdown of the Alliances Auth knows |
| Stale after (days) | When a section of the corptools Corporation audit counts as stale. Empty (the default): the same limit corptools uses for characters, `CT_CHAR_MAX_INACTIVE_DAYS` |
| Fetch member lists from ESI | See [ESI](#esi); on by default |
| Checks | One switch per check, grouped by app |
| Services | One switch per service, to hide a service the Alliance does not use |
| corptools: what the checks count | Four lists - Character Audit sections and scopes, Corporation Audit sections and scopes. Untick what the Alliance does not use, e.g. *Moon Observations* and `esi-industry.read_corporation_mining.v1` for an Alliance without moons; a section and its scope are separate entries |

A check, section or scope added in a later release starts switched on.

## Third-party assets

The searchable dropdown uses [Tom Select](https://tom-select.js.org/) 2.6.2,
loaded from cdnjs with a subresource integrity hash, on the settings page
only. Tables use the DataTables bundle Alliance Auth ships.

## Data protection

The app stores its settings and the last result of the task, nothing else.
The result holds what other apps already hold - character and Corporation
names, whether an account has linked Discord, Mumble, QQ or Telegram, which
checks a character fails - plus the names of Corporation members not
registered in Auth, read from ESI. It is shown to the holders of the
permissions above. It stores whether a service is linked, not the Discord, QQ
or Telegram account itself.

## Upgrading

```bash
pip install -U git+https://github.com/fthomas-de/eos-auth-monitor.git
```

```bash
python manage.py migrate
```

```bash
python manage.py collectstatic --noinput
```

Then restart supervisor.

## Uninstalling

1. Remove the app's tables:

   ```bash
   python manage.py migrate eos_auth_monitor zero
   ```

2. Remove `"eos_auth_monitor",` and the `CELERYBEAT_SCHEDULE` entry from
   `local.py`.
3. Uninstall the package and restart supervisor:

   ```bash
   pip uninstall eos-auth-monitor
   ```

The data of the other apps is not touched: the app only ever reads it. A
securegroups smart group that used the filter loses it with the tables.

## Possible extensions

- Checks for the services themselves, e.g. "main without Discord"
- Checks for further apps, each in its own group in the settings

## License

[MIT](LICENSE)
