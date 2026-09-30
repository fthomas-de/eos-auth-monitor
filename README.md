# EOS Auth Monitor

An [Alliance Auth](https://gitlab.com/allianceauth/allianceauth) app that shows
which accounts and Corporations of an Alliance need attention: characters
whose corptools audit is incomplete, Corporations without a working corptools
or aa-structures token, members not registered in Auth, and how many members
have linked Discord, Mumble, QQ and Telegram.

The app reads what Alliance Auth and the installed apps already hold. Its
only ESI calls are the member list and the roles of each Corporation, which no
installed app stores (see [ESI](#esi)). Every check can be switched off.

> **Status: in development.** Releases are tagged (`v0.0.1` is the first);
> install a tag, not the branch.

## Features

- **Cockpit**: percentages across the whole Alliance at a glance - share of
  mains with Discord, Mumble, QQ and Telegram linked (members Auth does not
  know count as mains that linked nothing, where the member list could be
  read), share of members
  registered in Auth, share of characters with a complete corptools
  Character Audit, share of Corporations with a working corptools
  Corporation Audit and aa-structures owner - and a tile with the number of
  connections per service. Every tile but *Members registered* opens a list,
  see *Service lists* and *Audit lists*
- **Most problems first**: Corporation tiles, mains, characters and the service
  lists are ordered by the number of problems, then by name
- **Filter** above the Corporations of the overview: name or ticker, and a
  switch to show only the Corporations with problems
- **Tiles or table**: the Corporations of the overview as tiles or as one
  sortable table line each; the browser remembers the choice
- **Service tiles** on the overview and on each Corporation page: the share of
  mains that linked Discord, Mumble, QQ or Telegram, each opening its list;
  on the Corporation page preceded by a tile per checked app (registered
  members, Character Audit, Corporation Audit, Structures)
- **One tile per Corporation**: its name as the title, the number of
  accounts with problems, below it each app with its share of complete
  entries (registered members, Character Audit, Corporation Audit,
  Structures, every service)
- **Each character counts where it is**: an account may have characters in
  several Corporations of the Alliance, and each is rated in the Corporation
  it is in - an alt with a problem turns its own Corporation red, not its
  main's. A character in a Corporation outside the overview counts with its
  main
- **Corporation detail**: a to-do list first - per failed check the mains it
  concerns (also mains elsewhere whose alts here fail it) and what they have
  to do (in aa-charlink where it is installed), and the members not registered in Auth,
  each group with a button that copies the names for an EVE mail and one that
  downloads them as a CSV file; a further button downloads the whole list, a
  line per name with its problem. Then every
  member of the Corporation, reduced to mains: the mains with problems as
  cards with keywords naming their problems (a main elsewhere whose alts
  here have problems too, marked "Main in ..."), the others as a compact list,
  members whose main is in another Corporation under that main, and members
  unknown to Auth as a compact list, each counting as a main of its own
- **Account detail**: the characters with problems, with the full details of
  each problem - which scopes are missing, which sections are stale - and
  what to do about it, with a link to
  [aa-charlink](https://github.com/Maestro-Zacht/aa-charlink) where it is
  installed (otherwise to the app where it is done), the Corporation's own
  problems in the header as well; each character's name links to its
  corptools Character Audit; the characters without problems folded away
  below
- **Service lists**: per Corporation and per service every main and whether
  it has linked that service; per service the same for the whole Alliance
- **Audit lists** behind the cockpit tiles, for the whole Alliance: *Character
  Audit* lists every main with a tag per failed character check (and how many
  of its characters fail it); *Corporation Audit* and *Structures* list every
  Director of the Alliance's Corporations with its main and whether it has
  the app's token - a token with every Corporation-audit scope, or a place
  among the enabled characters of the Corporation's aa-structures owner -
  those without first. A Director unknown to Auth is tagged *not in Auth*;
  see [Directors](#directors)
- **Page header**: the app's name and version, below it the page - Corporation
  overview, Corporation details, Main details, the service's name
- **Rebuild now** with a progress bar while the task runs
- **Build figures** in the footer for holders of `view_all` or `manage_settings`:
  duration, time per step, database queries, sizes of the Alliance and of the
  stored result
- **My account** for members: their own characters, what is wrong and what
  to do about it - nothing about other accounts; the service tiles open
  Alliance Auth's services page, and each problem links to aa-charlink where
  it is installed, with a hint which app to tick there (otherwise to the app
  of the check, with that app's hint)
- **Navbar tabs** from the narrowest view to the widest: *My account*, *My
  Corporation* (the Corporation of the own main), *Alliance overview*, then
  *Settings* - each only for those who may open it
- **Dashboard widgets** on Alliance Auth's dashboard: the own account in short
  (failed checks with the number of characters, linked services) for holders
  of `view_own`, and the own main's Corporation in short (its problems, each
  to-do group with the number of mains, the unregistered members) for holders
  of `basic_access`; each links to its page in the app and is hidden while the
  overview has nothing about the viewer
- **Settings page**: the Alliance, chosen from a searchable dropdown; a
  switch for every check, grouped by app, and for every service; which
  corptools sections and scopes the checks count
- **Smart filter** for
  [allianceauth-securegroups](https://github.com/Solar-Helix-Independent-Transport/allianceauth-secure-groups),
  see [Smart filter](#smart-filter)
- Sortable tables; the pages work on a phone
- Checks and services of an app that is not installed are hidden
  automatically

## How accounts are counted

An account belongs to the overview when its **main character** is in a
Corporation of the configured Alliance. It appears on the tile of the main's
Corporation. All characters of the account are checked, including alts
outside the Alliance: a missing token on an alt is a problem of the account.
Only *Director token missing* stays with the Alliance: a Director of a
Corporation elsewhere owes the Alliance no Corporation token, and that
Corporation is not asked for its roles. With *Only characters in the
Alliance* on, the alts outside the Alliance are left out altogether: not
checked, not shown, not counted.

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
| Director token missing | the character is in the Alliance, corptools has read its roles and it is a Director, but none of its tokens carries all scopes of the Corporation audit (`CORP_REQUIRED_SCOPES` plus the roles scope), minus the Corporation scopes left out in the settings; the detail names what the most complete token lacks. The Directors come from the roles corptools read and, with *Fetch data from ESI* on, from ESI (see [ESI](#esi)), which also names Directors without any token |

A Corporation where no Director's token could read the roles (the ESI call in
[ESI](#esi) found no token, or none worked) carries a small info mark beside
its name, *No Director token* as its tooltip, on the overview and its page:
the check cannot see its Directors there. The mark is not a problem and does
not count in the percentages; it only exists while *Fetch data from ESI* is
on together with the check or a Director list.

### Directors

The Director lists behind the *Corporation Audit* and *Structures* tiles take
the Directors of each Corporation of the Alliance from ESI (with *Fetch data
from ESI* on, see [ESI](#esi)) and from the roles corptools read. Without ESI
they know only the Directors corptools read - characters with a token - and
say so. A list exists while at least one check of its app is on; the lists
change no percentage and no problem count.

"Audit inactive" follows the conditions of corptools'
`CharacterAudit.is_active()` - which sections count depends on corptools'
`CT_CHAR_*_MODULE` settings and its own configuration - but is worked out by
this app: `is_active()` saves the audit, and this app does not write to
corptools' tables.

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
| `GET /corporations/{corporation_id}/members/` | `esi-corporations.read_corporation_membership.v1` | any token with that scope of a character in that Corporation, from django-esi's store - whichever app it was granted for; corptools' Corporation audit requires the scope anyway. No in-game role needed |
| `GET /corporations/{corporation_id}/roles` | `esi-corporations.read_corporation_membership.v1` | Corporations of the Alliance only; a token of a character corptools knows as a Director of that Corporation (ESI lists the roles of all members to a Director, Personnel Manager or a character with grantable roles). Names every Director, also those corptools never read the roles of because they have no token - for the check *Director token missing* and the Director lists. Skipped where no such token exists |
| `POST /universe/names/` | none | for members and Directors Auth has no name for |

django-esi caches the responses and honours their expiry. The app asks for
no scopes of its own and adds no login step. When it uses a token, django-esi
refreshes it and saves the new access token, as for any app. A token that
fails (a character who left the Corporation keeps its token) is skipped and the
next one tried, on every run; failed calls are not cached and count towards
ESI's error limit. *Fetch data from ESI*
in the settings switches all of these calls off; the Corporation page then
shows the registered accounts only, and the check *Director token missing*
and the Director lists know only the Directors corptools read.

The character count of a Corporation on the overview is not read from ESI by
this app: it is the member count Auth keeps on the Corporation
(`EveCorporationInfo.member_count`, public ESI data that Auth refreshes
itself). Where the member list was read, its count is used instead.

## How the data is updated

A periodic task, `eos_auth_monitor.tasks.update_snapshot`, reads the other
apps and stores the result; the pages only show that result and say how old
it is. The task runs once at a time (`QueueOnce`), keeps a single row and
replaces it on every run.

The task also runs after the settings are saved, and on *Rebuild now*, which
holders of `view_all` or `manage_settings` find above every page once an
Alliance is chosen. Settings saved while a run is under way apply from the
next run. While it is
queued or running, a progress bar shows its step; the page reloads itself
once the task is done. The progress lives in the default cache for up to an
hour.

While it builds, the task measures itself: the seconds per step, the number and
duration of its database queries, and how many Corporations, accounts and
characters it read. The figures are stored inside the snapshot and shown as a
line at the foot of the pages to holders of `view_all` or `manage_settings`
(the step times as its tooltip). ESI time is part of the *Reading member
lists* step. A page view only reads the settings and the stored result and
is not part of the figures.

## Requirements

| | |
|---|---|
| Alliance Auth | 5.1.4 or newer, below 6 (the migrations need `eveonline` 0025, first in 5.1.4) |
| Python | 3.10 or newer |
| Optional | allianceauth-corptools, aa-structures, aa-qqbot, aa-discord-telegram-bridge, the Discord and Mumble services of Alliance Auth |

None of the optional apps is a dependency of the package. `pip install` will
not pull them in, nor upgrade the ones you have.

## Installation

1. Install the package into the virtual environment of your Alliance Auth:

   ```bash
   pip install git+https://github.com/fthomas-de/eos-auth-monitor.git@v0.0.1
   ```

   Use the latest tag from the repository in place of `v0.0.1`.

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
| `eos_auth_monitor.basic_access` | CEOs, directors | The Corporation of their own main: its members, accounts and service lists, the CSV export of its to-do list, its widget on the dashboard; the progress bar |
| `eos_auth_monitor.view_all` | Leadership | Cockpit and every Corporation of the Alliance, the Alliance-wide service and audit lists, the CSV export of every to-do list, *Rebuild now* |
| `eos_auth_monitor.manage_settings` | Admins | The settings page: Alliance, checks, services, corptools sections and scopes; *Rebuild now* |
| `eos_auth_monitor.view_own` | Members (a state is fine) | *My account* and its widget on the dashboard: their own account - characters, problems, what to do, which services are linked. Nothing about other accounts or the Corporation's figures |

The menu entry shows for anyone holding one of them. Only the **main
character** counts for `basic_access`, and like every Alliance Auth app page,
the app needs a main character. Superusers hold every permission and see
everything.

`basic_access` shows every account of the Corporation with **all its alts**,
alts outside the Alliance included (unless *Only characters in the Alliance*
is on), and for members whose main is elsewhere
that main and its Corporation. Give it to a leadership group, **never to a
state**: every member would see who plays which alt. `basic_access` follows
the main, not in-game roles - someone who loses the CEO role keeps it until
removed from the group.

A holder of `view_own` alone is sent from the menu entry to *My account*. An
account whose main is not in the Alliance is not part of the overview, and
the page says so; its dashboard widget is not shown.

The dashboard widget of the Corporation follows `basic_access` only:
leadership with `view_all` alone sees no widget.

## Settings

Everything is set on the settings page in the app; there is nothing else to
put in `local.py`.

| Setting | Meaning |
|---|---|
| Alliance | The Alliance whose accounts and Corporations are monitored; a searchable dropdown of the Alliances Auth knows |
| Stale after (days) | When a section of the corptools Corporation audit counts as stale. Empty (the default): the same limit corptools uses for characters, `CT_CHAR_MAX_INACTIVE_DAYS` |
| Fetch data from ESI | See [ESI](#esi); on by default |
| Only characters in the Alliance | Leaves out every character of an account that is not in the Alliance - in the checks, the pages and the counts (see [How accounts are counted](#how-accounts-are-counted)); off by default |
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
checks a character fails, which alts belong to which main - plus the IDs
and names of Corporation members not registered in Auth, read from ESI:
people who never signed in to Auth. It is shown to the holders of the
permissions above, alts and cross-Corporation mains included (see
[Permissions](#permissions)). It stores whether a service is linked, not the
Discord, QQ or Telegram account itself. Every run replaces the result, so a
member who left is gone from it after the next run; nothing is kept longer.

## Languages

English, German, Russian and Simplified Chinese. The German, Russian and
Chinese texts are machine-generated and may be inaccurate; a correction goes
into `tools/glossary.py`. EVE terms - Corporation, Alliance, Character, Main -
stay English. The compiled catalogues are part of the package, no extra step
is needed.

## Upgrading

```bash
pip install -U git+https://github.com/fthomas-de/eos-auth-monitor.git@<tag>
```

```bash
python manage.py migrate
```

```bash
python manage.py collectstatic --noinput
```

Then restart supervisor.

**From 0.0.1:** the securegroups smart filter is gone, and migration 0005
drops its table. Before upgrading, remove *Smart Filter: Auth Monitor
problems* from every smart group and delete it in the Django admin; a
binding left behind (*Smart Filter Catalog*) points to a table that no
longer exists and breaks securegroups' group updates. The smart filter of
today, *Auth Monitor character problems*, is a new one with a table of its
own (migration 0007).

## Smart filter

With allianceauth-securegroups installed, the Django admin offers *Smart
Filter: Auth Monitor character problems*. It passes an account none of
whose characters has a problem - the character checks, not the
Corporation's own problems; alts in other Corporations count, as far as
*Only characters in the Alliance* keeps them. *Reversed logic* passes the
accounts that have problems instead. The group audit names the failed
checks.

The filter reads the last stored result, so it is as current as the last
rebuild. An account the overview does not know - main outside the
Alliance - fails either way. **Before the first result is stored,
everyone fails**: a smart group using the filter would lose its members
until the next rebuild, so run *Rebuild now* before binding it to a group.

## Uninstalling

1. Remove *Smart Filter: Auth Monitor character problems* from every smart
   group and delete it in the Django admin, then remove the app's tables:

   ```bash
   python manage.py migrate eos_auth_monitor zero
   ```

2. Remove `"eos_auth_monitor",` and the `CELERYBEAT_SCHEDULE` entry from
   `local.py`.
3. Uninstall the package and restart supervisor:

   ```bash
   pip uninstall eos-auth-monitor
   ```

4. Remove the app's permissions and content types, by app label only, in
   `python manage.py shell`:

   ```python
   from django.contrib.contenttypes.models import ContentType
   ContentType.objects.filter(app_label="eos_auth_monitor").delete()
   ```

   Deleting the content types takes their permissions with them. Do not use
   `remove_stale_contenttypes --include-stale-apps`: it also removes what
   other uninstalled apps left behind.

The data of the other apps is not touched: the app only reads it (django-esi
refreshing a token it used aside).

## Possible extensions

- Checks for the services themselves, e.g. "main without Discord"
- Checks for further apps, each in its own group in the settings

## License

[MIT](LICENSE)
