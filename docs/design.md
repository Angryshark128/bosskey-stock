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
    ├── __main__.py            # CLI 入口，子命令路由
    ├── app.py                 # 主循环：Rich Live + 非阻塞键盘输入
    ├── data.py                # Sina 数据层，解析 GBK 编码响应
    ├── boss.py                # 老板模式伪装内容
    ├── config.py              # 配置读写
    └── i18n.py                # 中英文案表与语言解析
```

## CLI 命令

| 命令 | 功能 |
|------|------|
| `bosskey run` | 启动监控界面（默认子命令） |
| `bosskey add CODE...` | 添加股票 / ETF / LOF / REITs / 债券 / 场外基金 |
| `bosskey rm CODE...` | 从监控列表移除代码 |
| `bosskey list` | 查看当前监控列表 |
| `bosskey group ...` | 管理分组（`add` / `rm` / `rename` / `list` / `add-codes` / `rm-codes`） |
| `bosskey pos add` | 交互式添加/更新持仓（份额支持小数） |
| `bosskey pos rm CODE` | 移除持仓 |
| `bosskey pos list` | 查看全部持仓 |

全局参数：`--lang {en,zh}` 指定本次运行**输出**的语言（只影响运行期输出，不影响帮助），`--list-langs` 列出支持语言。

**帮助文本一律中文**（`bosskey --help` / `bosskey add --help`），不随 `--lang` 切换、也不查 i18n 表 —— 它是给人读的用法说明，没必要让人为了看说明先猜语言。argparse 自带的框架词也一并中文化：`用法：` 前缀由 `_ZhHelpFormatter.add_usage()` 覆写（argparse 把它硬编码在 `HelpFormatter` 里），`参数` / `选项` 两个小标题与 `-h` 说明由 `_zh()` / `_sub()` 设置。

底层数据存 `~/.bosskey.toml`。

### 持仓录入（交互式）

`bosskey pos add` 无参数，纯交互（提示随语言切换）：

1. 列出 watchlist 全部代码（已有持仓标 `*`），按编号逗号多选（如 `1,3`，回车取消）。
2. 对每个选中代码逐个提示 `Shares:`（正数，整数照旧可用；场外基金是小数份额）与 `Cost:`（正数），带校验，无效输入重试。
3. 全部录入后写入 `[holdings]` 并输出 `Saved:` 确认。

## 配置文件

```toml
[display]
refresh_interval = 3
lang = "en"  # 界面语言：en / zh，TUI 内按 l 切换

[watchlist]
codes = ["000001", "600519", "300750"]

[holdings]
# code = { shares = 持仓份数, cost = 成本价 }
600519 = { shares = 100, cost = 1500.50 }
"fu:110022" = { shares = 352.4, cost = 2.8377 }  # 场外基金：份额是小数
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

按 `t` 键在 4 种显示模式间循环（仅内存态，不持久化）：**启动默认显示全部 14 列（mode 3）**，`t` 键从全列逐层收起持仓/收益列。

| 模式 | 追加列 | 说明 |
|------|--------|------|
| 0 | 无 | 基础行情 |
| 1 | `Pos` `Cost` | 持仓股数、成本价（中性色） |
| 2 | `HoldP/L` `HoldP/L%` | 持仓收益额、持仓收益率 |
| 3 | `TodayP/L` | 今日收益额（默认；今日收益率与基础列 `Chg%` 相同，不再重复展示） |

计算公式（`shares` 持仓股数、`cost` 成本价、`price` 现价、`change` 今日涨跌额）：

- 持仓收益 = `(price - cost) × shares`；持仓收益率 = `(price - cost) / cost × 100`
- 今日收益 = `change × shares`

收益列按自身符号着色（正红 `red3` 负绿 `green3`，零/空无色），不再跟随整行行情色；无持仓或数据缺失显示 `--`。状态栏右侧显示当前启用的列组（`Cols:` / `列:`）。

**底部汇总**：`t` 切换（或默认全列启动）时底部同步追加持仓汇总行（仅 mode>0 显示），全部英文：

| 模式 | 汇总内容 |
|------|----------|
| ≥1 | `Value <总市值> · Cost <总成本>` |
| ≥2 | 追加 `HoldP/L <总收益额> (<总收益率>%)` |
| ≥3 | 追加 `TodayP/L <今日收益额> (<今日收益率>%)` |

- 总市值 = Σ 现价×股数；总成本 = Σ 成本×股数；总收益 = 总市值 − 总成本；总收益率 = 总收益 / 总成本。
- 今日收益率 = 今日收益 / 昨日市值（Σ 昨收×股数），昨收缺失时退回按总成本。
- 收益金额与收益率按符号红绿着色。

> 14 列全开时建议较宽终端。

### 中英界面切换

默认英文（伪装设计），支持中文切换：

- **配置文件** `~/.bosskey.toml` 的 `[display] lang = "en"` 设初始语言（`en` / `zh`，未知值回落 `en`）。
- **TUI 内按 `l`** 会话内中英切换（仅内存态，不持久化，与 `t`/`b` 一致）。
- **CLI** 全局参数 `--lang {en,zh}` 单次覆盖运行期输出语言，`--list-langs` 列出支持语言。
- 文案集中在 `bosskey_stock/i18n.py`（key → (en, zh) 对照表），覆盖表头、状态栏、底部汇总、CLI 输出与 `pos add` 交互提示。**`--help` 不在表内**：帮助只提供中文，见 `_build_parser()`。
- 老板模式日志主体保持英文 Docker 命令（翻译反而穿帮），仅底部 `Running time:` 本地化。

### 英文 UI（伪装设计）

界面与 CLI 交互默认全英文：表头、状态栏、`pos add` 交互提示、`add/rm/list` 输出均无中文。理由：英文非母语，不会被一眼读懂，与老板模式一起构成「在工作」的伪装（决策见 `.claude/DECISIONS.md`）。中文仅在 `l` 键或配置显式切换时出现。

**例外：帮助文本恒为中文。** 帮助不会被同事一眼扫到（要主动敲 `--help`），伪装收益为零，却要人为了看说明先猜语言，不划算 —— 所以 `--help` 不走 i18n，`--lang` 也不影响它。

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
| `l` | 中英界面切换（会话内） |
| `h` | 底部快捷键提示开关 |

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
- 场内返回值包含：名称、开、昨收、现价、高、低、成交量（股）、成交额；场外基金（`fu_`）是另一套 10 字段布局，见下「字段映射」
- 本地计算涨跌额和涨跌幅

### 代码前缀转换

| 代码开头 / 前缀 | Sina 请求代码 |
|----------|-----------|
| 5 / 6 / 9 | `sh`（沪市 ETF/LOF/REITs 等场内基金、股票、B 股） |
| 沪市债券段：01 国债 / 110、113、118、71 转债 / 122、124、126、127 企业债 / 132 可交换 / 204 回购 | `sh` |
| 4 / 8 / 92 | `bj`（北交所） |
| 其余（0 / 1 / 2 / 3 等） | `sz`（深市股票、15/16/18 段场内基金、10-13 段债券） |
| 显式前缀 `fu:` | `fu_`（**下划线**连接，如 `fu:110022` → `fu_110022`；场内与指数是直接拼接，`sh:600519` → `sh600519`） |

`fu` 是唯一不能由段位规则得出的前缀 —— `default_prefix()` 只返回 `sh` / `sz` / `bj`，永远判不出场外基金；`make_key("fu", code)` 因此一定存成显式键 `fu:code`。

### 价格精度（`price_decimals`）

`data.price_decimals(key)` 是精度的唯一判定入口，行情层（涨跌额取整）与 TUI（价格/涨跌额/开高低渲染）共用，避免两处判定漂移。

| 类别 | 代码段 / 前缀 | 小数位 |
|------|--------|--------|
| 场外开放式基金 | 显式前缀 `fu:` | 4 |
| 场内基金 | 沪 5；深 15 / 16 / 18 | 3 |
| 债券 / 国债回购 | 沪市债券段；深 10-13 | 3 |
| 股票 / 北交所 | 其余 | 2 |

深市 18 段（REITs、封闭式基金，如 180101 蛇口产园）早期漏判为 2 位，现已纳入 3 位；沪市 508 段（REITs）因属 5 段本就正确。场外 4 位取自接口净值本身的小数位。

配套的展示细节：TUI 成本列（`app._fmt_price`）历史固定 3 位，故只有场外基金提到 4 位（`app._cost_decimals()`），其余品种零变化；份额列（`app._fmt_shares`）整数照旧显示、小数保留 2 位去尾零，容纳场外按金额申购得到的小数份额（1000 元 ÷ 2.8377 ≈ 352.4 份）。

### 存储键与同名代码消歧

监控列表 / 分组 / 持仓里存的是**存储键**：裸代码（`000001`）或带显式前缀的键（`sh:000001` / `fu:110022`）。

| 函数 | 作用 |
|------|------|
| `split_key(key)` | 键 → `(显式前缀 or None, 裸代码)`；前缀取自 `EXCHANGES` |
| `default_prefix(code)` | 段位规则：裸代码 → `sh` / `sz` / `bj`（**永不返回 `fu`**） |
| `make_key(prefix, code)` | 与规则一致时存裸代码，偏离规则才存 `sh:000001` / `fu:110022` |
| `sina_key(key)` | 键 → Sina 请求代码（有前缀直连，`fu:` 用下划线；否则走段位规则） |
| `probe(code, prefix=None)` | 探一个代码在各交易所的行情，返回 `[(前缀, 名称)]`，网络异常返回 `None`；未指定 prefix 时只探 `PROBE_EXCHANGES` |

两个集合要分清：`EXCHANGES = ("sh", "sz", "bj", "fu")` 是**可显式指定**的前缀（`split_key()` 用它判定），`PROBE_EXCHANGES = ("sh", "sz", "bj")` 是**裸代码默认探测**的交易所。分开是本次改动的关键 —— 场外代码段与 A 股/场内大面积重叠，若默认探测也带上 `fu`，`add 000001` 会多出一个「华夏成长混合A」候选，股票消歧体验被破坏。

`fetch()` 用 `sina_key()` 解析出请求代码，并把响应回填为原存储键（`code` 字段），使行情、持仓、分组按同一个键对齐；`price_decimals()` 只看显式 `fu:` 前缀与代码段，其余前缀不影响判定。

`_parse()` 用 `hq_str_([a-z]+)_?(\d+)="` 同时匹配 `hq_str_sh600519` 与 `hq_str_fu_110022`，按 `fu` 分派到 `_parse_fu()`；回填查表用的 Sina 代码由 `_join_sina()` 生成，与 `sina_key()` 同源，保证 `fu_110022` 能命中并回填成 `fu:110022`（否则持仓与分组会错位）。

CLI 层（`__main__.py`）在所有要填代码的管理命令（`add` / `rm` / `group add|add-codes|rm-codes` / `pos rm`）上用 `probe()` 消歧：
命中一个直接用；命中多个**不追问**，由 `_pick_by_rule()` 取段位规则那条并把另一条候选连同其强制前缀打成一行提示（如 `000001 = 平安银行（另有 上证指数 → sh:000001）`）；零命中提示「查无行情」（显式 `fu:` 命中空串时改提示「查不到净值 —— 代码不存在，或为不支持的场外货币基金」）；网络异常回退段位规则（离线可用）。
删除路径（`rm` / `group rm-codes` / `pos rm`）命中多条时仍由 `_choose_remove()` 列出候选让用户选一条或全部 —— 删除要明确，不做静默默认。

实测：会撞车的代码只有沪市 `000001`~`000999` 的上证系列指数（319 条）与深市同号段主板股票（506 只）的交集，**共 204 个**；这与「要不要给基金加前缀」无关，基金段位互斥、从不参与消歧。

### 字段映射

#### 场内（股票 / 场内基金 / 债券，32+ 字段）

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

#### 场外开放式基金（`fu_`，10 字段）

`fu_` 的行是另一套布局，比场内少得多：

| 索引 | 字段 | 映射到 |
|------|------|--------|
| 0 | 基金名称 | name |
| 1 | 估值时间 `HH:MM:SS` | trade_time |
| 2 | 当日估算净值 | price |
| 3 | 最近披露单位净值 | pre_close |
| 4 | 累计净值 | 未使用 |
| 5 | — | **未使用**（含义未确证） |
| 6 | 估算涨跌幅（%） | change_pct（解析不出时用 price/pre_close 自算） |
| 7 | 净值日期 `YYYY-MM-DD` | date |
| 8 / 9 | — | **未使用**（含义未确证） |

场外没有开高低、没有成交量/成交额 → `open` / `high` / `low` / `vol` / `amount` 一律 `None`（TUI 显示 `--`）；`change = round(price - pre_close, 4)`，`change_pct` 优先取 f[6]。字段数不足 10 或名称为空（场外货币基金返回空串，接口不返回净值）直接返回 `None`，按查无行情处理。

### 股票代码解析

正则 `hq_str_([a-z]+)_?(\d+)="` 从 JS 变量名提取（下划线可选，兼容场外的 `hq_str_fu_110022`），**保留前导零**（如 `000001`）。

### 错误处理

| 场景 | 表现 |
|------|------|
| 网络异常 / 超时 | 所有行维持上次数据，状态栏显示 `[Offline]`（黄色加粗） |
| 无效股票代码 | 静默跳过，不加入结果列表 |
| 场外货币基金（`fu_` 返回空串） | 返回 `None`，不加入结果列表；`add fu:511990` 时给「查不到净值 —— 代码不存在，或为不支持的场外货币基金」专门提示 |

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

> 最后更新：2026-09-13
