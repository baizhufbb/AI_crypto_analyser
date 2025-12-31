"""
市场概况快照脚本。

用途：
- 通过轻量级接口一次性获取 Binance / OKX 所有合约的 24h 行情概况
- 支持按报价资产过滤，只保留 USDT 等主流计价
- 自动计算成交量 Top N、涨幅榜、跌幅榜，供 AI 快速筛选候选交易对

生成的 JSON 保存在 `data/{exchange}/_snapshot/` 下，
AI 可以先阅读该文件挑选符号，再使用 `scripts/fetch_klines.py --symbols ...` 获取细节。
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence

import requests

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crypto_analyzer.core.config import BINANCE_BASE_URL, OKX_BASE_URL, OUTPUT_DIR


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="获取 Binance / OKX 合约市场的 24h 概况快照（批量行情摘要）"
    )
    parser.add_argument(
        "--exchange",
        choices=["binance", "okx"],
        default="binance",
        help="交易所：binance 或 okx",
    )
    parser.add_argument(
        "--inst-type",
        default="SWAP",
        help="OKX 合约类型，默认 SWAP（仅对 OKX 生效）",
    )
    parser.add_argument(
        "--quote",
        default="USDT",
        help="仅保留指定报价资产（如 USDT 或 USDT,BUSD），传 ALL 表示不过滤，默认 USDT",
    )
    parser.add_argument(
        "--min-quote-volume",
        type=float,
        default=0.0,
        help="24h 最小成交额（计价货币），用于硬过滤，默认 0 表示不过滤",
    )
    parser.add_argument(
        "--top",
        type=int,
        default=10,
        help="汇总榜单中展示的条目数量，默认 10",
    )
    parser.add_argument(
        "--include-raw",
        action="store_true",
        help="在快照中包含完整 tickers 数据，默认仅保存过滤后的列表",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    quote_assets = build_quote_filter(args.quote)

    if args.exchange == "binance":
        tickers = fetch_binance_tickers()
        filtered = filter_binance_tickers(tickers, quote_assets, args.min_quote_volume)
        summary = summarize_binance(filtered, args.top)
    else:
        tickers = fetch_okx_tickers(args.inst_type)
        filtered = filter_okx_tickers(tickers, quote_assets, args.min_quote_volume)
        summary = summarize_okx(filtered, args.top)

    if args.include_raw:
        summary["tickers"] = filtered

    summary["filters"] = {
        "quote_assets": sorted(quote_assets) if quote_assets else None,
        "min_quote_volume": args.min_quote_volume,
        "top": args.top,
    }

    output_path = save_snapshot(summary, args.exchange)
    print(f"概况快照已写入 {output_path}，包含 {summary['total_symbols']} 个交易对。")


# ---------- Binance ----------


def fetch_binance_tickers() -> List[Dict]:
    response = requests.get(f"{BINANCE_BASE_URL}/fapi/v1/ticker/24hr", timeout=30)
    response.raise_for_status()
    data = response.json()
    if not isinstance(data, list):
        raise ValueError("Binance ticker 接口返回格式异常（应为列表）")
    return data


def filter_binance_tickers(
    tickers: Sequence[Dict],
    quote_assets: set[str] | None,
    min_quote_volume: float,
) -> List[Dict]:
    filtered: List[Dict] = []
    for entry in tickers:
        symbol = entry.get("symbol", "")
        if not symbol:
            continue
        if quote_assets and not any(symbol.upper().endswith(q) for q in quote_assets):
            continue
        try:
            open_price = float(entry.get("openPrice", 0))
            high_price = float(entry.get("highPrice", 0))
            low_price = float(entry.get("lowPrice", 0))
            quote_volume = float(entry.get("quoteVolume", 0))

            # 成交额硬过滤
            if min_quote_volume and quote_volume < min_quote_volume:
                continue

            range_pct = 0.0
            if open_price > 0:
                range_pct = (high_price - low_price) / open_price * 100

            filtered.append(
                {
                    "symbol": symbol.upper(),
                    "priceChangePercent": float(entry.get("priceChangePercent", 0)),
                    "lastPrice": float(entry.get("lastPrice", 0)),
                    "highPrice": high_price,
                    "lowPrice": low_price,
                    "volume": float(entry.get("volume", 0)),
                    "quoteVolume": quote_volume,
                    "openPrice": open_price,
                    "count": int(entry.get("count", 0)),
                    "range24hPct": range_pct,
                }
            )
        except (TypeError, ValueError):
            continue
    return filtered


def summarize_binance(tickers: List[Dict], top: int) -> Dict:
    return build_summary(
        exchange="binance",
        tickers=tickers,
        volume_key="quoteVolume",
        change_key="priceChangePercent",
        top=top,
    )


# ---------- OKX ----------


def fetch_okx_tickers(inst_type: str) -> List[Dict]:
    response = requests.get(
        f"{OKX_BASE_URL}/api/v5/market/tickers",
        params={"instType": inst_type.upper()},
        timeout=30,
    )
    response.raise_for_status()
    result = response.json()
    if result.get("code") != "0":
        raise ValueError(f"OKX ticker 接口错误：{result.get('msg', '未知错误')}")
    data = result.get("data", [])
    if not isinstance(data, list):
        raise ValueError("OKX ticker 接口返回格式异常（应为列表）")
    return data


def filter_okx_tickers(
    tickers: Sequence[Dict],
    quote_assets: set[str] | None,
    min_quote_volume: float,
) -> List[Dict]:
    filtered: List[Dict] = []
    for entry in tickers:
        inst_id = entry.get("instId", "")
        if not inst_id:
            continue
        if quote_assets:
            parts = inst_id.upper().split("-")
            quote = parts[1] if len(parts) >= 2 else ""
            if quote not in quote_assets:
                continue
        try:
            open_price = float(entry.get("open24h", 0))
            last_price = float(entry.get("last", 0))
            high_price = float(entry.get("high24h", 0))
            low_price = float(entry.get("low24h", 0))
            quote_volume = float(entry.get("volCcy24h", 0))

            # 成交额硬过滤
            if min_quote_volume and quote_volume < min_quote_volume:
                continue

            change_pct = (last_price - open_price) / open_price * 100 if open_price != 0 else 0
            range_pct = 0.0
            if open_price > 0:
                range_pct = (high_price - low_price) / open_price * 100

            filtered.append(
                {
                    "symbol": inst_id.upper(),
                    "priceChangePercent": change_pct,
                    "lastPrice": last_price,
                    "highPrice": high_price,
                    "lowPrice": low_price,
                    "volume": float(entry.get("vol24h", 0)),
                    "quoteVolume": quote_volume,
                    "openPrice": open_price,
                    "range24hPct": range_pct,
                }
            )
        except (TypeError, ValueError):
            continue
    return filtered


def summarize_okx(tickers: List[Dict], top: int) -> Dict:
    return build_summary(
        exchange="okx",
        tickers=tickers,
        volume_key="quoteVolume",
        change_key="priceChangePercent",
        top=top,
    )


# ---------- 通用 ----------


def build_summary(
    exchange: str,
    tickers: List[Dict],
    volume_key: str,
    change_key: str,
    top: int,
) -> Dict:
    sorted_volume = sorted(tickers, key=lambda x: x.get(volume_key, 0), reverse=True)
    sorted_change = sorted(tickers, key=lambda x: x.get(change_key, 0), reverse=True)

    summary = {
        "exchange": exchange,
        "generated_at": datetime.now().isoformat(),
        "total_symbols": len(tickers),
        "top_volume": sorted_volume[:top],
        "top_gainers": sorted_change[:top],
        "top_losers": sorted_change[-top:][::-1],
    }
    return summary


def save_snapshot(summary: Dict, exchange: str) -> Path:
    folder = OUTPUT_DIR / exchange.lower() / "_snapshot"
    folder.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = folder / f"{timestamp}_snapshot.json"
    path.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
    cleanup_old_snapshots(folder, keep=1)
    return path


def cleanup_old_snapshots(folder: Path, keep: int = 1) -> None:
    """仅保留最新的快照文件。"""
    json_files = sorted(folder.glob("*.json"))
    if len(json_files) <= keep:
        return
    for old_file in json_files[:-keep]:
        try:
            old_file.unlink()
        except Exception:
            continue


def build_quote_filter(quote_text: str | None) -> set[str] | None:
    if not quote_text:
        return None
    normalized = quote_text.strip().upper()
    if normalized == "ALL":
        return None
    return {part.strip().upper() for part in normalized.split(",") if part.strip()}


if __name__ == "__main__":
    main()


