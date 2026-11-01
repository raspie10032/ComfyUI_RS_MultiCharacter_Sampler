# Prompt autocomplete validation

The workspace reuses the original ComfyUI widget textarea rather than creating a second prompt input. This preserves third-party listeners and keeps the graph and workspace values in sync. Original DOM position, inline styling and workspace listeners are restored when changing tabs or returning to graph view.

Without an enabled known provider, a small bundled offline tag vocabulary, tags already in the graph and local wildcard filenames provide suggestions. There are no model calls or dictionary downloads. This is a lightweight fallback, not a comprehensive character/artist database. Settings: `RS.MultiCharacter.Autocomplete`.

For an existing local dictionary, copy it to `web/autocomplete.txt` inside this extension and refresh the browser. The optional file is loaded once, on first tag completion. Custom Scripts `tag,count` text and A1111 CSV `tag,category,count,aliases` are supported; usage counts prioritize matches, aliases insert the canonical tag, and literal parentheses are escaped for ComfyUI. The user dictionary is ignored by Git and is not bundled or downloaded. Installed, enabled external providers still own their native inputs.

Known provider dispatch checks registered extension IDs and actual settings:

| Provider | Enabled setting | Evidence |
| --- | --- | --- |
| Custom Scripts AutoCompleter | `pysssss.AutoCompleter` | Actual upstream browser modules, fixture dictionary, live ComfyUI UI |
| Autocomplete-Plus | `AutocompletePlus.Autocompletion.Enable` | Actual upstream browser modules, fixture CSV/model endpoints, live ComfyUI UI |
| Autocomplete++ | `ComfyUI.AutocompletePlusPlus.Enabled` | Upstream source inspection and provider dispatch unit checks; full UI not exercised |

Sources: [Custom Scripts](https://github.com/pythongosssss/ComfyUI-Custom-Scripts), [Autocomplete-Plus](https://github.com/newtextdoc1111/ComfyUI-Autocomplete-Plus), [Autocomplete++](https://github.com/michikora/ComfyUI-Autocomplete-Plus-Plus). External backend data loading is represented by small fixtures in integration checks; these checks do not establish compatibility with every dictionary configuration. No external extension was installed into the user's server by these tests. rgthree Power Prompt is not treated as a global autocomplete provider.

## Checks

- `node tests/test_prompt_autocomplete.cjs`: token ranges, weighted prompts, trailing text, selections, wildcards and provider settings, ordinary STRING character connections, and exclusion of text-only or shared literal inputs. Both LF and CRLF modules parse.
- 19 JavaScript test files passed, including workspace routing, serialization, wildcards, mask/camera/pose UI. The camera parity test needs NumPy; use `CAMERA_PYTHON=<ComfyUI venv python>` when the system Python lacks it.
- Chromium with the actual running ComfyUI frontend: built-in candidate visibility and keyboard selection, actual native textarea identity, tab round-trip/value retention, closing the app and popup cleanup. Weighted insertion, IME composition, actual local `fabe` wildcard discovery, Ctrl+Space, and typography exclusion also passed.
- Actual Custom Scripts and Autocomplete-Plus modules: candidates appeared above the full-screen workspace, selection updated the graph widget, tab round-trips retained the input, and no duplicate fallback menu or page exceptions occurred. Autocomplete-Plus needs a workspace-specific stacking override.

No generation request or GPU job is needed for this UI-only change. Existing model execution and wildcard expansion remain covered by the workspace regressions; this validation does not claim new image-generation evidence.

- Upstream module revision: https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git @ `609f3afaa74b2f88ef9ce8d939626065e3247469`.

- Upstream module revision: https://github.com/newtextdoc1111/ComfyUI-Autocomplete-Plus.git @ `9cfd2aceb0205132942b6dc1e237a2377de92018`.

- Upstream module revision: https://github.com/michikora/ComfyUI-Autocomplete-Plus-Plus.git @ `cd0603dcd93d6ce66c815c8d78e2e49a71fda8b4`.
