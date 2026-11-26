# Working on eos-auth-monitor

Alliance Auth app that shows the problem accounts and Corporations of one
Alliance - incomplete corptools audits, missing corptools and aa-structures
tokens, linked Discord, Mumble, QQ and Telegram - read out of other apps'
models. `README.md` says what it does; this file says how to work on it;
`docs/HANDOVER.md` says where the work currently stands and what is open. Read
both before changing anything. The user's lasting decisions are in
`docs/DECISIONS.md`: look up the topic there when a task touches it.

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

`eos-test` keeps the test database between runs (`--keepdb`): building it
runs every migration of the instance on MySQL, about 100 seconds against 23
for this suite. A migration rewritten after it was applied, or another
branch's schema, needs `eos-test ... --fresh`; the suite at `/commit` always
runs fresh.

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
- Suite without translation tests: `eos-test eos_auth_monitor --fresh --exclude-tag translations`
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
- *My account* speaks to the member: its own texts (`Check.own_hint`,
  `Check.own_app_hint`, "your ...") address the reader - German with *du*,
  never *Sie* and never the third person. The other pages speak about the
  player in the third person (`Check.hint`, `Check.charlink_hint`).

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

- The app only reads other apps' tables and writes nothing but its own. The
  one exception is `charlink_hook.py`: a box on aa-charlink's page, CharLink's
  corptools *Corporation Audit* plus the sovereignty scope, registered through
  the `charlink` hook (user's yes of 2026-11-16). It reuses CharLink's own
  `LoginImport`; check it after every aa-charlink upgrade (the box still
  shows as *Corporation Audit (Full)*, and a CharLink admin setting for it,
  keyed by `unique_id` `sovereignty`, still applies), and drop it once
  `corptools.views.CORP_REQUIRED_SCOPES` carries the scope. Its
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
- The readers of aa-structures, aa-qqbot and the Telegram bridge are tested
  with fakes (`tests/test_sources_other.py`).
- Every new test gets checked against the broken code: break it, see it go
  red, restore the file.
- Compare the test count after every test change; an indentation slip drops
  a whole module silently.

## Traps

Dev instance and shell:

- A new file under `static/` needs `collectstatic` before the tests: the
  manifest storage of `sri_static` raises "Missing staticfiles manifest
  entry" and almost every view test errors. A new partial does not.
- The Celery worker (`-P solo`) does not reload code: restart it after any
  change, or *Rebuild now* builds with the old code.
- A snapshot is a stored result: after installing an app or changing a check
  the pages show the old one until it is rebuilt.
- `pkill -f`/`pgrep -f` inside `bash -lc '...'` match their own command
  line: the worker restart kills its own shell. Stop and start the worker
  from a script file.
- `eos-test` takes one test label per call ("unrecognized arguments"
  otherwise), and it is a login-shell function: a script calling it runs
  under `bash -l`. Grep its output for `^(Ran|OK|FAILED)`, not `tail`.
- `test_aa_dev` is shared by every app's runs: use `EOS_TEST_DB=<own name>`
  while other sessions may test, and check that a red run failed in a test,
  not in building the database.
- eos-spy-network and eos-tax are installed editable: another session's
  uncommitted change there is what this suite runs against. Look at their
  `git status` before suspecting this app.
- From Git Bash, `wsl.exe ... /mnt/c/...` needs `MSYS_NO_PATHCONV=1`; `sed`
  there turns a `\n` in the replacement into a line break.
- The Edit tool writes `"﻿"` as the character itself: a BOM in Python
  source goes in through a patch script.
- The dev server answers `localhost:8000` with `DisallowedHost`; open
  `http://127.0.0.1:8000/`. The Claude app's browser pane has no session
  there (the EVE SSO did not arrive): use Chrome.
- `/commit` and `/push` are typed by the user; Claude cannot start them.

Foreign apps:

- corptools 3.5.0 has two `CORP_REQUIRED_SCOPES`: `corptools.views` (*add_corp*
  and CharLink's box; no `esi-structures.read_corporation.v1`) and
  `corptools.app_settings` (read by `sources.corptools.corporation_scopes()`;
  with it). `add_corp_section` grows `_corp_scopes_base` in place with `+=`.
  Neither is reported upstream.
- django-esi's `Token.created` is overwritten on every refresh.
- `MumbleUser.objects.create()` is Auth's manager (takes a user, sets a
  password): a test row goes in with `MumbleUser(...).save()`.
- `AuthUtils.add_main_character_2` creates no `CharacterOwnership`; deleting
  a main's ownership makes Auth clear the main.

Templates:

- `{% url ... as var %}` inside `{% for %}` keeps `var` across iterations:
  clear it in an `{% else %}` (`{% firstof "" as var %}`). An unresolvable
  `{% url %}` sets `var` to "" - that is how an uninstalled app's link
  disappears.
- DataTables 2 right-aligns any column with a numeric `data-order` (hence
  `dt-left` in `tables.js`) and measures a hidden table as zero wide (hence
  `autoWidth: false`).
- `{% translate "..." as var %}` gives a safe string: an apostrophe renders
  as `'`, not `&#x27;`.

Tests:

- The view tests read tiles with regexes (`TestPages.gauge`,
  `TestOwnAccountServices.tile_colours`) that expect the bare label right
  after the icon: anything new on a tile goes at the end of its card body.
- Header buttons and tiles carry the same URL and percentage: a loose
  `assertContains` stays green when the tile is gone. Assert specifically.
- A test that cuts a page into parts ends each part at a marker that is on
  that page. Assert on a hint's own sentence: tooltips and descriptions repeat
  words like "corptools" or an old hint.
- A marker class must not be a substring of another attribute
  (`eos-auth-monitor-failed` is part of `data-eos-auth-monitor-failed`).
- `tests.test_views.main_cards`: the last card runs to the page's end, where
  the unregistered card is `border-danger` too - assert with
  `startswith('border-danger"')`.
- `assertRegex(text, pattern, re.DOTALL)` passes the flag as the message:
  compile the pattern.
- MySQL does not reset the auto-increment on rollback, and `--keepdb` lets
  pks grow: never fixed user IDs (`make_user(...).pk`), sort both sides of a
  list comparison.
- A fixture's `character_row` defaults to Corporation 2001: a character on
  another Corporation's account needs its `corporation_id`.
- A settings test posts the whole form (`TestSettings.unchanged`) and asserts
  the redirect: `changed_data` compares with the initial values, and a
  missing required field leaves the form invalid and the test green.
- django-esi's exceptions need their fields:
  `HTTPClientError(status_code=403, headers={}, data=None)`, likewise
  `HTTPServerError`.
- A test that patches `snapshot.build` calls the real one through a
  reference taken before the patch.
- Faking an uninstalled, already imported module: `sys.modules[name] = None`
  and remove the package attribute too, then put both back.
- A CEO-role test opens a page where that CEO's characters count, and also
  checks the other direction (nothing leaks onto other pages).

Sabotage rounds:

- Run them as a script in the background, scoped to the test class, never two
  runs at once; restore from a `cp` made just before.
- A sabotage pattern must be unique in its file: the script asserts a single
  match.
- Break what a test can see: an attribute no test looks at proves nothing.
  To drop a sort key over dataclasses use `key=lambda account: 0` (no `<`).

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
