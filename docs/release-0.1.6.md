# 0.1.6 Zeta

Zeta adds a LoRA file selector and separate model/CLIP strengths to each character
slot. The existing character pipe carries these settings to the sampler and local
detailer. Coordinates and boxes determine where character predictions are blended;
text slots do not receive character LoRAs. Global style or acceleration LoRAs can
still be connected through the usual model loader.

## Changes

- Eligible ordinary Anima LoRAs use ComfyUI's native Bypass LoRA with shared small
  factor matrices. The same file at different strengths shares its factors.
- Other supported models, adapter formats and older cores retain the low-memory
  weight-hook path. Distinct model-LoRA combinations still need separate predictions.
- The detailer applies the LoRA assigned to the matched character.
- PNG/WebP metadata and the image loader preserve regional filenames and strengths.
- Existing workflows default to no regional LoRA. Reducing the character count
  excludes hidden slots, including their saved LoRA selections.
- English, Korean and Japanese controls/documentation and an Anima example are included.

## Evidence and limits

Completed image checks cover Anima and SDXL regional LoRAs, assignment swaps,
Anima zero-strength/disabled cleanup, metadata restoration and matched-face detailing.
The optimized Anima backend averaged **65.82 s versus 153.02 s** for the previous
backend in one controlled 1024×768, 30-step, two-LoRA condition. Sampled process
RAM fell from roughly 8.3–8.5 GiB to 6.6 GiB; peak allocated VRAM was about 6.2 GiB
for both. These are measured conditions, not general speed or quality guarantees.

Calculation order changes can alter pixels. Regional masks do not guarantee that
LoRA effects stay perfectly inside the assigned region. Krea 2, MOSS and SD1.5
regional-LoRA completed-image checks remain unverified; SD1.5 generation remains
experimental and unstable. Model-family, CLIP and adapter restrictions are listed
in the usage guide.

Validation: **106 Python tests** against the installed ComfyUI core and **four
JavaScript UI suites** passed. Earlier old-core checks and actual image evidence
are recorded separately in the reports below.

- [Usage, costs and restrictions (English / 한국어 / 日本語)](regional-lora.md)
- [Regional LoRA image and workflow validation](regional-lora-validation.md)
- [Anima optimization measurements and cleanup checks](regional-lora-bypass-validation.md)
- [Two-character Anima LoRA example](../examples/zeta/two-character-loras-anima.json)

After updating, restart ComfyUI and refresh the browser page. Choose local LoRA
files in each character slot; the example filenames are not automatic downloads.
