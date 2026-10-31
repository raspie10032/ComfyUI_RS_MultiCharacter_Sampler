# SPDX-License-Identifier: GPL-3.0-only
"""Local text wildcards for the workspace. No generation or model dependencies."""
from fnmatch import fnmatchcase
from pathlib import Path
import random
import re

TOKEN = re.compile(r'__([^\n]+?)__')
CHOICE = re.compile(r'(?<!\\)\{([^{}]*\|[^{}]*)\}')
MAX_TEXT = 256_000


def roots():
    import folder_paths
    base = Path(folder_paths.base_path)
    found = [('user', Path(folder_paths.get_user_directory()) / 'wildcards'),
             ('comfy', base / 'wildcards')]
    for custom in folder_paths.get_folder_paths('custom_nodes'):
        directory = Path(custom)
        if directory.is_dir():
            for package in sorted(directory.iterdir()):
                if package.is_dir():
                    for name in ('wildcards', 'custom_wildcards'):
                        found.append((f'{package.name}:{name}', package / name))
    return found


def inventory(directories=None):
    files = {}
    for source, directory in roots() if directories is None else directories:
        directory = directory.resolve()
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob('*.txt')):
            if not path.resolve().is_relative_to(directory) or not path.is_file():
                continue
            name = path.relative_to(directory).with_suffix('').as_posix()
            files[f'{source}/{name}'] = path
    return files


def expand(texts, seed, files):
    if not isinstance(texts, dict) or len(texts) > 12 or any(
            not isinstance(k, str) or not isinstance(v, str) or len(v) > MAX_TEXT
            for k, v in texts.items()):
        raise ValueError('프롬프트는 12개 이하의 텍스트로 전달해 주세요.')
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2**64 - 1:
        raise ValueError('와일드카드 시드는 0 이상 정수로 지정해 주세요.')
    entries = {}
    budget = 4096

    def read(key):
        if key not in entries:
            path = files[key]
            if path.stat().st_size > 8 * 1024 * 1024:
                raise ValueError(f'와일드카드 파일이 너무 큽니다: {key} (최대 8 MiB)')
            raw = path.read_bytes()
            try:
                text = raw.decode('utf-8-sig')
            except UnicodeDecodeError:
                text = raw.decode('cp1252')
            entries[key] = [line.strip() for line in text.splitlines()
                            if line.strip() and not line.lstrip().startswith('#')]
        if not entries[key]:
            raise ValueError(f'와일드카드 파일이 비어 있습니다: {key}')
        return entries[key]

    def resolve(text, rng, stack=()):
        nonlocal budget
        if len(stack) > 32:
            raise ValueError('와일드카드 중첩은 32단계까지 지원합니다.')

        def token(match):
            nonlocal budget
            budget -= 1
            if budget < 0:
                raise ValueError('와일드카드 확장이 너무 많습니다. 중첩을 줄여 주세요.')
            name = match[1].strip().replace('\\', '/')
            if name in files:
                keys = [name]
            else:
                keys = [key for key in files if key.split('/', 1)[1] == name]
                if not keys and '*' in name:
                    keys = [key for key in files if fnmatchcase(key, name) or fnmatchcase(key.split('/', 1)[1], name)]
                elif len(keys) > 1:
                    raise ValueError(f'와일드카드 이름이 겹칩니다: {name}. 목록에서 전체 이름을 선택해 주세요.')
            if not keys:
                raise ValueError(f'와일드카드를 찾을 수 없습니다: {name}. 목록을 새로고침해 주세요.')
            key = rng.choice(sorted(keys))
            if key in stack:
                raise ValueError(f'와일드카드가 순환 참조합니다: {key}')
            return resolve(rng.choice(read(key)), rng, (*stack, key))

        for _ in range(33):
            previous = text
            text = CHOICE.sub(lambda m: rng.choice(m[1].split('|')).strip(), text)
            text = TOKEN.sub(token, text)
            if len(text) > MAX_TEXT:
                raise ValueError('확장된 프롬프트가 너무 깁니다. 중첩을 줄여 주세요.')
            if text == previous:
                return text
        raise ValueError('선택지 중첩이 너무 깊습니다. 중첩을 줄여 주세요.')

    # Each field has its own stream. Editing a background or hiding a slot must
    # not change the character selected for another field at the same seed.
    return {key: resolve(value, random.Random(f'{seed}:{key}')) for key, value in texts.items()}


def register_routes():
    try:
        from server import PromptServer
        from aiohttp import web
    except ImportError:
        return
    server = getattr(PromptServer, 'instance', None)
    if server is None:
        return

    @server.routes.get('/rs_mc/app/wildcards')
    async def listing(request):
        import asyncio
        files = await asyncio.to_thread(inventory)
        return web.json_response({'files': sorted(files), 'syntax': '__name__ / {a|b}'})

    @server.routes.post('/rs_mc/app/wildcards/resolve')
    async def resolving(request):
        import asyncio
        try:
            data = await request.json()
            if not isinstance(data, dict):
                raise ValueError('와일드카드 요청 형식을 확인해 주세요.')
            def run():
                return expand(data.get('texts'), data.get('seed'), inventory())
            return web.json_response({'texts': await asyncio.to_thread(run)})
        except (ValueError, OSError, UnicodeError) as error:
            return web.json_response({'error': str(error)}, status=400)


register_routes()
