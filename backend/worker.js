// QDII LOF ETF 溢价率监控 - Cloudflare Workers
// 使用 D1 数据库

// D1 数据库绑定
// export interface Env {
//   DB: D1Database;
//   JISILI_COOKIE: string;
// }

// Helper functions
async function dbQuery(sql, params) {
  const stmt = DB.prepare(sql);
  if (params) stmt.bind(...params);
  return await stmt.all();
}

async function dbFirst(sql, params) {
  const stmt = DB.prepare(sql);
  if (params) stmt.bind(...params);
  return await stmt.first();
}

// Router
const routes = {};

function addRoute(method, path, handler) {
  if (!routes[path]) routes[path] = {};
  routes[path][method] = handler;
}

// Health check
addRoute('GET', '/health', async () => {
  return Response.json({ status: 'ok' });
});

// Market status
addRoute('GET', '/api/v1/market-status', async () => {
  const now = new Date();
  const hour = now.getHours();
  const day = now.getDay();
  const isWeekday = day >= 1 && day <= 5;
  return Response.json({
    cn: isWeekday && (hour >= 9 && hour <= 15) ? 'open' : 'closed',
    hk: isWeekday && (hour >= 9 && hour <= 16) ? 'open' : 'closed',
    us: isWeekday && (hour >= 21 || hour < 4) ? 'open' : 'closed',
    jp: isWeekday && (hour >= 8 && hour <= 15) ? 'open' : 'closed',
    eu: isWeekday && (hour >= 14 && hour <= 21) ? 'open' : 'closed',
    timestamp: now.toISOString(),
  });
});

// Funds list
addRoute('GET', '/api/v1/funds', async (c) => {
  const url = new URL(c.url);
  const sp = url.searchParams;
  let sql = 'SELECT * FROM funds WHERE 1=1';
  const params = [];

  if (sp.get('fund_type')) { sql += ' AND fund_type = ?'; params.push(sp.get('fund_type')); }
  if (sp.get('region')) { sql += ' AND tracking_region = ?'; params.push(sp.get('region')); }
  if (sp.get('search')) { sql += ' AND (code LIKE ? OR name LIKE ?)'; params.push('%' + sp.get('search') + '%', '%' + sp.get('search') + '%'); }
  if (sp.get('tab') === 'QDII-ETF') { sql += " AND fund_type LIKE '%QDII%' AND fund_type LIKE '%ETF%'"; }
  else if (sp.get('tab') === 'QDII-LOF') { sql += " AND fund_type LIKE '%QDII%' AND fund_type LIKE '%LOF%'"; }
  else if (sp.get('tab') === 'ETF') { sql += " AND fund_type = 'ETF'"; }
  else if (sp.get('tab') === 'LOF') { sql += " AND fund_type = 'LOF'"; }

  const result = await dbQuery(sql, params);
  return Response.json({ items: result.results || [], total: (result.results || []).length });
});

// Fund detail
addRoute('GET', '/api/v1/funds/:code', async (c) => {
  const code = c.params.code;
  const fund = await dbFirst('SELECT * FROM funds WHERE code = ?', [code]);
  if (!fund) return Response.json({ code, name: 'Unknown' }, { status: 404 });

  const holdings = await dbQuery('SELECT * FROM fund_holdings WHERE fund_code = ? ORDER BY holding_date DESC LIMIT 10', [code]);
  const history = await dbQuery('SELECT * FROM premium_snapshots WHERE fund_code = ? ORDER BY snapshot_time DESC LIMIT 200', [code]);

  return Response.json({
    ...fund,
    holdings: holdings.results || [],
    premium_history: history.results || [],
  });
});

// Search
addRoute('GET', '/api/v1/funds/search', async (c) => {
  const url = new URL(c.url);
  const q = url.searchParams.get('q') || '';
  const result = await dbQuery('SELECT code, name, fund_type FROM funds WHERE code LIKE ? OR name LIKE ? LIMIT 20', ['%' + q + '%', '%' + q + '%']);
  return Response.json(result.results || []);
});

// Watchlist
addRoute('GET', '/api/v1/watchlist', async (c) => {
  const url = new URL(c.url);
  const openid = url.searchParams.get('openid') || 'default_user';
  const watchlist = await dbQuery('SELECT * FROM user_watchlist WHERE user_openid = ?', [openid]);
  const codes = (watchlist.results || []).map(r => r.fund_code);
  if (codes.length === 0) return Response.json({ items: [], total: 0 });
  const funds = await dbQuery('SELECT * FROM funds WHERE code IN (' + codes.map(() => '?').join(',') + ')', codes);
  return Response.json({ items: funds.results || [], total: (funds.results || []).length });
});

addRoute('POST', '/api/v1/watchlist', async (c) => {
  const url = new URL(c.url);
  const openid = url.searchParams.get('openid') || 'default_user';
  const body = await c.req.json();
  const { fund_code } = body;
  if (!fund_code) return Response.json({ success: false }, { status: 400 });

  const existing = await dbFirst('SELECT * FROM user_watchlist WHERE user_openid = ? AND fund_code = ?', [openid, fund_code]);
  if (existing) return Response.json({ success: true, message: 'Already in watchlist' });

  await dbQuery('INSERT INTO user_watchlist (user_openid, fund_code) VALUES (?, ?)', [openid, fund_code]);
  return Response.json({ success: true });
});

addRoute('DELETE', '/api/v1/watchlist/:fund_code', async (c) => {
  const url = new URL(c.url);
  const openid = url.searchParams.get('openid') || 'default_user';
  const fundCode = c.params.fund_code;
  await dbQuery('DELETE FROM user_watchlist WHERE user_openid = ? AND fund_code = ?', [openid, fundCode]);
  return Response.json({ success: true });
});

// Alerts
addRoute('GET', '/api/v1/alerts', async (c) => {
  const url = new URL(c.url);
  const openid = url.searchParams.get('openid') || 'default_user';
  const result = await dbQuery('SELECT * FROM user_alerts WHERE user_openid = ?', [openid]);
  return Response.json({ items: result.results || [] });
});

addRoute('POST', '/api/v1/alerts', async (c) => {
  const url = new URL(c.url);
  const openid = url.searchParams.get('openid') || 'default_user';
  const body = await c.req.json();
  const { fund_code, threshold_above, threshold_below } = body;
  await dbQuery('INSERT INTO user_alerts (user_openid, fund_code, threshold_above, threshold_below) VALUES (?, ?, ?, ?)', [openid, fund_code, threshold_above, threshold_below]);
  return Response.json({ success: true });
});

addRoute('DELETE', '/api/v1/alerts/:alert_id', async (c) => {
  const alertId = c.params.alert_id;
  await dbQuery('DELETE FROM user_alerts WHERE id = ?', [alertId]);
  return Response.json({ success: true });
});

// Extract path params
function extractParams(path, route) {
  const params = {};
  const routeParts = route.split('/');
  const pathParts = path.split('/');
  routeParts.forEach((part, i) => {
    if (part.startsWith(':')) {
      params[part.slice(1)] = pathParts[i];
    }
  });
  return params;
}

// Main handler
export default {
  async fetch(request, env, ctx) {
    // Set global DB binding
    globalThis.DB = env.DB;

    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // Simple routing
    if (routes[path] && routes[path][method]) {
      const handler = routes[path][method];
      return await handler({
        url: request.url,
        method: request.method,
        params: {},
        req: { json: async () => await request.json() }
      }, env, ctx);
    }

    // Check for path with params
    for (const [routePath, methods] of Object.entries(routes)) {
      if (routePath.includes(':')) {
        const base = routePath.split(':')[0];
        if (path.startsWith(base)) {
          const params = extractParams(path, routePath);
          if (methods[method]) {
            const handler = methods[method];
            return await handler({
              url: request.url,
              method: request.method,
              params: params,
              req: { json: async () => await request.json() }
            }, env, ctx);
          }
        }
      }
    }

    return Response.json({ error: 'Not found' }, { status: 404 });
  }
};
