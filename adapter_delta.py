# SPDX-License-Identifier: GPL-3.0-only
"""Execution-scoped adapters using the installed core's weight algebra.

Only the current layer is expanded, in FP32, then discarded. Packed checkpoint
storage and scale tensors are never replaced. The original quantized forward
is preserved and receives an affine output correction, (W_patched - W) x.
"""
from contextlib import contextmanager, nullcontext
from functools import partial
import logging
import threading

import torch
import torch.nn.functional as F

from .lora_bypass import BypassLora, linear_layer


def layer_kind(module):
    if linear_layer(module):
        return "linear"
    for kind, cls in (("conv1d", torch.nn.Conv1d), ("conv2d", torch.nn.Conv2d),
                      ("conv3d", torch.nn.Conv3d), ("layer_norm", torch.nn.LayerNorm),
                      ("group_norm", torch.nn.GroupNorm), ("rms_norm", torch.nn.RMSNorm)):
        if isinstance(module, cls):
            return kind
    return None


def describe_patch(key, patch):
    from comfy.weight_adapter.base import WeightAdapterBase
    kind = type(patch).__name__
    if isinstance(patch, WeightAdapterBase):
        kind += f"/{patch.name}"
    elif isinstance(patch, tuple) and patch and isinstance(patch[0], str):
        kind += f"/{patch[0]}"
    return f"key={key!r}, adapter={kind}, partial={isinstance(key, tuple)}"


def prepare_weight_delta(model, weights):
    from comfy.weight_adapter import adapters
    from comfy.weight_adapter.base import WeightAdapterBase
    from comfy.hooks import TransformerOptionsHook
    from .adapter_formats import ia3_adapter_type

    supported_adapters = (*adapters, ia3_adapter_type())

    entries = {}
    for raw_key, patch in weights.items():
        detail = describe_patch(raw_key, patch)
        def reject(reason):
            return None, f"{reason}: {detail}"
        key, offset = raw_key, None
        if isinstance(key, tuple):
            if len(key) not in (2, 3) or (len(key) == 3 and key[2] is not None):
                return reject("patch_function")
            key, offset = key[:2]
            if (not isinstance(offset, tuple) or len(offset) != 3
                    or not all(type(v) is int for v in offset)
                    or offset[0] < 0 or offset[1] < 0 or offset[2] <= 0):
                return reject("patch_offset")
        if not isinstance(key, str) or not key.startswith("diffusion_model."):
            return reject("non_diffusion_layer")
        if "llm_adapter" in key:
            return reject("text_adapter")
        path, _, parameter = key.rpartition(".")
        if parameter not in ("weight", "bias"):
            return reject("patch_parameter")
        try:
            module = model.model.get_submodule(path)
        except AttributeError:
            return reject("missing_layer")
        if layer_kind(module) is None or getattr(module, "comfy_force_forward", False):
            return reject("custom_or_unsupported_layer")
        tensor = getattr(module, parameter, None)
        if not isinstance(tensor, torch.Tensor):
            return reject("missing_parameter")
        from comfy.quant_ops import QuantizedTensor
        if type(tensor) not in (torch.Tensor, torch.nn.Parameter) and not isinstance(tensor, QuantizedTensor):
            return reject("custom_tensor")
        shape = list(tensor.shape)
        if offset is not None:
            dim, start, length = offset
            if dim >= len(shape) or start + length > shape[dim]:
                return reject("patch_offset")
            shape[dim] = length
        if isinstance(patch, WeightAdapterBase) and type(patch) in supported_adapters:
            new_shape = patch.calculate_shape(key)
            if new_shape is not None and tuple(new_shape) != tuple(shape):
                return reject("shape_changing_adapter")
        elif (isinstance(patch, tuple) and len(patch) == 2 and patch[0] in ("diff", "set")
              and isinstance(patch[1], (tuple, list)) and patch[1]
              and isinstance(patch[1][0], torch.Tensor)):
            if tuple(patch[1][0].shape) != tuple(shape):
                return reject("patch_shape")
        else:
            return reject("patch_type")
        entry = entries.setdefault(path[len("diffusion_model."):], {"module": module, "patches": {}})
        entry["patches"].setdefault(parameter, []).append((key, patch, offset))
    return WeightDeltaPlan(entries, TransformerOptionsHook), "native_weight_delta"


@contextmanager
def strict_core_errors(key):
    """Core adapters sometimes log shape errors and return unchanged weights."""
    owner = threading.get_ident()
    class Capture(logging.Handler):
        def emit(self, record):
            if record.thread == owner and record.levelno >= logging.WARNING:
                messages.append(record.getMessage())
    messages = []
    handler = Capture()
    root = logging.getLogger()
    root.addHandler(handler)
    try:
        yield
        if messages:
            raise ValueError(f"Regional adapter calculation failed for {key!r}: {'; '.join(messages)}")
    finally:
        root.removeHandler(handler)


def float_weight(tensor, device):
    from comfy.quant_ops import QuantizedTensor
    value = tensor.to(device=device)
    if isinstance(value, QuantizedTensor):
        value = value.dequantize()
    return value.to(dtype=torch.float32)


def parameter_delta(tensor, patches, strength, device):
    from comfy.lora import calculate_weight
    from comfy.weight_adapter import LoKrAdapter
    original = float_weight(tensor, device)
    key = patches[0][0]
    native = []
    for _, patch, offset in patches:
        # Native CP-LoKr's einsum may produce a strided tensor that torch.kron
        # cannot view. Materialize the same two factors contiguously for this
        # layer only; keep alpha/rank and DoRA semantics in the native adapter.
        if type(patch) is LoKrAdapter and patch.weights[1] is None and patch.weights[7] is not None:
            w1, _, alpha, w1a, w1b, w2a, w2b, t2, dora = patch.weights
            cast = lambda value: value.to(device=device, dtype=torch.float32)
            first = cast(w1) if w1 is not None else cast(w1a) @ cast(w1b)
            second = torch.einsum('ijkl,jr,ip->prkl', cast(t2), cast(w2b), cast(w2a)).contiguous()
            # The core's final reconstruction rank is w2b for CP-LoKr.
            scale = alpha / w2b.shape[0] if alpha is not None else 1.
            patch = LoKrAdapter(patch.loaded_keys, (first * scale, second, None, None, None, None, None, None, dora))
        native.append((strength, patch, 1., offset, None))
    with strict_core_errors(key):
        merged = calculate_weight(native, original.clone(), key, intermediate_dtype=torch.float32)
    if merged.shape != original.shape:
        raise ValueError(f"Regional adapter changed layer shape: {key!r}.")
    merged.sub_(original)
    return merged


def delta_forward(original, module, patches, strength, x, *args, **kwargs):
    base = original(x, *args, **kwargs)
    # Use native casts for dynamic VRAM/offloading and incoming global patches.
    # Reading module.weight directly can read an unmaterialized/offloaded tensor.
    if hasattr(module, "comfy_cast_weights"):
        from comfy.ops import CastBiasWeightContext
        context = CastBiasWeightContext(module, x, dtype=torch.float32, bias_dtype=torch.float32, offloadable=True)
    else:
        context = nullcontext((module.weight, getattr(module, "bias", None)))
    with context as (base_weight, base_bias):
        weight = (parameter_delta(base_weight, patches["weight"], strength, x.device)
                  if "weight" in patches else None)
        bias = (parameter_delta(base_bias, patches["bias"], strength, x.device)
                if "bias" in patches else None)
    kind = layer_kind(module)
    # Compute the correction in the input dtype, preserving the native base path.
    weight = weight.to(dtype=x.dtype) if weight is not None else None
    bias = bias.to(dtype=x.dtype) if bias is not None else None
    if weight is None:
        if kind in ("linear", "layer_norm", "rms_norm"):
            return base + bias
        shape = [1] * base.ndim
        shape[1] = bias.numel()
        return base + bias.reshape(shape)
    if kind == "linear":
        delta = F.linear(x, weight, bias)
    elif kind.startswith("conv"):
        # _conv_forward handles nonzero padding modes as well as stride/groups.
        delta = module._conv_forward(x, weight, bias, *args, **kwargs)
    elif kind == "layer_norm":
        delta = F.layer_norm(x, module.normalized_shape, weight, bias, module.eps)
    elif kind == "group_norm":
        delta = F.group_norm(x, module.num_groups, weight, bias, module.eps)
    elif kind == "rms_norm":
        delta = F.rms_norm(x, module.normalized_shape, weight, module.eps)
        if bias is not None:
            delta = delta + bias
    return base + delta.to(dtype=base.dtype)


class WeightDeltaPlan(BypassLora):
    supports_shared = False

    def __init__(self, entries, options_type):
        self.entries, self.options_type = entries, options_type
        self.layer_paths = list(entries)
        self.forward_calls = 0

    def forward(self, executor, *args, strength, **kwargs):
        if strength == 0:
            return executor(*args, **kwargs)
        runtime = executor.class_obj
        installed = []
        try:
            for path, entry in self.entries.items():
                module = runtime.get_submodule(path)
                source = entry["module"]
                if (layer_kind(module) != layer_kind(source)
                        or getattr(module, "comfy_force_forward", False)
                        or any(tuple(getattr(module, p).shape) != tuple(getattr(source, p).shape)
                               for p in entry["patches"])):
                    raise RuntimeError(f"Regional adapter: incompatible runtime layer {path!r}.")
                state = {k: module.__dict__[k] for k in ("forward", "comfy_force_forward") if k in module.__dict__}
                installed.append((module, state))
                module.forward = partial(delta_forward, module.forward, module, entry["patches"], strength)
                module.comfy_force_forward = True
            self.forward_calls += 1
            return executor(*args, **kwargs)
        finally:
            for module, state in reversed(installed):
                for key in ("forward", "comfy_force_forward"):
                    if key in state:
                        setattr(module, key, state[key])
                    else:
                        module.__dict__.pop(key, None)

    def release(self):
        # Deltas are local to each layer call. No expanded weights are retained.
        pass

    @property
    def factor_bytes(self):
        def size(value):
            if isinstance(value, torch.Tensor):
                return value.numel() * value.element_size()
            if isinstance(value, (tuple, list)):
                return sum(size(v) for v in value)
            return size(value.weights) if hasattr(value, "weights") else 0
        return sum(size(patch) for entry in self.entries.values()
                   for patches in entry["patches"].values() for _, patch, _ in patches)
