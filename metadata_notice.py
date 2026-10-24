# SPDX-License-Identifier: GPL-3.0-only
"""Read-only image selection notice, before a workflow is queued."""
from pathlib import Path
from PIL import Image
from .metadata import read_record


def inspect_file(filename):
    import folder_paths
    path = Path(folder_paths.get_annotated_filepath(filename)).resolve()
    roots = [Path(getter()).resolve() for getter in (folder_paths.get_input_directory,
             folder_paths.get_output_directory, folder_paths.get_temp_directory)]
    if not path.is_file() or not any(path.is_relative_to(root) for root in roots):
        raise ValueError("Select an image inside ComfyUI input, output or temp.")
    with Image.open(path) as image:
        record = read_record(image)
    rows = record.get("v4_prompt", {}).get("caption", {}).get("char_captions", [])
    if not isinstance(rows, list):
        raise ValueError("Invalid character captions.")
    count = len(rows)
    return {"character_count": count, "local_count": min(count, 10), "truncated": count > 10}


def register_routes():
    try:
        import asyncio
        from aiohttp import web
        from server import PromptServer
    except ImportError:
        return
    if not getattr(PromptServer, "instance", None):
        return

    @PromptServer.instance.routes.get("/rs_mc/metadata_notice")
    async def metadata_notice(request):
        try:
            return web.json_response(await asyncio.to_thread(inspect_file, request.query.get("image", "")))
        except (ValueError, OSError, TypeError, KeyError, AttributeError):
            return web.json_response({"error": "Cannot read character metadata. / 캐릭터 메타데이터를 읽을 수 없습니다."}, status=400)


register_routes()
