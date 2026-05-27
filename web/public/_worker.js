/**
 * QDII LOF ETF 溢价率监控 - Cloudflare Pages Worker
 * 代理所有 API 请求到 Worker
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const path = url.pathname;

    // API 请求全部代理到 Worker
    if (path.startsWith('/api/') || path === '/health') {
      // 使用 Worker 的直接 URL 进行代理
      const workerUrl = 'https://qdii-lof.980764131.workers.dev' + path + url.search;
      const newRequest = new Request(workerUrl, {
        method: request.method,
        headers: request.headers,
        body: request.body
      });

      try {
        return await fetch(newRequest);
      } catch (error) {
        return new Response(JSON.stringify({
          error: 'Worker error',
          message: error.message
        }), {
          status: 500,
          headers: { 'Content-Type': 'application/json' }
        });
      }
    }

    // 静态文件
    return env.ASSETS.fetch(request);
  }
};
