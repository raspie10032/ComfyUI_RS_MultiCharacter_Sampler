# SPDX-License-Identifier: GPL-3.0-only
# Copyright (c) 2025 raspie10032

import re
import math
import logging
notice = logging.getLogger(__name__).warning

# ---------------------------------------------------------------------------
# Shared helpers
#
# A single intermediate representation (a list of ``(text, weight)`` tags,
# commas being tag separators in every syntax) backs all six converters.
# Each format has one parser and one serializer; the node classes are thin
# wrappers. This removes the duplicated, partly-contradictory exception
# handling that used to live in every class.
# ---------------------------------------------------------------------------

_ARTIST_TOKEN = "__artist__"
_DEFAULT_WEIGHT = 1.1
_WEIGHT_MIN, _WEIGHT_MAX = -5.0, 5.0

# Strict number: rejects "1.2.3", "--", "." that the old "[\d.-]+" accepted.
_STRICT_NUM = re.compile(r"-?\d+(?:\.\d+)?")
# Trailing ":<number-ish>" probe (lenient on purpose, see _trailing_weight).
_TRAILING_WEIGHT = re.compile(r":([\d.-]+)\s*$")
# A NovelAI V4 scope opener at a tag boundary: "<number>::".
_V4_OPEN = re.compile(r"^\s*(-?\d+(?:\.\d+)?)::")


def _guard_artist(text):
    """Hide the colon in ``artist:`` so it is never read as a weight marker."""
    return text.replace("artist:", _ARTIST_TOKEN)


def _restore_artist(text):
    return text.replace(_ARTIST_TOKEN, "artist:")


def _strict_float(token):
    """Return ``float(token)`` only if ``token`` is a well-formed number."""
    token = token.strip()
    if _STRICT_NUM.fullmatch(token):
        try:
            return float(token)
        except ValueError:
            return None
    return None


def _format_weight(value):
    """Compact numeric form: ``1.0500 -> 1.05``, ``-1.5000 -> -1.5``."""
    return f"{value:.4f}".rstrip("0").rstrip(".")


def _closest_power(weight, base):
    """Nearest integer exponent ``n`` so that ``base ** n ~= weight``."""
    if weight <= 0 or base <= 0 or base == 1:
        return 0
    return round(math.log(weight) / math.log(base))


# ---------------------------------------------------------------------------
# ComfyUI  <->  IR
# ---------------------------------------------------------------------------


def _split_top_level(text):
    """Split on commas that are not escaped and not inside parentheses."""
    parts, buf, depth, i = [], [], 0, 0
    while i < len(text):
        ch = text[i]
        if ch == "\\" and i + 1 < len(text) and text[i + 1] in "()":
            buf.append(text[i:i + 2])
            i += 2
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            parts.append("".join(buf))
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    parts.append("".join(buf))
    return parts


def _matches_outer_paren(segment):
    depth, i = 0, 0
    while i < len(segment):
        ch = segment[i]
        if ch == "\\" and i + 1 < len(segment) and segment[i + 1] in "()":
            i += 2
            continue
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return i == len(segment) - 1
        i += 1
    return False


def _trailing_weight(inner):
    """Return ``(weight_token, body)`` if ``inner`` ends with ``:<num>``.

    Uses the lenient probe so a malformed ``1.2.3`` is still detected and
    then rejected by the strict float check, preserving the historical
    fallback (keep the whole inner text, default weight).
    """
    m = _TRAILING_WEIGHT.search(inner)
    if not m:
        return None, inner
    return m.group(1), inner[:m.start()].strip()


def _eval_comfy_segment(segment):
    """Resolve one comma-segment into ``(text, weight)`` or ``None``.

    ComfyUI nesting: every bare ``(...)`` level multiplies by the 1.1
    default while an explicit ``(...:w)`` level multiplies by ``w``.
    Escaped ``\\(`` / ``\\)`` are literal characters, not group markers.
    """
    segment = segment.strip()
    if not segment:
        return None

    if segment.startswith("(") and _matches_outer_paren(segment):
        inner = segment[1:-1]
        token, body = _trailing_weight(inner)

        has_valid_explicit_weight = False
        if token is None:
            level_weight, child_text = _DEFAULT_WEIGHT, inner
        else:
            parsed = _strict_float(token)
            if parsed is None:
                level_weight, child_text = _DEFAULT_WEIGHT, inner
            elif not (_WEIGHT_MIN <= parsed <= _WEIGHT_MAX):
                notice(f"Weight {parsed} is outside -5 to 5; using 1.1 for: {body.strip()[:160]}")
                level_weight, child_text = _DEFAULT_WEIGHT, body
            else:
                level_weight, child_text = parsed, body
                has_valid_explicit_weight = True

        child = _eval_comfy_segment(child_text)
        if child is None:
            return None
        inner_text, inner_weight = child
        # A resolved paren group whose text still holds a colon means an
        # unescaped literal "(" with a non-numeric ":" (e.g. "(tag:o)" that
        # should have been "\(tag:o\)"). artist: is already guarded, so any
        # remaining colon is a malformed group -> drop it entirely.
        if not inner_text or (":" in inner_text and not has_valid_explicit_weight):
            if inner_text:
                notice(f"Dropped malformed weight group: {segment[:160]}. Escape literal parentheses as \\( and \\).")
            return None
        return (inner_text, level_weight * inner_weight)

    return (segment.replace("\\(", "(").replace("\\)", ")"), 1.0)


def parse_comfyui(text):
    tags = []
    for segment in _split_top_level(_guard_artist(text)):
        if segment.strip() == "":
            tags.append(("", 1.0))  # preserve empty slots ("a, , b")
            continue
        resolved = _eval_comfy_segment(segment)
        if resolved is not None:  # drop fully empty groups "()"
            tags.append(resolved)
    return tags


def to_comfyui(tags):
    parts = []
    for text, weight in tags:
        escaped = text.replace("(", r"\(").replace(")", r"\)")
        if weight == 1.0:
            parts.append(escaped)
        else:
            parts.append(f"({escaped}:{_format_weight(weight)})")
    return _restore_artist(", ".join(parts))


# ---------------------------------------------------------------------------
# NovelAI V4  <->  IR
# ---------------------------------------------------------------------------


def parse_naiv4(text):
    """Parse NovelAI V4 numeric-scope syntax into IR.

    Rules (per the README spec):
      - commas separate tags;
      - ``<w>::`` at a tag boundary opens a numeric scope;
      - a closing ``::`` ends the active scope after the current tag;
      - an opened scope with no closing ``::`` applies forward to all
        following comma-separated tags.

    The intentional space before a closing ``::`` (the guard that stops a
    trailing number being read as a weight) is handled naturally: the
    opener is matched only at a tag boundary, so ``team 5 ::`` is a close.
    """
    guarded = _guard_artist(text)
    tags = []
    current_weight = 1.0
    scope_active = False

    for chunk in guarded.split(","):
        open_match = _V4_OPEN.match(chunk)
        if open_match:
            value = _strict_float(open_match.group(1))
            if value is not None:
                current_weight = value
                scope_active = True
                chunk = chunk[open_match.end():]

        if "::" in chunk:
            if chunk.split("::", 1)[1].strip():
                notice("Text after a V4 closing :: in the same comma segment is not supported and was dropped: " + chunk[:160] + ". Add a comma after the closing ::.")
            content = chunk.split("::", 1)[0].strip()
            weight = current_weight if scope_active else 1.0
            if content:
                tags.append((content, weight))
            current_weight, scope_active = 1.0, False
        else:
            content = chunk.strip()
            weight = current_weight if scope_active else 1.0
            tags.append((content, weight))

    return tags
