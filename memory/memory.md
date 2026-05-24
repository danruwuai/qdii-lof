# MEMORY.md

## 用户信息
- [用户档案](user_profile.md) — Windows 环境，Claude Hub 配置，额度刷新习惯

## 项目信息
- [项目状态](project_status.md) — QDII 小程序，排序筛选功能待实施

## 配置要点
- Claude Hub 使用 `find` 命令定位插件目录（glob 模式在 Windows + Git Bash 下不匹配）
- 额度快照路径使用 Windows 格式 `C:/Users/...`（POSIX 格式 `/c/...` Node.js 无法解析）
- 定期运行 `python3 ~/.claude/plugins/claude-hud/usage_snapshot.py` 刷新额度数据
