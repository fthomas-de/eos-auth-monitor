# Audit: programming errors and security

| | |
|---|---|
| Date | 2026-11-11 |
| Audited commit | `7d488cc9a00c4b91a7864058d92c183b3afac0a4` (0.0.23, clean working tree) |
| Scope | All non-test code of `eos_auth_monitor`: views, URLs, models, forms, task, hooks, admin, `checks.py`, `report.py`, `snapshot.py`, `progress.py`, `metrics.py`, `smart_filters.py`, `sources/`, template tags, all templates, all JavaScript, migrations 0001-0009, `pyproject.toml`. Tests were read only to name gaps. |
| Read alongside | The installed `celery_once`, `allianceauth.services.tasks`, `esi` (django-esi 9.10.0) and `corptools` in `~/aa-dev/venv`, to confirm what they raise and lock. |
| Not done | No test run, no database access, no browser. Nothing was changed but this file. |
| Not checked | The code of eos-tax and eos-spy-network (one repository per session): the contracts this app relies on are listed under *Checked and fine*, last line. |

**Implemented on 2026-11-13**, uncommitted: all five findings as described
below, with the eight tests named (427 without the translation tests; each
new test seen red against the old code or with its guard removed), the
CHANGELOG entries and three corrected README sentences. Open: `/commit`, and
moving the two decisions into `docs/HANDOVER.md` there.

Status: **CONFIRMED** = the path was read from its entry (URL or task) to its
effect and the trigger can be named. **PLAUSIBLE** = depends on something that
could not be checked, named in the finding.

| ID | Severity | Type | File | Summary | Status |
|---|---|---|---|---|---|
| AM-01 | Medium | Bug (ESI errors) | `sources/members.py` | An ESI outage is stored as "no token could read it": member lists and Director problems vanish from the snapshot, the smart filter flips | CONFIRMED |
| AM-02 | Low | Bug (wrong rows) | `templates/eos_auth_monitor/corporation_service.html` | A Corporation's service list also lists mains of other Corporations | CONFIRMED |
| AM-03 | Low | Bug (Celery) | `snapshot.py` | Settings saved while a build runs are not built, though the page says "is being rebuilt" | CONFIRMED |
| AM-04 | Low | Bug (empty case) | `sources/corptools.py` | With every scope unticked, a character without a token still gets "Scopes missing" | CONFIRMED |
| AM-05 | Low | Security (information shown) | `templates/eos_auth_monitor/corporation.html` | A CEO sees the service links and the Director crown of a main from another Corporation | CONFIRMED, fix decided by the user on 2026-11-12 |

No Critical or High finding. Every view has its permission and its object
check, see *Checked and fine*; AM-05 is the one place where a page shows more
than the viewer may open.

For whoever implements this:

- Follow `CLAUDE.md`: load `ponytail`, add a line under `[Unreleased]` in
  `CHANGELOG.md` per fix, run only the named test module, sabotage every new
  test (it must be red against the old code), compare the test count
  (419 before; 427 after all five fixes).
- No fix needs a migration, a new message or a translation run.
- Commands run from `~/aa-dev/working/myauth`. `eos-test` takes one label per
  call. While other sessions test, prefix `EOS_TEST_DB=test_eam_audit`.
- AM-01 and AM-03 change code the Celery worker runs: restart the dev worker
  afterwards.

---

## AM-01 - An ESI outage is stored as "no token could read it" (Medium, CONFIRMED)

**Where**

- `eos_auth_monitor/sources/members.py:57-69`, `corporation_members()`
- `eos_auth_monitor/sources/members.py:83-98`, `corporation_directors()`
- Effect in `eos_auth_monitor/snapshot.py:226-233` (`ask_roles`) and
  `snapshot.py:85-88` (`_members`)

**What happens**

The periodic task runs while ESI does not answer (the daily downtime around
11:00 UTC, a 5xx, the error limit, no network) and django-esi's cached
response has expired. django-esi raises `esi.exceptions.HTTPServerError`,
`ESIErrorLimitException` or an httpx error. Both functions catch every
exception as "this token is broken", try the next token, which fails the same
way, and return `None`. The build goes on and **stores** a snapshot in which:

- every Corporation has `no_director_token: true` and no ESI Directors, so
  `char_director_token_missing` disappears for every Director corptools does
  not know itself (the case the check exists for);
- every Corporation has `member_count: None`: the *Registered in Auth* rows
  and the unregistered members are gone, the Corporation widget on the
  dashboard turns green, `unknown_characters` answers 404, and the Corporation
  page says "no member has a token with the membership scope", which is false;
- `CharacterProblemsFilter` (securegroups) reads that snapshot: an account
  whose only problem was the Director token passes until the next good run
  (reversed logic: fails).

It heals with the next run that reaches ESI, 30 minutes later at the README's
schedule.

**Cause**

```python
        except Exception as error:  # noqa: BLE001 - a broken token must not stop the other Corporations
            # a character who left keeps its token; try the next one
            logger.warning("Member list of %s not readable with a token: %s", corporation_id, type(error).__name__)
            continue
        return [int(member) for member in members]
    return None
```

The same block, with "Roles of %s", is in `corporation_directors()`.
"The token cannot read this" and "ESI did not answer" end in the same `None`.

**Fix** (the user chose this on 2026-11-12, see *Decisions*)

Only a token failure moves on to the next token; anything else leaves the
function, the task fails (`tasks.update_snapshot` already calls
`progress.failed()` and re-raises), and the last good snapshot stays.

1. In `eos_auth_monitor/sources/members.py`, add after `_client()`:

   ```python
   def _is_token_failure(error: Exception) -> bool:
       """Whether this token cannot read the Corporation: revoked, or its character left or lost the role.

       Anything else - ESI down, the error limit, no network - says nothing
       about the token: the build has to fail and keep the last snapshot
       rather than store "no token could read it".
       """
       from esi.errors import TokenError
       from esi.exceptions import HTTPClientError

       return isinstance(error, (TokenError, HTTPClientError))
   ```

   (`HTTPClientError` is every 4xx; django-esi turns 420 into
   `ESIErrorLimitException` before, so the error limit is not in it.
   `TokenError` is what `Token.valid_access_token()` raises for a token SSO
   no longer refreshes.)

2. In `corporation_members()` change

   ```python
           except Exception as error:  # noqa: BLE001 - a broken token must not stop the other Corporations
               # a character who left keeps its token; try the next one
               logger.warning("Member list of %s not readable with a token: %s", corporation_id, type(error).__name__)
               continue
   ```

   to

   ```python
           except Exception as error:  # noqa: BLE001 - a broken token must not stop the other Corporations
               if not _is_token_failure(error):
                   raise
               # a character who left keeps its token; try the next one
               logger.warning("Member list of %s not readable with a token: %s", corporation_id, type(error).__name__)
               continue
   ```

3. In `corporation_directors()` add the same two lines
   (`if not _is_token_failure(error):` / `raise`) as the first lines of its
   `except` block.

4. Leave `names()` as it is: a missing name is replaced by the ID and loses
   nothing.

5. In `eos_auth_monitor/tests/test_sources_members.py` the two existing tests
   `test_should_try_the_next_token_when_one_fails` fake the failure with
   `RuntimeError("403")`. Replace both with a real 403:

   ```python
   from esi.exceptions import HTTPClientError, HTTPServerError

   FORBIDDEN = HTTPClientError(status_code=403, headers={}, data=None)
   ```

   and use `FORBIDDEN` in place of `RuntimeError("403")` in both
   `side_effect` lists.

**Test** (`eos_auth_monitor/tests/test_sources_members.py`)

- `TestCorporationMembers.test_should_fail_when_esi_does_not_answer`: a member
  of 2001 with a token carrying `SCOPE`;
  `self.operation.return_value.result.side_effect = HTTPServerError(status_code=503, headers={}, data=None)`;
  `with self.assertRaises(HTTPServerError): members.corporation_members(2001)`.
  Red before the fix (it returns `None`).
- `TestCorporationDirectors.test_should_fail_when_esi_does_not_answer`: the
  class's Director with a token carrying `SCOPE`, the same side effect,
  `assertRaises(HTTPServerError)` around `members.corporation_directors(2001)`.
  Red before the fix.

**Verify**

```bash
eos-test eos_auth_monitor.tests.test_sources_members
```

**Risk / depends on**

- While ESI is down, a run now fails as a whole: the pages keep the last good
  snapshot, the bar says "The rebuild failed", Celery logs one traceback per
  failed run. Character and service data are then also as old as the last
  good run. That is the trade against a wrong snapshot.
- With *Fetch data from ESI* off nothing changes.
- Independent of the other findings.

---

## AM-02 - A Corporation's service list also lists mains of other Corporations (Low, CONFIRMED)

**Where**

- `eos_auth_monitor/templates/eos_auth_monitor/corporation_service.html:24`
- `eos_auth_monitor/report.py:481-487`, `Corporation.accounts_by_problems`

**What happens**

Account 11 has its main in Corporation A and an alt in Corporation B, both in
the Alliance. The CEO of B (or anyone) opens B's Discord list
(`corporation/<B>/service/discord/`). The list has a row for account 11's
main, with its linked / not linked badge and a link to `account/11/`.

- The page is "one row per main of the Corporation" (CHANGELOG, HANDOVER);
  account 11's main is not one.
- The header counts `x/y` over B's own mains only
  (`Corporation.service_counts`), so the rows and the count disagree.
- For the CEO of B the link answers 403: `views.account` allows only the
  main's Corporation.

It came in with commit `853a252` ("count alts in their own Corporation"),
which widened `accounts_by_problems` to `evaluated_accounts` for the cards.

**Cause**

```django
{% for account in corporation.accounts_by_problems %}
    <tr>
```

```python
    @property
    def accounts_by_problems(self) -> list[Account]:
        """Most problems first, then most warnings; by name where they are equal."""
        return sorted(
            self.evaluated_accounts,   # the own mains AND the visiting ones
```

**Fix**

`accounts_by_problems` stays as it is: `card_accounts` needs the visiting
accounts. Filter in the template, which is the only other user.

1. In `corporation_service.html` change

   ```django
                           {% for account in corporation.accounts_by_problems %}
                               <tr>
   ```

   to

   ```django
                           {# a main elsewhere with an alt here links its services in its own Corporation's list #}
                           {% for account in corporation.accounts_by_problems %}{% if not account.visiting %}
                               <tr>
   ```

2. and the end of the loop from

   ```django
                               </tr>
                           {% endfor %}
   ```

   to

   ```django
                               </tr>
                           {% endif %}{% endfor %}
   ```

**Test** (`eos_auth_monitor/tests/test_views.py`, class
`TestAltsInAnotherCorporation`, whose `setUp` already gives account 11 an alt
in 2002)

- `test_should_list_only_the_own_mains_in_the_service_list`:
  `response = self.get(self.leader, "corporation_service", 2002, "discord")`;
  `assertNotContains(response, reverse("eos_auth_monitor:account", args=[11]))`
  and `assertContains(response, reverse("eos_auth_monitor:account", args=[22]))`.
  Red before the fix (the row of account 11 is there).

**Verify**

```bash
eos-test eos_auth_monitor.tests.test_views
```

**Risk / depends on**

None; a template-only change, no new static file. AM-05 is the same
question for the cards.

---

## AM-03 - Settings saved while a build runs are not built (Low, CONFIRMED)

**Where**

- `eos_auth_monitor/snapshot.py:385-400`, `update()`
- Entry: `eos_auth_monitor/views.py:342-373`, `settings()` and
  `_start_rebuild()`; `eos_auth_monitor/tasks.py:13`

**What happens**

A build is running (beat run or *Rebuild now*; it takes as long as the ESI
calls). An admin saves the settings, for example switches a check off or
changes *Scopes missing: a problem from*. `_start_rebuild()` calls
`update_snapshot.delay()`. The task is `QueueOnce` with `graceful: True`:
celery_once finds the lock of the running task and returns a rejected result
without queuing and without raising (`celery_once/tasks.py`, `apply_async`).
The page says "Settings saved. The overview is being rebuilt.", but the
running build read the configuration at its start and stores a snapshot of
the old settings. The new ones show only after the next beat run, or never
on an installation without the beat entry, until someone presses *Rebuild
now*. For a changed Alliance the notice "still the overview of the previous
one" stays; for every other setting nothing tells the admin.

**Cause**

```python
def update(on_step=_no_progress) -> Snapshot | None:
    """Rebuild and store the snapshot; without an Alliance the old one goes."""
    with Measurement(on_step) as measurement:
        data = build(MonitorConfiguration.get_solo(), measurement.on_step)
```

The configuration is read once; nothing notices that it changed during the
build, and the task that would have rebuilt was dropped.

**Fix**

Build once more when the settings the build uses changed meanwhile. Bounded
to one repeat; a third change waits for the next run like today.

1. In `eos_auth_monitor/snapshot.py` add to the imports (Django block):

   ```python
   from django.forms.models import model_to_dict
   ```

2. Replace the first three lines of `update()` shown above by:

   ```python
   def _build_settings(config) -> dict:
       # the notice is read by the pages, never by the build
       return model_to_dict(config, exclude=["member_notice"])


   def update(on_step=_no_progress) -> Snapshot | None:
       """Rebuild and store the snapshot; without an Alliance the old one goes."""
       # a save during the run queues nothing (QueueOnce drops the second task): build once more with what was saved
       for _attempt in range(2):
           config = MonitorConfiguration.get_solo()
           used = _build_settings(config)
           with Measurement(on_step) as measurement:
               data = build(config, measurement.on_step)
           if _build_settings(MonitorConfiguration.get_solo()) == used:
               break
   ```

   The rest of `update()` (`if data is None:` onwards) stays unchanged and
   stays outside the loop.

**Test** (`eos_auth_monitor/tests/test_snapshot.py`, class `TestUpdate`)

- `test_should_build_again_when_the_settings_changed_during_the_run`:

  ```python
  make_corporation(2001)
  configure()
  real_build = snapshot.build
  seen = []

  def build_and_save(config, on_step):
      seen.append(config.critical_scope_count)
      if len(seen) == 1:
          # the settings page saves while the first build runs
          configure(critical_scope_count=2)
      return real_build(config, on_step)

  with patch("eos_auth_monitor.snapshot.build", side_effect=build_and_save):
      stored = snapshot.update()

  self.assertEqual(seen, [5, 2])
  self.assertEqual(stored.data["critical_scope_count"], 2)
  ```

  Red before the fix (`seen == [5]`).
- `test_should_not_build_again_for_a_changed_notice`: the same, but the save
  is `configure(member_notice="Hello")`; assert `len(seen) == 1`. It guards
  the `exclude`; sabotage it by removing the `exclude`.

**Verify**

```bash
eos-test eos_auth_monitor.tests.test_snapshot
```

**Risk / depends on**

- A save during a build doubles that run's time and ESI calls (django-esi
  serves the second pass from its cache).
- With `SOLO_CACHE` set, `get_solo()` reads the cache; django-solo refreshes
  it on `save()`, and web and worker share the cache in Alliance Auth, so the
  worker sees the change. PLAUSIBLE only for an installation that gives web
  and worker different caches - then the fix does nothing and today's
  behaviour stays.
- Independent of the other findings; touches the same task path as AM-01, so
  restart the worker once for both.

---

## AM-04 - With every scope unticked, a character without a token still gets "Scopes missing" (Low, CONFIRMED)

**Where**

`eos_auth_monitor/sources/corptools.py:145-151`, `_missing_scopes()`;
called from `character_problems()` lines 222 and 224.

**What happens**

An admin unticks every box under *Character Audit: required scopes* on the
settings page (or every box under *Corporation Audit: required scopes*) and
leaves the check itself on. A character that has no token at all then gets
`{"check": "char_scopes_missing", "detail": []}`: `any()` over no tokens is
false, although nothing is required. With the default threshold of 5 it shows
as a yellow *Scopes missing* warning without a scope on the account and
Corporation pages. The Director variant is worse: a Director without a token
gets a red *Director token missing* with an empty detail, which counts as a
problem and fails the smart filter. A character with at least one token is
rated correctly (`set() <= scopes` is true).

**Cause**

```python
def _missing_scopes(tokens, required: set) -> list[str] | None:
    """None where one token carries every scope; else what the token closest to complete lacks."""
    if any(required <= scopes for scopes in tokens):
        return None
```

**Fix**

1. Change the condition to:

   ```python
       # nothing required (every scope unticked in the settings): a character without a token lacks nothing
       if not required or any(required <= scopes for scopes in tokens):
           return None
   ```

**Test** (`eos_auth_monitor/tests/test_sources_corptools.py`, class
`TestCharacterProblems`; the class is patched, so the method takes `_`)

- `test_should_report_no_missing_scopes_when_none_is_required`:
  `CharacterAudit.objects.create(character=self.main, update_timestamps=fresh())`,
  no token;
  `self.assertEqual(self.problems(excluded_scopes=self.scopes), [])`.
  Red before the fix (`[{"check": "char_scopes_missing", "detail": []}]`).

**Verify**

```bash
eos-test eos_auth_monitor.tests.test_sources_corptools
```

**Risk / depends on**

None. `corporation_token_holders()` and `corporation_problems()` use
django-esi's `require_scopes([])`, which already passes any token; a
Corporation without any token still fails `corp_token_missing` there, which
is right (no token, no audit).

---

## AM-05 - A CEO sees the service links and the Director crown of a main from another Corporation (Low, CONFIRMED)

**Where**

`eos_auth_monitor/templates/eos_auth_monitor/corporation.html:119` (the
crown) and `:153` (the service icons), inside the loop over
`corporation.card_accounts`.

**What happens**

Account 11 has its main in Corporation A and an alt with a problem in
Corporation B. The CEO of B (`basic_access` only) opens B's page. Account 11
gets a card "Main in A". The CEO may not open that account - the name is not
linked and `views.account` answers 403 - but the card shows which services
the account linked (one icon per service, green or grey, with a tooltip) and,
with a crown, that one of its characters is a Director of Corporation A,
naming the characters. Both are facts about an account of another
Corporation.

**Cause**

```django
                                    {% include "eos_auth_monitor/partials/director-icon.html" with corner=True %}
```

```django
                                        {% include "eos_auth_monitor/partials/service-icons.html" %}
```

Neither asks whether the card is a visiting one, as the name's link does
three lines below the first (`{% if account.visiting and not can_view_all %}`).

**Fix** (the user's decision of 2026-11-12: hide them in that case)

The card itself, its "Main in ..." line, the character count and the problem
tags stay: they are about the alt in this Corporation.

1. Line 119, change to:

   ```django
                                    {# a main elsewhere: its Director role and its services are its own Corporation's to see #}
                                    {% if not account.visiting or can_view_all %}{% include "eos_auth_monitor/partials/director-icon.html" with corner=True %}{% endif %}
   ```

2. Line 153, change to:

   ```django
                                        {% if not account.visiting or can_view_all %}{% include "eos_auth_monitor/partials/service-icons.html" %}{% endif %}
   ```

`can_view_all` is already in the page's context (`views.corporation`). The
*Without problems* list needs nothing: it holds the own mains only
(`problem_free_accounts` reads `self.accounts`).

**Test** (`eos_auth_monitor/tests/test_views.py`, class
`TestAltsInAnotherCorporation`; `main_cards` is the module's helper that cuts
the page into cards by main name)

In `setUp`, after the alt is appended and before `snapshot.save()`, make
account 11's main a Director of its Corporation, as `TestDirectorIcon` does:

```python
snapshot.data["corporations"][0]["directors"] = [
    {"id": 1101, "name": "Char 1101", "in_auth": True, "user_id": None, "main_name": None, "tokens": {}}
]
```

- `test_should_hide_the_services_and_the_crown_of_a_visiting_main_from_a_ceo`:
  `card = main_cards(self.get(self.ceo_2002, "corporation", 2002).content.decode())["Char 1101"]`;
  `assertNotIn("fa-discord", card)` and
  `assertNotIn("eos-auth-monitor-director", card)`. Red before the fix.
- `test_should_show_them_to_leadership`: the same card for `self.leader`;
  `assertIn` for both. It guards the `or can_view_all`; sabotage it by
  removing that half of the condition.

The card of account 22 (B's own main) is the last one and runs to the end of
the page; do not assert on it here.

**Verify**

```bash
eos-test eos_auth_monitor.tests.test_views
```

**Risk / depends on**

- `main_cards` keys a card by the first `Char <n>` in it. With the crown
  hidden, the first match on the visiting card is the main's name, still
  `Char 1101`.
- The new `directors` entry in `setUp` must not change the three existing
  tests of the class: they assert on borders, names and links only.
- Same file and class as AM-02's test; implement them together.

---

## Implementation order

1. **Commit 1: AM-01** alone. It changes what a run does when ESI is down and
   deserves its own CHANGELOG entry ("Changed").
2. **Commit 2: AM-02, AM-05** together ("Fixed" / "Changed"): both are about
   what a Corporation page shows of a main from another Corporation, both
   are template-only, and their tests sit in the same class.
3. **Commit 3: AM-03, AM-04** together ("Fixed"): two small, unrelated
   corrections in `snapshot.py` and `sources/corptools.py`.
4. After each commit's changes: the named test modules, one call each; the
   full suite runs at `/commit`. README: the *Corporation* paragraph should
   say that the card of a main elsewhere shows neither services nor crown to
   a viewer without `view_all` (AM-05), if it describes the cards at that
   depth - check, the checklist compares every claim.

## Checked and fine

One line each, so nobody checks them again.

- **Permission on every view**: all 13 URLs carry `any_permission_required`; `views.py` has no undecorated view; the two dashboard widgets check `has_perm` themselves and return `""`.
- **Object level (IDOR)**: `corporation`, `corporation_export`, `corporation_service` go through `_visible_corporation` -> `can_view_corporation`; `account` checks the Corporation of the account's main; `own_account` uses `request.user.pk` only; `view_all` lists are `view_all` only.
- **Visiting mains** on a Corporation page link to their account only for `view_all` (cards, to-dos, spy and GM entries), as decided on 2026-09-28.
- **Spy markers and GM transactions** are added per request and per viewer (`_report(user)`), never stored in the snapshot, never on *My account*, the widgets or the smart filter; the CSV export uses the same report, so a viewer without the permission gets 404 for `spy_*` and `gm_transactions`.
- **CSRF**: the only writing requests are the settings form and `rebuild`, both POST with `{% csrf_token %}`; `rebuild` is `require_POST`; no GET writes (`get_solo()` creating its row aside).
- **Open redirect**: `rebuild` checks `next` with `url_has_allowed_host_and_scheme` against the request's host and falls back to the index; covered by `test_should_never_send_anyone_elsewhere`.
- **XSS**: no `mark_safe`, `|safe`, `format_html` or `innerHTML` anywhere; every name from ESI or the snapshot is auto-escaped, also inside `title=`, `data-order=` and `data-eos-auth-monitor-copy=`; the JavaScript writes with `textContent` only; the member notice goes through `urlize|linebreaksbr` with auto-escaping on.
- **CSV export**: formula cells are prefixed (`_csv_cell`), the file name goes through `get_valid_filename`, `group` only selects among rows the page shows.
- **SQL**: no raw SQL, `extra()` or string-built queries; no `eval`, `pickle`, `yaml`.
- **Forms**: `MonitorConfigurationForm.Meta.fields` is an explicit list; the dynamic fields are booleans and choice fields validated against what is installed.
- **ESI tokens**: only tokens with the membership scope of characters Auth has in that Corporation (member list) or that corptools knows as Directors (roles); nothing but the exception's class name is logged; no token, scope list or response body in a log.
- **Outgoing requests**: ESI only, through django-esi; no webhooks, no user-supplied URLs.
- **Admin**: one `ModelAdmin` for the smart filter, no actions; `Snapshot` and `MonitorConfiguration` are not in the admin.
- **Celery**: one task, `QueueOnce`, no retries; a failed build leaves the previous snapshot (`update_or_create` runs only after `build` returned); the snapshot row is written in one statement.
- **Old snapshots**: a 0.0.5 snapshot (what production holds) was compared key by key with what `Report` reads: every newer key is read with `.get` and a default (`directors`, `in_auth`, `critical_scope_count`, `metrics`); `OtherMain(**entry)` gets the same five keys.
- **Dates**: `timezone.now()` throughout; `sources.corptools._parse` makes naive timestamps UTC; no ISK, no floats that matter.
- **Model defaults**: none comes from settings; `critical_scope_count` has a literal 5; migrations 0001-0009 match the models as read (`makemigrations --check` was not run, it runs at every `/commit`).
- **Templates**: every variable used exists in the context of each page that includes the partial (`own`, `charlink_url`, `can_view_all`, `link`, `corner`, `inline`, `hide_rows`, `hide_services`); every `{% url %}` of an optional app is `as var` and tested before use, except eos-tax's inside its own `gm_shown` block.
- **JavaScript**: all five files only read `data-` attributes and toggle classes; `tables.js` is only loaded on tables with a `tbody`; Tom Select comes from cdnjs with SRI.
- **Dependencies**: `allianceauth>=5.1.4,<6` and `django-solo`; no optional app is a dependency.
- **Deliberately not raised** (settled in `docs/HANDOVER.md`): failed ESI tokens retried every run; performance with a large Alliance (each page and each dashboard widget parses the whole snapshot); the bar and the lock staying up to an hour after a worker died mid-run; the smart filter failing everyone without a snapshot; `stale_after_days` 0 meaning "empty".
- **Not checked, another repository**: `eos_tax.db.gm_transactions` (`get_stored_gm_report`, `get_gm_page(...)["rows"]` with `character_id` and `counterparty`, `FLAGGED_PARTY`), the URL name `eos_tax:gm_transactions`; `eos_spy_network.api` (`KINDS`, `character_markers`, `label`, `description`), the URL names `eos_spy_network:corporation` and `:corporations`. An exception in either API is not caught here and would fail the page of a viewer who holds that app's permission.

## Decisions

Both open questions of the audit were answered by the user on 2026-11-12;
none is left. They belong into `docs/HANDOVER.md` when the fixes are
committed.

1. **AM-01: what a run does when ESI does not answer** - the run fails, the
   last good snapshot stays, the bar says so ("ok wie empfohlen"). Not chosen:
   carrying the member list and Directors over from the previous snapshot
   (more code, figures of two ages on one page), and leaving it as it is.
2. **Visiting mains on a Corporation page** - the card of a main from another
   Corporation hides that account's service icons and Director crown from a
   viewer without `view_all` ("hide under that circumstance"). This is
   AM-05. The question named both the icons and the crown, so both are
   hidden; if only the service icons were meant, drop step 1 of AM-05's fix
   and the crown assertions of its tests.
