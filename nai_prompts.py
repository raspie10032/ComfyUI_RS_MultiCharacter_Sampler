# SPDX-License-Identifier: GPL-3.0-only
"""NAI boundary conversion; negative-weight text moves unweighted to UC."""
import math
import re

_TOKENS = re.compile(r"\\.|[+-]?(?:\d+(?:\.\d*)?|\.\d+)::|::|[{}\[\]]", re.DOTALL)


def _tokens(text):
    end = 0
    for match in _TOKENS.finditer(text):
        if match.start() > end:
            yield text[end:match.start()]
        yield match.group()
        end = match.end()
    if end < len(text):
        yield text[end:]


def _spans(text):
    """Numeric scopes and legacy emphasis can nest; never drop text after ::."""
    stack = []
    spans = []
    weight = 1.0
    for token in _tokens(text):
        if token.endswith("::") and token != "::":
            factor = float(token[:-2])
            if not math.isfinite(factor) or not math.isfinite(weight * factor):
                raise ValueError("NAI prompt weights must be finite.")
            stack.append(("::", weight))
            weight *= factor
        elif token in ("{", "["):
            stack.append(("}" if token == "{" else "]", weight))
            weight *= 1.05 if token == "{" else 1 / 1.05
            if not math.isfinite(weight):
                raise ValueError("NAI prompt weights must be finite.")
        elif stack and token == stack[-1][0]:
            _, weight = stack.pop()
        else:
            # Parentheses and square brackets in NAI text are literal in CLIP.
            literal = token[1:] if token.startswith("\\") and len(token) == 2 else token
            if spans and spans[-1][1] == weight:
                spans[-1] = (spans[-1][0] + literal, weight)
            else:
                spans.append((literal, weight))
    return spans


def _clean(text):
    return re.sub(r",(?:\s*,)+", ",", text).strip(" ,\n\t")


def _escape(text):
    return re.sub(r"([()])", r"\\\1", text)


def _convert(text, *, negative_field=False):
    positive, negative = [], []
    previous_negative = False
    for literal, weight in _spans(text):
        if not weight:
            previous_negative = False
            continue
        if weight < 0:
            # Deliberately discard magnitude, including nested emphasis.
            if previous_negative:
                negative[-1] += literal
            else:
                negative.append(literal)
            previous_negative = True
            continue
        previous_negative = False
        escaped = _escape(literal)
        if weight != 1 and literal.strip(" ,\n\t"):
            leading = literal[:len(literal) - len(literal.lstrip())]
            trailing = literal[len(literal.rstrip()):]
            escaped = f"{leading}({_escape(literal.strip())}:{weight:.6g}){trailing}"
        positive.append(escaped)
    regular = _clean("".join(positive))
    moved = ", ".join(_escape(_clean(s)) for s in negative if _clean(s))
    if negative_field:
        return "", join_prompts(regular, moved)
    return regular, moved


def join_prompts(*parts):
    return ", ".join(part.strip(" ,\n\t") for part in parts if part.strip(" ,\n\t"))


def local_prompts(prompt, negative_prompt="", local_negative_prompt=""):
    positive, moved = _convert(prompt)
    _, negative = _convert(negative_prompt, negative_field=True)
    # This last input already uses local syntax; do not parse it as NAI.
    return positive, join_prompts(negative, moved, local_negative_prompt)
