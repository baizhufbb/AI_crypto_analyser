---
description: 加密货币市场分析与交易建议标准工作流
auto_execution_mode: 1
---

# 加密货币分析标准工作流

本工作流旨在规范 AI 交易员在处理用户行情分析请求时的操作步骤，确保数据准确、分析全面且策略一致。

## 1. 初始化与环境同步

在进行任何分析之前，必须先确立时间基准和用户策略偏好。

1. **获取当前时间**
   ```bash
   uv run --env-file .env scripts/utils/get_time.py
   ```
   *注意：后续所有分析中的"当前价格"、"今日涨跌"均需以此时间为准。*

2. **读取交易策略**
   - 文件路径: `docs/user_strategy.md`
   - 目的: 确认风险偏好、V1/V2 策略选择、报告格式要求及量化指标需求。

## 2. 意图识别与路径选择

根据用户指令类型选择合适的分析路径。

### 分支 A：特定交易对分析 (e.g. "分析 ETH", "看看 SOL")

直接跳到 **步骤 4**，对指定标的拉取详细数据。

### 分支 B：市场扫描与机会发现 (e.g. "找机会", "帮我在 OKX 找机会")

**必须首先运行全市场快照脚本**：
```bash
# OKX（默认）：全市场 USDT 永续基础快照
uv run --env-file .env scripts/fetch_snapshot.py --exchange okx --quote USDT --min-quote-volume 5000000 --include-raw
# Binance：全市场 USDT 永续基础快照
uv run --env-file .env scripts/fetch_snapshot.py --exchange binance --quote USDT --min-quote-volume 5000000 --include-raw
```

**snapshot 会自动完成：**
- 拉取指定交易所全量 USDT 永续合约（OKX 约 250+，Binance 约 300+）
- 按报价资产与最小成交额做硬过滤
- 计算成交量/涨跌幅 Top 榜
- 输出包含 `tickers` 全集的轻量快照，保存到 `data/{exchange}/_snapshot/`

**参数说明：**
- `--exchange okx|binance`：选择交易所（默认 okx）
- `--quote`：报价资产过滤（默认 USDT，传 ALL 表示不过滤）
- `--min-quote-volume`：24h 最小成交额门槛（计价货币），用于剔除流动性过差标的
- `--top N`：仅影响榜单展示数量（默认 10），不影响 `tickers` 全集，AI 会在全量 `tickers` 上做筛选
- `--include-raw`：是否在快照中包含 `tickers` 全集（AI 软筛选建议打开）

## 3. 候选确认

读取 snapshot 输出结果，特别是其中的 `tickers` 全集与成交量/涨跌幅榜，由 AI 根据当前策略与当前市场环境软筛选出一批候选标的。

## 4. 获取详细数据

对 AI 从 snapshot 中筛出的候选（或用户指定的标的），拉取多周期详细数据（默认使用 1d 4h 1h 15m）：

```bash
uv run --env-file .env scripts/fetch_klines.py --exchange okx --symbols [候选标的] --interval 1d 4h 1h 15m --limit 200
```

## 5. 指标提取与分析

使用 analyze_file 快速提取结构化指标：

```bash
uv run --env-file .env scripts/analyze_file.py --file [数据文件路径] --json
```

结合多周期数据进行综合研判：
- 趋势方向与强度
- RSI 位置与动能
- 价格相对均线位置（回调是否到位）
- 量能确认
- 关键支撑/阻力位

## 6. 报告生成

严格遵循 `docs/user_strategy.md` 的"AI 输出报告必填清单"：

1. **标的与方向**
2. **核心理由**
3. **量化评估**：胜率、持仓时长、走势概率、时间概率、盈亏比
4. **执行计划**：入场、止损、止盈
5. **仓位与杠杆**：具体 USDT 数值（不能只写"按规则计算"）
6. **下次交流时间建议**
7. **AI 独立视角建议**：批判性评估 + 替代方案 + 风控差异

## 7. 自动化循环与提醒

若需要持续跟踪（持仓中、等待入场条件触发等）：

```bash
uv run --env-file .env scripts/utils/timer.py [分钟数]
```

倒计时结束后，重新执行完整流程。

## 脚本职责速查

| 脚本 | 用途 | 何时使用 |
|------|------|----------|
| `scripts/fetch_snapshot.py` | 全市场基础快照 + 榜单（成交量/涨跌幅 Top） | **找机会时必须首先运行** |
| `scripts/fetch_klines.py` | 拉取单标的详细 K 线 | 对 AI 选出的候选或用户指定标的做深度分析 |
| `scripts/analyze_file.py` | 提取结构化指标 | 从 fetcher 输出中快速提取 RSI/MA/ATR 等 |
| `scripts/utils/timer.py` | 倒计时提醒 | 需要在若干分钟后自动复查行情/仓位时使用 |