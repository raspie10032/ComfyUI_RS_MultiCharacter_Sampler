# 1.0.9 Hangeul

2026-10-30. Experimental trained 3D pose guidance for Krea 2 Turbo and MOSS,
alongside the existing numbered character prompts and regions.

- **RS 3D Pose Adapter (Experimental)** receives MODEL, matching VAE and
  `scene_json` from RS 3D Pose Masks. Its MODEL feeds the standard RS sampler;
  the separate building pipe still supplies character ownership through Finalize.
- Krea 2 Turbo uses a trained OpenPose LoRA and cached pose-reference K/V.
  MOSS uses trained person-color/depth control and a replacement input embedder.
  Adapters download on first use, with progress and revision/checksum verification.
  Zero strength or an empty application interval downloads no weights.
- New sampler layout default `auto` chooses `moss_native` with active MOSS pose
  control, otherwise `regional`. Explicit saved choices remain unchanged.
  MOSS native converts masks to enclosing boxes while retaining learned pose
  maps; RS regional boundary controls do not apply in native mode.
- Existing Anima 2B LLLite setup and original 3D output slot indices are preserved.

## Start here

[한국어 가이드](pose3d-krea-moss-guide.ko.md) ·
[English setup](pose3d.md#krea2-turbo-and-moss-pose-adapters-experimental) ·
[Genshin workflow PNGs](../examples/pose3d/README.md#genshin-impact-workflow-pngs)

Restart ComfyUI and refresh its browser after updating. Select matching base
models/encoders/VAEs; install `requirements-reference.txt` with ComfyUI's Python
if optional dependencies are missing. First-use adapter downloads are about
229 MB (Krea) and 313 MB (MOSS); base models are not included.

## Evidence and limitations

The [36-image audit](pose3d-genshin-diverse-validation.md) uses Jean and Eula,
two models, six poses and two ON seeds, with one matched OFF/ON seed per scene.
No pose-action text or style/character LoRA is used; trained control LoRAs are
part of the adapters. Raised arms and sitting respond in both models. Exact
contact, orientation and joints remain unreliable; one MOSS side-view case swaps
character/pose roles. Prior extra-person failures with MOSS style LoRAs remain
unresolved. Execution success is not a pose-quality success rate.

Tested models: Krea 2 Turbo FP8 scaled and MOSS SFT BF16, current native core
`5cc4b87`. Other checkpoints, quantized pose patches and character-LoRA
combinations require independent tests. Image references, progressive sampling
and other attention replacements are restricted on this experimental path.
MOSS map start/end controls the conditioning interval; its control LoRA and
expanded input embedder remain installed throughout sampling.

Sources and redistribution terms are in [third-party notices](../THIRD_PARTY_NOTICES.md).
The full regression and installed-runtime release checks are recorded in the
[release verification report](pose3d-1.0.9-release-validation.md).

**한국어:** Krea 2는 리저널＋전용 포즈 어댑터, MOSS는 네이티브 JSON＋색상·깊이
어댑터를 우선 사용합니다. 마스크만 전달하는 것과 학습된 포즈 유도는 다른 경로이며,
캐릭터 영역 파이프와 어댑터 MODEL을 모두 연결해야 합니다. 큰 자세를 유도하는
시험 기능으로 제공하며 정확한 손·접촉이나 캐릭터 배정을 보장하지 않습니다.
