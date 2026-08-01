# BossKey-Stock — 终端摸鱼盯盘工具

终端摸鱼盯盘工具。Sina Finance API 获取盘中数据，Rich Live 渲染，按 `b` 键一键切换 Docker 编译日志伪装界面。

---

## 技术栈

| 层级 | 选型 | 说明 |
|------|------|------|
| 语言 | Python 3.10+ | 标准库 + 三个第三方包 |
| 数据源 | [Sina Finance 实时行情 API](https://hq.sinajs.cn/) | 免费，无需 API Key |
| 终端 UI | Rich Live + HORIZONTALS box | 保留终端默认背景色，无纵向边框 |
| 配置 | TOML (tomlkit) | 用户配置文件 `~/.bosskey.toml` |

## 架构

```
bosskey-stock/
├── pyproject.toml            # 打包配置，CLI entry point
├── docs/design.md            # 本文档
└── bosskey_stock/
    ├── __init__.py            # 包标记
    ├── __main__.py            # CLI 入口，子命令路由（49 行）
    ├── app.py                 # 主循环：Rich Live + 非阻塞键盘输入（211 行）
    ├── data.py                # Sina 数据层，解析 GBK 编码响应（103 行）
    ├── boss.py                # 老板模式伪装内容（72 行）
    └── config.py              # 配置读写（56 行）
```

## CLI 命令

| 命令 | 功能 |
|------|------|
| `bosskey run` | 启动监控界面（默认子命令） |
| `bosskey add 000001 600519` | 添加股票到监控列表 |
| `bosskey rm 000001` | 从监控列表移除股票 |
| `bosskey list` | 查看当前监控列表 |
| `bosskey pos add` | 交互式添加/更新持仓 |
| `bosskey pos rm CODE` | 移除持仓 |
| `bosskey pos list` | 查看全部持仓 |

底层数据存 `~/.bosskey.toml`。

### 持仓录入（交互式）

`bosskey pos add` 无参数，纯交互（提示全英文）：

1. 列出 watchlist 全部代码（已有持仓标 `*`），按编号逗号多选（如 `1,3`，回车取消）。
2. 对每个选中代码逐个提示 `Shares:`（正整数）与 `Cost:`（正数），带校验，无效输入重试。
3. 全部录入后写入 `[holdings]` 并输出 `Saved:` 确认。

## 配置文件

```toml
[display]
refresh_interval = 3

[watchlist]
codes = ["000001", "600519", "300750"]

[holdings]
# code = { shares = 持仓股数, cost = 成本价 }
600519 = { shares = 100, cost = 1500.50 }
```

无需 API Key，首次运行无配置时自动创建默认配置。

## 核心功能

### 行情展示

- 表格列：Code \| Name \| Price \| Chg% \| Chg \| Vol \| Open \| High \| Low
- 红涨绿跌（A 股惯例），**整行 9 列全部**应用红绿色（`red3` / `green3`）
- 仅横向分割线（`box=HORIZONTALS`），无纵向边框，无 `│` 竖线
- 表头不加粗（`header_style=""`），所有数据不加粗
- 成交量显示格式：`N`（<1 万手）→ `N.XX万`（≥1 万手）→ `N.XX亿`（≥1 亿手）

### 自动刷新

- 默认 3 秒刷新，可配置
- **交易时段**（9:30-11:30、13:00-15:00，仅工作日）内自动刷新，表格下方显示 `Last update: HH:MM:SS`（本地刷新时间）
- **非交易时段**不自动刷新，表格下方显示 `Last trade: 日期 时间`（数据源最后成交时间），前缀 `[After Hours]`
- 按 `r` 可手动刷新（非交易时段也可用）

### 持仓与收益显示

按 `t` 键在 4 种显示模式间循环（仅内存态，不持久化）：

| 模式 | 追加列 | 说明 |
|------|--------|------|
| 0 | 无 | 基础行情（默认） |
| 1 | `Pos` `Cost` | 持仓股数、成本价（中性色） |
| 2 | `HoldP/L` `HoldP/L%` | 持仓收益额、持仓收益率 |
| 3 | `TodayP/L` `TodayP/L%` | 今日收益额、今日收益率 |

计算公式（`shares` 持仓股数、`cost` 成本价、`price` 现价、`change` 今日涨跌额）：

- 持仓收益 = `(price - cost) × shares`；持仓收益率 = `(price - cost) / cost × 100`
- 今日收益 = `change × shares`；今日收益率 = `change_pct`

收益列按自身符号着色（正红 `red3` 负绿 `green3`，零/空无色），不再跟随整行行情色；无持仓或数据缺失显示 `--`。状态栏右侧显示当前启用的列组（英文 `Cols:`）。

**底部汇总**：`t` 切换时底部同步追加持仓汇总行（仅 mode>0 显示），全部英文：

| 模式 | 汇总内容 |
|------|----------|
| ≥1 | `Value <总市值> · Cost <总成本>` |
| ≥2 | 追加 `HoldP/L <总收益额> (<总收益率>%)` |
| ≥3 | 追加 `TodayP/L <今日收益额> (<今日收益率>%)` |

- 总市值 = Σ 现价×股数；总成本 = Σ 成本×股数；总收益 = 总市值 − 总成本；总收益率 = 总收益 / 总成本。
- 今日收益率 = 今日收益 / 昨日市值（Σ 昨收×股数），昨收缺失时退回按总成本。
- 收益金额与收益率按符号红绿着色。

> 15 列全开时建议较宽终端。

### 英文 UI（伪装设计）

界面与 CLI 交互刻意全英文：表头、状态栏、`pos add` 交互提示、`add/rm/list` 输出均无中文。理由：英文非母语，不会被一眼读懂，与老板模式一起构成「在工作」的伪装（决策见 `.claude/DECISIONS.md`）。

### 老板模式

按 `b` 键切换：

| 模式 | 显示内容 |
|------|---------|
| 正常模式 | 红绿配色的行情表格 |
| 老板模式 | 模拟 Docker build 日志，随机生成步骤，底部显示运行时间 |

再按 `b` 切回行情。状态仅在内存中，不持久化。

### TUI 内操作

| 按键 | 功能 |
|------|------|
| `b` | 老板模式切换 |
| `q` / `Ctrl+C` | 退出（终端完全恢复，无 traceback） |
| `r` | 手动刷新 |
| `t` | 循环切换持仓/收益显示模式 |

## 键盘输入实现

无需后台线程。一次 `tcsetattr` 完成终端配置：

- 仅修改 **输入侧** 参数：关掉 `ICANON`（逐键输入）、`ECHO`（不回显）、`ISIG`（不发信号）
- **保留输出侧** `OPOST`，确保 `\n` → `\r\n` 转换正常，Rich 输出不受影响
- 主循环调用 `select.select([fd], [], [], 0.5)` 等待按键或超时
- 按键用 `os.read(fd, 1).decode()` 读取（绕过 Python stdio 缓冲）

## 数据层

### Sina Finance API

- 接口：`https://hq.sinajs.cn/list=sh600519,sz000001,...`
- 需要 `Referer: https://finance.sina.com.cn` 请求头
- 响应编码：GBK
- 返回值包含：名称、开、昨收、现价、高、低、成交量（股）、成交额
- 本地计算涨跌额和涨跌幅

### 代码前缀转换

| 代码开头 | Sina 前缀 |
|----------|-----------|
| 6 / 9 | `sh`（上海） |
| 其他（0 / 3 等） | `sz`（深圳） |

### 字段映射

从 Sina 32+ 个字段中提取：

| 索引 | 字段 |
|------|------|
| 0 | name |
| 1 | open |
| 2 | pre_close |
| 3 | price |
| 4 | high |
| 5 | low |
| 8 | vol（股） |
| 9 | amount |
| 30 | date |
| 31 | time |

### 股票代码解析

正则 `hq_str_[a-z]+(\d+)="` 从 JS 变量名提取，**保留前导零**（如 `000001`）。

### 错误处理

| 场景 | 表现 |
|------|------|
| 网络异常 / 超时 | 所有行维持上次数据，状态栏显示 `[Offline]`（黄色加粗） |
| 无效股票代码 | 静默跳过，不加入结果列表 |

## 老板模式细节

伪装内容为 Docker build 日志，特征：

- `Step N/M : FROM python:3.12-slim` / `RUN pip install pkg==x.y.z` / `COPY . /app` / `WORKDIR /app` / `apt-get install ...`
- 偶尔穿插 `WARNING: package X has requirement Y, but you'll have incompatible version Z`
- 底部显示 `Running time: MM:SS`
- 日志预生成后 5 倍重复，每秒滚动 2 行，首行固定为 `$ docker build -t app:latest .`

## 状态栏

位于表格正下方，状态优先级：

| 条件 | 显示 |
|------|------|
| 网络断开 | `[Offline]`（黄色加粗） |
| 非交易时段 | `[After Hours] Last trade: 2026-07-30 16:30:00` |
| 交易时段 | `Last update: 14:30:00` |

颜色：`[After Hours]` 用 `bright_black`（灰色），深色和浅色终端均可见。

## 安装与运行

### pip 安装

```bash
pip install bosskey-stock
```

### 开发模式（可编辑，改代码立即生效）

```bash
git clone https://github.com/shark/bosskey-stock.git
cd bosskey-stock
pip install -e .
```

安装后直接使用 `bosskey` 命令：

```bash
bosskey run
bosskey add 600519
bosskey rm 000001
bosskey list
```

### 打包为独立二进制

```bash
pip install pyinstaller
pyinstaller --onefile -n bosskey bosskey_stock/__main__.py
# 产物在 dist/bosskey
```

## 依赖

```
rich>=13.0
tomlkit>=0.12
requests>=2.28
```

无 textual、无 tushare、无 curses。

## 截图生成

`README.md` 的截图由 `scripts/make_screenshots.py` 生成，可复现：

- 静态 SVG（`screenshot-normal.svg` / `screenshot-boss.svg`）：直接用 Rich `Console.export_svg` 渲染 TUI 视图（含 mode 3 持仓列与底部汇总）。
- 演示 GIF（`screenshot-demo.gif`）：逐帧渲染 4 种显示模式 + 老板模式为 SVG → macOS `qlmanage` 栅格化为 PNG → PIL 合成为循环动画。

```bash
python scripts/make_screenshots.py          # 全部重新生成
python scripts/make_screenshots.py --gif-only   # 只更新 demo GIF
```

仅开发时使用，非运行时依赖。

---

> 最后更新：2026-07-30
