# Epsilon model preset validation — 2026-10-17

This change adds explicit frontend preset application to the existing sampler. No backend sampling inputs or algorithms change. The preset values come from the checked-in model examples; see [values, source examples and usage](model-presets.md).

## Checks

| Scope | Result |
|---|---|
| Current ComfyUI Python regressions | 95 passed |
| ComfyUI v0.3.76 Python regressions | 88 passed, 7 unsupported integrations skipped |
| JavaScript tests | Four files passed: character UI, box UI, detailer UI, model presets |
| Eight preset definitions | Every sampling/regional value matches its published source example |
| Actual ComfyUI frontend on isolated port 8199 | 95 assertions passed across eight presets, graph save/load, image-restore conflict and submitted API inputs |
| English, Korean, Japanese | Labels and guidance inspected in the actual frontend; locale handling also covered by JS tests |
| Anima mixed preset → real GPU generation | Completed successfully; 2 characters, HELLO text and campus visible |
| Pixel comparison with the previous tuned Anima example | Exact equality; mean and maximum absolute differences both zero |

The real generation used seed **346751**, **1024×768**, **30 steps**, **CFG 4**, **Euler ancestral / SGM uniform**, and the full prompt/layout from `examples/epsilon/anima-mixed.json`. The frontend's submitted sampler inputs exactly matched that example. ComfyUI prompt ID: `35ba2187-a1c2-48b1-99c7-c0bdb232b3a6`; recorded execution time: **43.76 seconds**, including model loading on this run. This is an execution record, not a speed benchmark.

The UI tests check explicit application, manual editing, independence between sampler nodes, preserved input order, missing choices, connected/converted inputs, image-setting restoration, MOSS native mode and workflow reopening. Conflict validation happens before any preset value is written. Preset UI widgets do not become backend API inputs; only the ordinary sampler settings are submitted. Workflow properties retain a stable preset ID, and reopening never reapplies the selected preset over manually edited values.

Other model presets were applied in the live frontend and compared with their existing tested examples. They were not each generated again for this frontend-only change; their image evidence and limits remain those of the [previous model comparison](mixed-layout-tuning.md). SD1.5 remains a limited compatibility check, and MOSS 8-step requires the separate LoRA connection at the documented strength.

## Reproduce

From the repository root, using the Python environment with the repository's test dependencies:

```bash
RS_MC_TEST_COMFYUI=/path/to/current/ComfyUI python -m unittest discover -s tests -v
RS_MC_TEST_COMFYUI=/path/to/ComfyUI-v0.3.76 python -m unittest discover -s tests -v
node tests/test_ui.cjs
node tests/test_boxes_ui.cjs
node tests/test_detailer_ui.cjs
node tests/test_presets_ui.cjs
```

Load the Anima mixed example in ComfyUI, select **Anima — mixed** and press **Apply preset**. Confirm that the existing controls update, then generate. Edit CFG, save/reopen the workflow and confirm that your edited value is retained. For image restoration and externally linked settings, verify that Apply explains the conflict without changing the other settings.

Local raw evidence is retained at `/var/home/raspie/Documents/Codex/RS_MC_epsilon_presets_20261017/validation/`: Python and JS logs, `browser-evidence.json`, reproducible browser probe, English/Korean/Japanese screenshots, submitted workflow/API data, generation history, `anima-preset.png` and `generation-parity.json`. These machine-specific artifacts are separate from the extension package.
