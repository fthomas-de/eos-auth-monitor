# Working on eos-auth-monitor

Alliance Auth app that shows the problem accounts and Corporations of one
Alliance - incomplete corptools audits, missing corptools and aa-structures
tokens, linked Discord, Mumble, QQ and Telegram - read out of other apps'
models. `README.md` says what it does; this file says how to work on it;
`docs/HANDOVER.md` says where the work currently stands, which decisions the
user made and what is open. Read both before changing anything.

## Where things are

| | |
|---|---|
| This app | `~/aa-dev/working/eos-auth-monitor/eos_auth_monitor` |
| Alliance Auth instance | `~/aa-dev/working/myauth` (has `manage.py`) |
| Virtualenv | `~/aa-dev/venv` |
| Sister project with the long form of these rules | `~/aa-dev/working/eos-tax/CLAUDE.md` |
| Review checklist every release has to pass | https://github.com/fthomas-de/aa-app-checklist |

The installed `allianceauth` in the venv is what runs, not the checkout in
`~/aa-dev/working/allianceauth`; when a bundle's behaviour matters, look in
`~/aa-dev/venv/lib/python3.12/site-packages/allianceauth`.

## Commands

Run from `~/aa-dev/working/myauth`:

```bash
eos-test eos_auth_monitor --exclude-tag translations
```

```bash
~/aa-dev/venv/bin/python manage.py makemigrations eos_auth_monitor
```

```bash
~/aa-dev/venv/bin/python manage.py collectstatic --noinput
```

Standalone, without the dev instance, from the repo root:

```bash
~/aa-dev/venv/bin/python runtests.py eos_auth_monitor
```

## Release

Read by the personal skills `/commit` and `/push`; the same shape in every
app. Commands run from `~/aa-dev/working/myauth`.

- App: `eos_auth_monitor`
- Version file: `eos_auth_monitor/__init__.py`
- Changelog section: `[Unreleased]`
- Tests while working: `eos-test eos_auth_monitor.tests.<module>`
- Suite without translation tests: `eos-test eos_auth_monitor --exclude-tag translations`
- Checks: `~/aa-dev/venv/bin/python manage.py makemigrations eos_auth_monitor --check --dry-run`
- Translations: new messages into `tools/glossary.py`, then
  `~/aa-dev/venv/bin/python tools/translate.py` from the repo root
- Translation tests: run by `tools/translate.py` (`--tag translations`)

## Translations

Three catalogues: `de`, `ru`, `zh_Hans`, machine-generated and marked so in
the `.po` header. They are only touched **at a commit**; between commits all
texts are English.

- The glossary `tools/glossary.py` is the source of truth. Add every new
  message there (de, ru, zh_Hans; plurals under `PLURALS`), never in a `.po`
  file: the next run overwrites a hand edit.
- `tools/translate.py` runs makemessages, fills the catalogues, drops
  obsolete entries, checks them against the glossary, runs `msgfmt --check`
  and compilemessages, confirms each `.mo` is newer than its `.po` and runs
  the catalogue tests. A message missing from the glossary stops it with a
  list; it never leaves gettext's fuzzy guess. It needs `polib` in the venv.
- The `.mo` files are committed, like Alliance Auth's and corptools': there
  is no build step at deploy.
- EVE jargon stays English: Corporation, Alliance, Character, Main. Alliance
  Auth translates some short words itself and wins a msgid clash, so those
  carry a context: `EVE jargon` for the jargon words, `eos-auth-monitor` for
  ordinary words AA translates differently (Save, Structures, Services;
  `pgettext_lazy`, `{% translate ... context "..." %}`).
  `test_should_show_our_translation_for_every_message` asks Django what it
  shows for each entry and names every clash - it runs only inside
  `tools/translate.py`, like the other catalogue tests, because between
  commits the catalogues describe the last commit, not the code.
- Every new message must be a plain string in the source: xgettext does not
  look inside an f-string.

## The database is irreplaceable

`aa_dev` holds ESI-pulled corptools data that cannot be fetched again. There
is no binary log and there are no dumps.

- **Never** delete with a range filter on `EveCorporationInfo`. The cascade
  takes the wallet journal with it.
- Address rows by explicit id lists, and write the previous values out first.
- corptools and other foreign apps: read their models, never change their
  schema or their rows beyond what a seed of our own created.
- Migrations of this app may be applied to `aa_dev` without asking (the
  user's yes of 2026-09-29), and the dev instance's Celery worker may be
  restarted likewise. Read a migration before applying it: one that touches a
  foreign app's tables or deletes rows still needs the user's yes.

## Code

- The app only reads other apps' tables and writes nothing but its own. Its
  ESI calls are the Corporation member list and the Corporation roles
  (`sources/members.py`), with tokens corptools already holds; nothing else
  goes to ESI.
- Every foreign app is optional: guard it with `apps.is_installed(...)` and
  import its models inside that guard. Never add one to the dependencies.
- Mirror the foreign app's own rules instead of reinventing them - corptools'
  `get_character_scopes()`, aa-structures' `Owner.are_all_syncs_ok` - so both
  apps agree on who is fine. `sources.corptools.character_sections()` repeats
  the conditions of corptools' `CharacterAudit.is_active()` (which saves, so
  it cannot be called); compare the two after every corptools upgrade.
- Model defaults and choices never come straight from settings; use a
  module-level callable, or every other installation needs `makemigrations`.
- Comments say why, not what. English everywhere in the code.
- AA standard templates (`allianceauth/base-bs5.html`), bundles and
  partials instead of our own. JavaScript only in
  `static/eos_auth_monitor/js/`, loaded with `sri_static`. The searchable
  dropdown follows eos-invoices (Tom Select from cdnjs with SRI).
- Nothing is created behind the admin's back: no groups, states, permission
  assignments or periodic tasks in code or migrations. A periodic task goes
  into the README as a `CELERYBEAT_SCHEDULE` block for `local.py`.
- Keep the README true: the checklist compares every claim with the code.

## Tests

- Derive every test class from `tests.base.MonitorTestCase`, and call
  `super().setUp()`: it switches `SOLO_CACHE` off and puts the default cache
  (the progress bar) in memory, emptied per test. The dev instance points
  both at its own Redis - anything a test stored would otherwise outlive the
  rollback and leak into the next test and into the running instance.
- `tests.base.configure()` switches the ESI member lists off; a test that
  wants them patches `sources.members`. No test may reach ESI.
- Test users come from `tests.base.make_user`: it gives them a main and its
  ownership, which Alliance Auth's `main_character_required` and the
  snapshot need.
- aa-structures, aa-qqbot and the Telegram bridge are not installed here;
  their readers are tested with fakes (`tests/test_sources_other.py`).
- Every new test gets checked against the broken code: break it, see it go
  red, restore the file.
- Compare the test count after every test change; an indentation slip drops
  a whole module silently.

## Committing

Commits and pushes only go through the user's personal skills `/commit` and
`/push`, never unasked; both read `## Release` above. While working on a
feature, run only the affected test modules - the full suite runs at
`/commit`. `CHANGELOG.md` is kept up to date under `[Unreleased]` with every
change, unasked. English only between commits.

## Editing files

Write patch scripts with the Write tool and run them by path. Do not build them
with shell heredocs: an apostrophe in `Corporation's` or a backtick in a
CHANGELOG entry gets executed by bash before Python ever sees the text.

For a small, unambiguous change the Edit tool is one step instead of two - use
it. `git` runs in WSL only; the Windows path reports "dubious ownership".
