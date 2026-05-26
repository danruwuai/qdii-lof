/**
 * Cloudflare Pages Function
 * 拦截所有请求，/api/* 代理到 Workers，其他返回静态文件
 */

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);

  // /api/* 请求代理到 Workers
  if (url.pathname.startsWith('/api/') || url.pathname === '/health') {
    // 提取 Workers 路径（去掉 /api 前缀）
    const workerPath = url.pathname.replace(/^\/api/, '');
    const workerUrl = `https://qdii-lof.980764131.workers.dev${workerPath}${url.search}`;

    try {
      const response = await fetch(workerUrl, {
        method: request.method,
        headers: Object.fromEntries(request.headers),
        body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
      });

      return response;
    } catch (error) {
      console.error('Proxy error:', error);
      return new Response(JSON.stringify({ error: 'Failed to proxy to Workers', details: error.message }), {
        status: 502,
        headers: { 'Content-Type': 'application/json' },
      });
    }
  }

  // 其他请求返回 null（让 Pages 默认处理静态文件）
  return null;
}
