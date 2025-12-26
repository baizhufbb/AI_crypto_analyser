import argparse
import json
import sys
from pathlib import Path

# 添加项目根目录到 sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from crypto_analyzer.core.storage import load_json
from crypto_analyzer.analysis.summary import summarize, format_summary
from crypto_analyzer.analysis.volatility import (
    detect_volatility_expansion_signals,
    format_volatility_analysis,
)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract technical indicators from fetch_klines.py JSON output."
    )
    parser.add_argument("--file", required=True, help="Path to the JSON file to summarize")
    parser.add_argument("--json", action="store_true", help="Output as JSON instead of formatted text")
    parser.add_argument("--volatility", action="store_true", help="Include volatility expansion analysis")
    args = parser.parse_args()
    
    path = Path(args.file)
    try:
        data = load_json(path)
        summary = summarize(data)
        
        if args.json:
            # JSON输出模式，方便程序化处理
            output = {"summary": summary}
            if args.volatility:
                vol_result = detect_volatility_expansion_signals(
                    klines=data.get("klines", []),
                    ticker_24hr=data.get("ticker_24hr"),
                    funding_rate=data.get("funding_rate"),
                    open_interest=data.get("open_interest"),
                    order_book=data.get("order_book")
                )
                output["volatility_analysis"] = vol_result
            print(json.dumps(output, ensure_ascii=False, indent=2))
        else:
            # 格式化文本输出
            print(format_summary(summary))
            
            if args.volatility:
                print("\n" + "=" * 60)
                print("[VOLATILITY ANALYSIS]")
                print("=" * 60)
                vol_result = detect_volatility_expansion_signals(
                    klines=data.get("klines", []),
                    ticker_24hr=data.get("ticker_24hr"),
                    funding_rate=data.get("funding_rate"),
                    open_interest=data.get("open_interest"),
                    order_book=data.get("order_book")
                )
                print(format_volatility_analysis(vol_result))
    except Exception as e:
        print(f"Error processing file {path}: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
