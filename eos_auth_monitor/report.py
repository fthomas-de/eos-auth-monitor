"""The snapshot as the pages need it: labels, counts, percentages.

Nothing here queries the database - everything comes from the snapshot, so a
page costs one read however big the Alliance is.
"""

from dataclasses import dataclass, field

from django.utils.translation import gettext_lazy as _

from .checks import CHARACTER, CHECKS_BY_KEY, SERVICES_BY_KEY, Check, Service

# corporation-level check groups: (group key, label, cockpit icon)
CORPORATION_GROUPS = (
    ("corptools_corporations", _("Corporation Audit"), "fas fa-building-circle-check"),
    ("structures", _("Structures"), "fas fa-tower-broadcast"),
)


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
    def keywords(self) -> list[Check]:
        """Each check failed by any character of the account, once, in check order."""
        failed = {problem.check.key for character in self.characters for problem in character.problems}
        return [check for key, check in CHECKS_BY_KEY.items() if key in failed]

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
    def problem_accounts(self) -> list[Account]:
        return [account for account in self.accounts if account.has_problems]

    @property
    def accounts_by_problems(self) -> list[Account]:
        """Most problems first; by name where they are equal."""
        return sorted(self.accounts, key=lambda account: (-account.problem_count, account.main_name.lower()))

    @property
    def problem_count(self) -> int:
        """Problems of the Corporation itself plus those of all its accounts, to rank the tiles."""
        return len(self.problems) + sum(account.problem_count for account in self.accounts)

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
            characters = [character for account in self.accounts for character in account.characters]
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

    @property
    def percent(self) -> int | None:
        return percent(self.part, self.total)


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
        self.corporations = [self._corporation(row) for row in data["corporations"]]
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

    def _corporation(self, row) -> Corporation:
        accounts = [
            Account(
                user_id=account["user_id"],
                main_id=account["main_id"],
                main_name=account["main_name"],
                corporation_id=row["id"],
                services=[
                    ServiceLink(service, bool(account["services"].get(service.key))) for service in self.services
                ],
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
            )
            for account in row["accounts"]
        ]
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
        )

    @property
    def accounts(self) -> list[Account]:
        return [account for corporation in self.corporations for account in corporation.accounts]

    @property
    def corporations_by_problems(self) -> list[Corporation]:
        """Most problems first; by name where they are equal."""
        return sorted(self.corporations, key=lambda corporation: (-corporation.problem_count, corporation.name.lower()))

    def corporation(self, corporation_id: int) -> Corporation | None:
        return next((corporation for corporation in self.corporations if corporation.id == corporation_id), None)

    def account(self, user_id: int) -> tuple[Corporation, Account] | tuple[None, None]:
        for corporation in self.corporations:
            for account in corporation.accounts:
                if account.user_id == user_id:
                    return corporation, account
        return None, None

    def service(self, service_key: str) -> Service | None:
        return next((service for service in self.services if service.key == service_key), None)

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

        if any(check.scope == CHARACTER for check in self.checks):
            characters = [character for account in accounts for character in account.characters]
            gauges.append(
                Gauge(
                    _("Character Audit complete"),
                    sum(not character.problems for character in characters),
                    len(characters),
                    "fas fa-user-check",
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
                    )
                )

        return gauges
