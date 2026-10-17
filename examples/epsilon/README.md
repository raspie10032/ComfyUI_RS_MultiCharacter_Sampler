# Epsilon layout examples

Requires **0.1.5 Epsilon or later**. These are normal ComfyUI workflow JSON files; the `*-api.json` companions are for API submission. Select the model files installed on your computer before running.

| Workflow | Layout | Model |
|---|---|---|
| [anima-mixed.json](anima-mixed.json) | Two XY character regions plus a HELLO text box | Anima, 30 steps, CFG 4 |
| [sdxl-mixed.json](sdxl-mixed.json) | Two XY characters and a title box; tag-style prompts | Illustrious XL v1.0, 30 steps, CFG 5.5 |
| [krea2-mixed.json](krea2-mixed.json) | Two XY characters and a title box | Krea 2 Turbo, 8 steps, CFG 1 |
| [sd15-mixed.json](sd15-mixed.json) | Experimental two XY characters and a title box | SD1.5 base, 30 steps, CFG 7; checks distinguishable people and visible lettering only |
| [moss-mixed.json](moss-mixed.json) | Two XY character regions plus a HELLO text box, regional attention | MOSS with 8-step LoRA, strength 0.7, CFG 3 |
| [moss-native.json](moss-native.json) | Two character boxes plus a HELLO text box, native JSON | MOSS with 8-step LoRA, strength 0.7, CFG 3 |

For the mixed examples, region count is **3** but person count is **2**. Slots 1 and 2 are characters using point geometry. Slot 3 is text, with literal `HELLO` and a separate style caption. The top text box takes priority over the point regions within its bounds.

MOSS native requires every region to have a box. Use the regional method for mixed point/box layouts. Native generation ignores the regional common/character/boundary schedules.

The Anima example now uses stronger early common conditioning, shared scene context in each character caption, and a larger title box placed farther from the top edge. Its original white-background/clipped-title result is retained in the validation history. SDXL uses a lower common strength and tag-style descriptions; Krea 2 uses weaker spatial separation. These are model-specific starting examples, not universal automatic defaults. SD1.5 remains experimental, including literal text.

Use the [model settings and comparison](../../docs/mixed-layout-tuning.md) before transferring one model's settings to another. The MOSS examples retain the previously tested settings; MOSS's text can extend beyond its rectangle. Exact spelling, outlines, count and framing are not guaranteed.

[Two people + object: 10 kinds × Anima/Krea 2](objects) use the same mixed presets. They retain the actual trial prompts and seeds; object slots are generic character slots and are not excluded from face matching. See the [results and limits](../../docs/object-layout-validation.md).

[Settings and limits](../../docs/regional-layout.md) · [Validation scope](../../docs/epsilon-validation.md)
