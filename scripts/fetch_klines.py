"""
加密货币合约市场数据获取脚本。

功能：
- 从 Binance 或 OKX 交易所的合约 API 获取 K 线数据
- 自动计算技术指标（MA20、MA50、RSI14、涨跌幅）
- 获取24小时统计、资金费率、持仓量、最新价格、订单簿深度
- 保存为 JSON 文件到 data/{exchange}/{symbol}/{interval}/ 目录

注意：此脚本仅支持合约交易对，不支持现货。

AI助手说明：如果你是AI助手，请查看 README.md 中的\"🤖 AI 助手使用指南\"部分，
那里包含了完整的AI身份定义、职责说明和自动调用流程。
"""

import argparse
import asyncio
import sys
from pathlib import Path
from typing import List, Tuple

import httpx

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crypto_analyzer.data.fetchers.binance import (
    fetch_binance_24hr_ticker_async,
    fetch_binance_current_price_async,
    fetch_binance_funding_rate_async,
    fetch_binance_klines_async,
    fetch_binance_open_interest_async,
    fetch_binance_order_book_async,
    list_binance_symbols,
)
from crypto_analyzer.data.fetchers.okx import (
    fetch_okx_24hr_ticker_async,
    fetch_okx_current_price_async,
    fetch_okx_funding_rate_async,
    fetch_okx_klines_async,
    fetch_okx_open_interest_async,
    fetch_okx_order_book_async,
    list_okx_symbols,
)
from crypto_analyzer.analysis.indicators import calculate_indicators
from crypto_analyzer.core.storage import build_output_path, save_json


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(
        description="从 Binance 或 OKX 交易所获取合约交易对的 K 线数据并计算技术指标（仅支持合约，不支持现货）"
    )
    parser.add_argument(
        "--exchange",
        choices=["binance", "okx"],
        default="binance",
        help="交易所选择：binance 或 okx，默认 binance",
    )
    parser.add_argument(
        "--symbols",
        nargs="+",
        default=["BTCUSDT"],
        help="交易对列表：单个如 BTCUSDT，多个用逗号或空格分隔，或使用 ALL 表示遍历所有合约",
    )
    parser.add_argument("--interval", nargs="+", default=["1h"], help="K线周期（如 1m, 5m, 1h, 1d），默认 1h，支持多周期")
    parser.add_argument("--limit", type=int, default=100, help="拉取条数（最大 1500），默认 100")
    parser.add_argument(
        "--max-symbols",
        type=int,
        help="批量模式下最多处理多少个交易对（symbol=ALL 或 --symbols 时生效）",
    )
    parser.add_argument(
        "--quote",
        help="仅保留指定报价资产（批量模式），如 USDT 或 USDT,BUSD",
    )
    parser.add_argument(
        "--contract-type",
        default="PERPETUAL",
        help="Binance 批量模式的合约类型，默认 PERPETUAL",
    )
    parser.add_argument(
        "--inst-type",
        default="SWAP",
        help="OKX 批量模式的合约类型，默认 SWAP",
    )
    parser.add_argument(
        "--price-only",
        action="store_true",
        help="仅获取当前价格，不获取K线和其他数据（快速模式）",
    )
    return parser.parse_args()


def detect_exchange_from_symbol(symbol: str) -> str:
    """根据交易对格式自动识别交易所。"""
    if "-" in symbol and "SWAP" in symbol.upper():
        return "okx"
    return "binance"


def main() -> None:
    """主函数：协调数据获取、指标计算和文件保存。"""
    try:
        args = parse_args()
        asyncio.run(_async_main(args))
    except Exception as exc:  # pragma: no cover - 顶层兜底
        print(f"执行失败：{exc}", file=sys.stderr)
        sys.exit(1)


async def _async_main(args: argparse.Namespace) -> None:
    async with httpx.AsyncClient() as client:
        if args.price_only:
            await _run_price_only(args, client)
            return

        symbols = resolve_symbols(args)
        intervals = resolve_intervals(args)

        tasks = []
        for symbol in symbols:
            for interval in intervals:
                tasks.append(
                    _run_full_task(
                        client=client,
                        exchange=args.exchange,
                        symbol=symbol,
                        interval=interval,
                        limit=args.limit,
                    )
                )

        results: List[Tuple[bool, str]] = []
        if tasks:
            results = await asyncio.gather(*tasks)

        successes = sum(1 for ok, _ in results if ok)
        failures: List[str] = [msg for ok, msg in results if not ok and msg]

        if successes == 0:
            print("所有任务处理失败，请检查参数或网络。", file=sys.stderr)
            sys.exit(1)

        if len(symbols) * len(intervals) > 1:
            print(f"\n批量完成：成功 {successes} 个，失败 {len(failures)} 个。")
            if failures:
                print("失败详情：")
                for item in failures:
                    print(f"  - {item}")


async def _run_price_only(args: argparse.Namespace, client: httpx.AsyncClient) -> None:
    symbols = resolve_symbols(args)

    async def _worker(symbol: str) -> None:
        try:
            exchange = args.exchange
            if args.exchange == "binance":
                detected = detect_exchange_from_symbol(symbol)
                exchange = detected

            if exchange == "binance":
                price_data = await fetch_binance_current_price_async(client, symbol)
            else:
                price_data = await fetch_okx_current_price_async(client, symbol)
            print(f"{price_data['symbol']}: {price_data['price']}")
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            print(f"[{symbol}] 获取价格失败：{exc}", file=sys.stderr)

    if not symbols:
        return

    await asyncio.gather(*(_worker(symbol) for symbol in symbols))


async def _run_full_task(
    client: httpx.AsyncClient,
    exchange: str,
    symbol: str,
    interval: str,
    limit: int,
) -> Tuple[bool, str]:
    try:
        output_data = await collect_snapshot_async(client, exchange, symbol, interval, limit)
        output_path = build_output_path(exchange, symbol, interval, output_data["klines"])
        save_json(output_data, output_path)
        print(
            f"[{symbol} - {interval}] 已写入 {output_path}，K线 {len(output_data['klines'])} 条。"
            " 24小时统计、资金费率、持仓量、最新价格和订单簿深度已包含。"
        )
        return True, ""
    except (httpx.HTTPError, ValueError, KeyError) as exc:
        msg = f"{symbol} ({interval}): {exc}"
        print(f"[{symbol} - {interval}] 处理失败：{exc}", file=sys.stderr)
        return False, msg


async def collect_snapshot_async(
    client: httpx.AsyncClient,
    exchange: str,
    symbol: str,
    interval: str,
    limit: int,
) -> dict:
    if exchange == "binance":
        (
            records,
            ticker_24hr,
            funding_rate,
            open_interest,
            current_price,
            order_book,
        ) = await asyncio.gather(
            fetch_binance_klines_async(client, symbol, interval, limit),
            fetch_binance_24hr_ticker_async(client, symbol),
            fetch_binance_funding_rate_async(client, symbol),
            fetch_binance_open_interest_async(client, symbol),
            fetch_binance_current_price_async(client, symbol),
            fetch_binance_order_book_async(client, symbol),
        )
    else:
        (
            records,
            ticker_24hr,
            funding_rate,
            open_interest,
            current_price,
            order_book,
        ) = await asyncio.gather(
            fetch_okx_klines_async(client, symbol, interval, limit),
            fetch_okx_24hr_ticker_async(client, symbol),
            fetch_okx_funding_rate_async(client, symbol),
            fetch_okx_open_interest_async(client, symbol),
            fetch_okx_current_price_async(client, symbol),
            fetch_okx_order_book_async(client, symbol),
        )

    if not records:
        raise ValueError("未获取到任何数据，请检查交易对和参数。")

    records_with_indicators = calculate_indicators(records)

    return {
        "exchange": exchange,
        "klines": records_with_indicators,
        "ticker_24hr": ticker_24hr,
        "funding_rate": funding_rate,
        "open_interest": open_interest,
        "current_price": current_price,
        "order_book": order_book,
    }


def resolve_intervals(args: argparse.Namespace) -> List[str]:
    """处理 intervals 参数，支持逗号分隔和空格分隔。"""
    raw_list = args.interval
    if not raw_list:
        return ["1h"]
    
    if isinstance(raw_list, str):
        raw_list = [raw_list]
        
    intervals = []
    for item in raw_list:
        for part in item.replace(",", " ").split():
            cleaned = part.strip()
            if cleaned:
                intervals.append(cleaned)
                
    return list(set(intervals))  # 去重


def resolve_symbols(args: argparse.Namespace) -> List[str]:
    """根据 CLI 参数确定需要处理的交易对列表。"""
    raw_list = args.symbols
    if not raw_list:
        raise ValueError("请使用 --symbols 指定至少一个交易对，或 ALL。")

    # 处理输入列表，支持 "A B,C D" 这种混合格式
    symbols_candidates = []
    if isinstance(raw_list, str):
        raw_list = [raw_list]
        
    for item in raw_list:
        # 将逗号替换为空格，然后统一按空格分割
        # 这样无论是 "A,B" 还是 "A B" 还是 "A, B" 都能正确处理
        for part in item.replace(",", " ").split():
            cleaned = part.strip()
            if cleaned:
                symbols_candidates.append(cleaned)

    if not symbols_candidates:
        raise ValueError("未找到任何需要处理的交易对。")

    # 检查是否有 ALL
    if any(s.upper() == "ALL" for s in symbols_candidates):
        symbols = list_all_symbols(args)
    else:
        symbols = [normalize_symbol(s, args.exchange) for s in symbols_candidates]

    if args.max_symbols and len(symbols) > args.max_symbols:
        symbols = symbols[: args.max_symbols]

    return symbols


def list_all_symbols(args: argparse.Namespace) -> List[str]:
    """列出指定交易所的全部交易对，供批量模式使用。"""
    quote_assets = normalize_symbol_list(args.quote, args.exchange) if args.quote else None

    if args.exchange == "binance":
        symbols = list_binance_symbols(
            contract_type=args.contract_type.upper() if args.contract_type else "PERPETUAL",
            quote_assets=quote_assets,
        )
    else:
        symbols = list_okx_symbols(
            inst_type=args.inst_type.upper() if args.inst_type else "SWAP",
            quote_assets=quote_assets,
        )
    return [normalize_symbol(sym, args.exchange) for sym in symbols]


def normalize_symbol_list(symbols_text: str, exchange: str) -> List[str]:
    """将逗号分隔的交易对字符串标准化为列表。"""
    return [
        normalize_symbol(part, exchange)
        for part in symbols_text.split(",")
        if part.strip()
    ]


def normalize_symbol(symbol: str, exchange: str) -> str:
    """统一交易对格式（主要是大写处理）。"""
    return symbol.strip().upper()


if __name__ == "__main__":
    main()


