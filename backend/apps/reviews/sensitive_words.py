import re
from functools import lru_cache

from django.conf import settings


@lru_cache(maxsize=1)
def _compiled_patterns():
    words = getattr(settings, 'REVIEW_SENSITIVE_WORDS', []) or []
    patterns = []
    for word in words:
        escaped = re.escape(word)
        if escaped:
            patterns.append((re.compile(escaped, flags=re.IGNORECASE), '*' * len(word)))
    return patterns


def mask_sensitive_words(text):
    if not text:
        return text

    result = text
    for pattern, replacement in _compiled_patterns():
        result = pattern.sub(replacement, result)
    return result


def sanitize_with_feedback(text):
    """
    Return sanitized content with lightweight feedback fields:
    - hit_sensitive_words: masked hit tokens (no plain sensitive words leaked)
    - sanitized_content: content after masking
    - suggestion: user-facing hint when hits exist
    """
    source = text or ''
    sanitized = source
    hits = []

    for pattern, replacement in _compiled_patterns():
        matched = pattern.findall(source)
        if matched:
            hits.extend(str(item) for item in matched if str(item).strip())
            sanitized = pattern.sub(replacement, sanitized)

    # Keep unique order and return masked words only.
    deduped = []
    for word in hits:
        masked = '*' * len(word)
        if masked and masked not in deduped:
            deduped.append(masked)

    return {
        'sanitized_content': sanitized,
        'hit_sensitive_words': deduped,
        'suggestion': (
            '内容中包含敏感词，系统已自动净化；如语义受影响，可手动修改后再次提交。'
            if deduped
            else ''
        ),
    }
