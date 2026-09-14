<p align="center">
  <img src="https://img.shields.io/badge/python-3.10%2B-blue" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green" alt="License">
  <img src="https://img.shields.io/badge/pypi-v0.3.2-orange" alt="PyPI">
  <img src="https://img.shields.io/github/contributors/Angryshark128/bosskey-stock" alt="Contributors">
</p>

<h1 align="center">BossKey-Stock — 终端摸鱼盯盘工具</h1>

<p align="center">
  <b>A</b>股 · 在终端里偷看行情 · 按一下 <code>b</code> 秒变 Docker 编译日志
</p>

<p align="center">
  <code>pip install bosskey-stock</code> &nbsp;|&nbsp; <code>bosskey</code>
</p>

---

**BossKey-Stock** 是一个纯终端 A 股实时行情监控工具。不需要打开浏览器、不需要切窗口、不需要 API Key。`bosskey` 回车，你的终端就变成了红绿相间的行情看板；听到脚步声，按 `b` 键，它又变成了一个正经的 Docker 构建日志。

> 🐟 **这个项目为什么存在？**  
> 作为一名程序员，我一天 8+ 小时在终端里。行情软件切来切去不仅麻烦，而且屏幕上一片红绿实在过于醒目。  
> 我需要一个东西——安安静静地待在终端里，别人路过时看起来像是在认真看 build log，但实际上……它在盯盘。  
> 这个就是 BossKey — 老板键，专门为摸鱼而生。

## 截图

<p align="center">
  <img src="docs/screenshot-demo.gif" alt="BossKey-Stock demo" width="800">
</p>

*按 `t` 逐级展开持仓/成本、持仓收益、今日收益列与底部汇总；按 `l` 切换中文界面；按 `b` 一键切换老板模式*

![Normal mode](docs/screenshot-normal.svg)

*正常模式 — 行情 + 持仓/成本 + 持仓收益（率）+ 今日收益，底部汇总总市值 / 总成本 / 总收益 / 今日收益*

![Boss mode](docs/screenshot-boss.svg)

*老板模式 — 按 `b` 后秒变 Docker build 日志*

> 截图可用 `python scripts/make_screenshots.py` 重新生成（macOS，需 qlmanage）。

## 功能

| 功能 | 说明 |
|------|------|
| 📊 **实时行情** | Rich 表格渲染，红涨绿跌，整行着色；覆盖 A 股、场内基金、债券与国债回购（见 [支持的品种](#支持的品种)） |
| 🎨 **默认单色** | 启动即单色（全白，屏幕不显眼）；`c` 键会话内切换彩色，配置 `display.colorize = true` 可恢复彩色 |
| ⏱ **智能刷新** | 交易时段（工作日 9:30-11:30 / 13:00-15:00）自动刷新，非交易时段停刷 |
| 🕶 **老板模式** | 按 `b` 一键切换 Docker build 伪日志，再按 `b` 切回 |
| ⌨️ **零依赖终端控制** | 单线程，一次 `tcsetattr`，无后台线程 |
| ⚡ **键盘操作** | `r` 手动刷新，`t` 收起持仓/收益列（启动默认全部列），`g` 切换分组视图，`q` / `Ctrl+C` 退出 |
| 📝 **监控列表管理** | CLI 子命令 `add` / `rm` / `list`；同名代码 add 时按段位规则落位并提示另一条怎么写（**不追问**），rm 时列候选让你选；无行情代码直接提示；`list -i` 交互式调整顺序/删除（保留插入顺序） |
| 🗂 **分组** | `group add/rm/rename/list/add-codes/rm-codes` 管理分组；`add --group` 归组；TUI `g` 键循环切换，组内独立排序 |
| 💼 **持仓与收益** | `pos add` 交互式多选录入持仓，TUI 切换显示持仓、成本、持仓收益（率）、今日收益，底部同步汇总总市值/总收益 |
| 🌐 **中英界面** | 默认英文伪装，`l` 键 / `--lang {en,zh}` / 配置 `display.lang` 随时切中文；**`--help` 恒为中文**，不随语言切换 |
| 🕶️ **英文伪装** | 界面与 CLI 输出默认全英文，英文非母语一眼难读，继续强化「在工作」的伪装；帮助文本是例外（伪装无收益，看得懂更要紧） |
| 🌐 **离线检测** | 网络断开时黄色 `[Offline]` 提示，续网自动恢复 |

## 支持的品种

**基金、债券与股票走同一套管理命令** —— 直接把代码填进来就行，不需要前缀、开关或额外配置；监控列表、分组、排序、持仓与收益计算全部通用。

| 品种 | 代码段 | 小数位 | 示例 |
|------|--------|--------|------|
| A 股 | 沪 6 / 深 0、3 / 北交所 4、8、92 | 2 | `600519` `000001` `920002` |
| ETF | 沪 5 / 深 15 | 3 | `510300` `159915` |
| LOF | 沪 5 / 深 16 | 3 | `501000` `160105` |
| REITs | 沪 508 / 深 180 | 3 | `508000` `180101` |
| 场内货币基金 | 沪 511 | 3 | `511990` `511880` |
| 债券 / 国债回购 | 沪 01、110-118、71、122-127、132、204 / 深 10-13 | 3 | `113550` `123118` `204001` |
| B 股 | 沪 9 | 2 | `900901` |
| 场外开放式基金 | `fu:` 显式前缀（净值型，支付宝 / 天天基金上按金额申购那种） | 4 | `fu:110022` |

场内基金按 3 位小数显示（价格与涨跌额一致），股票按 2 位；沪 5 段与深 18 段的存量封闭式基金同样按 3 位处理。**场外基金按 4 位**（净值本身就是 4 位小数，`fu:110022` 显示 `2.8377`）。港股尚未支持。

管理基金和管股票没有区别：

```bash
bosskey add 510300 159915 508000       # 加进监控列表（股票 / 基金 / 债券混着填）
bosskey add 180101 --group 场内         # 顺手归组（组名不存在会自动建）
bosskey add fu:110022                  # 场外基金：必须带 fu: 前缀（见下）
bosskey group add 场内 510300 159915    # 或往已有分组里追加
bosskey group list                     # 看分组内容
bosskey list -i                        # 交互式调整顺序 / 删除
bosskey pos add                        # 录入持仓（份数 + 成本价），收益与汇总自动算
bosskey                                # 启动盯盘，TUI 内按 t 切换列、g 切换分组
```

### 场外开放式基金（`fu:` 前缀）

场外净值型基金（在支付宝 / 天天基金按金额申购的开放式基金，不是 ETF / LOF 那类场内品种）用**显式前缀 `fu:`** 指定，例如 `bosskey add fu:110022`（易方达消费行业股票）。数据取自 Sina 的场外接口，只有净值、没有盘口：

- 显示**当日估算净值**（4 位小数）与估算涨跌幅；开 / 高 / 低 / 成交量 / 成交额这些场内字段**没有**，表格里显示 `--`。
- 净值是日频估值而非逐笔成交价，「实时」的含义与场内不同。
- 持仓按**金额申购**：份额是小数（1000 元 ÷ 2.8377 ≈ 352.4 份），`pos add` 收小数份额，TUI 与 `pos list` 照实显示（整数份额仍显示为整数，与原来一致）。
- 前缀只能手写：场外代码段与 A 股、场内代码大面积重叠（`000001` 既是平安银行又是华夏成长混合，`110022` 既是沪市可转债段又是易方达消费行业），程序**不做**自动判别，裸代码一律按场内段位规则解析。想加场外基金就得写 `fu:`。

> ⚠️ **不支持场外货币基金**：这类基金接口不返回净值（`fu:511990` 返回空串），`add fu:511990` 会明确提示「查不到净值 —— 代码不存在，或为不支持的场外货币基金」。

### 同名代码与无行情代码

所有要填代码的管理命令（`add` / `rm` / `group add` / `group add-codes` / `group rm-codes` / `pos rm`）都会先探测这个代码在沪（`sh`）/ 深（`sz`）/ 京（`bj`）各交易所**有没有行情**，再决定怎么办（场外基金 `fu:` 不参与裸代码探测，只能显式写）：

- **只命中一个** → 直接用，静默完成（绝大多数代码）。
- **命中多个**（同名代码）→ **不打断、不追问**，直接用段位规则那条，并把另一条候选连同它的强制前缀打成一行提示：
  ```
  $ bosskey add 000001
  000001 = 平安银行（另有 上证指数 → sh:000001）
  Added: 000001
  ```
- **零命中** → 直接告诉你「查无行情」，**不再静默跳过**。
- **删除时命中多条**（`rm` / `group rm-codes` / `pos rm`）→ 列出候选（带名称）让你选一条，或按 `a` 全删（删除要明确，这里仍然会问）。
- **离线** → 探测失败就回退段位规则照常加入，不阻塞。

想取另一条候选，自己写前缀即可，同样不追问：`bosskey add sh:000001`（上证指数）、`bosskey add sz:510300`（强制按深市解析）、`bosskey add fu:110022`（场外基金，见上）。`bosskey add --help` 里有同样的说明（帮助恒为中文）。

存成**带显式前缀的键**（如 `sh:000001`）时，`list` 与 TUI 里也照此显示 —— 这样两条同码能区分开；与段位规则一致时仍存裸代码，**老配置不用改**。

| 代码 | 以前 | 现在 |
|------|------|------|
| `000001` | 只能是 `sz000001` 平安银行，上证指数取不到 | 落段位规则 `000001` 平安银行，并提示「上证指数 → sh:000001」 |
| `000300` | `sz000300` 返回空 → 该行静默消失 | 唯一命中在沪市，自动存 `sh:000300` 沪深 300 |
| `110022` | `sh110022` 返回空 → 该行静默消失 | 探测命中深市贴现国债 `sz110022` 贴债2381（偏离段位规则，故存 `sz:110022`），**裸代码会被静默加进去、显示的是债券行情**；要加易方达消费行业请写 `fu:110022` |

**场内基金与股票不会撞车** —— 段位互斥（沪 5 段基金 vs 6 段股票，深 15/16/18 段基金 vs 00/30 段股票，10-13 段债券）。同名只发生在跨市场/跨命名空间：指数 vs 股票、场外基金 vs 场内代码。

**会撞车的代码就那么一组**：实测沪市 `000001`~`000999` 有 319 条上证系列指数（上证指数、A股指数、工业指数、沪深300…），深市同号段有 506 只主板股票，**两边同时有行情的只有 204 个**。也就是说需要那行提示的只有这 204 个代码，其余一律静默完成 —— 并且这件事跟基金无关，基金段位压根没参与。

## 安装

### 从 PyPI（推荐）

```bash
pip install bosskey-stock
```

### 从源码

```bash
git clone https://github.com/Angryshark128/bosskey-stock.git
cd bosskey-stock
pip install -e .
```

安装后使用 `bosskey` 命令。

## 快速开始

```bash
# 启动盯盘
bosskey

# 添加代码到监控列表（股票 / ETF / LOF / REITs / 债券 / 回购 混着填都行）
bosskey add 601318 000858
bosskey add 510300 508000 113550

# 移除代码
bosskey rm 000001

# 查看当前监控列表
bosskey list

# 交互式调整监控列表顺序并删除（展示代码+中文名，↑/↓ 移动游标，空格拿起/放下，d 标记删除，s 保存，q 退出）
bosskey list -i

# 交互式记录持仓：列出监控列表多选，逐个录入股数/份数与成本价
bosskey pos add

# 移除持仓
bosskey pos rm 000001

# 查看全部持仓
bosskey pos list

# 指定语言运行（可选：默认取配置 display.lang，未设置时英文）
bosskey --lang zh run
bosskey --lang zh list
```

### 终端内操作

| 按键 | 功能 |
|------|------|
| `b` | 老板模式切换（行情 ↔ Docker 日志） |
| `r` | 手动刷新行情 |
| `t` | 循环切换显示模式（启动默认全部 14 列）：全部 → 收起今日收益 → 收起持仓收益（率） → 仅基础行情；底部汇总同步切换 |
| `c` | 彩色/单色切换：关闭红绿着色，全白显示 |
| `l` | 中英界面切换（会话内，默认英文） |
| `h` | 底部快捷键提示开关 |
| `q` / `Ctrl+C` | 退出（终端完全恢复，无 traceback） |

## 配置

配置文件 `~/.bosskey.toml` 在首次运行时自动创建：

```toml
[display]
refresh_interval = 3
lang = "en"  # 界面语言：en / zh（TUI 内按 l 切换）
colorize = false  # 红绿着色：false=单色（默认）/ true=彩色（TUI 内按 c 切换）

[watchlist]
codes = ["000001", "600519", "300750"]

[holdings]
# code = { shares = 持仓股数, cost = 成本价 }
600519 = { shares = 100, cost = 1500.50 }
```

> 持仓可用 `bosskey pos add/rm/list` 管理；`pos add` 交互式多选监控列表中的股票并逐个录入股数与成本价。

## 数据来源

本项目使用 **[Sina Finance 实时行情 API](https://hq.sinajs.cn/)**，这是一个免费、无需 API Key 的公开接口。

> ⚠️ **免责声明**  
> Sina Finance API 是非官方的公开接口，无正式服务等级承诺。数据仅作个人参考，不构成投资建议。  
> 如新浪调整接口策略导致工具不可用，请提交 Issue，我们会跟进适配。

## 与同类工具对比

| | BossKey-Stock | 同花顺/东方财富 | tushare | 
|--|---------------|----------------|---------|
| 终端运行 | ✅ | ❌ | ✅ |
| 老板模式 | ✅ | ❌ | ❌ |
| 需 API Key | ❌ | ❌ | ✅ |
| 需注册 | ❌ | ✅ | ✅ |
| 安装大小 | 3 个依赖 | 几百 MB | 中等 |

## 项目结构

```
bosskey-stock/
├── bosskey_stock/
│   ├── __init__.py        # 包标记
│   ├── __main__.py        # CLI 入口，子命令路由
│   ├── app.py             # 主循环：Rich Live + 非阻塞键盘输入
│   ├── data.py            # Sina 数据层，GBK 编码解析
│   ├── boss.py            # 老板模式（Docker build 伪日志）
│   ├── config.py          # 配置读写
│   └── i18n.py            # 中英文案表与语言解析
├── tests/
│   ├── test_data.py       # 数据解析测试
│   ├── test_config.py     # 配置管理测试
│   └── test_boss.py       # 老板模式测试
├── docs/
│   └── design.md          # 架构设计文档
├── pyproject.toml          # 打包与项目配置
├── LICENSE
├── README.md
└── CHANGELOG.md
```

## 为什么是 Python？

这是有意为之的。典型办公环境预装 Python，`pip install bosskey-stock` 就能用——不需要申请安装权限、不需要 IT 审批、不需要管理员权限。  
一个纯文本的工具，在任何 SSH 会话、tmux 窗口、甚至远程服务器上都能跑。

## 贡献

见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 致谢

感谢以下代码贡献者与 issue 提出者：

| | 贡献 |
| --- | --- |
| [<img src="https://github.com/mcxue.png?size=64" width="32" height="32" alt="mcxue">](https://github.com/mcxue) | **[@mcxue](https://github.com/mcxue)** — 代码贡献：单色模式（`c` 键切换）、`list -i` 交互式排序/删除、ETF 与北交所（4/8/92 开头）代码支持（[PR #3](https://github.com/Angryshark128/bosskey-stock/pull/3)） |
| [<img src="https://github.com/vhmlee-dev.png?size=64" width="32" height="32" alt="vhmlee-dev">](https://github.com/vhmlee-dev) | **[@vhmlee-dev](https://github.com/vhmlee-dev)** — 提出 ETF 支持需求（[Issue #4](https://github.com/Angryshark128/bosskey-stock/issues/4)） |

## License

[MIT License](LICENSE)
