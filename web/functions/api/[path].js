/**
 * Cloudflare Pages Function
 * 代理 /api/* 请求到 Workers
 */

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);

  // 提取 API 路径（去掉 /api 前缀）
  const apiPath = url.pathname.replace(/^\/api/, '');
  const workerUrl = `https://qdii-lof.980764131.workers.dev${apiPath}${url.search}`;

  try {
    // 转发请求到 Workers
    const response = await fetch(workerUrl, {
      method: request.method,
      headers: request.headers,
      body: request.method !== 'GET' && request.method !== 'HEAD' ? request.body : null,
    });

    return response;
  } catch (error) {
    console.error('Proxy error:', error);
    return new Response(JSON.stringify({ error: 'Failed to proxy to Workers' }), {
      status: 502,
      headers: { 'Content-Type': 'application/json' },
    });
  }
}
