import math
from datetime import datetime, timezone
from typing import Any, Dict, List


def calculate_indicators(records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    为 K 线数据计算技术指标：MA、RSI、涨跌幅、波动率等。
    预计算这些指标可以节省 AI 分析时的计算时间。
    
    注意：输入 records 必须是按时间倒序排列（最新的在前，符合 binance/okx fetcher 的统一输出）。
    但在计算指标时，为了逻辑简单，我们会先将其临时反转为正序（旧->新），
    计算完成后再反转回来返回。
    """
    if not records:
        return records

    # 临时反转为正序（旧->新）进行计算
    records_sorted = records[::-1]
    result_sorted: List[Dict[str, Any]] = []
    closes = [r["close"] for r in records_sorted]
    volumes = [r.get("volume", 0) for r in records_sorted]
    quote_volumes = [r.get("quote_volume", 0) for r in records_sorted]
    short_alpha = 2 / 13
    long_alpha = 2 / 27
    signal_alpha = 2 / 10
    ema_short = None
    ema_long = None
    dea = None
    dif = None
    
    # EMA20和EMA50的alpha值
    ema20_alpha = 2 / 21  # 2 / (20 + 1)
    ema50_alpha = 2 / 51  # 2 / (50 + 1)
    ema20 = None
    ema50 = None
    
    # VWAP计算（日内VWAP，每天00:00 UTC重置）
    cumulative_price_volume = 0.0
    cumulative_volume = 0.0
    current_day = None  # 用于跟踪当前日期

    for i, record in enumerate(records_sorted):
        enriched = record.copy()
        close_price = record["close"]
        volume = record.get("volume", 0)
        # 使用quote_volume（成交额）计算VWAP更准确，如果没有则用volume * close_price
        quote_vol = record.get("quote_volume", volume * close_price if volume > 0 else 0)

        # SMA计算
        if i >= 19:
            enriched["ma20"] = round(sum(closes[i - 19 : i + 1]) / 20, 8)
        if i >= 49:
            enriched["ma50"] = round(sum(closes[i - 49 : i + 1]) / 50, 8)
        
        # EMA20和EMA50计算
        if ema20 is None:
            ema20 = close_price
        else:
            ema20 = ema20 + ema20_alpha * (close_price - ema20)
        if i >= 19:  # EMA20需要至少20根K线才有效
            enriched["ema20"] = round(ema20, 8)
        
        if ema50 is None:
            ema50 = close_price
        else:
            ema50 = ema50 + ema50_alpha * (close_price - ema50)
        if i >= 49:  # EMA50需要至少50根K线才有效
            enriched["ema50"] = round(ema50, 8)
        
        # 日内VWAP计算（每天00:00 UTC重置）
        # VWAP = Σ(典型价格 × 成交量) / Σ成交量（当天累计）
        # 典型价格 = (high + low + close) / 3
        
        # 获取当前K线的日期（UTC时区，只取日期部分）
        # open_time是毫秒时间戳
        kline_timestamp = record.get("open_time", 0) / 1000  # 转换为秒
        kline_date = datetime.fromtimestamp(kline_timestamp, tz=timezone.utc).date()
        
        # 检查是否进入新的一天，如果是则重置累计值
        if current_day is None or kline_date != current_day:
            current_day = kline_date
            cumulative_price_volume = 0.0
            cumulative_volume = 0.0
        
        # 计算典型价格并累加
        typical_price = (record.get("high", close_price) + record.get("low", close_price) + close_price) / 3
        if volume > 0:
            cumulative_price_volume += typical_price * volume
            cumulative_volume += volume
            if cumulative_volume > 0:
                enriched["vwap"] = round(cumulative_price_volume / cumulative_volume, 8)

        if i >= 14:
            period_closes = closes[i - 14 : i + 1]
            gains = []
            losses = []
            for j in range(1, len(period_closes)):
                change = period_closes[j] - period_closes[j - 1]
                if change > 0:
                    gains.append(change)
                    losses.append(0.0)
                else:
                    gains.append(0.0)
                    losses.append(abs(change))
            avg_gain = sum(gains) / 14
            avg_loss = sum(losses) / 14
            if avg_loss == 0:
                enriched["rsi14"] = 100.0
            else:
                rs = avg_gain / avg_loss
                enriched["rsi14"] = round(100 - (100 / (1 + rs)), 2)

        if i > 0:
            prev_close = records_sorted[i - 1]["close"]
            price_change = record["close"] - prev_close
            price_change_pct = (price_change / prev_close) * 100
            enriched["price_change"] = round(price_change, 8)
            enriched["price_change_pct"] = round(price_change_pct, 4)

        # 计算波动率指标（ATR和标准差）
        # ATR (Average True Range) - 14周期
        if i >= 14:
            true_ranges = []
            for j in range(max(1, i - 13), i + 1):
                high = records_sorted[j]["high"]
                low = records_sorted[j]["low"]
                if j > 0:
                    prev_close = records_sorted[j - 1]["close"]
                    tr = max(
                        high - low,
                        abs(high - prev_close),
                        abs(low - prev_close)
                    )
                else:
                    tr = high - low
                true_ranges.append(tr)
            enriched["atr14"] = round(sum(true_ranges) / len(true_ranges), 8)
            # ATR百分比（相对于价格）
            if record["close"] > 0:
                enriched["atr14_pct"] = round((enriched["atr14"] / record["close"]) * 100, 4)

        # 标准差波动率（20周期）
        if i >= 19:
            period_closes = closes[i - 19 : i + 1]
            mean = sum(period_closes) / len(period_closes)
            variance = sum((x - mean) ** 2 for x in period_closes) / len(period_closes)
            std_dev = math.sqrt(variance)
            enriched["volatility_20"] = round(std_dev, 8)
            # 波动率百分比
            if mean > 0:
                enriched["volatility_20_pct"] = round((std_dev / mean) * 100, 4)
                upper = mean + 2 * std_dev
                lower = mean - 2 * std_dev
                enriched["boll_upper_20"] = round(upper, 8)
                enriched["boll_lower_20"] = round(lower, 8)
                width = upper - lower
                enriched["boll_width_20"] = round(width, 8)
                enriched["boll_width_20_pct"] = round((width / mean) * 100, 4)
                if width > 0:
                    pct_b = (close_price - lower) / width
                    enriched["boll_pct_b_20"] = round(pct_b, 4)

        # MACD计算（使用独立的EMA）
        if ema_short is None:
            ema_short = close_price
            ema_long = close_price
            dif = 0.0
            dea = 0.0
        else:
            ema_short = ema_short + short_alpha * (close_price - ema_short)
            ema_long = ema_long + long_alpha * (close_price - ema_long)
            dif = ema_short - ema_long
            if dea is None:
                dea = dif
            else:
                dea = dea + signal_alpha * (dif - dea)
        if dif is not None and dea is not None and i >= 26:
            macd_hist = (dif - dea) * 2
            enriched["macd_dif"] = round(dif, 8)
            enriched["macd_dea"] = round(dea, 8)
            enriched["macd_hist"] = round(macd_hist, 8)

        result_sorted.append(enriched)

    # 计算完成后，反转回倒序（最新的在前）返回
    return result_sorted[::-1]


