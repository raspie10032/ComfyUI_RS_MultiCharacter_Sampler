# Anima reference frame adapter (experimental)

This is a separate Anima-only reference-frame method; the existing numbered image-reference node is unchanged. Adapted from [ElectronGirl/ComfyUI-Anima-Ref-Adapter](https://github.com/ElectronGirl/ComfyUI-Anima-Ref-Adapter) at `af9a438d` under Apache-2.0. See `ANIMA-REF-ADAPTER-LICENSE` for the preserved license.

## Connect

Download the author's Anima reference-frame adapter weights separately into `ComfyUI/models/loras`. Follow the weight download and licensing information in the upstream README. Do not select an ordinary style or character LoRA as the adapter.

`Load Diffusion Model → RS Anima Reference Adapter (Experimental) → RS MultiCharacter Sampler`

For a **global reference**, connect `Load Image` to the adapter's optional IMAGE. For **numbered character references**, leave that IMAGE disconnected, then connect each image to `RS Anima Character Reference` and match its number to Prompt/Position, as with per-character LoRAs. Connect their BUILDING_PIPE through Finalize to the sampler. Building-node order does not matter; the last enabled value for a repeated number wins. Do not combine the global image with numbered references.

The sampler fits references inside a reference canvas and VAE-encodes each distinct image once per generation. Default reference scale 1 uses the target size. Scale 0.8 uses 80% of each side, rounded to 16 pixels, without changing target resolution. It packs the smaller reference token grid with the target, rather than resizing it back up. Reference rotary coordinates preserve the target spatial extent. This experimental change can affect identity, fine details and composition. The model must be Anima. Native KSampler, progressive sampler and the detailer are deliberately rejected by this experiment, instead of silently ignoring the reference. Character masks/prompts still control target regions. A global reference affects the **whole image**, including other characters.

Numbered references use separate source-conditioned predictions and blend their results in the matching point/box/mask regions, like precision LoRA application. A source branch cannot read the other reference image. Uncovered pixels use the ordinary prediction; overlapping regions blend their active references with normalized weights. This prevents shared reference hidden states but does **not** guarantee perfect final-image identity isolation: image denoising still couples adjacent regions. Keep one character per reference image. OFF/strength 0 removes only that numbered reference; mask and prompt remain. More references require more predictions, so this can be significantly slower. Fidelity and style preservation remain experimental.

- **strength**: adapter multiplier, default 1. Set 0 to bypass all reference processing.
- **reference_guidance**: reference influence in the author's guidance formula, default 4.5. With one global image, 1 omits the extra unreferenced prediction; this saves compute **and changes the image**. Numbered references retain the ordinary background prediction. Zero bypasses reference processing.
- **correction**: APG (default), rescale or none, following the upstream guidance math.
- **reference_scale** (default 1): reference side-length multiplier, 0.5–1.0. For example, target 1024×768 with scale 0.8 uses an 816×608 reference canvas: 1,938 reference tokens versus 3,072 at full size. This reduces reference tokens by 36.9%, not the whole generation cost. Global and independent numbered references support it.
- **cache_text_kv** (default OFF): reuse identical text projections inside one generation, up to 256 MiB. Retain a bounded subset instead of cycling through evictions. Automatically disabled with per-character LoRAs. It cannot cache the changing reference-image self-attention features. Initial measurements found negligible speed improvement for up to 256 MiB extra memory, so this optional cache defaults OFF.

Adapters, temporary hooks and GPU caches are scoped to a generation and released even after cancellation/error. Per-character LoRA overrides are suspended during the unreferenced guidance prediction and restored afterwards. Unsupported combinations with the older per-character image-reference method are rejected.

Generation metadata records adapter settings and numbered reference fingerprints for inspection. It does not embed reference pixels or automatically rebuild the reference connection. Keep the original images and save a workflow with the normal ComfyUI image save node if you need that connection. Metadata-only reload requires reconnecting these source images.

## Validation limits

The initial native CPU tests cover RoPE offsets, cached/uncached equality, target/reference token routing, restoration and bounded cache. GPU results, timings and limitations are recorded in the external experiment directory. Test success does not establish reference fidelity across arbitrary images, quantized checkpoints or LoRAs.
