import re
from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def highlight(text, query):
    """Hebt alle Suchwörter in <mark> hervor. Sicher gegen XSS."""
    if not text or not query:
        return text
    safe_text = escape(str(text))
    for word in query.split():
        if len(word) >= 2:
            safe_text = re.sub(
                re.escape(escape(word)),
                lambda m: f'<mark class="search-hl">{m.group()}</mark>',
                safe_text,
                flags=re.IGNORECASE,
            )
    return mark_safe(safe_text)
