"""Server-side sanitization of rich-text post body HTML.

This is the authoritative XSS guard: any HTML that reaches ``CommunicationPost.body``
(feed composer, GraphQL, imports) is cleaned here on write, so every downstream reader
(feed, PDF/newsletter exports) can trust the stored markup. The frontend applies its own
render-time pass as defence in depth, but never as the sole barrier.

The allow-list matches what the feed's contentEditable editor emits (``execCommand``
across browsers produces a mix of semantic tags and inline styles).
"""
import bleach
from bleach.css_sanitizer import CSSSanitizer

ALLOWED_TAGS = [
    'p', 'br', 'div', 'span',
    'b', 'strong', 'i', 'em', 'u', 's', 'strike', 'sub', 'sup',
    'a', 'ul', 'ol', 'li',
    'h1', 'h2', 'h3', 'h4', 'blockquote', 'font', 'img',
]

ALLOWED_ATTRIBUTES = {
    '*': ['style'],
    'a': ['href', 'title', 'target', 'rel'],
    'img': ['src', 'alt', 'width', 'height'],
    'font': ['color'],
}

# Deliberately no 'data' — inline images are stored files referenced by URL, never data URIs.
ALLOWED_PROTOCOLS = ['http', 'https', 'mailto']

ALLOWED_CSS_PROPERTIES = [
    'color', 'background-color', 'text-align',
    'text-decoration', 'font-weight', 'font-style',
]

_css_sanitizer = CSSSanitizer(allowed_css_properties=ALLOWED_CSS_PROPERTIES)


def sanitize_post_html(html):
    """Return `html` cleaned to the feed allow-list, or the input unchanged if not a string."""
    if not html or not isinstance(html, str):
        return html
    return bleach.clean(
        html,
        tags=ALLOWED_TAGS,
        attributes=ALLOWED_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        css_sanitizer=_css_sanitizer,
        strip=True,
    )
