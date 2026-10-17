# Epsilon layout examples

Requires the **0.1.5 development candidate**. These are normal ComfyUI workflow JSON files; the `*-api.json` companions are for API submission. Select the model files installed on your computer before running.

| Workflow | Layout | Model |
|---|---|---|
| [anima-mixed.json](anima-mixed.json) | Two XY character regions plus a HELLO text box | Anima, 30 steps, CFG 4 |
| [moss-mixed.json](moss-mixed.json) | Two XY character regions plus a HELLO text box, regional attention | MOSS with 8-step LoRA, strength 0.7, CFG 3 |
| [moss-native.json](moss-native.json) | Two character boxes plus a HELLO text box, native JSON | MOSS with 8-step LoRA, strength 0.7, CFG 3 |

For the mixed examples, region count is **3** but person count is **2**. Slots 1 and 2 are characters using point geometry. Slot 3 is text, with literal `HELLO` and a separate style caption. The top text box takes priority over the point regions within its bounds.

MOSS native requires every region to have a box. Use the regional method for mixed point/box layouts. Native generation ignores the regional common/character/boundary schedules.

The Anima mixed example spells HELLO but clips the title and omits the requested campus background. The MOSS mixed example retains the campus; its text is wider than the requested box. Exact spelling, outlines, count and framing are not guaranteed.

[Settings and limits](../../docs/regional-layout.md) · [Validation scope](../../docs/epsilon-validation.md)
