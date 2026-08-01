# STATUS

## [2026-08-01] v0.2.0 发布 — 持仓与收益显示

### 现状
- v0.2.0 已发布至 PyPI：持仓管理（`pos add/rm/list`，交互式多选录入）、TUI 按 `t` 切换持仓/成本/持仓收益/今日收益列与底部汇总、全英文 UI（伪装设计）、README 截图更新。
- 30 个测试全绿；包级 ruff/format 通过；本地构建 0.2.0 sdist+wheel 成功。
- 顺手修复历史遗留：boss.py 两处 lint、ci.yml `astock/` 路径 bug。

### 计划
- 功能分支已合并 main，tag `v0.2.0`，GitHub Release 触发 Trusted Publishing 到 PyPI。

### 待办
- [x] 版本号 0.1.0 → 0.2.0（pyproject / README badge / CHANGELOG）— P0
- [x] 截图重新生成（normal / boss / demo GIF）+ 生成脚本 — P1
- [x] 推送分支 → 合并 main → tag → Release 发布 PyPI — P0

## [2026-08-01] feature/holdings — 持仓与收益显示

### 现状
- 持仓功能完成：`[holdings]` 配置读写、CLI `pos add/rm/list`（`add` 交互式多选录入）、TUI 按 `t` 循环 4 种显示模式、收益红盈绿亏着色、底部汇总随 `t` 切换、全英文 UI。
- 30 个测试全绿；改动文件 ruff/format 通过。
