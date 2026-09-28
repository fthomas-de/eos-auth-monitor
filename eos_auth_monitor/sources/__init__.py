"""Readers for the apps the checks and services come from.

Each module reads one app and only reads: nothing here saves a foreign row.
The apps are optional, so their models are imported inside the functions,
which the caller only calls when the app is installed.

A problem is a dict ``{"check": <check key>, "detail": [<str>, ...]}`` - plain
data, because it is stored in the snapshot as JSON.
"""


def problem(check: str, detail=None) -> dict:
    return {"check": check, "detail": list(detail or [])}
