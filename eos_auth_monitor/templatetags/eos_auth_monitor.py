from django import template

register = template.Library()


@register.filter
def is_linked(account, service_key) -> bool:
    return account.is_linked(service_key)


@register.filter
def percent_class(percent) -> str:
    """Bootstrap text colour for a cockpit percentage."""
    if percent is None:
        return "text-body-secondary"
    if percent >= 90:
        return "text-success"
    if percent >= 60:
        return "text-warning"
    return "text-danger"


@register.filter
def row_class(row) -> str:
    """Text colour for a row of the overview: a voluntary service's share is shown, not rated."""
    if row.service is not None and row.service.voluntary:
        return "text-body-secondary"
    return percent_class(row.percent)
