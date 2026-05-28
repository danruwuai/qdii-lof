# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

QDII/LOF/ETF 实时溢价率监控微信小程序。类似集思录，核心功能是基于计算得出准确的实时溢价率和实时估值。

## 技术栈

- **后端**: Python + FastAPI + SQLite + APScheduler
- **前端**: 微信小程序（原生）
- **数据源**: akshare + 东方财富 push API + 天天基金 JSONP + 集思录

## 目录结构

```
backend/
  main.py                 # FastAPI 入口 + lifespan
  config.py               # 环境变量配置
  database.py             # SQLite 连接管理
  models.py               # SQLAlchemy ORM (Fund, FundHolding, PremiumSnapshot, UserWatchlist, UserAlert)
  schemas.py              # Pydantic schemas
  data_sources/           # akshare, eastmoney, tiantian, jisilu 数据源
  services/
    nav_calculator.py     # 核心：Type A/B/C 溢价率计算引擎
    premium_service.py    # 溢价率内存缓存
    scheduler.py          # APScheduler 定时任务
    market_hours.py       # 市场状态检测 (CN/HK/US/JP/EU)
    alert_engine.py       # 提醒阈值检测
  api/                    # REST + WebSocket 路由
  utils/
    index_mapper.py       # 基金代码→底层指数映射（Type A 关键）
    exchange_rate.py      # 汇率获取
miniprogram/
  pages/                  # index(列表), detail(详情), watchlist(监控), alerts(提醒), settings(设置)
  components/             # fund-card, premium-badge
  utils/                  # api.js, websocket.js, format.js
```

## 常用命令

```bash
# 安装依赖
cd backend && pip install -r requirements.txt

# 初始化数据库（种子数据）
cd backend && python seed.py

# 启动后端服务
cd backend && python main.py

# 查看 Swagger API 文档
# 浏览器打开 http://localhost:8000/docs
```

## 核心计算逻辑

溢价率计算在 `backend/services/nav_calculator.py`，`calculate_premium()` 是统一入口，按优先级尝试：

1. **Type A（指数跟踪）**: `nav_t2 × (1 + 指数涨跌幅 × 仓位比 + 汇率变动)`
2. **Type B（持仓加权）**: `Σ(持仓权重 × 资产涨跌幅)`
3. **Type C（简单兜底）**: `(价格 - T-1净值) / T-1净值`

指数映射在 `backend/utils/index_mapper.py`，维护了基金代码到底层指数的映射表。

## 数据源

- `data_sources/akshare_source.py` — `fund_etf_spot_em()`, `fund_lof_spot_em()`, `fund_open_fund_info_em()`, `fund_portfolio_hold_em()`
- `data_sources/eastmoney_source.py` — push2.eastmoney.com 实时行情
- `data_sources/tiantian_source.py` — fundgz.1234567.com.cn JSONP 估算净值
- `data_sources/jisilu_source.py` — 集思录申购状态+限额（使用 Playwright 自动获取，无需 cookie）

## 注意事项

- 集思录数据通过 Playwright 无头浏览器自动获取，无需手动配置 cookie（需安装 `playwright` 和 Chromium）
- QDII 基金净值有 T+2 延迟，Type A 计算基于 T-2 NAV + 指数调整
- 小程序 WebSocket 断连后有 5 秒自动重连机制
- `index_mapper.py` 中的指数映射需要手动维护，新增基金需在此添加映射

## 防循环机制

### 项目级（代码中）

执行可能重复的操作前，使用 `backend/anti_loop_guard.py` 检查：

```bash
python backend/anti_loop_guard.py check <operation_name>
python backend/anti_loop_guard.py success <operation_name>
python backend/anti_loop_guard.py status
python backend/anti_loop_guard.py reset
```

### Claude Code 级（对话中）

当 Claude 陷入循环时，**用户可以直接说**：

> "检查循环守护状态"
> "强制恢复"
> "重置守护"

Claude 会自动运行：
```bash
python3 .claude/loop_guard.py status   # 查看状态
python3 .claude/loop_guard.py recover  # 强制恢复
python3 .claude/loop_guard.py reset    # 重置全部
```

**工作原理**：
- 每次工具调用前检查 `.claude/loop_guard.json`
- 统计最近 30 分钟内每种工具的调用次数
- 超过 3 次 → 标记为 BLOCKED，输出警告
- 60 秒后自动恢复，或手动 `recover`

**配置**（编辑 `.claude/loop_guard.json`）：
```json
{
  "config": {
    "max_repeats": 3,
    "window_seconds": 1800,
    "auto_recover": true,
    "recover_delay_seconds": 60
  }
}
```

**时间窗口**：默认 30 分钟，超过窗口后计数器自动重置。
