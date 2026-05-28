// QDII LOF ETF 溢价率监控 - Cloudflare Workers
// 使用 D1 数据库

// Helper functions - CRITICAL: bind() returns a NEW PreparedStatement, must capture return value
async function dbQuery(db, sql, params) {
  let stmt = db.prepare(sql);
  if (params && params.length > 0) {
    stmt = stmt.bind(...params);
  }
  return await stmt.all();
}

async function dbFirst(db, sql, params) {
  let stmt = db.prepare(sql);
  if (params && params.length > 0) {
    stmt = stmt.bind(...params);
  }
  return await stmt.first();
}

// Router
const routes = {};

function addRoute(method, path, handler) {
  if (!routes[path]) routes[path] = {};
  routes[path][method] = handler;
}

// Helper to get DB from context
function getDB(c) {
  return c.env?.DB || globalThis.DB;
}

// Health check
addRoute('GET', '/health', async (c) => {
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

// Helper to calculate premium rate
function calcPremiumRate(fund) {
  if (fund.market_price && fund.nav && fund.nav > 0) {
    return ((fund.market_price - fund.nav) / fund.nav * 100);
  }
  return null;
}

// Determine NAV accuracy label based on tracking region and nav_date
function getNavAccuracyLabel(fund) {
  // QDII funds: T-2 delay
  if (fund.tracking_region && ['US', 'JP', 'EU', 'IN', 'SA', 'BR', 'HK+US', 'HK+IN+TW', 'IN+KR+TW', 'HK+JP+AU'].includes(fund.tracking_region)) {
    return 'T-2';
  }
  // HK funds: T-1 delay
  if (fund.tracking_region && ['HK', 'CN+KR'].includes(fund.tracking_region)) {
    return 'T-1';
  }
  // Default: estimated (no confirmed NAV)
  return fund.nav_accuracy || 'T-2';
}

// Add premium info to fund object
function addPremiumInfo(fund) {
  const premiumRate = calcPremiumRate(fund);
  const navAccuracy = getNavAccuracyLabel(fund);

  return {
    ...fund,
    change_pct: fund.change_pct !== null && fund.change_pct !== undefined ? fund.change_pct : null,
    premium: premiumRate !== null ? {
      premium_rate: Math.round(premiumRate * 100) / 100, // round to 2 decimal places
      nav_date: fund.nav_date,
      nav_accuracy: navAccuracy,
      // Explicitly mark as estimated for QDII
      is_estimated: true,
      note: `基于${navAccuracy}净值估算`
    } : null
  };
}

// Funds list
addRoute('GET', '/api/v1/funds', async (c) => {
  const db = getDB(c);
  if (!db) {
    return Response.json({ error: 'Database not available' }, { status: 500 });
  }
  const url = new URL(c.url);
  const sp = url.searchParams;
  let sql = 'SELECT * FROM funds WHERE 1=1';
  const params = [];

  // Tab filter
  const tab = sp.get('tab');
  if (tab === 'QDII-ETF') { sql += " AND fund_type LIKE '%QDII%' AND fund_type LIKE '%ETF%'"; }
  else if (tab === 'QDII-LOF') { sql += " AND fund_type LIKE '%QDII%' AND fund_type LIKE '%LOF%'"; }
  else if (tab === 'ETF') { sql += " AND fund_type = 'ETF'"; }
  else if (tab === 'LOF') { sql += " AND fund_type = 'LOF'"; }
  else if (tab === 'arbitrage') {
    sql += " AND ((market_price - nav) / nav * 100 > 2 OR arbitrage_type IS NOT NULL)";
  }
  else if (tab === 'watchlist') {
    const openid = sp.get('openid') || 'default_user';
    const watchlist = await dbQuery(db, 'SELECT fund_code FROM user_watchlist WHERE user_openid = ?', [openid]);
    const codes = (watchlist.results || []).map(r => r.fund_code);
    if (codes.length === 0) {
      return Response.json({ items: [], total: 0 });
    }
    sql += ` AND code IN (${codes.map(() => '?').join(',')})`;
    params.push(...codes);
  }

  // Additional filters
  if (sp.get('region')) { sql += ' AND tracking_region = ?'; params.push(sp.get('region')); }
  if (sp.get('search')) { sql += ' AND (code LIKE ? OR name LIKE ?)'; params.push('%' + sp.get('search') + '%', '%' + sp.get('search') + '%'); }
  if (sp.get('premium_level') === 'high') { sql += " AND (market_price - nav) / nav * 100 > 5"; }
  else if (sp.get('premium_level') === 'normal') { sql += " AND (market_price - nav) / nav * 100 BETWEEN 0 AND 5"; }
  else if (sp.get('premium_level') === 'discount') { sql += " AND (market_price - nav) / nav * 100 < 0"; }
  if (sp.get('can_subscribe') !== undefined) { sql += ' AND can_subscribe = ?'; params.push(sp.get('can_subscribe') === 'yes' ? 1 : 0); }

  // Sorting
  const sortField = sp.get('sort');
  const sortDir = sp.get('sort_dir') === 'asc' ? 'ASC' : 'DESC';
  if (sortField) {
    const allowedSortFields = ['premium_rate', 'change_pct', 'volume', 'daily_limit', 'code', 'name', 'market_price', 'nav'];
    if (allowedSortFields.includes(sortField)) {
      if (sortField === 'premium_rate') {
        sql = sql.replace('SELECT *', "SELECT *, ((market_price - nav) / nav * 100) AS premium_rate_calc");
        sql += ` ORDER BY premium_rate_calc ${sortDir}`;
      } else {
        sql += ` ORDER BY ${sortField} ${sortDir}`;
      }
    }
  }

  // Pagination
  const page = parseInt(sp.get('page')) || 1;
  const pageSize = Math.min(parseInt(sp.get('page_size')) || 20, 100);
  const offset = (page - 1) * pageSize;
  sql += ' LIMIT ? OFFSET ?';
  params.push(pageSize, offset);

  try {
    const result = await dbQuery(db, sql, params);
    const items = (result.results || []).map(addPremiumInfo);

    // Get total count for pagination
    let countSql = 'SELECT COUNT(*) as total FROM funds WHERE 1=1';
    const tab2 = sp.get('tab');
    if (tab2 === 'QDII-ETF') { countSql += " AND fund_type LIKE '%QDII%' AND fund_type LIKE '%ETF%'"; }
    else if (tab2 === 'QDII-LOF') { countSql += " AND fund_type LIKE '%QDII%' AND fund_type LIKE '%LOF%'"; }
    else if (tab2 === 'ETF') { countSql += " AND fund_type = 'ETF'"; }
    else if (tab2 === 'LOF') { countSql += " AND fund_type = 'LOF'"; }
    else if (tab2 === 'arbitrage') { countSql += " AND ((market_price - nav) / nav * 100 > 2 OR arbitrage_type IS NOT NULL)"; }
    else if (tab2 === 'watchlist') {
      const openid2 = sp.get('openid') || 'default_user';
      const watchlist2 = await dbQuery(db, 'SELECT fund_code FROM user_watchlist WHERE user_openid = ?', [openid2]);
      const codes2 = (watchlist2.results || []).map(r => r.fund_code);
      if (codes2.length === 0) {
        return Response.json({ items: [], total: 0 });
      }
      countSql += ` AND code IN (${codes2.map(() => '?').join(',')})`;
      const countResult = await dbFirst(db, countSql, codes2);
      const total = countResult?.total || 0;
      return Response.json({ items, total });
    }

    if (sp.get('premium_level') === 'high') { countSql += " AND (market_price - nav) / nav * 100 > 5"; }
    else if (sp.get('premium_level') === 'normal') { countSql += " AND (market_price - nav) / nav * 100 BETWEEN 0 AND 5"; }
    else if (sp.get('premium_level') === 'discount') { countSql += " AND (market_price - nav) / nav * 100 < 0"; }

    const countResult = await dbFirst(db, countSql, []);
    const total = countResult?.total || 0;

    return Response.json({ items, total });
  } catch (err) {
    return Response.json({ error: err.message }, { status: 500 });
  }
});

// Fund detail
addRoute('GET', '/api/v1/funds/:code', async (c) => {
  const db = getDB(c);
  if (!db) {
    return Response.json({ error: 'Database not available' }, { status: 500 });
  }
  const code = c.params.code;
  try {
    const fund = await dbFirst(db, 'SELECT * FROM funds WHERE code = ?', [code]);
    if (!fund) return Response.json({ code, name: 'Unknown' }, { status: 404 });

    const holdings = await dbQuery(db, 'SELECT * FROM fund_holdings WHERE fund_code = ? ORDER BY holding_date DESC LIMIT 10', [code]);
    const history = await dbQuery(db, 'SELECT * FROM premium_snapshots WHERE fund_code = ? ORDER BY snapshot_time DESC LIMIT 200', [code]);

    return Response.json({
      ...addPremiumInfo(fund),
      holdings: holdings.results || [],
      premium_history: history.results || [],
    });
  } catch (err) {
    return Response.json({ error: err.message }, { status: 500 });
  }
});

// Search
addRoute('GET', '/api/v1/funds/search', async (c) => {
  const db = getDB(c);
  if (!db) {
    return Response.json({ error: 'Database not available' }, { status: 500 });
  }
  const url = new URL(c.url);
  const q = url.searchParams.get('q') || '';
  const likePattern = '%' + q + '%';
  try {
    const result = await dbQuery(db, `SELECT code, name, fund_type, market_price, nav, nav_date, nav_accuracy FROM funds WHERE code LIKE ? OR name LIKE ? LIMIT 20`, [likePattern, likePattern]);
    const items = (result.results || []).map(addPremiumInfo);
    return Response.json(items);
  } catch (err) {
    return Response.json({ error: err.message }, { status: 500 });
  }
});

// Watchlist
addRoute('GET', '/api/v1/watchlist', async (c) => {
  const db = getDB(c);
  if (!db) {
    return Response.json({ error: 'Database not available' }, { status: 500 });
  }
  const url = new URL(c.url);
  const openid = url.searchParams.get('openid') || 'default_user';
  try {
    const watchlist = await dbQuery(db, 'SELECT * FROM user_watchlist WHERE user_openid = ?', [openid]);
    const codes = (watchlist.results || []).map(r => r.fund_code);
    if (codes.length === 0) return Response.json({ items: [], total: 0 });
    const funds = await dbQuery(db, 'SELECT * FROM funds WHERE code IN (' + codes.map(() => '?').join(',') + ')', codes);
    const items = (funds.results || []).map(addPremiumInfo);
    return Response.json({ items, total: items.length });
  } catch (err) {
    return Response.json({ error: err.message }, { status: 500 });
  }
});

addRoute('POST', '/api/v1/watchlist', async (c) => {
  const db = getDB(c);
  if (!db) {
    return Response.json({ error: 'Database not available' }, { status: 500 });
  }
  const url = new URL(c.url);
  const openid = url.searchParams.get('openid') || 'default_user';

  let body;
  try {
    body = await c.req.json();
  } catch {
    return Response.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { fund_code } = body;
  if (!fund_code) return Response.json({ success: false }, { status: 400 });

  try {
    const existing = await dbFirst(db, 'SELECT * FROM user_watchlist WHERE user_openid = ? AND fund_code = ?', [openid, fund_code]);
    if (existing) return Response.json({ success: true, message: 'Already in watchlist' });
    await dbQuery(db, 'INSERT INTO user_watchlist (user_openid, fund_code) VALUES (?, ?)', [openid, fund_code]);
    return Response.json({ success: true });
  } catch (err) {
    return Response.json({ error: err.message }, { status: 500 });
  }
});

addRoute('DELETE', '/api/v1/watchlist/:fund_code', async (c) => {
  const db = getDB(c);
  if (!db) {
    return Response.json({ error: 'Database not available' }, { status: 500 });
  }
  const url = new URL(c.url);
  const openid = url.searchParams.get('openid') || 'default_user';
  const fundCode = c.params.fund_code;
  try {
    await dbQuery(db, 'DELETE FROM user_watchlist WHERE user_openid = ? AND fund_code = ?', [openid, fundCode]);
    return Response.json({ success: true });
  } catch (err) {
    return Response.json({ error: err.message }, { status: 500 });
  }
});

// Alerts
addRoute('GET', '/api/v1/alerts', async (c) => {
  const db = getDB(c);
  if (!db) {
    return Response.json({ error: 'Database not available' }, { status: 500 });
  }
  const url = new URL(c.url);
  const openid = url.searchParams.get('openid') || 'default_user';
  try {
    const result = await dbQuery(db, 'SELECT * FROM user_alerts WHERE user_openid = ?', [openid]);
    return Response.json({ items: result.results || [] });
  } catch (err) {
    return Response.json({ error: err.message }, { status: 500 });
  }
});

addRoute('POST', '/api/v1/alerts', async (c) => {
  const db = getDB(c);
  if (!db) {
    return Response.json({ error: 'Database not available' }, { status: 500 });
  }
  const url = new URL(c.url);
  const openid = url.searchParams.get('openid') || 'default_user';

  let body;
  try {
    body = await c.req.json();
  } catch {
    return Response.json({ error: 'Invalid JSON body' }, { status: 400 });
  }

  const { fund_code, threshold_above, threshold_below } = body;
  if (!fund_code) return Response.json({ success: false }, { status: 400 });

  try {
    await dbQuery(db, 'INSERT INTO user_alerts (user_openid, fund_code, threshold_above, threshold_below) VALUES (?, ?, ?, ?)', [openid, fund_code, threshold_above, threshold_below]);
    return Response.json({ success: true });
  } catch (err) {
    return Response.json({ error: err.message }, { status: 500 });
  }
});

addRoute('DELETE', '/api/v1/alerts/:alert_id', async (c) => {
  const db = getDB(c);
  if (!db) {
    return Response.json({ error: 'Database not available' }, { status: 500 });
  }
  const alertId = c.params.alert_id;
  try {
    await dbQuery(db, 'DELETE FROM user_alerts WHERE id = ?', [alertId]);
    return Response.json({ success: true });
  } catch (err) {
    return Response.json({ error: err.message }, { status: 500 });
  }
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
    // Set global DB binding as fallback
    globalThis.DB = env?.DB || null;

    const url = new URL(request.url);
    const path = url.pathname;
    const method = request.method;

    // Create context with env for DB access
    const context = {
      url: request.url,
      method: request.method,
      params: {},
      req: { json: async () => await request.json() },
      env: env,
      ctx: ctx
    };

    // Check exact match FIRST
    if (routes[path] && routes[path][method]) {
      const handler = routes[path][method];
      return await handler(context);
    }

    // Then check for path with params
    for (const [routePath, methods] of Object.entries(routes)) {
      if (routePath.includes(':')) {
        const colonIdx = routePath.indexOf(':');
        const base = routePath.substring(0, colonIdx);
        if (path.startsWith(base) && path.length > base.length) {
          const afterBase = path.substring(base.length);
          if (afterBase && afterBase !== '/') {
            const params = extractParams(path, routePath);
            if (methods[method]) {
              context.params = params;
              const handler = methods[method];
              return await handler(context);
            }
          }
        }
      }
    }

    // For SPA: serve index.html for non-API, non-file requests
    if (!path.includes('.') && !path.startsWith('/api/') && path !== '/health') {
      return env.ASSETS.fetch(new Request('http://localhost' + path, request));
    }

    // Fall back to static assets
    return env.ASSETS.fetch(request);
  }
};
