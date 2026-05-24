# QDII LOF ETF 实时溢价率监控

类似集思录的微信小程序，用于监控 QDII、LOF 和 ETF 的实时溢价率和估值。

## 功能

- **实时溢价率计算**：三种算法（指数跟踪 / 持仓加权 / T-1 净值兜底）
- **申购信息**：是否可申购、申购限额、场内/场外、买卖状态
- **混合数据源**：akshare + 东方财富 + 天天基金 + 集思录
- **监控列表**：自定义关注标的
- **溢价提醒**：溢价率超阈值推送通知
- **WebSocket 实时推送**：交易时间内自动刷新

## 快速启动

### 后端

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env
# 编辑 .env，填入集思录 cookie（可选）
python seed.py          # 初始化数据库
python main.py          # 启动服务，访问 http://localhost:8000/docs
```

### 小程序

1. 打开微信开发者工具
2. 导入 `miniprogram` 目录
3. 修改 `app.js` 中的 `BASE_URL` 为后端地址
4. 编译预览

## 溢价率计算

| 方法 | 说明 | 适用场景 |
|------|------|---------|
| Type A | 指数跟踪法：nav_t2 × (1 + 指数涨跌幅 × 仓位比 + 汇率变动) | 指数型 QDII |
| Type B | 持仓加权法：Σ(持仓权重 × 资产涨跌幅) | 有完整持仓数据的基金 |
| Type C | 简单兜底：(价格 - T-1净值) / T-1净值 | 无法使用 A/B 时 |

## 项目结构

```
backend/          # FastAPI 后端
  data_sources/   # 数据源（akshare、东方财富、天天基金、集思录）
  services/       # 业务逻辑（计算、调度、提醒）
  utils/          # 工具（指数映射、汇率）
  api/            # REST + WebSocket 路由
miniprogram/      # 微信小程序
  pages/          # 页面
  components/     # 组件
  utils/          # 工具函数
```

## 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| JISILI_COOKIE | 集思录 cookie | 空 |
| DATABASE_URL | 数据库连接 | sqlite:///./data/qdii.db |
| PORT | 服务端口 | 8000 |
