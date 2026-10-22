# SPDX-License-Identifier: GPL-3.0-only
"""Additional static LyCORIS files not parsed by the native core loader."""
from functools import lru_cache

import torch


@lru_cache(maxsize=1)
def ia3_adapter_type():
    from comfy.weight_adapter.base import WeightAdapterBase

    class IA3Adapter(WeightAdapterBase):
        name = "ia3"

        def __init__(self, loaded_keys, weights):
            self.loaded_keys, self.weights = loaded_keys, weights

        def calculate_weight(self, weight, key, strength, strength_model, offset,
                             function, intermediate_dtype=torch.float32, original_weight=None):
            # LyCORIS merged-weight semantics: ΔW = W * channel_scale.
            # Input scales columns; output scales rows. Bias is unchanged.
            vector, on_input = self.weights
            axis = 1 if bool(on_input.item()) else 0
            if vector.numel() != weight.shape[axis]:
                raise ValueError(f"IA3 channel count mismatch for {key!r}.")
            shape = [1] * weight.ndim
            shape[axis] = vector.numel()
            delta = weight * vector.to(device=weight.device, dtype=intermediate_dtype).reshape(shape)
            return weight.add_(function(strength * delta))

    return IA3Adapter


def load_additional_adapters(weights, mapping):
    """Return IA3 patches; do not register or change global core adapters."""
    result = {}
    for marker, on_input in weights.items():
        if not marker.endswith('.on_input'):
            continue
        prefix = marker[:-len('.on_input')]
        if prefix not in mapping:
            continue
        vector = weights.get(prefix + '.weight')
        if (not isinstance(on_input, torch.Tensor) or on_input.numel() != 1
                or on_input.item() not in (0, 1) or not isinstance(vector, torch.Tensor)
                or not vector.is_floating_point() or vector.numel() == 0):
            raise ValueError(f"Malformed IA3 adapter at {prefix!r}.")
        cls = ia3_adapter_type()
        result[mapping[prefix]] = cls({marker, prefix+'.weight'}, (vector, on_input))
    return result


def validate_file_format(weights):
    # Reject known timestep-dependent files before native partial parsing can
    # silently discard their rank mask or initialization residual information.
    marker = next((key for key in weights if key.endswith('.lambda_layer')), None)
    if marker is not None:
        raise ValueError(f"T-LoRA is not supported regionally: {marker!r}. Timestep rank masks and initialization residuals require a dedicated loader. / T-LoRA는 시간별 rank 마스크와 초기 잔차를 처리하는 전용 로더가 필요합니다.")
