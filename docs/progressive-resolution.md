# RS Progressive Resolution Sampler

A separate T2I sampler for producing larger images faster in exchange for some detail. It starts at a smaller size, expands with floating-point Lanczos, and finishes at the selected final resolution. Actual speed depends on the model and settings. **The existing RS MultiCharacter Sampler remains available.** The new node uses the same character pipe, prompts, masks, text regions, character LoRAs and outputs.

## Use

Replace the sampler in an existing RS workflow with **RS Progressive Resolution Sampler**. Connect the same MODEL, CLIP, VAE and finalized character pipe. Choose final width/height, **start_scale (0.5–1.0)**, sampler, scheduler, total steps, CFG and seed. Existing advanced regional controls remain available. No model download or extra package is required.

**Lower start scales can reduce quality or change composition; quality is not guaranteed.** The intended tradeoff is some lost detail for shorter sampling time at a large final resolution. Detail/composition changes are expected; merged people, severely broken faces or execution failures are recorded separately as limitations. A scale of 0.5 halves each side and starts at about one quarter of the final pixel count. A scale of 1.0 uses ordinary fixed-resolution sampling.

The first expansion is at approximately 8/30 of the total schedule and the final expansion at approximately 16/30. Dimensions are rounded to each model's spatial grid. For 1152×1728, scale 0.67 and 30 steps, the usual plan is:

| Steps | Size |
| --- | --- |
| 1–8 | 768×1152 |
| 9–16 | 960×1440 |
| 17–30 | 1152×1728 |

The panel previews the plan; the executed plan in the result/metadata is authoritative for connected inputs and restored image settings. The **total steps** is shared across all stages, not repeated for each stage.

[Anima example PNG](../examples/progressive/two-characters-anima.png) · [workflow JSON](../examples/progressive/two-characters-anima.json): uses the same modular character inputs as the ordinary sampler, with no required style LoRA. Select locally installed model/encoder/VAE files before running. The PNG contains the editable ComfyUI workflow.

## Regional behavior and limitations

- Original point/box/mask geometry is recalculated at each resolution. Body-part masks and conditioning masks follow the current grid.
- Exclusive character regions keep a separation floor of 0.99 below final resolution. Overlap regions retain the existing interaction policy. At final resolution the ordinary separation schedule resumes.
- MOSS native mode keeps native structured captions and rectangular regions; it does not gain attention-mask separation from this option. Use the existing attention mode when testing that behavior.
- Native ComfyUI sampler and scheduler choices are preserved. A solver's history restarts at expansion, so multi-step/adaptive solvers can behave differently. A sampler's actual evaluation count can exceed the nominal total steps.
- SD1.5 is supported for execution compatibility; high-resolution image quality is not a recommendation or guarantee. The approximately 2Mpx trial already showed repeated people/body parts with the original sampler.
- Lower-resolution composition, anatomical mistakes, extra people, identity or costume mixing and text errors can remain. Supported model execution does not guarantee equal aesthetic quality.
- Outputs remain IMAGE, LATENT, character_pipe and generation_info. Autosave stores the effective stage plan; the regular sampler/detailer can still consume these outputs. Image references retain their existing experimental status.

## Validation scope

The 2026-10-27 candidate was generated on an RTX 4070 Ti SUPER in an isolated ComfyUI instance. Matched quality comparisons used final 1152×1728 or 1728×1152, the same prompt/seed/step count, and Euler ancestral / SGM uniform:

| Model branch | Total steps | Observed limits in the matched comparison |
| --- | ---: | --- |
| Anima Aesthetic v1.1 | 30 | Two people retained at 0.67 and 0.5; costume/hand detail and composition change. Two additional landscape seeds were also compared. |
| SDXL / Illustrious XL v1.0 | 30 | Two people retained at 0.67; the 0.5 example merged into one person. A separate 0.8 check retained two people. |
| SD1.5 / v1-5-pruned-emaonly | 30 | Execution compatibility only. The ordinary approximately 2Mpx baseline also repeated people/body parts. |
| Krea 2 Turbo | 8 | Two people retained; hands, accessories and composition change. |
| MOSS attention and native JSON | 50 | Both paths generated at all three settings; identity, costume and rendering details vary. Native mode retains its own layout behavior. |
| FLUX.1 Dev | 30 | Two people retained; costume/identity and pose can change. |
| FLUX.2 Klein Base 4B | 50 | Two people retained; identity/hand limitations also occur in the baseline. |
| FLUX 3 Klein Base | 50 | Two people retained; pose, colors and costume details vary. |

Execution checks also covered installed FLUX.1 Schnell, FLUX.2 Klein distilled 4B/9B and Dev, FLUX 3 distilled, and MOSS SFT BF16 variants. Those short execution checks are not full quality comparisons. This is coverage of the installed supported branches, not every checkpoint or sampler/scheduler combination.

Additional checks covered start-scale bounds, final latent/image dimensions, full step accounting, conditioning masks, drawn masks with text, body-part guidance without text, character LoRA Normal/Precision modes, MOSS native layout, PNG metadata restoration, WebP autosave, and representative stateful solvers. Body-part guidance with text remains unsupported and reports the existing readable error; turn its strength to zero to use masks with text. A warmed 1.0 comparison was pixel-identical to the ordinary sampler for all eight branches.

## References

- [ComfyUI-SPEED](https://github.com/ruwwww/ComfyUI-SPEED)
- [SPEED research implementation](https://github.com/howardhx/speed) and [research description](https://howardxiao.ca/speed/)

We compared frequency-preserving expansion, noise/time correction and expansion timing with the preceding RS Lanczos experiments. Lanczos expansion and resolution-aware regional separation existed in RS trials before that comparison. This node uses Lanczos and ComfyUI's native model noise scaling; it does not implement SPEED's DCT expansion or frequency-derived automatic timing. SPEED is cited as the subsequent design comparison/reference. The preserved comparison did not show a consistent quality advantage for SPEED at the same fixed expansion steps.
