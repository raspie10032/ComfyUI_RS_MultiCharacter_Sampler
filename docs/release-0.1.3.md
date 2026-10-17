# 0.1.3 Gamma

SDXL now works on ComfyUI versions predating Anima. Ordinary SD1.5 checkpoints
can use the existing regional sampler, with explicitly experimental and unstable
character counts and attribute separation. The package version is `0.1.3`;
Gamma is the release label. The standard Python development classifier remains
Beta because it has no Gamma category.

## Included changes

| Change | Implementation commit | Evidence |
| --- | --- | --- |
| Load architecture-specific code only when needed; use the compatible U-Net latent helper; check optional architectures independently | `b287ca2` | [Compatibility review](compatibility.md) |
| Ordinary 4-channel SD1.5 generation, matching CLIP-L checks, metadata restoration and examples | `716f6d4` | [SD1.5 trial and limitations](sd15-validation.md) |

SD1.5 uses the same character pipe and sampler, with a standard checkpoint loader
providing MODEL, CLIP and VAE. Start with the
[SD1.5 workflow](../examples/two-characters-sd15.json). The four real checkpoint
trials completed, but two produced an extra person and appearance attributes
could mix or disappear. These results do not establish a general success rate
or the quality of SD1.5 fine-tunes. SD1.5 detailing is untested.

The compatibility review also records existing SDXL, Krea 2 and MOSS detailer
smoke results. Each model completed one run correcting two faces; these are
execution checks, not a quality benchmark.

## Compatibility and updating

There are still six nodes. Node IDs, pipe types, widget ordering, defaults and
output types are retained. The visible release label changes to Gamma, with
Korean and Japanese labels and documentation updated too. Metadata schema
version 1 and the existing engine identifiers remain unchanged; SD1.5 adds its
own `sd1.5-spatial-alpha-1` identifier.

Update the existing installation through ComfyUI-Manager or Git and restart
ComfyUI when the queue is idle. Generation checkpoints are supplied separately.
Anima, Krea 2 and MOSS still require a host with native support for those models.
SD2, refiner/inpainting checkpoints, ControlNet and other attention patches are
outside the regional sampler's supported paths.

The detailer retains its existing combined common/character prompt behavior.
The separate step-conditioned detailer experiment is not part of this release.

## Validation

The CPU test workflow checks Linux with ComfyUI `v0.3.76` and pinned
`5cc4b870094c89090db54bd8d12649dcaf89f2ba`, plus Windows with the latter snapshot.
Native tests use small random models and synthetic text/VAE data to check API
integration; actual image evidence is documented in the reports linked above.
Windows CPU checks do not establish Windows GPU generation quality.
The UI test harness accepts both LF and Windows CRLF line endings. Each CI
command has its own step so a later success cannot hide an earlier failure.

```sh
RS_MC_TEST_COMFYUI=/path/to/ComfyUI python -m unittest discover -s tests -v
node tests/test_ui.cjs
node tests/test_detailer_ui.cjs
comfy node validate
git diff --check
```

See the [compatibility workflow](../.github/workflows/tests.yml) and
[repository Actions](https://github.com/raspie10032/ComfyUI_RS_MultiCharacter_Sampler/actions)
for results associated with the release commit.
