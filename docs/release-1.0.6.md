# 1.0.6 Hangeul

Released source update dated 2026-10-27.

- Add **RS Progressive Resolution Sampler**, a separate T2I node using the existing MODEL, CLIP, VAE and finalized character pipe. The existing RS MultiCharacter Sampler remains available.
- Choose final width/height, start scale **0.5–1.0** (default **0.67**), sampler, scheduler, total steps, CFG and seed. Middle sizes and expansion steps are calculated automatically. No additional model or dependency is required.
- Expand the denoised latent with Lanczos and apply the model's native noise scaling. Recalculate regional masks at each size; below final resolution keep exclusive character-region separation at least 0.99. Preserve the existing overlap policy.
- Retain character LoRA Normal/Precision modes, masks, text regions, camera controls and outputs. Store the effective stage plan in PNG/WebP generation metadata and support restoring image settings.
- Add localized UI/help in English, Korean, Japanese and Simplified/Traditional Chinese, plus a workflow embedded in an actual generated example PNG.

## Use and limits

See the [progressive resolution guide](progressive-resolution.md) and [workflow PNG](../examples/progressive/two-characters-anima.png). For 1152×1728, 30 steps and scale 0.67, the usual plan is 768×1152 for 8 steps, 960×1440 for 8 steps, then 1152×1728 for 14 steps. Total steps are shared across the stages.

This trades some detail for shorter sampling at larger resolutions. Lower start scales can lose detail, alter composition or merge people; quality and speed gains are not guaranteed. Scale 1.0 uses ordinary fixed-resolution sampling. SD1.5 is supported for execution compatibility only, with no recommendation for high-resolution quality. Native MOSS keeps its own JSON layout behavior. Stateful solvers restart their history at expansion. Body-part guidance combined with text regions retains the existing unsupported-combination error.

## Validation

The development candidate was verified in an isolated ComfyUI on RTX 4070 Ti SUPER: **34 matched quality images** across Anima, SDXL, SD1.5, Krea 2, MOSS attention/native and FLUX.1/2/3. Additional short executions covered installed distilled/Dev/Schnell/SFT variants. These are limited comparisons, not every checkpoint or sampler/scheduler combination. A warmed scale-1.0 comparison was pixel-identical to the ordinary sampler in all eight branches. Actual generation also covered regional LoRAs, masks/text, body-part guidance without text, metadata restoration and WebP autosave.

The development regression run passed **275 Python tests**, with **8 conditional skips**, and all **15 JavaScript suites**. Seven skips require the optional GGUF fixture; one applies only to older ComfyUI cores. The [feature guide](progressive-resolution.md) records model-specific quality limits, representative solver checks and references. The prior fixed-stage Lanczos/SPEED comparison is design evidence, not an independent speed benchmark of this final node.

## References

[SPEED ComfyUI implementation](https://github.com/ruwwww/ComfyUI-SPEED) · [research implementation](https://github.com/howardhx/speed) · [research description](https://howardxiao.ca/speed/). RS compared frequency-preserving expansion, noise/time correction and expansion timing after its earlier Lanczos trials. The released node uses Lanczos; it does not contain SPEED's DCT expansion or frequency-derived automatic timing. See [third-party notices](../THIRD_PARTY_NOTICES.md).

**한국어:** 큰 이미지를 조금 더 빠르게 샘플링하는 대신 디테일을 일부 희생하는 별도 노드입니다. 시작 배율은 0.5~1.0이며 낮을수록 디테일 손실·구도 변화가 커질 수 있어 품질을 보장하지 못합니다. 기존 멀티캐릭터 샘플러와 캐릭터 파이프 기능은 그대로 사용할 수 있습니다. 업데이트 후 ComfyUI를 재시작하고 브라우저를 새로고침하세요.
