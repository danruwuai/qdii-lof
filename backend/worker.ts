/**
 * QDII LOF ETF 溢价率监控 - Cloudflare Workers 版本
 * 使用 D1 数据库 + Cron Triggers 定时任务
 */

import { Hono } from 'hono';

// D1 数据库绑定（在 wrangler.jsonc 中配置）
interface Env {
  DB: D1Database;
  JISILI_COOKIE: string;
}

// 初始化 Hono 应用
const app = new Hono<{ Bindings: Env }>();

// ========== 数据库辅助函数 ==========

async function dbQuery(sql: string, params?: unknown[]) {
  const result = await env.DB.prepare(sql).bind(...(params || [])).all();
  return result;
}

async function dbFirst(sql: string, params?: unknown[]) {
  const result = await env.DB.prepare(sql).bind(...(params || [])).first();
  return result;
}

// ========== 路由 ==========

// Health check
app.get('/health', async () => {
  return Response.json({ status: 'ok' });
});

// 市场状态
app.get('/api/v1/market-status', async () => {
  const now = new Date();
  const hour = now.getHours();
  const day = now.getDay(); // 0=Sunday

  // 简单判断：周一到周五的交易时段
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

// 基金列表
app.get('/api/v1/funds', async (c) => {
  const { searchParams } = new URL(c.req.url);
  const fundType = searchParams.get('fund_type');
  const region = searchParams.get('region');
  const search = searchParams.get('search');
  const tab = searchParams.get('tab') || 'all';
  const page = parseInt(searchParams.get('page') || '1');
  const pageSize = Math.min(parseInt(searchParams.get('page_size') || '50'), 1000);

  let sql = 'SELECT * FROM funds WHERE 1=1';
  const params: unknown[] = [];

  if (fundType) {
    sql += ' AND fund_type = ?';
    params.push(fundType);
  }
  if (region) {
    sql += ' AND tracking_region = ?';
    params.push(region);
  }
  if (search) {
    sql += ' AND (code LIKE ? OR name LIKE ?)';
    params.push(`%${search}%`, `%${search}%`);
  }
  if (tab === 'QDII-ETF') {
    sql += " AND fund_type LIKE '%QDII%' AND fund_type LIKE '%ETF%'";
  } else if (tab === 'QDII-LOF') {
    sql += " AND fund_type LIKE '%QDII%' AND fund_type LIKE '%LOF%'";
  } else if (tab === 'ETF') {
    sql += " AND fund_type = 'ETF'";
  } else if (tab === 'LOF') {
    sql += " AND fund_type = 'LOF'";
  }

  const result = await dbQuery(sql, params);
  const funds = result.results || [];

  return Response.json({
    items: funds,
    total: funds.length,
  });
});

// 基金详情
app.get('/api/v1/funds/:code', async (c) => {
  const code = c.req.param('code');

  const fund = await dbFirst('SELECT * FROM funds WHERE code = ?', [code]);
  if (!fund) {
    return Response.json({ code, name: '未知' }, { status: 404 });
  }

  // 持仓数据
  const holdingsResult = await dbQuery(
    'SELECT * FROM fund_holdings WHERE fund_code = ? ORDER BY holding_date DESC LIMIT 10',
    [code]
  );

  // 溢价历史（最近 200 条）
  const historyResult = await dbQuery(
    'SELECT * FROM premium_snapshots WHERE fund_code = ? ORDER BY snapshot_time DESC LIMIT 200',
    [code]
  );

  return Response.json({
    ...fund,
    holdings: holdingsResult.results || [],
    premium_history: historyResult.results || [],
  });
});

// 搜索基金
app.get('/api/v1/funds/search', async (c) => {
  const { searchParams } = new URL(c.req.url);
  const q = searchParams.get('q') || '';

  const result = await dbQuery(
    'SELECT code, name, fund_type FROM funds WHERE code LIKE ? OR name LIKE ? LIMIT 20',
    [`%${q}%`, `%${q}%`]
  );

  return Response.json(result.results || []);
});

// 监控列表
app.get('/api/v1/watchlist', async (c) => {
  const openid = c.req.query('openid') || 'default_user';

  const watchlistResult = await dbQuery(
    'SELECT * FROM user_watchlist WHERE user_openid = ?',
    [openid]
  );

  const codes = watchlistResult.results?.map((r: any) => r.fund_code) || [];

  if (codes.length === 0) {
    return Response.json({ items: [], total: 0 });
  }

  const fundsResult = await dbQuery(
    `SELECT * FROM funds WHERE code IN (${codes.map(() => '?').join(',')})`,
    codes
  );

  return Response.json({
    items: fundsResult.results || [],
    total: fundsResult.results?.length || 0,
  });
});

// 添加监控
app.post('/api/v1/watchlist', async (c) => {
  const openid = c.req.query('openid') || 'default_user';
  const body = await c.req.json();
  const { fund_code } = body;

  if (!fund_code) {
    return Response.json({ success: false, message: '缺少 fund_code' }, { status: 400 });
  }

  // 检查是否已存在
  const existing = await dbFirst(
    'SELECT * FROM user_watchlist WHERE user_openid = ? AND fund_code = ?',
    [openid, fund_code]
  );

  if (existing) {
    return Response.json({ success: true, message: '已在监控列表中' });
  }

  await dbQuery(
    'INSERT INTO user_watchlist (user_openid, fund_code) VALUES (?, ?)',
    [openid, fund_code]
  );

  return Response.json({ success: true });
});

// 移除监控
app.delete('/api/v1/watchlist/:fund_code', async (c) => {
  const openid = c.req.query('openid') || 'default_user';
  const fundCode = c.req.param('fund_code');

  await dbQuery(
    'DELETE FROM user_watchlist WHERE user_openid = ? AND fund_code = ?',
    [openid, fundCode]
  );

  return Response.json({ success: true });
});

// 提醒列表
app.get('/api/v1/alerts', async (c) => {
  const openid = c.req.query('openid') || 'default_user';

  const result = await dbQuery(
    'SELECT * FROM user_alerts WHERE user_openid = ?',
    [openid]
  );

  return Response.json({ items: result.results || [] });
});

// 创建提醒
app.post('/api/v1/alerts', async (c) => {
  const openid = c.req.query('openid') || 'default_user';
  const body = await c.req.json();
  const { fund_code, threshold_above, threshold_below } = body;

  await dbQuery(
    'INSERT INTO user_alerts (user_openid, fund_code, threshold_above, threshold_below) VALUES (?, ?, ?, ?)',
    [openid, fund_code, threshold_above, threshold_below]
  );

  return Response.json({ success: true });
});

// 删除提醒
app.delete('/api/v1/alerts/:alert_id', async (c) => {
  const alertId = c.req.param('alert_id');

  await dbQuery('DELETE FROM user_alerts WHERE id = ?', [alertId]);

  return Response.json({ success: true });
});

// ========== SSE 实时推送（替代 WebSocket）==========

app.get('/api/v1/realtime/stream', async (c) => {
  // SSE 流式响应
  const { readable, writable } = new TransformStream();
  const writer = writable.getWriter();
  const encoder = new TextEncoder();

  // 发送初始数据
  const initialData = {
    type: 'init',
    timestamp: new Date().toISOString(),
  };
  await writer.write(encoder.encode(`event: message\ndata: ${JSON.stringify(initialData)}\n\n`));

  // 这里实际应该连接到溢价率更新服务
  // 在 Workers 中，可以使用 Durable Objects 或 KV 轮询来实现

  return new Response(readable, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    },
  });
});

// 获取最新溢价率（轮询接口）
app.get('/api/v1/realtime/premiums', async (c) => {
  const { searchParams } = new URL(c.req.url);
  const codes = searchParams.get('codes')?.split(',') || [];

  if (codes.length === 0) {
    // 返回所有基金的最新溢价快照
    const result = await dbQuery(
      `SELECT fs.*, ps.premium_rate, ps.calc_method, ps.snapshot_time
       FROM funds fs
       LEFT JOIN (
         SELECT * FROM premium_snapshots
         WHERE id IN (
           SELECT MAX(id) FROM premium_snapshots GROUP BY fund_code
         )
       ) ps ON fs.code = ps.fund_code`
    );
    return Response.json(result.results || []);
  } else {
    // 返回指定基金的溢价率
    const placeholders = codes.map(() => '?').join(',');
    const result = await dbQuery(
      `SELECT fs.*, ps.premium_rate, ps.calc_method, ps.snapshot_time
       FROM funds fs
       LEFT JOIN (
         SELECT * FROM premium_snapshots
         WHERE id IN (
           SELECT MAX(id) FROM premium_snapshots GROUP BY fund_code
         )
       ) ps ON fs.code = ps.fund_code
       WHERE fs.code IN (${placeholders})`,
      codes
    );
    return Response.json(result.results || []);
  }
});

export default app;
