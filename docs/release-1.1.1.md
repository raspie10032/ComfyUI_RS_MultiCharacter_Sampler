# 1.1.1 Hangeul — 3D pose guidance in the building pipe

Configure learned pose guidance directly in **RS 3D Pose Masks**. Connect its
**building_pipe** to the character builder and Finalize, then use the normal RS
sampler. No MODEL, VAE or patch-loader connections are needed on the 3D node.

The sampler uses the model and VAE it already receives to route compatible
Anima 2B, Krea 2 and MOSS guidance. Required pose weights are downloaded when
needed. Unsupported families and Anima 2.9B retain masks and report the reason.

## Update and use

1. Update the extension to **1.1.1** and restart ComfyUI.
2. Hard-refresh the browser with **Ctrl+Shift+R** (macOS: **Cmd+Shift+R**).
3. In **RS 3D Pose Masks**, edit the scene, choose **auto**, and set strength and
   start/end. The building pipe can carry prompts and positions in either order.
4. Connect to Finalize and an RS sampler. The RS Workspace app now uses this
   same route automatically.

Saved older 3D nodes retain **masks_only** until explicitly changed. Existing app
graphs migrate their old generated helper settings into the 3D editor. The old
MODEL-input pose adapter remains deprecated for older saved workflows; remove it
when enabling the new route so the model is not patched twice.

## Validation and limitations

The Python regression suite ran 427 tests: 413 passed and 14 skipped. The final
targeted pose recheck ran 51 tests: 49 passed and 2 skipped. All 18 JavaScript
regression scripts passed. An actual Anima 2B image was generated on RTX 5060 Ti
at 768×1024, 30 steps, Euler ancestral / SGM uniform through the building pipe.
The PNG was opened in ComfyUI to verify its restored controls and connections.

[Detailed trial and scope](pose3d-building-pipe-validation.md) ·
[3D setup guide](pose3d.md) ·
[Loadable workflow PNG](../examples/pose3d/anima-building-pipe.png).

Krea 2/MOSS learned-guidance routing is covered by regressions; this patch does
not claim new image-quality trials for them. Their learned guidance requires
full resolution. Learned guidance cannot currently be combined with image
references. Pose guidance is approximate and does not guarantee exact joints,
hands, identity or anatomy.
