# SPDX-License-Identifier: GPL-3.0-only
"""Matching consumes tagger scores; request construction never receives them."""

import math
import re
from collections import Counter
from dataclasses import dataclass

from .prompt_syntax import parse_comfyui


@dataclass(frozen=True)
class Match:
    character_index: int | None
    score: float
    margin: float
    reason: str


def normalize_tag(tag):
    return " ".join(
        tag.replace(r"\(", "(").replace(r"\)", ")").replace("_", " ").casefold().split()
    )


def prompt_tags(prompt, vocabulary=()):
    # Only compare a normalized copy. Never serialize this copy into a request.
    tags = {normalize_tag(tag) for tag, weight in parse_comfyui(prompt) if weight > 0}
    # Local examples also use "short black hair" instead of two Danbooru tags.
    # Extract only literal whole-word phrases present in the actual vocabulary;
    # do not invent identities or add inferred tags to the generation prompt.
    for phrase in tuple(tags):
        if re.search(r"\b(no|not|without)\b", phrase):
            continue
        words = phrase.split()
        for start in range(len(words)):
            for end in range(start + 2, min(len(words), start + 16) + 1):
                tag = " ".join(words[start:end])
                if tag in vocabulary:
                    tags.add(tag)
    return tags


def match_characters(scores, characters, min_score=0.25, min_margin=0.08):
    """Independent assignments permit multiple eyes/regions per character.

    Shared features have no discriminating value. Absence is not contradiction:
    a crop may simply not show a tag. Unknown/ambiguous regions stay unmatched.
    """
    normalized = {
        normalize_tag(k): float(v)
        for k, v in scores.items()
        if math.isfinite(float(v)) and 0 <= float(v) <= 1
    }
    tags = [prompt_tags(c.prompt, normalized) for c in characters]
    counts = Counter(tag for group in tags for tag in group)
    ranked = []
    for index, group in enumerate(tags):
        features = []
        for tag in group:
            if tag not in normalized or (len(characters) > 1 and counts[tag] > 1):
                continue
            if re.fullmatch(r"\d+(girls?|boys?|others?)", tag) or tag in {
                "solo",
                "multiple girls",
                "multiple boys",
            }:
                continue
            if tag.startswith("artist:") or any(
                x in tag for x in ("quality", "resolution", "background")
            ):
                continue
            weight = 0.25 if tag.endswith(" eyes") else 1.0
            features.append((weight, normalized[tag]))
        # Strongest discriminating evidence avoids penalizing a longer original
        # prompt for attributes outside the crop. Competing strong identities
        # then produce a small margin and remain unmatched, rather than letting
        # the character with fewer prompt tags win. Eye-only evidence is capped.
        score = max((w * v for w, v in features), default=0.0)
        ranked.append((score, index))
    ranked.sort(reverse=True)
    if not ranked:
        return Match(None, 0.0, 0.0, "no_characters")
    score, index = ranked[0]
    margin = score - (ranked[1][0] if len(ranked) > 1 else 0.0)
    if score < min_score or margin < min_margin:
        return Match(None, score, margin, "ambiguous")
    return Match(index, score, margin, "tag_match")


def selected_prompts(base_prompt, base_negative, characters, match):
    """Only original user text crosses the request boundary.

    Keep original names, franchise qualifiers, weights, and negative text intact.
    The base inputs must be shared/detail-stage instructions, not mixed identities.
    """
    if match.character_index is None:
        return base_prompt, base_negative
    character = characters[match.character_index]
    return (
        ", ".join(x for x in (base_prompt, character.prompt) if x),
        ", ".join(x for x in (base_negative, character.uc) if x),
    )
