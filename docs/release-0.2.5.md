# 0.2.5 Mieum / 미음 / ミウム

Adds **RS Character Image Reference · Experimental**, supported but not recommended.
One IMAGE input binds to a numbered character and follows existing point, box and
mask placement. Select the longest edge in 64px increments (64–1024, default 384),
strength (default 0.6), or OFF. See [usage, dependencies and limits](image-reference.md).

The family-specific paths cover Anima, SD1.5, SDXL/Illustrious, FLUX.1/2/3, Krea 2
and MOSS. These are not one interchangeable IP-Adapter: SD/Anima use learned
adapters, FLUX.1 uses Redux, and the others use reference latents with matching
edit weights where required. Optional dependencies and selected weights are
loaded only when an active reference is sampled.

Earlier isolated experiments completed 40 controls across eight representative
checkpoints (baseline / on / exchanged / off-again / zero) and 12 additional SD
baseline trials. This establishes those prototype paths, not universal quality.
SDXL has weak outfit fidelity and oversaturation; a character LoRA remains the
recommended option. Integrated-node verification is recorded separately in the
Release report. No claim is made that arbitrary LoRA combinations or ten-person
reference generation have been validated.

The integrated release node completed **21 further generations**: all eight
families generated with active references; Anima and the two SD families also
received fresh disable/zero controls. Anima and warmed-up SD baselines matched
their disabled/zero results pixel-for-pixel. Python: 188 passed, one skipped;
nine JavaScript UI files passed, including 303 controls in three locales.

Settings metadata records hashes and reference options without embedding reference
images. Image settings loading does not reconstruct references. The Detailer does
not apply image references. Native MOSS layout and foreign attention patches retain
their compatibility restrictions. Existing workflows need no additional nodes.

The experiment report and generated comparisons are **Release assets**, not git
files: downloading or updating the node does not download the report. Only this
short documentation and its links travel with the source.
