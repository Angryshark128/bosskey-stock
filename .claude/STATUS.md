# STATUS

## [2026-09-14] 发布 v0.4.0

- 产出：commit `caa351c`（main）+ tag `v0.4.0` + GitHub Release v0.4.0；`publish.yml` 经 OIDC 发 PyPI 成功，`bosskey_stock-0.4.0-py3-none-any.whl` / `.tar.gz` 已上线；CI（3.10 / 3.11 / 3.12）通过。
- 本文件下方标「未发版」的条目**均已随本次发布生效**：显式交易所前缀 `sh:` / `sz:` / `bj:`、场外基金 `fu:` 前缀、同名代码多命中不再追问、帮助文本恒中文、深市 180 段 REITs 小数位修正；另有 `README` 的 PyPI badge 由静态 `v0.3.2` 改为 shields 动态徽章（不再需要每次发版手改）。
- 版本号定为 **0.4.0**（跳 minor）：新增一个品种大类（场外基金）+ `add` 交互行为变更，量级对齐 0.3.0（分组那次）。
- 踩坑：本机 git 的 credential helper 指向 `/usr/bin/gh`，而 gh 实际在 `/usr/local/bin/gh`，直接 `git push` 报 `could not read Username for 'https://github.com'`。本次用 `git -c credential.helper= -c credential.helper='!/usr/local/bin/gh auth git-credential' push` 绕开，**未改全局配置**；要长期修可跑 `gh auth setup-git`。
- 注意：push 时远端回了一句 `Changes must be made through a pull request.`（仓库有 PR 规则提示），但推送实际成功，未被拦。

## [2026-09-14] 帮助文本改为恒中文（未发版）

### 现状
- 起因：用户问「help 现在有中文说明么」—— 实测 `--lang zh add --help` 确实出中文，但 argparse 自带的框架词（`usage:` / `positional arguments` / `options` / `-h` 说明）仍是英文；用户随即定调：**默认 help 应该是中文，或者 help 只需要中文**。
- 决策：帮助文本**恒中文**，不随 `--lang` 切换、也不进 i18n 表。理由：帮助不会被同事一眼扫到（得主动敲 `--help`），伪装收益为零，却要人为了看说明先猜语言 —— 与 TUI / 运行期输出的「英文伪装」不冲突。`--lang` 从此只影响运行期输出。
- 改动：
  - `__main__.py`：`_build_parser(tr)` → `_build_parser()`，help 文案全部中文硬编码；新增 `_ZhHelpFormatter`（覆写 `add_usage()`，把 `usage: ` 换成 `用法：` —— argparse 把它硬编码在 `HelpFormatter` 里，只能覆写）、`_zh()`（`_positionals.title` / `_optionals.title` → `参数` / `选项`，argparse 无公开 API）、`_sub()`（子命令统一：中文 formatter + `add_help=False` + 自定义 `-h` 说明）；`_HELP_ADD_EPILOG` 承接原 `help_add_epilog` 的内容。
  - `__main__.py`：**删除 `_argv_lang()`** 及 `main()` 里的预扫 —— 那个补丁唯一的用途就是让帮助跟随 `--lang`，帮助恒中文后它没有存在意义。
  - `i18n.py`：删除全部 25 条 `help_*` key（含 `help_add_epilog`），表内只剩运行期文案（界面 / CLI 输出 / 交互提示 / reorder）。
- 帮助现在的形态（`bosskey add --help`，框架词也是中文）：
  ```
  用法：bosskey add [-h] [--group NAME] CODE [CODE ...]

  参数:
    CODE          代码，如 000001 600519；sh:000001 强制指定交易所；fu:110022 = 场外基金

  选项:
    -h, --help    显示帮助并退出
    --group NAME  归入该分组（不存在则自动创建）
  ```
- 测试：168 → **181 全绿**（+13，新增 `tests/test_help.py`）。覆盖：输出里无 `usage:` / `positional arguments` / `options:` / `show this help message` 残留、顶层子命令列表中文、add 用法说明含三种命中情形与四类示例、7 个子命令帮助均中文、`--lang en` / `--lang zh` / `--lang=zh` 下帮助一律中文。`tests/test_reorder.py` 里 `_build_parser(lang("en")["t"])` 的调用随之去掉参数（14 个测试因此改为无参）。
- 文档：README（功能表「中英界面」「英文伪装」两行 + add 帮助说明去掉「`--lang zh` 可切中文」）、design（CLI 命令表更新 + 新段落讲清中文化的三个实现点 + 「英文 UI」段落补例外说明）、CHANGELOG（Changed 两条；删掉已不成立的 `_argv_lang` 那条 Fixed）。

### 口径声明（本次范围）
- 只动帮助文本与 `-h`：运行期输出（`Added:` / 查无行情 / `pos add` 提示 / TUI）的语言行为未动，仍随 `--lang` 与配置。
- `parser._positionals` / `_optionals` 是 argparse 私有属性 —— 官方无公开 API，此为社区通行做法，代码注释已写明原因。
- 未发版，版本号未动。

### 待办
- [x] 帮助恒中文 + argparse 框架词中文化 — P1
- [x] 删 `_argv_lang()` 与 25 条 `help_*` i18n key — P1
- [x] `tests/test_help.py` + README / design / CHANGELOG 同步 — P1

## [2026-09-14] 同名代码多命中：不再追问，改为「默认 + 一行提示」（未发版）

### 现状
- 起因：用户提议「场内基金是否也像场外一样都加前缀，这样就不需要添加时选择了」。实测否定该前提 —— 逐只探测沪/深 `000001`~`000999`：沪市 319 条有行情（上证系列指数），深市 506 条有行情（主板股票），**交集 204 个**，会撞车的代码全部是「沪市指数 vs 深市股票」，**与基金无关**。场内基金（沪 5 段、深 15/16/18 段）与股票段位互斥，加不加前缀都不减少任何一次询问，只会每次多打三个字符。故未采用「给场内基金加前缀」。
- 采纳方案（用户：「按你的想法来」）：`add` / `group add` 命中多个时**不追问**，直接取段位规则那条，并把另一条候选连同其强制前缀打成一行提示。
- 改动：
  - `__main__.py`：删除 `_choose_quote()`（交互式候选选择），新增 `_pick_by_rule()`（取规则那条 + 打印提示）；`_resolve_add()` 多命中分支改调它并更新 docstring；`p_add` 加 `epilog=help_add_epilog` + `RawDescriptionHelpFormatter`，用法说明进 `--help`；新增 `_argv_lang()`，`main()` 用它预扫 `--lang`。
  - `i18n.py`：删 `cli_multi_quote` / `cli_choose_one` / `cli_choose_hint`，新增 `cli_multi_default`（`{code} = {name} (also {others})`）与 `help_add_epilog`（中英双语用法说明）。
- 行为变化：`add 000001` 从「列候选 + 按一次回车」变成零输入：
  ```
  000001 = 平安银行（另有 上证指数 → sh:000001）
  Added: 000001
  ```
  落位结果与原「回车取默认」完全一致（裸代码仍存裸代码）。删除路径（`rm` / `group rm-codes` / `pos rm`）仍由 `_choose_remove()` 列候选让用户选，未动 —— 删除要明确。
- 顺带修复：`--lang zh add --help` 之前出英文 —— argparse 的 `--help` 是在 `parse_args()` **内部**打印的，那一刻 `args.lang` 还不存在，`_build_parser()` 只能拿配置语言；现在 `_argv_lang()` 先扫 `sys.argv`。
- 测试：157 → **168 全绿**（+11）。多命中分支的测试改为把 `input` 打桩成抛 `AssertionError`（证明不再询问）；新增 `000xxx` 撞车 10 个代表代码的参数化回归、显式前缀取另一条候选、规则那条不在候选里时取第一个命中且提示不重复列、真实 `fetch` 路径下 `add 000001` 输出不含 "matches multiple"。`ruff check` 通过。
- 文档：README（功能表一行、同名代码小节重写 + 实际输出示例、表格 `000001` 行、补 204 个撞车代码的实测数据）、design（CLI 消歧流程 + `_pick_by_rule`/`_choose_remove` 分工）、CHANGELOG（Added 改写 + Changed 两条 + Fixed 一条）。

### 口径声明（本次范围）
- 只改多命中分支的交互；探测集合、段位规则、存储键规范化均未动。
- 不提供「强制询问」开关：想取另一条候选写前缀即可，`--help` 与 README 都给了写法。
- 未发版，版本号未动。

### 待办
- [x] `_pick_by_rule` 替代 `_choose_quote`，多命中零输入 — P1
- [x] `add --help` 用法说明（中英双语 + `--lang` 生效修复） — P1
- [x] README / design / CHANGELOG 同步 + 204 代码实测数据入档 — P1

## [2026-09-14] 场外开放式基金（`fu:` 显式前缀）支持（未发版）

### 现状
- 起因：明确要求新增「场外开放式基金（净值型 —— 支付宝 / 天天基金上按金额申购那种）」的管理能力，用 `fu:` 与股票/场内代码区分；硬约束是**裸代码解析零改动**（`default_prefix()` 与不带前缀时的 sh/sz/bj 探测一个字不许变）、不动无关代码、不加依赖。本条目取代 2026-09-13 条目里「`fu:` 未做 / 待拍板」的口径。
- 改动（逐文件）：
  - `data.py`：`EXCHANGES` 加 `fu`；**新增 `PROBE_EXCHANGES = ("sh", "sz", "bj")`**，`probe()` 未指定 prefix 时只探这三个（关键：否则 `add 000001` 会多出「华夏成长混合A」候选）；新增 `_join_sina()`，`sina_key("fu:110022") == "fu_110022"`（下划线，场内仍是 `sh600519`）；`price_decimals()` 对 `fu:` 返回 4；`_parse()` 正则改 `hq_str_([a-z]+)_?(\d+)="`，按 `fu` 分派到新增的 `_parse_fu()`（10 字段净值布局，开高低/量额一律 `None`，`change = round(price - pre_close, 4)`，`change_pct` 优先取 f[6]，空串返回 `None`），回填查表用 `_join_sina()` 与 `sina_key()` 同源。`default_prefix()` 一字未改。
  - `app.py`：`_fmt_price(v, dp=3)` 可传精度（默认值不变）；新增 `_cost_decimals()`（只有场外给 4 位，避免股票成本被降到 2 位）与 `_fmt_shares()`（整数照旧 `100`，小数 2 位去尾零 `352.4`），替换 `int(m['shares'])`。
  - `__main__.py`：`_resolve_add()` 的显式前缀分支对 `fu` 空命中给专门提示；`pos add` 份额提示 `int` → `float`；`_fmt_money(v, dp=3)` + `_print_positions()` 改用上面的助手（整数份额不再显示成 `100.0`，场外成本不再被截成 3 位）。
  - `config.py`：`add_position()` 本就无整数假设，仅更新 `list_positions()` 文档串；TOML 里 `fu:` 键由 tomlkit 自动加引号（`[holdings."fu:110022"]`），实测可读写。
  - `i18n.py`：新增 `cli_no_quote_fu`（场外货基专门提示），`help_add_codes` / `help_rm_codes` / `help_pos_rm_code` 补 `fu:` 前缀说明。
- 测试：130 → **157 全绿**（+27）。新增覆盖：`split_key` / `sina_key` / `make_key` / `price_decimals` 的 `fu` 分支、真实原文 `hq_str_fu_110022` 解析（含 name/price/pre_close/change/change_pct/date 与 5 个 `None` 字段）、与场内输出同构、空串货基 → `None`、f[6] 缺失回退自算、`probe("000001")` 请求列表里没有 `fu_`（回归保护）、`fu:` 显式前缀只探场外、`fetch` 下划线键回填、`add fu:110022` 走显式前缀、`fu:511990` 专门提示、裸 `110022` 只探 sh/sz/bj、`add 000001` 仍只问两家、小数份额渲染/存取/`pos list` 显示。
- 端到端实测（真实网络，临时 HOME，未触碰用户 `~/.bosskey.toml`）：`add fu:110022` → `Added: fu:110022`；`pos add` 录 352.4 份 @2.8377 → `[holdings."fu:110022"] shares = 352.4`；`pos list` → `fu:110022  352.4sh  cost 2.8377`；`fetch(["fu:110022"])` → price 2.8377 / pre_close 2.826 / change 0.0117 / change_pct 0.4149 / date 2026-09-14 / open·high·low·vol·amount 全 `None`，`_build_table` 里 Price 显示 `2.8377`、Vol/Open/High/Low 显示 `--`、Pos 显示 `352.4`；`probe("110022", prefix="fu")` → 易方达消费行业股票，`probe("110022")` → 深市 `贴债2381`（无 `fu` 候选），`add 000001` 仍只列 sh000001 / sz000001 两家。
- `ruff check` 全通过；`ruff format --check` 仍只有历史未格式化文件（`__main__.py` / `app.py` / `data.py` / `test_reorder.py`，加 `test_cli_resolve.py` 里一处上次遗留的多行 `setattr`），本次新增行已格式化。README / design / CHANGELOG 已同步。

### 口径声明（本次范围）
- 只做场外开放式基金（净值型），`fu:` **必须显式写**，裸代码行为一个字节没变。
- **场外货币基金不做**：接口返回空串，`add fu:511990` 给专门提示。
- 场外净值为日频估值，不是逐笔成交价，「实时」含义与场内不同 —— 已在 README 里写明。
- 未发版，版本号未动。

### 待办
- [x] `fu:` 前缀 + 10 字段场外解析 + 4 位净值精度 — P1
- [x] 小数份额（`pos add` 浮点、TUI/`pos list` 渲染、config 存取） — P1
- [x] README（品种表 + `fu:` 用法 + 场外货基说明 + 修掉 `110022` 一行的过时描述） / design / CHANGELOG 同步 — P1
- [ ] `f[8]` / `f[9]` 含义未确证（实测 2.8378 / 0.4184，疑似非官方净值与对应涨跌幅），本次按用户要求不使用 — P3
- [ ] 顺手项：README PyPI badge 仍写 v0.2.2（PyPI 已是 0.3.3），发版时一并更新 — P2
- [ ] 版本号 / tag / PyPI 发布 — P0（未做，等指示）

## [2026-09-13] 同名代码消歧 + 显式交易所前缀（未发版）

### 现状
- 起因：问「基金和股票代码重复了怎么办」「能不能在添加和删除等管理时让用户选」。
- 实现：`data.py` 引入存储键 —— `split_key` / `make_key` / `default_prefix` / `sina_key` / `probe`（`_sina_code` 拆出 `default_prefix`，既有行为不变）；`fetch()` 用 `sina_key()` 解析请求代码并把响应回填为原存储键（`code` 字段），行情/持仓/分组按同一键对齐；`price_decimals()` 只看代码段，不受前缀影响。`__main__.py` 的 `add` / `rm` / `group add-codes` / `group rm-codes` 走探测消歧；i18n 新增 9 条中英文案。
- 顺手修掉一个真 bug：i18n 取词函数 `t` 的形参名 `key` 与文案占位符 `{key}` 同名，`tr("...", key=...)` 抛 `TypeError`；形参改为 `_key`。
- 行为：单命中直接用（与段位规则一致时存裸代码）；多命中列出候选让用户选（回车取规则默认值）；零命中提示「查无行情」不再静默跳过；`rm` 多命中列出存储键 + 名称，可选一条或 `a` 全删；离线回退段位规则。**旧配置零迁移**。
- 端到端实测（临时 HOME，未触碰用户 `~/.bosskey.toml`）：`add 000001` 提示选上证指数/平安银行；`add 000300` 自动落 `sh:000300` 沪深 300（此前静默消失）；`add 999999` / `add abc` 明确报错；`rm 000001` 两条匹配后选一条移除；两条同码在 TUI 显示为 `000001 平安银行` 与 `sh:000001 上证指数`，可区分。
- 127 测试全绿（+24，含新增 `tests/test_cli_resolve.py`）；`ruff check` 通过；`ruff format --check` 仍只有 4 处历史未格式化文件（新增文件已格式化）。README / design / CHANGELOG 已同步。

### 口径声明（本次范围）
- 本批仍未发版。`sh:` / `sz:` / `bj:` 前缀**已实现**；**`fu:`（场外基金）未做** —— 场外代码在探测中会得到「查无行情」提示，不会被误解析成股票/债券。
- 场外开放式基金是否支持仍**待拍板**，未动；场外货币基金不做。

## [2026-09-13] 场内基金小数位判定收敛（未发版）

### 现状
- 按 my-memo 评估结论只做切分建议 ①（深市 REITs 小数位 + 精度判定收敛）。
- 改动：`data.py` 新增 `SZ_FUND_PREFIXES` 与 `price_decimals()`，`_is_etf` → `_is_fund`（纳入深市 18 段），`_parse` 改用统一入口；`app.py` 删除重复的 `dp` 判定；测试 +3（`test_is_fund`（改写自 `test_is_etf`）、`test_price_decimals`、`test_parse_reit_sz`、`test_build_table_reit_price_precision`）；README / design / CHANGELOG（`[Unreleased]`）同步。
- README 补「支持的品种」段（起因：反馈「看不出支持基金、支持哪些基金、怎么管理」）：品种 × 代码段 × 小数位 × 示例 一览（A 股 / ETF / LOF / REITs / 场内货基 / 债券回购 / B 股），附管理命令示例（`add` / `add --group` / `group add|list` / `list -i` / `pos add` / TUI 按键），并明确声明**不支持场外基金**（代码段与 A 股重叠，会误解析成股票/债券）与港股未支持；「功能」表该行改为指向该段，快速开始的「添加股票」改为「添加代码」、持仓注释补「份数」。
- 103 测试全绿；`ruff check` 通过；`ruff format --check` 仍有 4 处历史未格式化文件（本次未动）。
- 同名代码（2026-09-13，起因：问「基金和股票代码重复了怎么办」）：实测确认现有实现**无运行期歧义** —— `_sina_code` 对每个代码按段位生成唯一前缀，同一代码每次都指向同一标的，不会时好时坏；但撞车时另一半取不到，且是**静默跳过**：`000001` → `sz000001` 平安银行（拿不到 `sh000001` 上证指数）、`000300` → `sz000300` 返回空、表里不出现该行（拿不到 `sh000300` 沪深 300）、`110022` → `sh110022` 返回空、静默消失（拿不到 `fu_110022` 场外基金）。场内基金与股票**段位互斥、不会撞车**，撞车只跨命名空间（指数 vs 股票、场外基金 vs 场内代码）。README 新增「同名代码怎么处理」小节记现状与实测表；对策（显式前缀 `sh:`/`sz:`/`bj:` 覆盖、无行情不再静默跳过）记入 my-memo 待办，**未实施**。
- 本机 clone 原停在 v0.3.1，已 fetch 快进到 origin/main（a1a20a6 / v0.3.3）后再改。

### 口径声明（本次范围）
- 只做 ①：**深市 REITs 180xxx 小数位修正 + 价格精度判定收敛**。未发版，已发布版本内容不变。
- ② 场外开放式基金（`fu_` 前缀，10 字段净值格式）**未做，待拍板**：代码段与 A 股冲突须显式声明，且净值为日频、与实时盯盘定位冲突。
- ③ 场外货币基金（`fu_` 返回空串）**不做**。
- 评估与取舍详见 my-memo「bosskey-stock：终端 A 股行情监控」笔记「评估：基金类型支持」。

### 待办
- [x] 深市 REITs 180xxx 小数位修正 — P1
- [x] 精度判定收敛到 `data.price_decimals()` — P1
- [x] 测试与 README / design / CHANGELOG 同步 — P1
- [ ] ② 场外开放式基金是否支持：待拍板 — P2
- [ ] 顺手项：README PyPI badge 仍写 v0.2.2（PyPI 已是 0.3.3），发版时一并更新 — P2
- [ ] 版本号 / tag / PyPI 发布 — P0（未做，等指示）

## [2026-08-19] v0.3.2 — 默认单色模式

### 现状
- 待办「默认为单色模式」（2026-08-18 记录，P1）已实施：启动即单色（`colorize=False` 全白显示），`c` 键仍会话内切换彩色/单色。
- 配置新增 `[display] colorize`：默认 `false`（单色），`true` 恢复彩色；旧配置无此键自动按单色处理。
- 改动：`config.py`（DEFAULT + `get_colorize`/`set_colorize`）、`app.py`（初始值读配置）、`tests/`（+3 测试：config 默认值/读写、TUI 首次渲染单色）。
- 98 个测试全绿；版本 0.3.1 → 0.3.2（pyproject / README badge / CHANGELOG）。
- 待办来源：my-memo decisions.md 2026-08-18「bosskey-stock 新增待办：默认为单色模式」。

### 待办
- [x] 默认单色：config 加 `colorize` 项（默认 false），TUI 初始值读配置 — P1
- [x] 测试：config 默认/读写 + main_loop 首次渲染 colorize=False — P1
- [x] 版本 0.3.1 → 0.3.2 + CHANGELOG/README — P0
- [ ] 推送分支 → tag v0.3.2 → Release 发布 PyPI — P0

## [2026-08-06] v0.2.1 发布 — TodayP/L% 去重 + 中英界面切换

### 现状
- v0.2.1 已发布至 PyPI（0.2.1，Trusted Publishing 成功）。
- 功能：删除 mode 3 的 `TodayP/L%` 列（与 `Chg%` 重复，模式 3 共 14 列）；新增 `bosskey_stock/i18n.py` 中英文案表；`[display] lang` 设初始语言（默认 `en`）；TUI 按 `l` 会话内切换、按 `h` 开关底部快捷键提示；CLI `--lang {en,zh}` / `--list-langs`；TUI 与 CLI 全部文案中英化（老板模式仅底部状态行本地化）。
- 42 个测试全绿；ruff check / format 通过；CI 三版本（3.10/3.11/3.12）通过；CLI 双语手工冒烟通过。
- 顺手修复历史遗留：test_data.py 两处 ruff 格式、test_boss.py 未用变量。

### 待办
- [x] 版本号 0.2.0 → 0.2.1（pyproject / README badge / CHANGELOG）— P0
- [x] 截图重新生成（normal / boss / demo GIF 含中文帧与快捷键提示帧）+ 生成脚本 — P1
- [x] 推送分支 → PR #2 → 合并 main → tag v0.2.1 → Release 发布 PyPI — P0
- [x] 回归：TUI 内 `l`/`h` 键切换、`t` 循环后语言与帮助状态保持 — P1

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
