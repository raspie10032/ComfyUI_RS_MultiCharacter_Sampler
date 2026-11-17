# SPDX-License-Identifier: GPL-3.0-only
"""Recognize standalone prompt tags that describe a different camera view."""
from functools import partial
import re

from .prompt_syntax import filter_prompt_tags


_EPSILON = 1e-8
_NORMALIZE = str.maketrans({"_": " ", "-": " ", "–": " ", "‑": " ", "’": "'"})

_YAW = {
    **dict.fromkeys(("from front", "from the front", "viewed from the front"), ("front", "front quarter")),
    **dict.fromkeys(("from behind", "from the rear", "from back", "viewed from behind"), ("rear", "rear quarter")),
    **dict.fromkeys(("front view", "straight on front view", "straight on",
                     "camera on the character's front"), ("front",)),
    **dict.fromkeys(("rear view", "back view", "straight on rear view",
                     "camera on the character's rear"), ("rear",)),
    **dict.fromkeys(("from side", "from the side", "side view", "side profile", "profile"), ("side",)),
    **dict.fromkeys(("three quarter view", "3/4 view"), ("front quarter", "rear quarter")),
    **dict.fromkeys(("front three quarter view", "three quarter front view", "front 3/4 view"), ("front quarter",)),
    **dict.fromkeys(("rear three quarter view", "three quarter rear view", "rear 3/4 view", "back three quarter view"), ("rear quarter",)),
}
_LATERAL = {
    alias: (side, view)
    for side in ("left", "right")
    for alias, view in (
        (f"from {side}", None), (f"from the {side}", None), (f"from the {side} side", None),
        (f"viewed from the {side} side", None), (f"camera on the character's {side}", "side"),
        (f"{side} profile", "side"), (f"{side} side view", "side"),
        (f"{side} front three quarter view", "front quarter"),
        (f"{side} rear three quarter view", "rear quarter"),
        (f"camera on the character's front {side}", "front quarter"),
        (f"camera on the character's rear {side}", "rear quarter"),
    )
}
_PITCH = {
    **dict.fromkeys(("from above", "high angle", "high angle shot", "high camera angle"), ("high", "overhead")),
    **dict.fromkeys(("from below", "low angle", "low angle shot", "low camera angle"), ("low", "underneath")),
    **dict.fromkeys(("eye level", "eye level shot", "level camera angle"), ("level",)),
    **dict.fromkeys(("overhead", "overhead view", "directly overhead", "directly above", "top down", "top down view",
                     "bird's eye view", "birds eye view", "camera directly above the character"), ("overhead",)),
    **dict.fromkeys(("directly underneath", "directly below", "bottom up view",
                     "worm's eye view", "worms eye view", "camera directly below the character"), ("underneath",)),
}
_SPECIFIC_PITCH = frozenset({
    "slight high camera angle", "slight low camera angle",
    "steep high camera angle", "steep low camera angle",
})
_FACING = {
    **dict.fromkeys(("facing front", "facing forward", "facing viewer", "facing the viewer",
                     "facing camera", "facing the camera"), ("front",)),
    **dict.fromkeys(("facing away", "facing away from viewer", "facing away from the camera",
                     "facing away from the viewer"), ("rear", "rear quarter")),
}
_FACE_TAGS = frozenset({
    "blush", "closed eyes", "closed mouth", "expressionless", "fang", "fangs",
    "frown", "grin", "hair between eyes", "looking at viewer", "looking at the viewer",
    "looking at camera", "looking at the camera", "eye contact", "looking back",
    "looking over shoulder", "looking over the shoulder", "one eye closed",
    "open mouth", "parted lips", "pout", "smile", "smirk", "tongue out", "wink",
})
_EYE_COLOR = re.compile(
    r"(?:(?:light|dark) )?(?:amber|aqua|black|blue|brown|cyan|gold|golden|gray|grey|"
    r"green|hazel|orange|pink|purple|red|silver|teal|violet|white|yellow|heterochromatic) eyes"
)
_EYE_DETAILS = re.compile(r"(?:[a-z]+(?:[ -][a-z]+)* )?(?:pupils?|eyebrows?)")

# MOSS also accepts standalone prose camera sentences, including its own captions.
_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])(\s+)")
_QUOTED = re.compile(r'"(?:\\.|[^"\\])*"|“[^”]*”')
_PROTECTED_QUOTE = re.compile(r"\x00(\d+)\x00")
_MOSS_YAW = {
    "straight on front view, with the front of the torso visible": "front",
    "front three quarter view, with the front and one side of the torso visible": "front quarter",
    "side profile, with the camera looking directly at the side of the torso": "side",
    "rear three quarter view, with the back and one side of the torso visible": "rear quarter",
    "straight on rear view, with the back of the torso visible": "rear",
    "the subject faces straight away from the camera": "rear",
}
_MOSS_YAW.update({tag.split(", ", 1)[0]: yaw for tag, yaw in _MOSS_YAW.items()})
_DIRECTION_TAGS = _YAW.keys() | _LATERAL.keys() | _PITCH.keys() | _SPECIFIC_PITCH


def _normalize(tag):
    return " ".join(tag.casefold().translate(_NORMALIZE).split()).rstrip(".!?")


def view_direction(view):
    """Describe the bearing and height of the snapped training view."""
    (x, y, z), _, _ = view
    side = "left" if x < -_EPSILON else "right" if x > _EPSILON else None
    if abs(z) <= _EPSILON:
        yaw = "side" if side else "pole"
    elif z > 0:
        yaw = "front quarter" if side else "front"
    else:
        yaw = "rear quarter" if side else "rear"
    if abs(y) < _EPSILON:
        pitch = "level"
    elif y > 0:
        pitch = "overhead" if yaw == "pole" else "high"
    else:
        pitch = "underneath" if yaw == "pole" else "low"
    return yaw, side, pitch


def camera_prompt_filter(view, hidden_details=()):
    """Build a filter for the snapped training view used by the camera adapter."""
    yaw, side, pitch = view_direction(view)
    learned_pitch = view[1].rsplit(", ", 1)[-1]

    def conflicts(tag, *, replace_lateral):
        tag = _normalize(tag)
        if tag in hidden_details:
            return True
        if tag in _YAW:
            return yaw not in _YAW[tag]
        if tag in _LATERAL:
            tag_side, tag_view = _LATERAL[tag]
            return (side != tag_side or (tag_view is not None and yaw != tag_view)
                    or (replace_lateral and tag == f"from {side}"))
        if tag in _PITCH:
            return pitch not in _PITCH[tag]
        if tag in _SPECIFIC_PITCH:
            return tag != learned_pitch
        if yaw != "pole":
            if tag in _FACING:
                return yaw not in _FACING[tag]
            if tag in ("facing left", "facing right"):
                return tag != f"facing {side}"
        return yaw in ("rear", "rear quarter") and (
            tag in _FACE_TAGS or _EYE_COLOR.fullmatch(tag) is not None or _EYE_DETAILS.fullmatch(tag) is not None
        )

    def clean(prompt, syntax, *, replace_lateral=False, literal_sentences=False):
        remove = partial(conflicts, replace_lateral=replace_lateral)
        quotes = []

        def protect_quote(match):
            quotes.append(match[0])
            return f"\x00{len(quotes) - 1}\x00"

        prompt = _QUOTED.sub(protect_quote, prompt)
        # Weighted captions use the tag filter. Mask quoted text in both passes
        # so a phrase printed on a sign is preserved verbatim.
        if literal_sentences and not any(mark in prompt for mark in ("(", ")", "::")):
            parts = _SENTENCE_BOUNDARY.split(prompt)
            parts.append("")
            kept = []
            for sentence, whitespace in zip(parts[::2], parts[1::2]):
                tag = _normalize(sentence)
                direction = _MOSS_YAW.get(tag)
                prefix, separator, tail = tag.partition(", ")
                # An upstream camera can prefix its prose with learned tags.
                # Recognize the support sentence before splitting its own comma.
                while direction is None and separator and prefix in _DIRECTION_TAGS:
                    direction = _MOSS_YAW.get(tail)
                    prefix, separator, tail = tail.partition(", ")
                if direction is not None:
                    if direction != yaw:
                        continue
                elif remove(sentence):
                    continue
                kept.extend((sentence, whitespace))
            if len(kept) != len(parts):
                prompt = "".join(kept).rstrip()
        cleaned = filter_prompt_tags(prompt, syntax, remove)
        return _PROTECTED_QUOTE.sub(lambda match: quotes[int(match[1])], cleaned) if quotes else cleaned

    return clean
