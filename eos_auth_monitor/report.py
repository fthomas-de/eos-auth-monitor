"""The snapshot as the pages need it: labels, counts, percentages.

Nothing here queries the database - everything comes from the snapshot, so a
page costs one read however big the Alliance is. What a page adds on top
(spy markers, GM transactions, Active in Mumble) the view reads and hands in.
"""

from dataclasses import dataclass, field, replace
from datetime import datetime

from django.urls import NoReverseMatch, reverse
from django.utils.translation import gettext_lazy as _
from django.utils.translation import ngettext, pgettext_lazy

from .checks import CHARACTER, CHECKS_BY_KEY, SERVICES_BY_KEY, WARNING_CHECK, Check, Service

DIRECTOR_CHECK = "char_director_token_missing"

# corporation-level check groups: (group key, label, cockpit icon)
CORPORATION_GROUPS = (
    ("corptools_corporations", _("Corporation Audit"), "fas fa-building-circle-check"),
    ("structures", pgettext_lazy("eos-auth-monitor", "Structures"), "fas fa-tower-broadcast"),
)
CORPORATION_GROUP_LABELS = {group: label for group, label, _icon in CORPORATION_GROUPS}

# the help mode's texts of the tiles (partials/help.html)
COCKPIT_GROUP_HELP = {
    "corptools_corporations": _(
        "Corporations whose corptools Corporation Audit exists, has a token and updates in time."
    ),
    "structures": _(
        "Corporations set up as an active owner in aa-structures, with a character left and a sync "
        "that is up to date."
    ),
}
REGISTERED_HELP = _(
    "Members of this Corporation whose character belongs to an account in Auth. Click for the list."
)
CORPORATION_GROUP_HELP = _('The checks of this app that fail for the Corporation, or "No problems".')
SERVICE_HELP = _("Share of mains that linked this service to their account in Auth.")
ACTIVITY_HELP = _(
    "Active in Mumble: of the days the mains played EVE, the share they were in Mumble too; "
    "the period is set in the settings."
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


# a token can lack a dozen scopes: the pages name this many, count the rest and keep the whole list as a tooltip
SCOPES_SHOWN = 2


def shorten(item: dict) -> str:
    """The detail as the pages show it: a list of scopes cut after the first ones."""
    detail = item["detail"]
    if not CHECKS_BY_KEY[item["check"]].lists_scopes or len(detail) <= SCOPES_SHOWN:
        return describe(item)
    rest = len(detail) - SCOPES_SHOWN
    more = ngettext("and %(count)d more", "and %(count)d more", rest) % {"count": rest}
    return f"{', '.join(detail[:SCOPES_SHOWN])} {more}"


def percent(part: int, total: int) -> int | None:
    if not total:
        return None
    return round(100 * part / total)


@dataclass
class Problem:
    check: Check
    detail: str
    # the whole detail where `detail` was shortened, for the tooltip; empty otherwise
    full_detail: str = ""


def _problem(item: dict) -> Problem:
    check = CHECKS_BY_KEY[item["check"]]
    detail, full = shorten(item), describe(item)
    return Problem(check, detail, full if full != detail else "")


def _problems(items) -> list[Problem]:
    # a check a later release dropped may still sit in an old snapshot
    return [_problem(item) for item in items if item["check"] in CHECKS_BY_KEY]


def _is_warning(item: dict, critical_scope_count: int, covered: bool = False) -> bool:
    """A to-do on the Corporation and account pages, never a problem.

    Scopes missing below the setting's number, and a Director token missing where another Director of the
    account in the same Corporation has one (`covered`).
    """
    if item["check"] == DIRECTOR_CHECK:
        return covered
    return item["check"] == WARNING_CHECK and len(item["detail"]) < critical_scope_count


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
    # problems below the setting's threshold (_is_warning): shown in the warning colour, counted nowhere
    warnings: list[Problem] = field(default_factory=list)
    # eos-spy-network's markers (sources.spy_network.SpyMarker), filled for its viewers only; never a problem
    spy: list = field(default_factory=list)
    # a GM transaction against "GM X" in eos-tax, filled for its viewers only; never a problem
    gm: bool = False
    # a Director of its own Corporation, any of the Alliance's; the crown on the account pages
    is_director: bool = False


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
    # the names of the account's characters that are Directors of its main's Corporation, alts elsewhere included
    directors: list[str] = field(default_factory=list)
    # Active in Mumble (Report.add_activity): its days with Mumble of its days in EVE; None without Mumble linked
    activity: "Row | None" = None
    # off on the copy of a Corporation that may not show the viewer's eos-spy-network / eos-tax findings (CEO roles)
    spy_shown: bool = True
    gm_shown: bool = True
    # a GM transaction anywhere in the whole account, alts elsewhere included (Report.add_gm_transactions)
    account_gm: bool = False
    # other Corporations of the Alliance where the account's alts count; own mains only, display only
    alt_corporations: list[str] = field(default_factory=list)

    @property
    def problem_characters(self) -> list[Character]:
        return [character for character in self.characters if character.problems]

    @property
    def problem_count(self) -> int:
        return sum(len(character.problems) for character in self.characters)

    @property
    def has_problems(self) -> bool:
        return bool(self.problem_characters)

    @property
    def warning_count(self) -> int:
        return sum(len(character.warnings) for character in self.characters)

    @property
    def has_warnings(self) -> bool:
        return any(character.warnings for character in self.characters)

    @property
    def spy_markers(self) -> list:
        """The eos-spy-network markers of the characters counted here, each kind once, as first met."""
        if not self.spy_shown:
            return []
        return list({marker.kind: marker for character in self.characters for marker in character.spy}.values())

    @property
    def has_gm(self) -> bool:
        """A GM transaction in the whole account, on a page that may show it - the card is the account's, the user's
        choice, not only of the characters counted here."""
        return self.gm_shown and self.account_gm

    @property
    def has_markers(self) -> bool:
        """Spy markers or GM transactions: shown on a card, never a problem."""
        return bool(self.spy_markers) or self.has_gm

    @property
    def listed_characters(self) -> list[Character]:
        """The account page's table: the characters with problems, warnings, eos-spy-network markers or GM
        transactions.

        Most problems first, then most warnings and markers; those only show, they rank no account.
        """
        return sorted(
            (
                character
                for character in self.characters
                if character.problems or character.warnings or character.spy or character.gm
            ),
            key=lambda character: (
                -len(character.problems),
                -len(character.warnings),
                -len(character.spy),
                not character.gm,
                not character.is_main,
                character.name.lower(),
            ),
        )

    @property
    def problem_free_characters(self) -> list[Character]:
        """The characters without a problem, warning or marker: the main first, then by name."""
        return sorted(
            (
                character
                for character in self.characters
                if not (character.problems or character.warnings or character.spy or character.gm)
            ),
            key=lambda character: (not character.is_main, character.name.lower()),
        )

    def _checks(self, kind: str) -> list[Check]:
        """Each check in the characters' `kind` ("problems" or "warnings"), once, in check order."""
        failed = {problem.check.key for character in self.characters for problem in getattr(character, kind)}
        return [check for key, check in CHECKS_BY_KEY.items() if key in failed]

    def _counts(self, kind: str) -> list[tuple[Check, int]]:
        return [
            (
                check,
                sum(
                    any(problem.check.key == check.key for problem in getattr(character, kind))
                    for character in self.characters
                ),
            )
            for check in self._checks(kind)
        ]

    @property
    def keywords(self) -> list[Check]:
        """Each check failed by any character of the account, once, in check order."""
        return self._checks("problems")

    @property
    def keyword_counts(self) -> list[tuple[Check, int]]:
        """Each failed check with the number of characters failing it - the account in short."""
        return self._counts("problems")

    @property
    def warning_keywords(self) -> list[Check]:
        return self._checks("warnings")

    @property
    def warning_counts(self) -> list[tuple[Check, int]]:
        return self._counts("warnings")

    def is_linked(self, service_key: str) -> bool:
        return any(link.linked for link in self.services if link.service.key == service_key)


@dataclass
class Row:
    """An app and how complete it is: a line of a Corporation tile, or a statistic tile of its own."""

    label: str
    icon: str
    part: int | None = None
    total: int | None = None
    # corporation-level checks pass or fail as a whole: None, or the problems
    problems: list[Problem] | None = None
    service: Service | None = None
    # the list behind a tile that is not a service's: a URL name and its arguments
    url_name: str | None = None
    url_args: tuple = ()
    # on the Mumble tile: Active in Mumble, shown below the linked share
    activity: "Row | None" = None
    # a count without a total, and why: shown instead of a share
    note: str = ""
    # what the tile counts, for the help mode
    help: str = ""

    @property
    def percent(self) -> int | None:
        if self.problems is not None:
            return 0 if self.problems else 100
        return percent(self.part or 0, self.total or 0)

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


MEMBER_LIST_UNREAD = _(
    "The member list of this Corporation could not be read: no member has a token with the membership scope."
)
MUMBLE = "mumble"
ACTIVITY_LABEL = _("Active in Mumble")
ACTIVITY_ICON = "fas fa-microphone-lines"


def _mean_activity(accounts) -> Row:
    """Active in Mumble of several mains, weighted by days: every day a main played EVE is one point, every day
    it was in Mumble too one hit, so a main with more days weighs more.

    A main without Mumble linked has no row and stays out; one without a day in EVE adds no point.
    """
    rows = [account.activity for account in accounts if account.activity]
    return Row(
        ACTIVITY_LABEL,
        ACTIVITY_ICON,
        sum(row.part for row in rows),
        sum(row.total for row in rows),
        help=ACTIVITY_HELP,
    )


def _card_order(account: Account) -> tuple:
    """Sort key of the Corporation page's cards: red, then yellow, then nothing open; within red and yellow
    Directors first, then GM transactions. Sort `accounts_by_problems` with it: the sort is stable."""
    colour = 0 if account.has_problems or account.has_markers else 1 if account.has_warnings else 2
    return colour, colour < 2 and not account.directors, colour < 2 and not account.has_gm


@dataclass
class Todo:
    """A failed character check and the mains whose accounts fail it - whom to write to."""

    check: Check
    accounts: list[Account]
    # the mains with the check's warnings, not its problems
    warning: bool = False

    @property
    def names(self) -> str:
        return ", ".join(account.main_name for account in self.accounts)

    @property
    def group(self) -> str:
        """The key of the group in the CSV export."""
        return self.check.key + WARNING_GROUP_SUFFIX if self.warning else self.check.key

    @property
    def label(self) -> str:
        return _("%(check)s (warning)") % {"check": self.check.label} if self.warning else str(self.check.label)



@dataclass
class SpyTodo:
    """An eos-spy-network marker and the characters counted here that carry it."""

    marker: object  # sources.spy_network.SpyMarker
    characters: list[Character]
    # the account of each character, to link its name to the main's page
    accounts: list[Account] = field(default_factory=list)

    @property
    def entries(self) -> list[tuple[Character, Account]]:
        return list(zip(self.characters, self.accounts))

    @property
    def group(self) -> str:
        return SPY_GROUP_PREFIX + self.marker.kind

    @property
    def names(self) -> str:
        return ", ".join(character.name for character in self.characters)


# the to-do group of the members Auth does not know; the others are check keys
UNREGISTERED = "unregistered"
# the to-do groups of eos-spy-network's markers: this prefix and the marker kind
SPY_GROUP_PREFIX = "spy_"
# the to-do group of the mains with eos-tax GM transactions
GM_GROUP = "gm_transactions"
# the to-do group of a check's warnings: its key and this
WARNING_GROUP_SUFFIX = "_warning"


@dataclass
class TodoRow:
    """One name of the to-do list, as the CSV export writes it."""

    group: str
    label: str
    name: str


@dataclass
class UnknownCharacter:
    """A member of a Corporation with no main to count it under."""

    id: int
    name: str
    # False: not in Auth; True: in Auth on an account without a main; None: a snapshot from before it was kept
    in_auth: bool | None


@dataclass
class Member:
    """A member of a Corporation on its Registered in Auth list."""

    id: int
    name: str
    # empty for a member without a main
    main_name: str = ""
    user_id: int | None = None
    # the main's Corporation where it is another one: no link, that account belongs to its own Corporation's viewers
    main_corporation_name: str = ""
    # without a main, as UnknownCharacter.in_auth
    in_auth: bool | None = None


@dataclass
class OtherMain:
    """A main in another Corporation that has characters in this one."""

    user_id: int
    main_id: int
    main_name: str
    main_corporation_name: str
    characters: list[dict]
    # its characters here as Characters, for a main the overview does not rate (outside the Alliance), built by
    # Report; eos-spy-network's markers and eos-tax's GM transactions set on them where the viewer may see them here
    alts: list[Character] = field(default_factory=list)
    # a GM transaction of its alts here or of its main, where the viewer may see it here (Report.add_gm_transactions)
    has_gm: bool = False

    # no account page: the overview does not rate this account (the to-do leaves its alts unlinked)
    unrated = True

    @property
    def spy_alts(self) -> list[Character]:
        return [character for character in self.alts if character.spy]

    @property
    def spy_markers(self) -> list:
        """The markers of its alts here, each kind once, as first met."""
        return list({marker.kind: marker for character in self.spy_alts for marker in character.spy}.values())


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
    # when it last joined the Alliance; None when ESI did not say or the snapshot predates it
    alliance_joined: datetime | None = None
    # eos-spy-network's marker kinds in its order once its markers were added for the viewer; None: not shown
    spy_kinds: tuple | None = None
    # set by Report.add_gm_transactions: the viewer may see eos-tax's GM transactions
    gm_shown: bool = False
    # set by Report.add_activity
    activity_shown: bool = False
    # no token could read the member list: the lists hold the characters Auth knows here
    member_list_unread: bool = False

    @property
    def spy_shown(self) -> bool:
        return self.spy_kinds is not None

    @property
    def activity(self) -> Row:
        return _mean_activity(self.accounts)

    @property
    def gm_accounts(self) -> list:
        """The mains with a card here whose account has a GM transaction, by name - whom to look at; also what the
        GM tile and column count. Accounts or OtherMains (outside the Alliance)."""
        return sorted(
            [
                *(account for account in self.evaluated_accounts if account.has_gm),
                *(other for other in self.unrated_other_mains if other.has_gm),
            ],
            key=lambda account: account.main_name.lower(),
        )

    @property
    def gm_names(self) -> str:
        return ", ".join(account.main_name for account in self.gm_accounts)

    @property
    def spy_characters(self) -> list[Character]:
        """The characters counted here with an eos-spy-network marker, by name; alts of mains outside the Alliance
        included."""
        return [character for _account, character in self._spy_pairs()]

    def _spy_pairs(self) -> list[tuple]:
        """(account or OtherMain, character) of every marked character here, by the character's name."""
        pairs = [
            (account, character)
            for account in self.evaluated_accounts
            for character in account.characters
            if character.spy
        ]
        pairs += [(other, character) for other in self.other_mains for character in other.spy_alts]
        return sorted(pairs, key=lambda pair: pair[1].name.lower())

    @property
    def spy_todos(self) -> list[SpyTodo]:
        """Per eos-spy-network marker, in its order, the characters counted here that carry it."""
        by_kind: dict[str, SpyTodo] = {}
        for account, character in self._spy_pairs():
            for marker in character.spy:
                todo = by_kind.setdefault(marker.kind, SpyTodo(marker, []))
                todo.characters.append(character)
                todo.accounts.append(account)
        return [by_kind[kind] for kind in self.spy_kinds or () if kind in by_kind]

    @property
    def characters(self) -> int | None:
        """All characters of the Corporation: the member list where it could be read, else Auth's stored count."""
        return self.member_count if self.member_count is not None else self.member_total

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
    def warning_accounts(self) -> list[Account]:
        """The accounts with warnings and no problem: a card in the warning colour on the Corporation page."""
        return [account for account in self.evaluated_accounts if account.has_warnings and not account.has_problems]

    @property
    def accounts_by_problems(self) -> list[Account]:
        """Most problems first, then most warnings; by name where they are equal."""
        return sorted(
            self.evaluated_accounts,
            key=lambda account: (-account.problem_count, -account.warning_count, account.main_name.lower()),
        )

    @property
    def card_accounts(self) -> list[Account]:
        """The cards of the own mains: problems, warnings or markers, in the cards' order (`_card_order`)."""
        return sorted(
            (
                account
                for account in self.accounts_by_problems
                if not account.visiting and (account.has_problems or account.has_warnings or account.has_markers)
            ),
            key=_card_order,
        )

    @property
    def visiting_cards(self) -> list[Account]:
        """Every main elsewhere with characters counted here, a card each: in the cards' order, nothing open last."""
        return sorted((account for account in self.accounts_by_problems if account.visiting), key=_card_order)

    @property
    def unrated_other_mains(self) -> list[OtherMain]:
        """The member list's mains elsewhere whose account the overview does not rate: mains outside the Alliance.

        Those with eos-spy-network markers or a GM transaction first, then by name as the member list has them.
        """
        rated = {account.user_id for account in self.visiting}
        return sorted(
            (other for other in self.other_mains if other.user_id not in rated),
            key=lambda other: not (other.spy_alts or other.has_gm),
        )

    @property
    def other_main_count(self) -> int:
        return len(self.visiting) + len(self.unrated_other_mains)

    @property
    def problem_free_accounts(self) -> list[Account]:
        return sorted(
            (
                account
                for account in self.accounts
                if not (account.has_problems or account.has_warnings or account.has_markers)
            ),
            key=lambda account: account.main_name.lower(),
        )

    def _todos(self, warning: bool) -> list[Todo]:
        accounts_by_check: dict[str, list[Account]] = {}
        for account in sorted(self.evaluated_accounts, key=lambda account: account.main_name.lower()):
            for check in account.warning_keywords if warning else account.keywords:
                accounts_by_check.setdefault(check.key, []).append(account)
        return [
            Todo(check, accounts_by_check[key], warning)
            for key, check in CHECKS_BY_KEY.items()
            if key in accounts_by_check
        ]

    @property
    def todos(self) -> list[Todo]:
        """Per failed character check, in check order, the mains it concerns, by name."""
        return self._todos(warning=False)

    @property
    def warning_todos(self) -> list[Todo]:
        """Per check with warnings, the mains they concern - open, but no problem."""
        return self._todos(warning=True)

    @property
    def listed_todos(self) -> list[Todo]:
        """The to-do list's check groups: the problems, then the warnings."""
        return self.todos + self.warning_todos

    @property
    def unregistered_names(self) -> str:
        return ", ".join(character["name"] for character in self.unregistered)

    @property
    def todo_rows(self) -> list[TodoRow]:
        """The to-do list name by name, in the order of the page: the checks, the unregistered members, then
        eos-spy-network's markers where they were added for the viewer."""
        rows = [
            TodoRow(todo.group, todo.label, account.main_name) for todo in self.listed_todos for account in todo.accounts
        ]
        rows += [
            TodoRow(UNREGISTERED, _("Not registered in Auth"), character["name"]) for character in self.unregistered
        ]
        rows += [
            TodoRow(todo.group, todo.marker.label, character.name)
            for todo in self.spy_todos
            for character in todo.characters
        ]
        rows += [TodoRow(GM_GROUP, _("GM transactions"), account.main_name) for account in self.gm_accounts]
        return rows

    @property
    def problem_count(self) -> int:
        """Problems of the Corporation itself plus those of every character counted here."""
        return len(self.problems) + sum(account.problem_count for account in self.evaluated_accounts)

    @property
    def registered(self) -> int | None:
        if self.member_count is None:
            # without the list: the characters Auth knows here that have a main
            return len(self.members) - len(self.unregistered) if self.member_list_unread else None
        return self.member_count - len(self.unregistered)

    @property
    def service_counts(self) -> list[Row]:
        """Per service the share of the mains that linked it.

        Members unknown to Auth stay out: nobody can say whose they are, and
        the cockpit and the Corporation page show them on their own.
        """
        return [
            Row(
                service.label,
                service.icon,
                sum(account.is_linked(service.key) for account in self.accounts),
                self.mains,
                service=service,
                activity=self.activity if self.activity_shown and service.key == MUMBLE else None,
                help=SERVICE_HELP,
            )
            for service in self.services
        ]

    @property
    def rows(self) -> list[Row]:
        """What the tile lists: every app that ran with its share of complete entries, then Active in Mumble.

        A row without a share stays on the Corporation's own pages: the overview compares shares.
        """
        shares = [row for row in self.check_rows if not row.note]
        return shares + self.service_counts + ([self.activity] if self.activity_shown else [])

    @property
    def check_rows(self) -> list[Row]:
        """The rows of the apps whose checks ran, without the services."""
        rows = []
        if self.member_count is not None:
            rows.append(
                Row(
                    _("Registered in Auth"),
                    "fas fa-user-plus",
                    self.registered,
                    self.member_count,
                    url_name="eos_auth_monitor:corporation_registered",
                    url_args=(self.id,),
                    help=REGISTERED_HELP,
                )
            )
        elif self.member_list_unread:
            rows.append(
                Row(
                    _("Registered in Auth"),
                    "fas fa-user-plus",
                    self.registered,
                    url_name="eos_auth_monitor:corporation_registered",
                    url_args=(self.id,),
                    note=MEMBER_LIST_UNREAD,
                    help=REGISTERED_HELP,
                )
            )
        if any(check.scope == CHARACTER for check in self.checks):
            rows.append(
                Row(
                    _("Character Audit"),
                    "fas fa-user-check",
                    sum(not character.problems for account, character in self.audited_characters),
                    # members without a main in Auth: corptools cannot audit them, so they count as failing
                    len(self.audited_characters) + len(self.unregistered),
                    url_name="eos_auth_monitor:corporation_character_audit",
                    url_args=(self.id,),
                    help=_(
                        "Characters here with a complete Character Audit. "
                        "Members not registered in Auth count as missing."
                    ),
                )
            )
        for group, label, icon in CORPORATION_GROUPS:
            if any(check.group == group for check in self.checks):
                rows.append(
                    Row(
                        label,
                        icon,
                        problems=[problem for problem in self.problems if problem.check.group == group],
                        help=CORPORATION_GROUP_HELP,
                    )
                )
        return rows

    @property
    def members(self) -> list[Member]:
        """The list behind Registered in Auth: the members without a main first, then the others by name."""
        registered = [
            Member(character.id, character.name, account.main_name, account.user_id)
            for account in self.accounts
            for character in account.characters
            # an alt outside the overview counts with its main here, but is no member
            if character.corporation_id == self.id
        ]
        registered += [
            Member(character["id"], character["name"], other.main_name, other.user_id, other.main_corporation_name)
            for other in self.other_mains
            for character in other.characters
        ]
        unknown = [Member(entry["id"], entry["name"], in_auth=entry.get("in_auth")) for entry in self.unregistered]
        return unknown + sorted(registered, key=lambda member: member.name.lower())

    @property
    def audited_characters(self) -> list[tuple[Account, Character]]:
        """The characters the Character Audit tile rates, with their accounts: most problems first, then by name."""
        return sorted(
            ((account, character) for account in self.evaluated_accounts for character in account.characters),
            key=lambda pair: (-len(pair[1].problems), pair[1].name.lower()),
        )

    @property
    def has_problems(self) -> bool:
        return bool(self.problems) or bool(self.problem_accounts)


class Report:
    def __init__(self, snapshot):
        self.built_at = snapshot.built_at
        data = snapshot.data
        self.alliance_id = data["alliance_id"]
        self.alliance_name = data["alliance_name"]
        self.checks = [CHECKS_BY_KEY[key] for key in data["checks"] if key in CHECKS_BY_KEY]
        self.services = [SERVICES_BY_KEY[key] for key in data["services"] if key in SERVICES_BY_KEY]
        self.stale_after_days = data.get("stale_after_days")
        # a snapshot from before the setting: every missing scope a problem, as it was built
        self.critical_scope_count = data.get("critical_scope_count", 1)
        self.members_fetched = data.get("members_fetched", False)
        # set by add_spy_markers: the viewer may see eos-spy-network's markers
        self.spy_shown = False
        # set by add_gm_transactions: the viewer may see eos-tax's GM transactions
        self.gm_shown = False
        # set by add_activity
        self.activity_shown = False
        rows = data["corporations"]
        # (Corporation, character) of every Director the snapshot knows; one from before the Director lists has none
        self._director_ids = {(row["id"], director["id"]) for row in rows for director in row.get("directors", [])}
        # the whole accounts, by the Corporation of their main: the account pages and the Alliance-wide lists
        self._accounts = {
            account["user_id"]: self._account(row, account) for row in rows for account in row["accounts"]
        }
        self._counted = self._characters_by_corporation({row["id"] for row in rows})
        names = {row["id"]: row["name"] for row in rows}
        self.corporations = [self._corporation(row, names) for row in rows]
        self._corporations_by_id = {corporation.id: corporation for corporation in self.corporations}
        # alts of mains outside the Alliance: eos-spy-network and eos-tax check them, this overview does not
        for corporation in self.corporations:
            for other in corporation.unrated_other_mains:
                other.alts = [
                    Character(
                        character["id"],
                        character["name"],
                        corporation.id,
                        corporation.name,
                        corporation.ticker,
                        "",
                        is_main=False,
                        problems=[],
                    )
                    for character in other.characters
                ]
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

    def _account(self, row, account) -> Account:
        # a snapshot from before the Director lists has none
        director_ids = {director["id"] for director in row.get("directors", [])}
        # a snapshot from before 0.0.31 has no such flag: every Director without a token stays a problem
        covered = {
            character["corporation_id"] for character in account["characters"] if character.get("corporation_token")
        }
        return Account(
            user_id=account["user_id"],
            main_id=account["main_id"],
            main_name=account["main_name"],
            corporation_id=row["id"],
            directors=sorted(
                (character["name"] for character in account["characters"] if character["id"] in director_ids),
                key=str.lower,
            ),
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
                    problems=_problems(
                        item
                        for item in character["problems"]
                        if not _is_warning(item, self.critical_scope_count, character["corporation_id"] in covered)
                    ),
                    warnings=_problems(
                        item
                        for item in character["problems"]
                        if _is_warning(item, self.critical_scope_count, character["corporation_id"] in covered)
                    ),
                    is_director=(character["corporation_id"], character["id"]) in self._director_ids,
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
            replace(
                self._accounts[account["user_id"]],
                characters=counted.get(account["user_id"], []),
                alt_corporations=sorted(
                    names[corporation_id]
                    for corporation_id, by_user in self._counted.items()
                    if corporation_id != row["id"] and account["user_id"] in by_user
                ),
            )
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
            alliance_joined=datetime.fromisoformat(row["alliance_joined"]) if row.get("alliance_joined") else None,
            member_list_unread=row.get("member_list_unread", False),
        )

    @property
    def accounts(self) -> list[Account]:
        """Every account of the Alliance with all its characters."""
        return list(self._accounts.values())

    @property
    def corporations_by_problems(self) -> list[Corporation]:
        """Most accounts with problems first - the number shown - then most Corporation problems, then by name."""
        return sorted(
            self.corporations,
            key=lambda corporation: (
                -len(corporation.problem_accounts),
                -len(corporation.problems),
                corporation.name.lower(),
            ),
        )

    def corporation(self, corporation_id: int) -> Corporation | None:
        return self._corporations_by_id.get(corporation_id)

    def account(self, user_id: int) -> tuple[Corporation, Account] | tuple[None, None]:
        """The whole account and the Corporation of its main."""
        account = self._accounts.get(user_id)
        if account is None:
            return None, None
        return self._corporations_by_id[account.corporation_id], account

    def add_spy_markers(self, markers: dict, kinds: tuple, corporation_id: int | None = None) -> None:
        """Give each character its eos-spy-network markers (EVE ID -> SpyMarkers), for a viewer who may see them.

        The Corporations share the characters with the whole accounts, so each
        page sees them wherever the character counts. With ``corporation_id``
        (eos-spy-network's CEO role) only that Corporation shows them, as
        ``add_gm_transactions`` does.
        """
        for account in self._accounts.values():
            for character in account.characters:
                character.spy = markers.get(character.id, [])
        for corporation in self.corporations:
            shown = corporation_id in (None, corporation.id)
            corporation.spy_kinds = tuple(kinds) if shown else None
            # the cards' tags: an alt of the CEO's mains counted elsewhere stays off that Corporation's page
            for account in corporation.evaluated_accounts:
                account.spy_shown = shown
            for other in corporation.unrated_other_mains:
                for character in other.alts:
                    character.spy = markers.get(character.id, []) if shown else []
        self.spy_shown = corporation_id is None

    def add_gm_transactions(self, character_ids: set[int], corporation_id: int | None = None) -> None:
        """Mark the characters with an eos-tax GM transaction, for a viewer who may see them.

        Every character of an account, alts outside the Alliance included (the
        user's choice of 2026-11-19), and a card marks the whole account. With
        ``corporation_id`` (eos-tax's CEO role) only that Corporation shows
        them: the Alliance-wide tile and column would read 0 everywhere else.
        """
        for account in self._accounts.values():
            for character in account.characters:
                character.gm = character.id in character_ids
        for corporation in self.corporations:
            shown = corporation.gm_shown = corporation_id in (None, corporation.id)
            # cards, to-do and CSV: another Corporation's findings stay off the CEO's view of this page
            for account in corporation.evaluated_accounts:
                account.gm_shown = shown
                account.account_gm = any(character.gm for character in self._accounts[account.user_id].characters)
            # a main outside the Alliance: its alts here and its main, all this app knows of the account
            for other in corporation.unrated_other_mains:
                for character in other.alts:
                    character.gm = shown and character.id in character_ids
                other.has_gm = shown and (other.main_id in character_ids or any(c.gm for c in other.alts))
        self.gm_shown = corporation_id is None

    def add_activity(self, rates: dict[int, tuple[int, int]]) -> None:
        """Give each main with Mumble linked its Active in Mumble: user ID -> (days with Mumble, days in EVE).

        Nothing where the Mumble service is switched off or not installed.
        """
        if self.service(MUMBLE) is None:
            return
        # the Corporations hold copies of the accounts, not the accounts themselves
        for account in [*self._accounts.values(), *(a for c in self.corporations for a in c.accounts)]:
            if account.is_linked(MUMBLE):
                account.activity = Row(ACTIVITY_LABEL, ACTIVITY_ICON, *rates.get(account.user_id, (0, 0)))
        for corporation in self.corporations:
            corporation.activity_shown = True
        self.activity_shown = True

    @property
    def gm_count(self) -> int:
        """The cockpit tile: the sum of the Corporations' GM counts, as the spy tile sums its column - an account with
        cards in two Corporations counts in both."""
        return sum(len(corporation.gm_accounts) for corporation in self.corporations)

    @property
    def spy_characters(self) -> list[Character]:
        """Every character with an eos-spy-network marker, each in the Corporation it counts in: the column's sum."""
        return [character for corporation in self.corporations for character in corporation.spy_characters]

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

    @property
    def has_member_lists(self) -> bool:
        """Whether any Corporation's member list was read - only those can name unknown members."""
        return any(corporation.member_count is not None for corporation in self.corporations)

    def unknown_characters(self) -> list[tuple[Corporation, UnknownCharacter]]:
        """Every member of the Alliance without a main in Auth, with its Corporation; by Corporation, then name."""
        return sorted(
            (
                (corporation, UnknownCharacter(entry["id"], entry["name"], entry.get("in_auth")))
                for corporation in self.corporations
                for entry in corporation.unregistered
            ),
            key=lambda row: (row[0].name.lower(), row[1].name.lower()),
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

    def cockpit(self) -> list[Row]:
        """The cockpit's tiles; the service ones also feed its Connections tile."""
        accounts = self.accounts
        gauges = [
            Row(
                service.label,
                service.icon,
                sum(account.is_linked(service.key) for account in accounts),
                # the mains only: the members unknown to Auth have a tile of their own
                len(accounts),
                service=service,
                activity=_mean_activity(accounts) if self.activity_shown and service.key == MUMBLE else None,
                help=SERVICE_HELP,
            )
            for service in self.services
        ]

        counted = [corporation for corporation in self.corporations if corporation.member_count is not None]
        if counted:
            gauges.append(
                Row(
                    _("Members registered"),
                    "fas fa-user-plus",
                    sum(corporation.registered for corporation in counted),
                    sum(corporation.member_count for corporation in counted),
                    # the list of the rest: the members without a main in Auth
                    url_name="eos_auth_monitor:unknown_characters",
                    help=_(
                        "Members of the Alliance's Corporations whose character belongs to an account in Auth. "
                        "Only Corporations whose member list could be read count."
                    ),
                )
            )

        if self.has_character_checks:
            characters = [character for account in accounts for character in account.characters]
            gauges.append(
                Row(
                    _("Character Audit complete"),
                    "fas fa-user-check",
                    sum(not character.problems for character in characters),
                    # as on the Corporation tiles: members without a main in Auth count as failing
                    len(characters) + sum(len(corporation.unregistered) for corporation in self.corporations),
                    url_name="eos_auth_monitor:character_audit",
                    help=_(
                        "Characters with a complete corptools Character Audit: present, all scopes granted, "
                        "up to date. Members not registered in Auth count as missing."
                    ),
                )
            )

        for group, label, icon in CORPORATION_GROUPS:
            if any(check.group == group for check in self.checks):
                gauges.append(
                    Row(
                        _("%(app)s working") % {"app": label},
                        icon,
                        sum(
                            not any(problem.check.group == group for problem in corporation.problems)
                            for corporation in self.corporations
                        ),
                        len(self.corporations),
                        url_name="eos_auth_monitor:directors",
                        url_args=(group,),
                        help=COCKPIT_GROUP_HELP[group],
                    )
                )

        return gauges
