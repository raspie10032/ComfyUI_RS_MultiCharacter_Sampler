# GGUF compatibility

Use the MODEL output from [ComfyUI-GGUF](https://github.com/city96/ComfyUI-GGUF)
with the existing RS sampler and detailer. Install that extension separately,
including its requirements, and put the GGUF diffusion model in its supported
model folder. Keep the model family's matching CLIP and VAE. This extension
does not download GGUF models or replace a loader.

## Character LoRAs

Connect **Unet Loader (GGUF) → RS MultiCharacter Sampler**, with the matching
CLIP, VAE and finalized character pipe. Select character LoRAs as usual. A
global LoRA can also be attached before the sampler. The same MODEL can be
used by **RS MultiCharacter Detailer**.

Plain linear LoRAs run the loader's original packed forward, then add the
character's low-rank calculation. More complex supported adapters read the
loader's materialized layer through its native cast operation. This includes
any incoming global patches and avoids reading packed bytes as ordinary
floating-point weights. Complex adapters can require larger temporary tensors.

GGUF weights stay in their loader's packed representation. The loader still
dequantizes individual layers during execution; this change does not eliminate
that cost or promise lower latency. Shared Normal mode retains its existing
model restrictions: FLUX automatically uses Precision. The selected/effective
mode and fallback reason remain in metadata.

Points, boxes, masks and prompt controls use the existing model family's
regional routing. Other execution engines, including Nunchaku, and unrelated
custom tensor subclasses remain unverified and are not enabled by this bridge.
GGUF CLIP-specific adapters, multi-GPU clones and unsupported shape changes
are not covered by this change. Installing this bridge does not establish
support for every model architecture or quantization type.

## Validation

The optional CPU tests use real ComfyUI-GGUF operations, rather than a fake
quantized tensor. They cover Q4_0, Q8_0 and F16, incoming global LoRA, signed
strengths, exact zero strength, partial output slices, DoRA/diff weight deltas,
runtime clones and exception cleanup. Original packed bytes and dispatch are
checked after execution. Unrelated custom tensor types are still rejected.

```bash
RS_MC_TEST_COMFYUI=/path/to/ComfyUI RS_MC_TEST_GGUF=/path/to/ComfyUI-GGUF \
  python -m unittest discover -s tests -p 'test_gguf_lora.py' -v
```

CI installs `gguf==0.19.0` and checks out ComfyUI-GGUF at
`6ea2651e7df66d7585f6ffee804b20e92fb38b8a` for these optional tests. Normal
installation has no mandatory GGUF dependency.

### GPU generation: 2026-10-23

Tested FLUX.1 Dev `flux1-dev-Q4_K_S.gguf` on an RTX 5060 Ti 16 GB,
768 × 512, two adult characters, seed 346751, 20 steps, Euler ancestral /
SGM uniform, CFG 1.0 and FLUX guidance 3.5. Matching CLIP/VAE came from the
existing FLUX.1 FP8 checkpoint. The installed ComfyUI-GGUF revision was the
revision pinned above. The local character adapter was
`LaraCroft_flux_lora_v1_000001800.safetensors`.

Passed generation cases: no character adapter, exact zero strength, left slot,
right slot, Normal-to-Precision fallback, mask regions, incoming global adapter,
incoming global plus character adapter, and adapter-free generation after use.
The zero-strength and after-use images exactly matched the initial GGUF image;
Normal's fallback image exactly matched Precision. Two representative packed
Q4_K layers retained identical byte hashes and forward dispatch in every run.
This is a representative live audit, not a hash of every model parameter.

The detailer additionally detected and matched two faces and actually corrected
both (2 edited, 0 skipped), including the character adapter on one region.
It used the existing face segmentation model, WD ViT v3, denoise 0.25 and
384-pixel guide size. Its validation server initially lacked the detector
extension; the completed run followed installing that extension in the isolated
server. A successful generation was required, rather than counting detection
or a pass-through as a detailer result.

Sampler runs took approximately 33 seconds without adapters, 53 seconds with
a character adapter, and 71–73 seconds with global patching. Device memory
included other processes; peak allocated PyTorch memory was about 7.15 GiB
for the character-adapter case. FP8 baseline images were also generated, but
loading and residency differed, so these measurements do not establish a
controlled FP8/GGUF speed or memory comparison. Image quality and complete
character isolation remain model-dependent.

Local evidence bundle: `RS_MC_gguf_validation_20261023` contains each submitted
API graph, prompt receipt, history, packed-layer audit, output image, numerical
test log, UI log and an installation backup. These large artifacts are not
bundled with the extension. GPU evidence here covers this FLUX.1 Q4_K_S model;
Q4_0/Q8_0/F16 CPU tests do not establish live support for every model family,
GGUF CLIP adapter or another quantized execution engine.
