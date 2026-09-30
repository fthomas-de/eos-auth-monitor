"""The snapshot as the pages need it: labels, counts, percentages.

Nothing here queries the database - everything comes from the snapshot, so a
page costs one read however big the Alliance is.
"""

from dataclasses import dataclass, field, replace

from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import pgettext_lazy

from .checks import CHARACTER, CHECKS_BY_KEY, SERVICES_BY_KEY, Check, Service

# corporation-level check groups: (group key, label, cockpit icon)
CORPORATION_GROUPS = (
    ("corptools_corporations", _("Corporation Audit"), "fas fa-building-circle-check"),
    ("structures", pgettext_lazy("eos-auth-monitor", "Structures"), "fas fa-tower-broadcast"),
)
CORPORATION_GROUP_LABELS = {group: label for group, label, _icon in CORPORATION_GROUPS}


PHASE_LABELS = {
    "accounts": _("Reading accounts"),
    "characters": _("Checking characters"),
    "corporations": _("Checking Corporations"),
    "members": _("Reading member lists"),
    "services": _("Reading services"),
    "store": _("Saving"),
}


def describe(item: dict) -> str:
    """The detail of a problem as one line of text."""
    if item["check"] == "corp_data_stale" and not item["detail"]:
        return str(_("never updated"))
    return ", ".join(item["detail"])


def percent(part: int, total: int) -> int | None:
    if not total:
        return None
    return round(100 * part / total)


@dataclass
class Problem:
    check: Check
    detail: str


def _problems(items) -> list[Problem]:
    # a check a later release dropped may still sit in an old snapshot
    return [Problem(CHECKS_BY_KEY[item["check"]], describe(item)) for item in items if item["check"] in CHECKS_BY_KEY]


@dataclass
class Character:
    id: int
    name: str
    corporation_id: int
    corporation_name: str
    corporation_ticker: str
    alliance_name: str
    is_main: bool
    problems: list[Problem]


@dataclass
class Director:
    """A Director of a Corporation, the account it belongs to and the tokens the Director lists ask about."""

    id: int
    name: str
    in_auth: bool
    # the account in the overview, or None: unknown to Auth, or a main outside the Alliance
    user_id: int | None
    main_name: str | None
    # group key -> whether the Director has that app's token
    tokens: dict[str, bool]

    def has_token(self, group: str) -> bool:
        return self.tokens.get(group, False)


@dataclass
class ServiceLink:
    service: Service
    linked: bool


@dataclass
class Account:
    user_id: int
    main_id: int
    main_name: str
    corporation_id: int
    services: list[ServiceLink]
    characters: list[Character]
    # characters outside the Alliance that *Only characters in the Alliance* left out
    left_out: int = 0
    # on another Corporation's page: the account of a main elsewhere, with only the characters counted there
    visiting: bool = False
    main_corporation_name: str = ""

    @property
    def problem_characters(self) -> list[Character]:
        return [character for character in self.characters if character.problems]

    @property
    def problem_count(self) -> int:
        return sum(len(character.problems) for character in self.characters)

    @property
    def characters_by_problems(self) -> list[Character]:
        """Most problems first; the main before its alts and then by name where they are equal."""
        return sorted(
            self.characters,
            key=lambda character: (-len(character.problems), not character.is_main, character.name.lower()),
        )

    @property
    def has_problems(self) -> bool:
        return bool(self.problem_characters)

    @property
    def problem_characters_by_problems(self) -> list[Character]:
        return [character for character in self.characters_by_problems if character.problems]

    @property
    def problem_free_characters(self) -> list[Character]:
        """The characters without a problem: the main first, then by name."""
        return sorted(
            (character for character in self.characters if not character.problems),
            key=lambda character: (not character.is_main, character.name.lower()),
        )

    @property
    def keywords(self) -> list[Check]:
        """Each check failed by any character of the account, once, in check order."""
        failed = {problem.check.key for character in self.characters for problem in character.problems}
        return [check for key, check in CHECKS_BY_KEY.items() if key in failed]

    @property
    def keyword_counts(self) -> list[tuple[Check, int]]:
        """Each failed check with the number of characters failing it - the account in short."""
        return [
            (
                check,
                sum(
                    any(problem.check.key == check.key for problem in character.problems)
                    for character in self.characters
                ),
            )
            for check in self.keywords
        ]

    def is_linked(self, service_key: str) -> bool:
        return any(link.linked for link in self.services if link.service.key == service_key)


@dataclass
class Row:
    """One line of a Corporation tile: an app and how complete it is."""

    label: str
    icon: str
    part: int | None = None
    total: int | None = None
    # corporation-level checks pass or fail as a whole: None, or the problems
    problems: list[Problem] | None = None
    service: Service | None = None

    @property
    def percent(self) -> int | None:
        if self.problems is not None:
            return 0 if self.problems else 100
        return percent(self.part or 0, self.total or 0)


@dataclass
class Todo:
    """A failed character check and the mains whose accounts fail it - whom to write to."""

    check: Check
    accounts: list[Account]

    @property
    def names(self) -> str:
        return ", ".join(account.main_name for account in self.accounts)


# the to-do group of the members Auth does not know; the others are check keys
UNREGISTERED = "unregistered"


@dataclass
class TodoRow:
    """One name of the to-do list, as the CSV export writes it."""

    group: str
    label: str
    name: str


@dataclass
class OtherMain:
    """A main in another Corporation that has characters in this one."""

    user_id: int
    main_id: int
    main_name: str
    main_corporation_name: str
    characters: list[dict]


@dataclass
class Corporation:
    id: int
    name: str
    ticker: str
    problems: list[Problem]
    accounts: list[Account]
    member_count: int | None
    other_mains: list[OtherMain]
    unregistered: list[dict]
    services: list[Service] = field(repr=False)
    checks: list[Check] = field(repr=False)
    member_total: int | None = None
    # no Director token could read the roles: Director problems of this Corporation go unseen
    no_director_token: bool = False
    directors: list[Director] = field(default_factory=list)
    # accounts whose main is in another Corporation, each with only its characters in this one
    visiting: list[Account] = field(default_factory=list)

    @property
    def characters(self) -> int | None:
        """All characters of the Corporation: the member list where it could be read, else Auth's stored count."""
        return self.member_count if self.member_count is not None else self.member_total

    @property
    def service_total(self) -> int:
        """What the service shares count: the mains, plus every member Auth does not know.

        An unknown character is a main of its own that cannot have linked anything.
        """
        return self.mains + len(self.unregistered)

    @property
    def mains(self) -> int:
        return len(self.accounts)

    @property
    def evaluated_accounts(self) -> list[Account]:
        """Every account with a character counted here: the own mains' and those visiting from elsewhere."""
        return self.accounts + self.visiting

    @property
    def problem_accounts(self) -> list[Account]:
        return [account for account in self.evaluated_accounts if account.has_problems]

    @property
    def accounts_by_problems(self) -> list[Account]:
        """Most problems first; by name where they are equal."""
        return sorted(
            self.evaluated_accounts, key=lambda account: (-account.problem_count, account.main_name.lower())
        )

    @property
    def problem_free_accounts(self) -> list[Account]:
        return sorted(
            (account for account in self.accounts if not account.has_problems),
            key=lambda account: account.main_name.lower(),
        )

    @property
    def todos(self) -> list[Todo]:
        """Per failed character check, in check order, the mains it concerns, by name."""
        accounts_by_check: dict[str, list[Account]] = {}
        for account in sorted(self.evaluated_accounts, key=lambda account: account.main_name.lower()):
            for check in account.keywords:
                accounts_by_check.setdefault(check.key, []).append(account)
        return [Todo(check, accounts_by_check[key]) for key, check in CHECKS_BY_KEY.items() if key in accounts_by_check]

    @property
    def unregistered_names(self) -> str:
        return ", ".join(character["name"] for character in self.unregistered)

    @property
    def todo_rows(self) -> list[TodoRow]:
        """The to-do list name by name, in the order of the page: the checks, then the unregistered members."""
        rows = [
            TodoRow(todo.check.key, todo.check.label, account.main_name)
            for todo in self.todos
            for account in todo.accounts
        ]
        rows += [
            TodoRow(UNREGISTERED, _("Not registered in Auth"), character["name"]) for character in self.unregistered
        ]
        return rows

    @property
    def problem_count(self) -> int:
        """Problems of the Corporation itself plus those of every character counted here, to rank the tiles."""
        return len(self.problems) + sum(account.problem_count for account in self.evaluated_accounts)

    @property
    def registered(self) -> int | None:
        if self.member_count is None:
            return None
        return self.member_count - len(self.unregistered)

    @property
    def service_counts(self) -> list[Row]:
        return [
            Row(
                service.label,
                service.icon,
                sum(account.is_linked(service.key) for account in self.accounts),
                self.service_total,
                service=service,
            )
            for service in self.services
        ]

    @property
    def service_gauges(self) -> list["Gauge"]:
        """Per service the share of this Corporation's mains that linked it, as on the overview."""
        return [Gauge(row.label, row.part, row.total, row.icon, row.service) for row in self.service_counts]

    @property
    def rows(self) -> list[Row]:
        """What the tile lists: every app that ran, with its share of complete entries."""
        return self.check_rows + self.service_counts

    @property
    def check_rows(self) -> list[Row]:
        """The rows of the apps whose checks ran, without the services."""
        rows = []
        if self.member_count is not None:
            rows.append(Row(_("Registered in Auth"), "fas fa-user-plus", self.registered, self.member_count))
        if any(check.scope == CHARACTER for check in self.checks):
            characters = [character for account in self.evaluated_accounts for character in account.characters]
            rows.append(
                Row(
                    _("Character Audit"),
                    "fas fa-user-check",
                    sum(not character.problems for character in characters),
                    len(characters),
                )
            )
        for group, label, icon in CORPORATION_GROUPS:
            if any(check.group == group for check in self.checks):
                rows.append(
                    Row(label, icon, problems=[problem for problem in self.problems if problem.check.group == group])
                )
        return rows

    @property
    def has_problems(self) -> bool:
        return bool(self.problems) or bool(self.problem_accounts)


@dataclass
class Gauge:
    label: str
    part: int
    total: int
    icon: str
    service: Service | None = None
    # the list behind a tile that is not a service's: a URL name and its arguments
    url_name: str | None = None
    url_args: tuple = ()

    @property
    def percent(self) -> int | None:
        return percent(self.part, self.total)

    @property
    def url(self) -> str:
        """Where the tile leads; "" for a tile without a list."""
        if self.service is not None:
            return reverse("eos_auth_monitor:service", args=[self.service.key])
        if self.url_name is None:
            return ""
        try:
            return reverse(self.url_name, args=self.url_args)
        except NoReverseMatch:
            return ""


class Report:
    def __init__(self, snapshot):
        self.built_at = snapshot.built_at
        data = snapshot.data
        self.alliance_id = data["alliance_id"]
        self.alliance_name = data["alliance_name"]
        self.checks = [CHECKS_BY_KEY[key] for key in data["checks"] if key in CHECKS_BY_KEY]
        self.services = [SERVICES_BY_KEY[key] for key in data["services"] if key in SERVICES_BY_KEY]
        self.stale_after_days = data.get("stale_after_days")
        self.members_fetched = data.get("members_fetched", False)
        rows = data["corporations"]
        # the whole accounts, by the Corporation of their main: the account pages and the Alliance-wide lists
        self._accounts = {
            account["user_id"]: self._account(row["id"], account) for row in rows for account in row["accounts"]
        }
        self._counted = self._characters_by_corporation({row["id"] for row in rows})
        names = {row["id"]: row["name"] for row in rows}
        self.corporations = [self._corporation(row, names) for row in rows]
        self._corporations_by_id = {corporation.id: corporation for corporation in self.corporations}
        self.metrics = self._metrics(data.get("metrics"))

    @staticmethod
    def _metrics(stored) -> dict | None:
        """The build figures ready to show; None for a snapshot from before they were kept."""
        if not stored:
            return None
        return {
            **stored,
            "kilobytes": round(stored["payload_bytes"] / 1024),
            "phases": [
                (PHASE_LABELS[phase], seconds) for phase, seconds in stored["phases"].items() if phase in PHASE_LABELS
            ],
        }

    def _account(self, corporation_id, account) -> Account:
        return Account(
            user_id=account["user_id"],
            main_id=account["main_id"],
            main_name=account["main_name"],
            corporation_id=corporation_id,
            services=[ServiceLink(service, bool(account["services"].get(service.key))) for service in self.services],
            characters=[
                Character(
                    id=character["id"],
                    name=character["name"],
                    corporation_id=character["corporation_id"],
                    corporation_name=character["corporation_name"],
                    corporation_ticker=character["corporation_ticker"],
                    alliance_name=character["alliance_name"],
                    is_main=character["id"] == account["main_id"],
                    problems=_problems(character["problems"]),
                )
                for character in account["characters"]
            ],
            # a snapshot from before 0.0.5 has no such count
            left_out=account.get("left_out", 0),
        )

    def _characters_by_corporation(self, corporation_ids) -> dict[int, dict[int, list[Character]]]:
        """Where each character counts: per Corporation, per account, its characters there.

        An account may have characters in several Corporations of the Alliance;
        each counts in the one it is in. A character in a Corporation outside
        the overview counts with its main.
        """
        counted = {}
        for account in self._accounts.values():
            for character in account.characters:
                where = character.corporation_id
                if where not in corporation_ids:
                    where = account.corporation_id
                counted.setdefault(where, {}).setdefault(account.user_id, []).append(character)
        return counted

    def _corporation(self, row, names) -> Corporation:
        counted = self._counted.get(row["id"], {})
        accounts = [
            replace(self._accounts[account["user_id"]], characters=counted.get(account["user_id"], []))
            for account in row["accounts"]
        ]
        visiting = sorted(
            (
                replace(
                    self._accounts[user_id],
                    characters=characters,
                    visiting=True,
                    main_corporation_name=names[self._accounts[user_id].corporation_id],
                )
                for user_id, characters in counted.items()
                if self._accounts[user_id].corporation_id != row["id"]
            ),
            key=lambda account: account.main_name.lower(),
        )
        return Corporation(
            row["id"],
            row["name"],
            row["ticker"],
            _problems(row["problems"]),
            accounts,
            row.get("member_count"),
            [OtherMain(**entry) for entry in row.get("other_mains", [])],
            row.get("unregistered", []),
            self.services,
            self.checks,
            row.get("member_total"),
            row.get("no_director_token", False),
            # a snapshot from before the Director lists has none
            [Director(**director) for director in row.get("directors", [])],
            visiting=visiting,
        )

    @property
    def accounts(self) -> list[Account]:
        """Every account of the Alliance with all its characters."""
        return list(self._accounts.values())

    @property
    def corporations_by_problems(self) -> list[Corporation]:
        """Most problems first; by name where they are equal."""
        return sorted(self.corporations, key=lambda corporation: (-corporation.problem_count, corporation.name.lower()))

    def corporation(self, corporation_id: int) -> Corporation | None:
        return next((corporation for corporation in self.corporations if corporation.id == corporation_id), None)

    def account(self, user_id: int) -> tuple[Corporation, Account] | tuple[None, None]:
        """The whole account and the Corporation of its main."""
        account = self._accounts.get(user_id)
        if account is None:
            return None, None
        return self._corporations_by_id[account.corporation_id], account

    def service(self, service_key: str) -> Service | None:
        return next((service for service in self.services if service.key == service_key), None)

    @property
    def has_character_checks(self) -> bool:
        return any(check.scope == CHARACTER for check in self.checks)

    def accounts_by_problems(self) -> list[tuple[Corporation, Account]]:
        """Every account of the Alliance with its Corporation: most problems first, then by Corporation and name."""
        return sorted(
            ((self._corporations_by_id[account.corporation_id], account) for account in self.accounts),
            key=lambda row: (-row[1].problem_count, row[0].name.lower(), row[1].main_name.lower()),
        )

    def has_director_list(self, group: str) -> bool:
        """Whether the checks of ``group`` ran, which is what gives it a list of Directors."""
        return group in CORPORATION_GROUP_LABELS and any(check.group == group for check in self.checks)

    def directors(self, group: str) -> list[tuple[Corporation, Director, bool]]:
        """Every Director of the Alliance with its Corporation and whether it has the token of ``group``.

        Those without the token first, then by Corporation and name.
        """
        return sorted(
            (
                (corporation, director, director.has_token(group))
                for corporation in self.corporations
                for director in corporation.directors
            ),
            key=lambda row: (row[2], row[0].name.lower(), row[1].name.lower()),
        )

    def overview_table(self) -> tuple[list[Row], list[tuple[Corporation, list[Row | None]]]]:
        """The overview as a table: a column per row of the tiles, a line per Corporation.

        Every tile has the same rows except Registered in Auth, which only a
        Corporation with a readable member list has; the longest tile gives the
        columns in tile order, and a line leaves a row it lacks empty.
        """
        if not self.corporations:
            return [], []
        columns = max(self.corporations, key=lambda corporation: len(corporation.rows)).rows
        keys = [str(column.label) for column in columns]
        lines = []
        for corporation in self.corporations_by_problems:
            rows = {str(row.label): row for row in corporation.rows}
            lines.append((corporation, [rows.get(key) for key in keys]))
        return columns, lines

    def connections(self) -> list[tuple[Service, int]]:
        """Linked accounts per service across the Alliance, for the cockpit."""
        accounts = self.accounts
        return [(service, sum(account.is_linked(service.key) for account in accounts)) for service in self.services]

    def cockpit(self) -> list[Gauge]:
        accounts = self.accounts
        gauges = [
            Gauge(
                service.label,
                sum(account.is_linked(service.key) for account in accounts),
                sum(corporation.service_total for corporation in self.corporations),
                service.icon,
                service,
            )
            for service in self.services
        ]

        counted = [corporation for corporation in self.corporations if corporation.member_count is not None]
        if counted:
            gauges.append(
                Gauge(
                    _("Members registered"),
                    sum(corporation.registered for corporation in counted),
                    sum(corporation.member_count for corporation in counted),
                    "fas fa-user-plus",
                )
            )

        if self.has_character_checks:
            characters = [character for account in accounts for character in account.characters]
            gauges.append(
                Gauge(
                    _("Character Audit complete"),
                    sum(not character.problems for character in characters),
                    len(characters),
                    "fas fa-user-check",
                    url_name="eos_auth_monitor:character_audit",
                )
            )

        for group, label, icon in CORPORATION_GROUPS:
            if any(check.group == group for check in self.checks):
                gauges.append(
                    Gauge(
                        _("%(app)s working") % {"app": label},
                        sum(
                            not any(problem.check.group == group for problem in corporation.problems)
                            for corporation in self.corporations
                        ),
                        len(self.corporations),
                        icon,
                        url_name="eos_auth_monitor:directors",
                        url_args=(group,),
                    )
                )

        return gauges
