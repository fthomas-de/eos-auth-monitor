"""Translations of every eos_auth_monitor message: (de, ru, zh_Hans).

The German, Russian and Simplified Chinese translations are machine-generated and may be inaccurate.
Checked for sense, not by a native speaker - a correction goes here.

The source of truth for the catalogues - tools/translate.py writes these into
the .po files and refuses to run while a message is missing here. Add a new
message here, never in a .po file: the next run would overwrite a hand edit.

EVE jargon stays English in every language: Corporation, Alliance, Main,
Character, ISK. A term Alliance Auth translates itself (Alliance, Corporation)
needs the "EVE jargon" context in the code as well, or AA's catalogue wins
and the English never shows.

A short word Alliance Auth translates differently ("Open", "Name", "Overview")
needs the "eos-auth-monitor" context in the code; the translation test in
tests/test_translations.py names every such clash.

Plural forms: de 2, ru 3, zh_Hans 1.
"""

LANGUAGES = ("de", "ru", "zh_Hans")

PLURAL_FORMS = {
    "de": "nplurals=2; plural=(n != 1);",
    "ru": "nplurals=3; plural=(n%10==1 && n%100!=11 ? 0 : n%10>=2 && n%10<=4 && (n%100<10 || n%100>=20) ? 1 : 2);",
    "zh_Hans": "nplurals=1; plural=0;",
}

TRANSLATIONS = {
    "Auth Monitor": ("Auth Monitor", "Auth Monitor", "Auth Monitor"),
    "corptools - Character Audit": (
        "corptools - Character-Audit",
        "corptools - аудит Character",
        "corptools - Character 审计",
    ),
    "corptools - Corporation Audit": (
        "corptools - Corporation-Audit",
        "corptools - аудит Corporation",
        "corptools - Corporation 审计",
    ),
    "aa-structures": ("aa-structures", "aa-structures", "aa-structures"),
    "Audit missing": ("Audit fehlt", "Аудит отсутствует", "缺少审计"),
    "The character has no corptools Character Audit.": (
        "Der Character hat kein corptools-Character-Audit.",
        "У Character нет аудита Character в corptools.",
        "该 Character 没有 corptools Character 审计。",
    ),
    "Scopes missing": ("Scopes fehlen", "Не хватает скоупов", "缺少 Scope"),
    "None of the character's tokens carries all scopes corptools asks for.": (
        "Keiner der Tokens des Characters trägt alle Scopes, die corptools verlangt.",
        "Ни один из токенов Character не содержит все скоупы, которые требует corptools.",
        "该 Character 的令牌中没有一个包含 corptools 所需的全部 Scope。",
    ),
    "Audit inactive": ("Audit inaktiv", "Аудит неактивен", "审计未激活"),
    "corptools marks the audit inactive: a section has not updated for too long.": (
        "corptools markiert das Audit als inaktiv: Ein Abschnitt wurde zu lange nicht aktualisiert.",
        "corptools считает аудит неактивным: один из разделов слишком долго не обновлялся.",
        "corptools 将该审计标记为未激活：某个部分太久没有更新。",
    ),
    "Director token missing": ("Director-Token fehlt", "Нет токена Director", "缺少 Director 令牌"),
    "The character is a Director of its Corporation, but none of its tokens carries all scopes corptools needs for the Corporation audit.": (
        "Der Character ist Director seiner Corporation, aber keiner seiner Tokens trägt alle Scopes, die corptools für das Corporation-Audit braucht.",
        "Character — Director своей Corporation, но ни один из его токенов не содержит все скоупы, нужные corptools для аудита Corporation.",
        "该 Character 是其 Corporation 的 Director，但其令牌中没有一个包含 corptools 进行 Corporation 审计所需的全部 Scope。",
    ),
    "Corporation audit missing": (
        "Corporation-Audit fehlt",
        "Аудит Corporation отсутствует",
        "缺少 Corporation 审计",
    ),
    "The Corporation has no corptools Corporation Audit.": (
        "Die Corporation hat kein corptools-Corporation-Audit.",
        "У Corporation нет аудита Corporation в corptools.",
        "该 Corporation 没有 corptools Corporation 审计。",
    ),
    "Corporation token missing": (
        "Corporation-Token fehlt",
        "Нет токена Corporation",
        "缺少 Corporation 令牌",
    ),
    "No character of the Corporation has a token with the scopes the Corporation audit needs.": (
        "Kein Character der Corporation hat einen Token mit den Scopes, die das Corporation-Audit braucht.",
        "Ни у одного Character из Corporation нет токена со скоупами, нужными для аудита Corporation.",
        "该 Corporation 没有任何 Character 拥有 Corporation 审计所需 Scope 的令牌。",
    ),
    "Corporation data stale": (
        "Corporation-Daten veraltet",
        "Данные Corporation устарели",
        "Corporation 数据已过期",
    ),
    "A section of the Corporation audit has not updated within the limit.": (
        "Ein Abschnitt des Corporation-Audits wurde nicht innerhalb der Frist aktualisiert.",
        "Один из разделов аудита Corporation не обновлялся в пределах установленного срока.",
        "Corporation 审计的某个部分未在期限内更新。",
    ),
    "No structure owner": ("Kein Structure-Owner", "Нет владельца структур", "没有建筑所有者"),
    "The Corporation is not set up as an owner in aa-structures.": (
        "Die Corporation ist in aa-structures nicht als Owner eingerichtet.",
        "Corporation не настроена как владелец в aa-structures.",
        "该 Corporation 未在 aa-structures 中设置为所有者。",
    ),
    "Structure owner inactive": (
        "Structure-Owner inaktiv",
        "Владелец структур неактивен",
        "建筑所有者未启用",
    ),
    "The aa-structures owner of the Corporation is switched off.": (
        "Der aa-structures-Owner der Corporation ist ausgeschaltet.",
        "Владелец aa-structures для Corporation отключён.",
        "该 Corporation 的 aa-structures 所有者已被关闭。",
    ),
    "No structure owner character": (
        "Kein Structure-Owner-Character",
        "Нет Character владельца структур",
        "没有建筑所有者 Character",
    ),
    "The aa-structures owner has no enabled character left to fetch data with.": (
        "Dem aa-structures-Owner ist kein aktivierter Character mehr geblieben, mit dem Daten abgerufen werden können.",
        "У владельца aa-structures не осталось включённого Character для получения данных.",
        "该 aa-structures 所有者没有剩余的已启用 Character 可用于获取数据。",
    ),
    "Structure sync failing": (
        "Structure-Sync schlägt fehl",
        "Синхронизация структур не удаётся",
        "建筑同步失败",
    ),
    "aa-structures reports a sync that is not up to date.": (
        "aa-structures meldet einen Sync, der nicht aktuell ist.",
        "aa-structures сообщает о синхронизации, которая не актуальна.",
        "aa-structures 报告有同步未保持最新。",
    ),
    "Discord": ("Discord", "Discord", "Discord"),
    "Mumble": ("Mumble", "Mumble", "Mumble"),
    "QQ": ("QQ", "QQ", "QQ"),
    "Telegram": ("Telegram", "Telegram", "Telegram"),
    "Character Audit: sections that count": (
        "Character-Audit: Abschnitte, die zählen",
        "Аудит Character: учитываемые разделы",
        "Character 审计：计入的部分",
    ),
    "A character is inactive when one of these has not updated within corptools' limit.": (
        "Ein Character gilt als inaktiv, wenn einer davon nicht innerhalb der corptools-Frist aktualisiert wurde.",
        "Character считается неактивным, если один из них не обновлялся в пределах срока corptools.",
        "如果其中任何一项未在 corptools 的期限内更新，Character 即被视为未激活。",
    ),
    "Character Audit: required scopes": (
        "Character-Audit: benötigte Scopes",
        "Аудит Character: необходимые скоупы",
        "Character 审计：所需 Scope",
    ),
    "A character's token must carry all of these.": (
        "Der Token eines Characters muss alle diese tragen.",
        "Токен Character должен содержать все из них.",
        "Character 的令牌必须包含以下全部内容。",
    ),
    "Corporation Audit: sections that count": (
        "Corporation-Audit: Abschnitte, die zählen",
        "Аудит Corporation: учитываемые разделы",
        "Corporation 审计：计入的部分",
    ),
    "A Corporation's data is stale when one of these has not updated within the limit above.": (
        "Die Daten einer Corporation gelten als veraltet, wenn einer davon nicht innerhalb der obigen Frist aktualisiert wurde.",
        "Данные Corporation считаются устаревшими, если один из них не обновлялся в пределах указанного выше срока.",
        "如果其中任何一项未在上述期限内更新，Corporation 的数据即被视为已过期。",
    ),
    "Corporation Audit: required scopes": (
        "Corporation-Audit: benötigte Scopes",
        "Аудит Corporation: необходимые скоупы",
        "Corporation 审计：所需 Scope",
    ),
    "One token of a Corporation member must carry all of these.": (
        "Ein Token eines Corporation-Mitglieds muss alle diese tragen.",
        "Один токен участника Corporation должен содержать все из них.",
        "Corporation 成员的某一个令牌必须包含以下全部内容。",
    ),
    "Alliance": ("Alliance", "Alliance", "Alliance"),
    "The Alliance whose accounts and Corporations are monitored.": (
        "Die Alliance, deren Accounts und Corporations überwacht werden.",
        "Alliance, чьи аккаунты и Corporation отслеживаются.",
        "被监控其账号和 Corporation 的 Alliance。",
    ),
    "Stale after (days)": ("Veraltet nach (Tagen)", "Устаревает через (дней)", "过期天数"),
    "Days after which a section of the corptools Corporation audit counts as stale. Empty: the same limit corptools uses for characters.": (
        "Tage, nach denen ein Abschnitt des corptools-Corporation-Audits als veraltet gilt. Leer: dieselbe Frist, die corptools für Characters verwendet.",
        "Через сколько дней раздел аудита Corporation в corptools считается устаревшим. Пусто: тот же срок, что corptools использует для Character.",
        "corptools Corporation 审计的某个部分在多少天后被视为过期。留空：使用 corptools 对 Character 采用的同一期限。",
    ),
    "Fetch member lists from ESI": (
        "Mitgliederlisten von ESI abrufen",
        "Получать списки участников из ESI",
        "从 ESI 获取成员列表",
    ),
    "Reads each Corporation's member list with a token corptools already has, to show members that are not registered in Auth.": (
        "Liest die Mitgliederliste jeder Corporation mit einem Token, den corptools bereits hat, um Mitglieder zu zeigen, die nicht in Auth registriert sind.",
        "Читает список участников каждой Corporation с помощью токена, который уже есть у corptools, чтобы показать участников, не зарегистрированных в Auth.",
        "使用 corptools 已有的令牌读取每个 Corporation 的成员列表，以显示未在 Auth 中注册的成员。",
    ),
    "Configuration": ("Konfiguration", "Конфигурация", "配置"),
    "Pass accounts that HAVE problems instead of those without.": (
        "Accounts durchlassen, die Probleme HABEN, statt solcher ohne.",
        "Пропускать аккаунты, у которых ЕСТЬ проблемы, а не тех, у кого их нет.",
        "放行有问题的账号，而不是没有问题的账号。",
    ),
    "Also count the problems of the Corporation of the main.": (
        "Auch die Probleme der Corporation des Mains zählen.",
        "Учитывать также проблемы Corporation основного персонажа.",
        "同时计入该 Main 所在 Corporation 的问题。",
    ),
    "Smart Filter: Auth Monitor problems": (
        "Smart Filter: Auth-Monitor-Probleme",
        "Smart Filter: проблемы Auth Monitor",
        "Smart Filter：Auth Monitor 问题",
    ),
    "Corporation Audit": ("Corporation-Audit", "Аудит Corporation", "Corporation 审计"),
    "Structures": ("Structures", "Структуры", "建筑"),
    "Reading accounts": ("Accounts werden gelesen", "Чтение аккаунтов", "正在读取账号"),
    "Checking characters": ("Characters werden geprüft", "Проверка Character", "正在检查 Character"),
    "Checking Corporations": ("Corporations werden geprüft", "Проверка Corporation", "正在检查 Corporation"),
    "Reading member lists": ("Mitgliederlisten werden gelesen", "Чтение списков участников", "正在读取成员列表"),
    "Reading services": ("Dienste werden gelesen", "Чтение сервисов", "正在读取服务"),
    "Saving": ("Speichern", "Сохранение", "正在保存"),
    "never updated": ("nie aktualisiert", "ни разу не обновлялось", "从未更新"),
    "Registered in Auth": ("In Auth registriert", "Зарегистрированы в Auth", "已在 Auth 注册"),
    "Character Audit": ("Character-Audit", "Аудит Character", "Character 审计"),
    "Members registered": ("Mitglieder registriert", "Участники зарегистрированы", "已注册成员"),
    "Character Audit complete": (
        "Character-Audit vollständig",
        "Аудит Character завершён",
        "Character 审计完整",
    ),
    "%(app)s working": ("%(app)s funktioniert", "%(app)s работает", "%(app)s 正常运行"),
    "Not in the Auth Monitor overview": (
        "Nicht in der Auth-Monitor-Übersicht",
        "Нет в обзоре Auth Monitor",
        "不在 Auth Monitor 概览中",
    ),
    "No problems": ("Keine Probleme", "Проблем нет", "没有问题"),
    "linked": ("verknüpft", "привязано", "已关联"),
    "not linked": ("nicht verknüpft", "не привязано", "未关联"),
    "Character": ("Character", "Character", "Character"),
    "Corporation": ("Corporation", "Corporation", "Corporation"),
    "Problems": ("Probleme", "Проблемы", "问题"),
    "Overview": ("Übersicht", "Обзор", "概览"),
    "Settings": ("Einstellungen", "Настройки", "设置"),
    "This Corporation is not part of the overview.": (
        "Diese Corporation gehört nicht zur Übersicht.",
        "Эта Corporation не входит в обзор.",
        "此 Corporation 不在概览中。",
    ),
    "Mains of this Corporation": (
        "Mains dieser Corporation",
        "Main этой Corporation",
        "此 Corporation 的 Main",
    ),
    "No main of this Corporation is registered in Auth.": (
        "Kein Main dieser Corporation ist in Auth registriert.",
        "Ни один Main этой Corporation не зарегистрирован в Auth.",
        "此 Corporation 没有任何 Main 在 Auth 中注册。",
    ),
    "Members whose main is in another Corporation": (
        "Mitglieder, deren Main in einer anderen Corporation ist",
        "Участники, чей Main состоит в другой Corporation",
        "其 Main 在另一个 Corporation 的成员",
    ),
    "The member list of this Corporation could not be read: no member has a token with the membership scope.": (
        "Die Mitgliederliste dieser Corporation konnte nicht gelesen werden: Kein Mitglied hat einen Token mit dem Membership-Scope.",
        "Не удалось прочитать список участников этой Corporation: ни у одного участника нет токена со скоупом членства.",
        "无法读取此 Corporation 的成员列表：没有任何成员拥有带成员资格 Scope 的令牌。",
    ),
    "Not registered in Auth": (
        "Nicht in Auth registriert",
        "Не зарегистрированы в Auth",
        "未在 Auth 注册",
    ),
    "Main": ("Main", "Main", "Main"),
    "Cockpit": ("Cockpit", "Панель", "仪表盘"),
    "Connections": ("Verbindungen", "Подключения", "连接"),
    "Corporations": ("Corporations", "Corporation", "Corporation"),
    "Filter Corporations ...": (
        "Corporations filtern ...",
        "Фильтр Corporation ...",
        "筛选 Corporation ...",
    ),
    "Filter Corporations": ("Corporations filtern", "Фильтр Corporation", "筛选 Corporation"),
    "Mains": ("Mains", "Main", "Main"),
    "Characters": ("Characters", "Character", "Character"),
    "No Corporation of the Alliance is known to Auth.": (
        "Auth kennt keine Corporation der Alliance.",
        "Auth не знает ни одной Corporation этой Alliance.",
        "Auth 中没有该 Alliance 的任何 Corporation。",
    ),
    "No Corporation matches the filter.": (
        "Keine Corporation passt zum Filter.",
        "Ни одна Corporation не соответствует фильтру.",
        "没有 Corporation 符合筛选条件。",
    ),
    "Accounts with problems": ("Accounts mit Problemen", "Аккаунты с проблемами", "有问题的账号"),
    "%(part)s of %(total)s": ("%(part)s von %(total)s", "%(part)s из %(total)s", "%(part)s / %(total)s"),
    "Last rebuild %(seconds)s s, %(queries)s queries (%(query_seconds)s s)": (
        "Letzter Neuaufbau %(seconds)s s, %(queries)s Abfragen (%(query_seconds)s s)",
        "Последняя пересборка %(seconds)s с, запросов: %(queries)s (%(query_seconds)s с)",
        "上次重建 %(seconds)s 秒，%(queries)s 次查询（%(query_seconds)s 秒）",
    ),
    "%(corporations)s Corporations, %(accounts)s accounts, %(characters)s characters": (
        "%(corporations)s Corporations, %(accounts)s Accounts, %(characters)s Characters",
        "Corporation: %(corporations)s, аккаунтов: %(accounts)s, Character: %(characters)s",
        "%(corporations)s 个 Corporation，%(accounts)s 个账号，%(characters)s 个 Character",
    ),
    "member lists %(lists)s/%(corporations)s": (
        "Mitgliederlisten %(lists)s/%(corporations)s",
        "списки участников %(lists)s/%(corporations)s",
        "成员列表 %(lists)s/%(corporations)s",
    ),
    "%(kilobytes)s KB stored": (
        "%(kilobytes)s KB gespeichert",
        "сохранено %(kilobytes)s КБ",
        "已存储 %(kilobytes)s KB",
    ),
    "No Alliance is chosen yet, so there is nothing to monitor.": (
        "Es ist noch keine Alliance gewählt, daher gibt es nichts zu überwachen.",
        "Alliance ещё не выбрана, поэтому отслеживать нечего.",
        "尚未选择 Alliance，因此没有可监控的内容。",
    ),
    "Choose one in the settings.": (
        "In den Einstellungen eine wählen.",
        "Выберите её в настройках.",
        "请在设置中选择。",
    ),
    "The overview has not been built yet. It is built by a periodic task; the first run can take a few minutes.": (
        "Die Übersicht wurde noch nicht aufgebaut. Sie wird von einer periodischen Aufgabe aufgebaut; der erste Lauf kann einige Minuten dauern.",
        "Обзор ещё не построен. Его строит периодическая задача; первый запуск может занять несколько минут.",
        "概览尚未生成。它由定时任务生成，首次运行可能需要几分钟。",
    ),
    "The Alliance was changed. This is still the overview of the previous one until the rebuild has finished.": (
        "Die Alliance wurde geändert. Bis der Neuaufbau fertig ist, ist dies noch die Übersicht der vorherigen.",
        "Alliance была изменена. Пока пересборка не завершена, это всё ещё обзор прежней Alliance.",
        "Alliance 已更改。在重建完成之前，这仍是之前那个 Alliance 的概览。",
    ),
    "Data as of %(since)s ago": (
        "Daten von vor %(since)s",
        "Данные обновлены %(since)s назад",
        "数据更新于 %(since)s 前",
    ),
    "Rebuild now": ("Jetzt neu aufbauen", "Пересобрать сейчас", "立即重建"),
    "Waiting for a worker to start the rebuild ...": (
        "Warte darauf, dass ein Worker den Neuaufbau startet ...",
        "Ожидание запуска пересборки воркером ...",
        "正在等待 worker 开始重建 ...",
    ),
    "The rebuild failed. The overview shows the last good result.": (
        "Der Neuaufbau ist fehlgeschlagen. Die Übersicht zeigt das letzte gute Ergebnis.",
        "Пересборка не удалась. В обзоре показан последний удачный результат.",
        "重建失败。概览显示的是上一次成功的结果。",
    ),
    "Rebuild progress": ("Fortschritt des Neuaufbaus", "Ход пересборки", "重建进度"),
    "%(part)s of %(total)s mains linked": (
        "%(part)s von %(total)s Mains verknüpft",
        "Привязано Main: %(part)s из %(total)s",
        "已关联 %(part)s / %(total)s 个 Main",
    ),
    "Services": ("Dienste", "Сервисы", "服务"),
    "corptools: what the checks count": (
        "corptools: was die Prüfungen zählen",
        "corptools: что учитывают проверки",
        "corptools：检查所计入的内容",
    ),
    "Untick what the Alliance does not use, e.g. Moon Observations and the mining scope for an Alliance without moons. A section and its scope are separate entries.": (
        "Abwählen, was die Alliance nicht nutzt, z. B. Moon Observations und den Mining-Scope für eine Alliance ohne Monde. Ein Abschnitt und sein Scope sind getrennte Einträge.",
        "Снимите отметку с того, чем Alliance не пользуется, например Moon Observations и скоуп добычи для Alliance без лун. Раздел и его скоуп — отдельные пункты.",
        "取消勾选 Alliance 不使用的内容，例如没有月球的 Alliance 可取消 Moon Observations 及采矿 Scope。某个部分与其 Scope 是各自独立的条目。",
    ),
    "None of the apps the checks and services read from is installed.": (
        "Keine der Apps, aus denen die Prüfungen und Dienste lesen, ist installiert.",
        "Ни одно из приложений, из которых читают проверки и сервисы, не установлено.",
        "检查和服务所读取的应用均未安装。",
    ),
    "Save": ("Speichern", "Сохранить", "保存"),
    "Settings saved. The overview is being rebuilt.": (
        "Einstellungen gespeichert. Die Übersicht wird neu aufgebaut.",
        "Настройки сохранены. Обзор пересобирается.",
        "设置已保存。概览正在重建。",
    ),
    "The overview is being rebuilt.": (
        "Die Übersicht wird neu aufgebaut.",
        "Обзор пересобирается.",
        "概览正在重建。",
    ),
}

PLURALS = {
    "%(counter)s character": (
        ["%(counter)s Character", "%(counter)s Characters"],
        ["%(counter)s Character", "%(counter)s Character", "%(counter)s Character"],
        ["%(counter)s 个 Character"],
    ),
}


def problems():
    """What is malformed in the entries above, as readable lines.

    tools/translate.py stops on any of these before it touches a catalogue,
    and the normal test suite runs the same check: a tuple one language short
    would otherwise end in an IndexError deep inside the fill, and a plural
    with the wrong number of forms or a lost placeholder would only show when
    a page renders it.
    """
    import re

    placeholder = re.compile(r"%\([a-z_]+\)s|\{[^}]*\}")
    found = []

    def check(msgid, text, where):
        if not isinstance(text, str) or not text:
            found.append(f"{where}: {msgid!r} has an empty or non-text translation")
        elif sorted(placeholder.findall(text)) != sorted(placeholder.findall(msgid)):
            found.append(f"{where}: {msgid!r} has other placeholders than the English")

    for msgid, values in TRANSLATIONS.items():
        if not isinstance(values, tuple) or len(values) != len(LANGUAGES):
            found.append(f"{msgid!r} needs one translation per language {LANGUAGES}")
            continue
        for language, text in zip(LANGUAGES, values):
            check(msgid, text, language)

    for msgid, values in PLURALS.items():
        if not isinstance(values, tuple) or len(values) != len(LANGUAGES):
            found.append(f"{msgid!r} needs one list of plural forms per language {LANGUAGES}")
            continue
        for language, forms in zip(LANGUAGES, values):
            wanted = int(re.search(r"nplurals=(\d+)", PLURAL_FORMS[language]).group(1))
            if not isinstance(forms, list) or len(forms) != wanted:
                found.append(f"{language}: {msgid!r} needs {wanted} plural forms")
                continue
            for text in forms:
                check(msgid, text, language)

    return found
