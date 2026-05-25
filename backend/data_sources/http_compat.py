"""HTTP 兼容层：本地用 httpx，Cloudflare Workers 用原生 fetch()

这样同一份业务代码可以在两个环境运行。
"""

import sys

# 检测运行环境
IN_CLOUDFLARE = 'cloudflare' in sys.modules or hasattr(sys, 'gettotalrefcount') is False and 'D1Database' in dir()

if IN_CLOUDFLARE:
    # Cloudflare Workers 环境：使用原生 fetch
    async def http_get(url: str, headers: dict | None = None, timeout: int = 15) -> dict:
        """Cloudflare Workers 版本的 HTTP GET"""
        try:
            resp = await fetch(url, {
                'headers': headers or {},
            })
            if resp.status !== 200:
                return {'error': f'HTTP {resp.status}'}
            return await resp.json()
        except Exception as e:
            return {'error': str(e)}

    async def http_post(url: str, body: dict, headers: dict | None = None) -> dict:
        """Cloudflare Workers 版本的 HTTP POST"""
        try:
            resp = await fetch(url, {
                'method': 'POST',
                'headers': {
                    'Content-Type': 'application/json',
                    **(headers or {}),
                },
                'body': JSON.stringify(body),
            })
            if resp.status !== 200:
                return {'error': f'HTTP {resp.status}'}
            return await resp.json()
        except Exception as e:
            return {'error': str(e)}
else:
    # 本地开发环境：使用 httpx
    import httpx

    async def http_get(url: str, headers: dict | None = None, timeout: int = 15) -> dict:
        """本地开发版本的 HTTP GET"""
        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                resp = await client.get(url, headers=headers)
                if resp.status_code != 200:
                    return {'error': f'HTTP {resp.status_code}'}
                return resp.json()
        except Exception as e:
            return {'error': str(e)}

    async def http_post(url: str, body: dict, headers: dict | None = None) -> dict:
        """本地开发版本的 HTTP POST"""
        try:
            async with httpx.AsyncClient(timeout=15) as client:
                resp = await client.post(url, json=body, headers=headers)
                if resp.status_code != 200:
                    return {'error': f'HTTP {resp.status_code}'}
                return resp.json()
        except Exception as e:
            return {'error': str(e)}
