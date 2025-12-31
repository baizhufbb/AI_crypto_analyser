# 加密货币 AI 交易分析系统

一个集成了 **AI 分析**、**实时监控**、**数据采集** 的加密货币合约交易工具箱。

## ✨ 核心特性

- 🤖 **AI 交易助手** - 基于 Claude 的智能交易分析，支持 IDE 和 Telegram 双模式
- 📡 **KOL 信号监控** - 实时追踪加密货币 KOL 消息和交易员操作，钉钉推送
- 📊 **多维数据采集** - K线、技术指标、资金费率、持仓量、订单簿
- 🔄 **双交易所支持** - Binance 和 OKX 合约市场

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 安装依赖
pip install uv
uv sync

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入必要的 API Keys
```

### 2. 核心功能使用

#### 🧠 AI 交易助手

**方式一：IDE 沉浸式**（推荐开发时）
- 直接在 Windsurf/Cursor 对话框中输入：`"分析 BTCUSDT"`

**方式二：Telegram 远程**（推荐日常使用）
```bash
uv run --env-file .env bot_service/services/ai_assistant.py
```
然后在 Telegram 发送 `"帮我找找机会"`

#### 📡 KOL 信号监控

**一键启动（推荐）**
```bash
# 同时启动 KOL 消息和交易员监控
uv run --env-file .env start_kol_monitor.py
```

**单独启动**
```bash
# KOL 消息监控
uv run --env-file .env bot_service/services/kol_monitor/signal_radar.py

# 交易员操作监控
uv run --env-file .env bot_service/services/kol_monitor/trader_radar.py
```

**环境变量配置：**
- `DINGTALK_WEBHOOK` - 钉钉机器人 Webhook
- `DINGTALK_SECRET` - 钉钉加签密钥
- `KOL_API_URL` - KOL 消息 API
- `TRADER_API_URL` - 交易员信号 API

---

## � 数据采集工具

### 市场快照（大盘扫描）

```bash
# Binance USDT 合约 24h 概况
uv run --env-file .env scripts/fetch_snapshot.py --exchange binance --top 15 --include-raw

# OKX SWAP 合约概况
uv run --env-file .env scripts/fetch_snapshot.py --exchange okx --inst-type SWAP --quote ALL --top 15
```

### K线与技术指标

```bash
# 单个标的多周期分析
uv run --env-file .env scripts/fetch_klines.py \
  --exchange binance \
  --symbols BTCUSDT \
  --interval 1d,4h,1h \
  --limit 200

# 批量扫描
uv run --env-file .env scripts/fetch_klines.py \
  --exchange binance \
  --symbols ALL \
  --quote USDT \
  --max-symbols 20

# OKX 永续合约批量
uv run --env-file .env scripts/fetch_klines.py \
  --exchange okx \
  --symbols ALL \
  --inst-type SWAP \
  --max-symbols 15
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--exchange` | 交易所（`binance` / `okx`） | `binance` |
| `--symbols` | 交易对（单个 / 多个 / `ALL`） | `BTCUSDT` |
| `--interval` | K线周期（`1h`, `4h`, `1d`） | `1h` |
| `--limit` | 拉取数量 | `100` |
| `--quote` | 报价资产过滤（批量模式用） | `None` |
| `--max-symbols` | 批量模式最大数量 | `None` |
| `--contract-type` | Binance 合约类型（如 `PERPETUAL`） | `PERPETUAL` |
| `--inst-type` | OKX 产品类型（如 `SWAP`） | `SWAP` |

**交易对格式：**
- Binance: `BTCUSDT`, `ETHUSDT`（无横杠）
- OKX: `BTC-USDT-SWAP`, `ETH-USDT-SWAP`（带横杠）

---

## 📁 项目架构

```
crypto_anal_AI/
├── bot_service/              # 自动化服务
│   ├── transport/            # 通信层
│   │   ├── telegram/         # Telegram Bot
│   │   └── dingtalk/         # 钉钉机器人
│   ├── services/             # 业务服务
│   │   ├── ai_assistant.py   # AI 助手（Telegram）
│   │   └── kol_monitor/      # KOL 监控
│   │       ├── base.py       # 监控基类
│   │       ├── signal_radar.py    # KOL 消息
│   │       └── trader_radar.py    # 交易员信号
│   └── agent/                # AI Agent 核心
│
├── crypto_analyzer/          # 分析引擎
│   ├── core/                 # 基础设施（配置、存储）
│   ├── analysis/             # 分析逻辑（指标、信号）
│   └── data/                 # 数据获取（交易所适配器）
│
├── scripts/                  # 命令行工具
│   ├── fetch_klines.py       # K线数据采集
│   ├── fetch_snapshot.py     # 市场快照
│   └── analyze_file.py       # 数据分析
│
├── docs/                     # 配置文档
│   ├── user_strategy.md      # 交易策略（AI 读取）
│   └── AI_GUIDE.md           # AI 使用指南
│
└── data/                     # 数据存储
    └── {exchange}/
        ├── _snapshot/        # 市场快照
        └── {symbol}/{interval}/   # K线数据
```

---

## ⚙️ 配置说明

### 策略定制

修改 `docs/user_strategy.md` 定制 AI 分析逻辑：
- 交易偏好（做多/做空、左侧/右侧）
- 风控规则（止盈止损、杠杆限制）

AI 每次分析前会读取此文件，确保建议符合你的交易纪律。

### 数据存储

- 默认目录：`data/`
- 修改路径：编辑 `crypto_analyzer/core/config.py` 中的 `OUTPUT_DIR`

### API 地址

- Binance: `https://fapi.binance.com`
- OKX: `https://www.okx.com`

如需代理或修改域名，编辑 `crypto_analyzer/core/config.py`

---

## 📄 数据格式

### 输出位置
```
data/{exchange}/{symbol}/{interval}/{timestamp}_{count}.json
```

### 数据内容
- `klines` - K线（价格、成交量、MA/RSI等指标）
- `ticker_24hr` - 24小时价格统计
- `funding_rate` - 资金费率（多空情绪）
- `open_interest` - 持仓量（趋势强度）
- `order_book` - 订单簿深度

---

## ⚠️ 注意事项

- 仅支持**合约交易对**，不支持现货
- 周期格式：
  - Binance: 小写（`1h`, `4h`）
  - OKX: 大写（`1H`, `4H`）
- 技术指标需足够历史数据：
  - MA20 需 20 根 K线
  - MA50 需 50 根 K线
  - RSI14 需 14 根 K线

---

## 📚 相关文档

- [AI 使用指南](docs/AI_GUIDE.md)
- [交易策略配置](docs/user_strategy.md)
- [Claude AI 提示词](CLAUDE.md)

---

## 🛠️ 技术栈

- **语言**: Python 3.11+
- **包管理**: uv
- **AI**: Claude (Anthropic)
- **数据源**: Binance / OKX API
- **通信**: Telegram Bot / 钉钉机器人
