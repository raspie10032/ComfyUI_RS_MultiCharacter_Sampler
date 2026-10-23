# SPDX-License-Identifier: GPL-3.0-only
"""Optional bridge to ComfyUI-GGUF's live layer types, without importing nodes.

The extension can be installed under different package names. Resolve its actual
GGMLLayer base instead of importing a fixed custom_nodes path or accepting every
Tensor subclass. Its own cast handles dequantization and incoming global LoRAs.
"""
import sys


def is_gguf_layer(module):
    for base in type(module).__mro__:
        if base.__name__ != "GGMLLayer":
            continue
        namespace = sys.modules.get(base.__module__)
        tensor_type = getattr(namespace, "GGMLTensor", None)
        if (getattr(namespace, "GGMLLayer", None) is base
                and isinstance(tensor_type, type)
                and isinstance(getattr(module, "weight", None), tensor_type)
                and callable(getattr(module, "cast_bias_weight", None))):
            return True
    return False
