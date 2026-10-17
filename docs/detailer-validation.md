# Local multi-character detailer validation — 2026-10-17

The implementation adds `RSMultiCharacterDetailer`, `RSMultiCharacterDetectionLoader` and `RSMultiCharacterTaggerLoader` to the independent Anima extension. It builds on the sampler recommendation commit `f091f09`. The RS NAI extension is not loaded by the isolated test server, and no NovelAI requests or Anlas are used.

## What was implemented

- IMAGE and the existing `character_pipe` can come directly from the sampler or the image loader. MODEL/CLIP/VAE, including LoRA, are supplied by the caller.
- Each masked crop uses common text plus one original character prompt. Tagger scores select a character; inferred tags never become prompt text. Local crop sampling uses ComfyUI's sampler, without applying full-frame regional attention to the crop.
- SEGM has priority. BBOX and SAM selections are skipped with SEGM; BBOX alone and BBOX + SAM are optional alternatives. Catalog models and files in the existing Impact folders appear in the loader.
- Hole/notch repair and dilation produce disjoint masks. Every crop starts from the original image. Feathering remains inside the correction mask.
- PNG/WebP autosave retains original captions/settings and appends a separate detail history. No workflow is embedded by autosave. The output pipe includes the new history.
- The basic detailer UI shows denoise, seed and autosave. Sampling/crop/matching/save controls are folded under advanced settings. Korean and Japanese node definitions and all three READMEs were added/updated.

## Actual Anima execution

A separate ComfyUI server on port 8197 loaded this extension, ComfyUI core, Impact Pack and Impact Subpack. Tests used Anima Base v1.0, the Qwen text encoder and image VAE, Euler ancestral / SGM uniform, 20 detail steps, CFG 4 and denoise 0.25. Default SEGM was `Anzhc Face seg 640 v2 y8n.pt`. MODEL/CLIP/VAE and the original LoRA were explicitly connected for the similar-looking pair and relevant existing research samples.

| Case | Detections / edits | Observed outcome |
| --- | --- | --- |
| Public two-person cafe output, default WD and alternative tagger | 2 / 2 each | Correct black-haired/red-jacket and blond/white-blouse original character assignments after fixing literal phrase matching. |
| User's similar-looking brown-haired pair, with original LoRA | 2 / 2 | Long/short hair distinguishes both original prompts; both faces edited. |
| Existing five-person output, both taggers | 5 / 4 each | First four matched correctly. The silver-haired character remained ambiguous and was preserved. |
| Fresh sampler → detailer example | 2 / 2 | Actual generation, pipe propagation, correction and autosave completed without rebuilding the pipe. |
| Six-slot station scene with profiles/backs | 1 / 1 | Only one frontal face detected. Six prompt slots do not imply six detected faces. |
| Fresh six-person campus row, both taggers | 6 / 6 each | **Not a matching pass:** assignments were `[1,2,3,4,5,2]`, although intended identities were `[1,2,3,4,5,6]`. The last purple-haired subject was confidently assigned to black-haired character 2. |
| Same six-person image, WD matching crop factor increased from 2 to 3 | 6 / 6 | Still a failure: the last subject was assigned to adjacent blue-haired character 5. A larger matching crop did not resolve identity and can include a neighbor. |
| BBOX only, public two-person image | 2 / 2 | Rectangular-mask correction completed. |
| BBOX + SAM, same image | 2 / 2 | SAM-refined correction completed. |

The early two-person trials returned 2 detections and 0 corrections. The cause was a literal phrase such as `short black hair` not matching the tag vocabulary's `black hair`. Matching now extracts literal whole-word phrases present in that vocabulary without changing the original generation text; the same image and settings then produced correct assignments with both taggers. The early failures remain in the evidence.

The five-person and similar-pair input fixtures retained source pixels and used original character text/coordinates extracted from their research workflows. These fixtures contain captions but no standalone sampler settings; they are not evidence that arbitrary ComfyUI workflow metadata is automatically imported. Fresh native sampler outputs exercise complete original-settings preservation.

The six-person result illustrates that a high score/margin does **not** prove identity. Independent matching supports multiple regions belonging to one character, so the code does not impose one face per slot or forcibly assign leftovers. Exposed matching crop size and thresholds can be adjusted, but universal matching correctness is not claimed. Profile/back-view detection and the silver/white hair distinction also remain limitations.

## Pixel, metadata, source and UI evidence

The compact [runtime evidence](detailer-runtime-evidence.json) records each request ID, source/result/mask SHA-256, detection/edit counts, assignments and reasons. Saved PNGs were decoded and compared pixel by pixel. Every tested case with a saved correction mask had **zero changed pixels outside that mask**. Cases without saved masks are explicitly `null`, not counted as verified. All saved output records preserved original positive/negative captions and original local settings when present, contained the reported detail history, and omitted workflow/prompt graph metadata. Lossy WebP does not promise exact pixel preservation.

**57 Python tests passed**, including the original sampler/routing/metadata tests and new tests for matching, immutable crops, disjoint composition, no-match preservation, direct pipe history, Anima 5D and ordinary 4D latent adapters, input errors, detector precedence and download-progress events. The 4D adapter test uses a fake VAE/sampler; it does not establish actual SDXL support. Both JavaScript checks passed for character slot folding and detailer/detector controls.

Firefox loaded the UI example on the isolated server with seven actual connected detailer inputs. A temporary test extension exercised the live LiteGraph widgets: advanced settings were hidden initially, became visible, and returned to exactly the same serialized values after folding. The loader displayed `SEGM only. BBOX / SAM are skipped.` and the tagger had three choices. The temporary probe and fixture were removed from the package after evidence capture. Node download/status messages were visible during local execution. Model files were already cached for these trials; a fresh network download is not claimed by this report.

Run source checks from the extension directory using the same Python environment as ComfyUI:

```bash
python -m unittest discover -s tests -v
node tests/test_ui.cjs
node tests/test_detailer_ui.cjs
git diff --check
```

Load [the UI example](../examples/two-characters-detailer-anima.json) or submit [its API form](../examples/two-characters-detailer-anima-api.json) to repeat the two-person generation/detailing flow. Select locally available model filenames, install the documented optional dependencies, and connect identical model/LoRA assets to generation and detailing. Full test histories, masks, images and the evidence collector remain in the local `RS_MC_detailer/validation` and `runtime` directories.

## Scope of this evidence

This report records Anima local-detailer validation before its inclusion in 0.1.2 Beta, with real generation and known matching failures. It does not establish universal 5/6-person identity matching, SDXL detailer quality or Windows runtime behavior. The tests used an isolated ComfyUI installation. Source lineage for the adapted helpers is recorded in [detailer-source-lineage.json](detailer-source-lineage.json).

## Subsequent 0.1.2 model compatibility smoke checks

After the Anima study above, release `5689176` was run once per family on ComfyUI
`a639f187a9f6abfecbda9673034f2045148b6d85`. Each existing two-character image used
WD ViT v3, SEGM face detection and denoise 0.25:

| Model | Sampler / scheduler | Steps / CFG | Detected / edited / skipped | Changed pixels outside mask |
| --- | --- | --- | --- | --- |
| Illustrious XL v1.0 | Euler ancestral / normal | 30 / 5.5 | 2 / 2 / 0 | 0 |
| Krea 2 Turbo | Euler / simple | 8 / 1.0 | 2 / 2 / 0 | 0 |
| MOSS-Image SFT | Euler / simple | 50 / 3.0 | 2 / 2 / 0 | 0 |

These are real execution smoke checks, not comparative quality, accuracy or
all-sampler validation. The [compact evidence](detailer-multimodel-smoke.json)
contains request IDs, parameters and source/result/mask hashes. The retained
result and mask file hashes were rechecked during this compatibility review.
No new detailer sampling was needed for the import/API fixes described in the
[compatibility report](compatibility.md).
