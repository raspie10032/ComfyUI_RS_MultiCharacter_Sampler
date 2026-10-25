# SPDX-License-Identifier: GPL-3.0-only
"""Normalize the shared pipe protocol at local node inputs."""
from functools import wraps
import inspect
from dataclasses import replace
from .characters import CharacterPipe, PIPE_TYPE


def merge_negative(*parts):
    """Keep an already merged caption stable on repeated queue executions."""
    result = ""
    for part in parts:
        part = (part or "").strip(" ,\n\t")
        if part and (", " + part + ", ") not in (", " + result + ", "):
            result = ", ".join(filter(None, (result, part)))
    return result


def regional_negatives(encode, common, regions, masks, clips=None):
    """Partition negative captions without leaking one person's UC to others."""
    if not any(c.uc.strip() for c in regions):
        return encode(common)
    from .regional_lora import grouped_masks
    groups = grouped_masks(list(range(len(regions))), masks, regions)
    output = []
    for slot, mask in groups:
        caption = common if slot is None else merge_negative(common, regions[slot].uc)
        encoded = encode(caption, **({'encoder': clips[slot]} if clips is not None and slot is not None and slot < len(clips) else {}))
        for tokens, metadata in encoded:
            output.append([tokens, {**metadata, 'mask': mask.unsqueeze(0),
                                   'mask_strength': 1., 'set_area_to_bounds': False}])
    return output


def sampling_pipe(pipe, prompt, negative, syntax):
    """Resolve text once; keep character UC for detailer/metadata round trips."""
    from .nai_prompts import local_prompts
    if pipe.prompt is not None:
        source_syntax = pipe.syntax
        # A connected scene supplies its own common caption. The receiver's
        # negative remains useful for local defects/model-specific exclusions.
        extra = local_prompts("", negative)[1] if syntax == "NovelAI" else negative
        prompt, negative = pipe.prompt, pipe.negative_prompt or ""
    else:
        source_syntax, extra = syntax, ""
    if source_syntax not in ("NovelAI", "ComfyUI"):
        raise ValueError("Unsupported prompt syntax.")
    convert = local_prompts if source_syntax == "NovelAI" else lambda p, n: (p, n)
    prompt, negative = convert(prompt, negative)
    convert_character = local_prompts if (pipe.character_syntax or source_syntax) == "NovelAI" else lambda p, n: (p, n)
    chars = []
    for c in pipe.characters:
        positive, uc = convert_character(c.prompt, c.uc)
        chars.append(replace(c, prompt=positive, uc=uc))
    texts = []
    for c in pipe.text_regions:
        positive, uc = convert_character(c.prompt, c.uc)
        texts.append(replace(c, prompt=positive, uc=uc))
    return replace(pipe, characters=tuple(chars), text_regions=tuple(texts), prompt=prompt,
                   negative_prompt=merge_negative(negative, extra), syntax="ComfyUI", character_syntax="ComfyUI")


def local_pipe(value):
    if isinstance(value, CharacterPipe):
        return value
    convert = getattr(value, "as_local_character_pipe", None)
    if not callable(convert):
        raise ValueError("Connect an RS MultiCharacter pipe.")
    result = convert()
    if not isinstance(result, CharacterPipe):
        raise ValueError("Incompatible shared character pipe.")
    return result


def building_pipe(value):
    from .character_builder import BuildPipe, Slot
    if value is None or isinstance(value, BuildPipe):
        return value
    seed = getattr(value, "rs_as_building_pipe", None)
    if callable(seed):
        result = seed(BuildPipe)
        if not isinstance(result, BuildPipe):
            raise ValueError("Incompatible building pipe. / 조립 파이프 형식을 확인해 주세요.")
        return result
    source = local_pipe(value)
    if source.syntax == "NovelAI" or source.character_syntax == "NovelAI":
        converted = sampling_pipe(source, source.prompt or "", source.negative_prompt or "", source.syntax)
        source = replace(converted, prompt=None) if source.prompt is None else converted
    slots = []
    for i, character in enumerate(source.regions, 1):
        box = character.bbox
        common = dict(number=i, prompt=character.prompt, uc=character.uc,
                      x=character.x, y=character.y, geometry="box" if box else "point",
                      width=box[2]-box[0] if box else .4, height=box[3]-box[1] if box else .8)
        from .characters import TextRegion
        if isinstance(character, TextRegion):
            slots.append(Slot(**common, kind="text", literal_text=character.text))
        else:
            slots.append(Slot(**common, lora_name=character.lora_name,
                strength_model=character.lora_strength, strength_clip=character.lora_clip_strength,
                region_mask=character.region_mask, body_parts=character.body_parts,
                body_part_strength=character.body_part_strength, reference=character.reference))
    return BuildPipe(tuple(slots), len(slots), source.lora_application_mode,
                     source.interaction_json, source)


def shared_pipe_inputs(cls):
    function = getattr(cls, cls.FUNCTION)
    signature = inspect.signature(function)
    names = {name for name in signature.parameters if name in ("character_pipe", "building_pipe")}
    if not names:
        return

    original_inputs = cls.INPUT_TYPES

    @classmethod
    def shared_inputs(klass):
        schema = {group: dict(items) for group, items in original_inputs().items()}
        for group in ("required", "optional"):
            for name, spec in schema.get(group, {}).items():
                if name in names and spec[0] in (PIPE_TYPE, "RS_MC_BUILD_PIPE"):
                    types = "RS_MC_CHARACTER_PIPE,NAI_CONTEXT"
                    if name == "building_pipe":
                        types = "RS_MC_BUILD_PIPE," + types
                    schema[group][name] = (types, *spec[1:])
        return schema

    cls.INPUT_TYPES = shared_inputs

    @wraps(function)
    def run(self, *args, **kwargs):
        bound = signature.bind(self, *args, **kwargs)
        for name in names & bound.arguments.keys():
            bound.arguments[name] = (building_pipe if name == "building_pipe" else local_pipe)(bound.arguments[name])
        return function(*bound.args, **bound.kwargs)

    setattr(cls, cls.FUNCTION, run)
