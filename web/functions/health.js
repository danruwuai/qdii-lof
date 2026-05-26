/**
 * Cloudflare Pages Function
 * 拦截 /health 请求，代理到 Workers
 */

export async function onRequest(context) {
  const { request, env } = context;
  const url = new URL(request.url);

  const workerUrl = `https://qdii-lof.980764131.workers.dev${url.pathname}${url.search}`;

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
