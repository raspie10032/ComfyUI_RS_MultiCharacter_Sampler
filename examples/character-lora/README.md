# Character LoRA examples

Drag a UI JSON into ComfyUI, choose installed model/CLIP/VAE files and a compatible character LoRA, then generate. The API JSON contains the same tested inputs. Weights are not included.

- `krea2.json` / `krea2-api.json`: Krea 2 Turbo FP8, 768×512, Lara character LoRA, 8 steps, CFG 1, Euler/simple.
- `illustrious.json` / `illustrious-api.json`: Illustrious, 1024×768, Phoebe character LoRA, 24 steps, CFG 5.5, Euler ancestral/normal.

Both use model LoRA strength 1 and CLIP 0 on character 1. Character 2 has no LoRA. Swap the LoRA slot to compare the other side. The examples use the compatible legacy prompt node; the current character builder can provide the same character pipe.

[Actual generation checks and limits](../../docs/character-lora-matrix-20261021.md). Sampling presets change sampling/region controls only; select canvas size and LoRA separately.
