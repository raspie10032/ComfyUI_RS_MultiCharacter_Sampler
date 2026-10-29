# Legacy xFormers compatibility

2026-10-29, version 1.0.7. An isolated environment was used; the resident
ComfyUI's PyTorch and attention packages were not replaced.

## Tested stack and scope

- Python 3.12, PyTorch 2.5.1 with CUDA 12.4, xFormers 0.0.28.post3.
- ComfyUI v0.3.76, physical RTX 4070 Ti SUPER, Linux.
- Four GPU tests passed using actual xFormers kernels, with FP16 and BF16.
- Masked/unmasked attention, shaped/flattened inputs and outputs, and
  non-aligned token counts were compared against PyTorch SDPA.
- Native CrossAttention projection/output and RS regional cross-attention
  were compared against reference calculations. Krea2/MOSS joint-routing
  calls used real xFormers, including unequal caption lengths and CFG rows.
- Comparisons require finite output and use FP16 rtol/atol 0.003 and BF16
  rtol/atol 0.03. These are numerical compatibility checks, not visual scores.

Anima and SDXL regional attention use PyTorch SDPA directly; some other model
paths delegate to ComfyUI's selected attention backend. Passing these tests
does not claim that all operations use xFormers, or establish full-generation
quality on every model, Windows GPU compatibility, or support for every old
xFormers version. The recent Anima pose/reference functions need a ComfyUI
version that actually includes their model classes; v0.3.76 predates Anima.

## Reproduce

Run separately from the CPU integration suite, which sets CPU mode:

```bash
RS_MC_TEST_XFORMERS=1 RS_MC_TEST_COMFYUI=/path/to/ComfyUI-v0.3.76 \
  python -m unittest discover -s tests -p test_xformers.py -v
python -m xformers.info
```

Use a separate environment with a matching PyTorch/xFormers wheel pair. An
explicit GPU test fails if the requested backend is unavailable; ordinary CPU
CI skips these four optional tests.

## Additional Windows correction

Windows CPU CI exposed a reference-weight verification cache collision: a
quick same-size overwrite could retain the cached modification/creation times.
On Windows the adapter resolver now rehashes the file on reuse. A deterministic
regression test freezes the old stat information while changing the bytes and
requires the resolver to reject the changed file without deleting it.

Full CUDA logs and backend inventory are included with the optional 1.0.7
validation Release assets. [Compatibility scope](compatibility.md).
