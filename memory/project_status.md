---
name: project_status
description: 小程序项目当前状态和待办事项
metadata:
  type: project
---

## 项目概述

QDII/LOF/ETF 实时溢价率监控微信小程序，类似集思录。

### 技术栈
- **后端**: Python + FastAPI + SQLite + APScheduler
- **前端**: 微信小程序（原生）
- **数据源**: akshare + 东方财富 push API + 天天基金 JSONP + 集思录

### 核心文件
- `backend/services/nav_calculator.py` — 溢价率计算引擎 (Type A/B/C)
- `backend/utils/index_mapper.py` — 基金代码→底层指数映射
- `miniprogram/pages/index/index.js` — 列表页逻辑
- `miniprogram/pages/index/index.wxml` — 列表页模板

## 待完成功能

### 排序筛选功能增强
**计划文件**: `C:\Users\zgj\.claude\plans\cozy-finding-walrus.md`

当前状态：已规划，未实施

需要完成：
1. **后端**: 添加 `sort_dir` 参数支持升序/降序
2. **前端**: 添加升序/降序切换指示器 (↑/↓)
3. **前端**: 添加更多排序字段（估算净值、成交量、申购限额）
4. **前端**: 添加筛选功能（申购状态、溢价等级、套利类型、跟踪地区）
