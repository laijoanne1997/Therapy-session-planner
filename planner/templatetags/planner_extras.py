from django import template

register = template.Library()


@register.filter
def splitlines_clean(value):
    """Split a block of text into a list of non-empty, stripped lines."""
    if not value:
        return []
    return [line.strip() for line in value.splitlines() if line.strip()]


BLOCK_TYPE_LABELS = {
    "warm_up": "Warm-up",
    "main": "Main",
    "movement_reset": "Movement reset",
    "warm_down": "Warm-down",
}


@register.filter
def block_type_label(value):
    return BLOCK_TYPE_LABELS.get(value, value)
