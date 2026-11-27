# SPDX-License-Identifier: GPL-3.0-only
"""Apply a Korean text pack to Anima's model and tokenizer."""
from collections import OrderedDict
from contextlib import contextmanager, nullcontext
from contextvars import ContextVar
import json
from pathlib import Path
import re
from unicodedata import normalize

from .model_download import ensure_model_file

PACKS = "rs_anima_korean_text"
BETA_PACK = "RS-Anima-Korean-Text-v0.1-beta.safetensors"
BETA_PACK_URL = f"https://huggingface.co/raspie/RS-Anima-Korean-Text/resolve/main/{BETA_PACK}"
BETA_PACK_SIZE = 114_445_120
BETA_PACK_SHA256 = "ca6d5f81c19cfda133ce5c517ca69c64d0b76e7f7335272057ac33b58629a0c8"
T5_SIZE = 32128
HANGUL = re.compile(r"[가-힣]")
LITERAL = re.compile(r"[가-힣](?:[가-힣.!?,]| +(?=[가-힣.!?,]))*")
KOREAN_BYPASS = "rs_mc_korean_text"


def has_hangul(text):
    return HANGUL.search(normalize("NFC", text)) is not None


def pack_names():
    return list(dict.fromkeys((BETA_PACK, *_pack_paths().get_filename_list(PACKS))))


def _pack_paths():
    import folder_paths

    folder_paths.add_model_folder_path(PACKS, str(Path(folder_paths.models_dir) / PACKS), is_default=True)
    folder_paths.folder_names_and_paths[PACKS][1].add(".safetensors")
    return folder_paths


class _KoreanTokenizer:
    def __init__(self, tokenizer, char_map):
        self.base = tokenizer
        self.rows = char_map

    def __getattr__(self, name):
        return getattr(self.base, name)

    def tokenize_with_weights(self, text, return_word_ids=False, **kwargs):
        text = normalize("NFC", text)
        result = self.base.tokenize_with_weights(text, return_word_ids, **kwargs)
        if not HANGUL.search(text):
            return result

        from comfy.sd1_clip import escape_important, token_weights, unescape_important

        t5 = self.base.t5xxl.tokenizer
        pairs = []
        segments = token_weights(escape_important(text), 1.0)
        for word_id, (segment, weight) in enumerate(segments):
            segment = unescape_important(segment)
            ids = []
            end = 0
            for match in LITERAL.finditer(segment):
                if match.start() > end:
                    ids.extend(t5(segment[end:match.start()], add_special_tokens=False).input_ids)
                ids.extend(T5_SIZE + self.rows[c] if c in self.rows else t5.unk_token_id for c in match[0])
                end = match.end()
            if end < len(segment):
                ids.extend(t5(segment[end:], add_special_tokens=False).input_ids)
            pairs.extend((token, weight, word_id) if return_word_ids else (token, weight) for token in ids)
        if len(pairs) >= 512:
            raise ValueError("The Anima T5 stream allows up to 511 prompt tokens before EOS.")
        eos = (t5.eos_token_id, 1.0, len(segments)) if return_word_ids else (t5.eos_token_id, 1.0)
        result["t5xxl"] = [pairs + [eos]]
        return result


def _vocab_hooks(table):
    original_ids = ContextVar("rs_anima_korean_ids", default=None)

    def clamp_ids(_, args):
        ids = args[0]
        mask = ids >= T5_SIZE
        if mask.any():
            original_ids.set((ids, mask))
            return (ids.masked_fill(mask, 2), *args[1:])
        original_ids.set(None)

    def insert_rows(_, args, output):
        entry = original_ids.get()
        original_ids.set(None)
        if entry is not None:
            ids, mask = entry
            rows = table[ids[mask].cpu().long() - T5_SIZE]
            output[mask] = rows.to(output)
            return output

    return clamp_ids, insert_rows


def _patch_vocab(model, table):
    path = "diffusion_model.llm_adapter.embed"
    for attribute, hook in zip(("_forward_pre_hooks", "_forward_hooks"), _vocab_hooks(table)):
        key = f"{path}.{attribute}"
        hooks = OrderedDict(model.get_model_object(key))
        hooks[id(hook)] = hook
        model.add_object_patch(key, hooks)


class RSAnimaKoreanTextLoader:
    CATEGORY = "RS/Anima"
    RETURN_TYPES = ("MODEL", "CLIP", "RS_KOREAN_WEIGHTS")
    RETURN_NAMES = ("model", "clip", "glyph_weights")
    FUNCTION = "load"
    DESCRIPTION = ("Load the Korean LoRA and learned T5 embeddings from one Anima pack. "
                   "The bundled beta selection downloads on first use. "
                   "Connect both MODEL and CLIP to the generation workflow.")

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {
            "model": ("MODEL",),
            "clip": ("CLIP",),
            "pack": (pack_names(),),
            "lora_strength": ("FLOAT", {"default": 1.0, "min": 0, "max": 2.0, "step": 0.05}),
        }}

    def load(self, model, clip, pack, lora_strength):
        table, chars, patches, glyph = _read_pack(model, clip, pack, lora_strength, read_glyph=True)
        model = model.clone()
        if patches and len(model.add_patches(patches, lora_strength)) != len(patches):
            raise ValueError("The connected Anima model could not apply every Korean LoRA layer.")
        _patch_vocab(model, table)
        return model, _patch_tokenizer(clip, chars), glyph


def _patch_tokenizer(clip, chars):
    clip = clip.clone()
    clip.tokenizer = _KoreanTokenizer(clip.tokenizer, chars)
    return clip


def _read_pack(model, clip, pack, lora_strength, *, read_glyph=False):
    import comfy.lora
    from safetensors import safe_open

    try:
        from comfy.ldm.anima.model import Anima
        from comfy.text_encoders.anima import AnimaTokenizer
    except ImportError as exc:
        raise ValueError("Update ComfyUI to a version with native Anima support to use this loader.") from exc

    diffusion_model = model.get_model_object("diffusion_model")
    if not isinstance(diffusion_model, Anima) or not isinstance(clip.tokenizer, AnimaTokenizer):
        raise ValueError("Connect an Anima diffusion model and its Qwen3-0.6B text encoder.")
    if Path(pack).suffix.lower() != ".safetensors":
        raise ValueError("Select an Anima Korean text pack in .safetensors format.")

    paths = _pack_paths()
    if pack == BETA_PACK:
        if len(diffusion_model.blocks) != 28:
            raise ValueError("The Anima Korean text beta pack requires a 28-block Anima 2B model.")
        path = ensure_model_file(PACKS, BETA_PACK, BETA_PACK_URL, BETA_PACK_SIZE, BETA_PACK_SHA256)
    else:
        path = paths.get_full_path_or_raise(PACKS, pack)
    with safe_open(path, framework="pt") as source:
        keys = source.keys()
        metadata = (source.metadata() or {}).get("rs_anima_korean_vocab")
        if not metadata or "vocab.ext_embed" not in keys:
            raise ValueError("The selected file lacks the learned Anima Korean vocabulary.")
        mapping = json.loads(metadata)
        if not isinstance(mapping, dict):
            raise ValueError("The Anima Korean vocabulary metadata must be an object.")
        table = source.get_tensor("vocab.ext_embed")
        glyph = {k.removeprefix("glyph."): source.get_tensor(k) for k in keys if k.startswith("glyph.")} if read_glyph else {}
        lora = {k: source.get_tensor(k) for k in keys if k.startswith("lora_unet_")} if lora_strength else {}
    chars = mapping.get("char")
    if (table.shape != (mapping.get("rows"), 1024) or not mapping.get("literal_hangul")
            or not isinstance(chars, dict) or not chars
            or any(type(row) is not int or not 0 <= row < table.shape[0] for row in chars.values())):
        raise ValueError("The pack must contain valid learned Anima T5 rows for Korean characters.")
    patches = {}
    if lora_strength:
        patches = comfy.lora.load_lora(lora, comfy.lora.model_lora_keys_unet(model.model, {}))
        expected = sum(k.endswith(".lora_down.weight") for k in lora)
        if len(patches) != expected or expected == 0:
            raise ValueError(f"The loaded Anima supports {len(patches)} of {expected} packed Korean LoRA layers.")
    return table, chars, patches, glyph


class KoreanTextRegions:
    """Prepare Korean captions and denoiser deltas for the active text boxes."""

    def __init__(self, model, clip, pack, strength, slots):
        from .lora_bypass import _prepare_factor_bypass

        if isinstance(clip.tokenizer, _KoreanTokenizer):
            raise ValueError("Connect Anima MODEL and CLIP directly to the sampler for Korean BBox mode.")
        table, chars, patches, _ = _read_pack(model, clip, pack, strength)
        self.slots = frozenset(slots)
        self.clip = _patch_tokenizer(clip, chars)
        self.table = table
        self.strength = strength
        self.image_weights = {key: patch for key, patch in patches.items()
                              if not (key[0] if isinstance(key, tuple) else key).startswith("diffusion_model.llm_adapter.")}
        text_weights = {key: patch for key, patch in patches.items() if key not in self.image_weights}
        self.text_adapter = None
        if text_weights:
            self.text_adapter, reason = _prepare_factor_bypass(model, text_weights, allow_text_adapter=True)
            if self.text_adapter is None:
                raise ValueError(f"Korean BBox mode cannot apply the pack's text adapter: {reason}.")

    @contextmanager
    def text_context(self, diffusion_model):
        if self.text_adapter is None:
            adapter = nullcontext()
        else:
            adapter = self.text_adapter.installed(diffusion_model, self.strength)
        before, after = _vocab_hooks(self.table)
        embedding = diffusion_model.llm_adapter.embed
        with embedding.register_forward_pre_hook(before), embedding.register_forward_hook(after):
            try:
                with adapter:
                    yield
            finally:
                if self.text_adapter is not None:
                    self.text_adapter.release()
