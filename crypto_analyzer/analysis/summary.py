from typing import Any, Dict, Iterable

def latest_kline(klines: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    data = list(klines)
    if not data:
        raise ValueError("No kline data found in JSON")
    
    # 自动判断顺序：取 open_time 最大的那个
    first = data[0]
    last = data[-1]
    
    t1 = first.get('open_time', 0)
    t2 = last.get('open_time', 0)
    
    if t1 > t2:
        return first  # 倒序，第一个是最新的
    else:
        return last   # 正序，最后一个是最新的


def order_book_imbalance(order_book: Dict[str, Any], depth: int = 10) -> float:
    bids = order_book.get("bids") or []
    asks = order_book.get("asks") or []
    bid_value = sum(float(price) * float(qty) for price, qty in bids[:depth])
    ask_value = sum(float(price) * float(qty) for price, qty in asks[:depth])
    total = bid_value + ask_value
    return (bid_value - ask_value) / total if total else 0.0


def volume_spike(klines: Iterable[Dict[str, Any]], lookback: int = 20) -> float:
    """计算最后一根K线的成交量相对于过去平均值的倍数"""
    data = list(klines)
    if len(data) < lookback + 1:
        return 0.0
    last_vol = float(data[-1].get('volume', 0))
    # 取前 n 根（不含当前）计算平均
    prev_vols = [float(k.get('volume', 0)) for k in data[-lookback-1:-1]]
    avg_vol = sum(prev_vols) / len(prev_vols) if prev_vols else 0
    return last_vol / avg_vol if avg_vol > 0 else 0.0


def analyze_signals(summary: Dict[str, Any], klines: list) -> Dict[str, Any]:
    """客观识别技术信号，不含主观判断"""
    signals = {}
    
    # 1. RSI 状态
    rsi = summary.get('rsi14')
    if rsi is not None:
        if rsi < 20:
            signals['rsi_status'] = 'extreme_oversold'
            signals['rsi_level'] = '<20'
        elif rsi < 30:
            signals['rsi_status'] = 'oversold'
            signals['rsi_level'] = '20-30'
        elif rsi > 80:
            signals['rsi_status'] = 'extreme_overbought'
            signals['rsi_level'] = '>80'
        elif rsi > 70:
            signals['rsi_status'] = 'overbought'
            signals['rsi_level'] = '70-80'
        elif rsi > 50:
            signals['rsi_status'] = 'bullish'
            signals['rsi_level'] = '50-70'
        elif rsi > 30:
            signals['rsi_status'] = 'bearish'
            signals['rsi_level'] = '30-50'

    # 2. 均线位置关系（SMA和EMA）
    price = summary.get('current_price', 0)
    ma20 = summary.get('ma20')
    ma50 = summary.get('ma50')
    ema20 = summary.get('ema20')
    ema50 = summary.get('ema50')
    vwap = summary.get('vwap')
    
    if ma20 and ma50 and price:
        # 价格与SMA均线的距离百分比
        signals['price_vs_ma20_pct'] = round(((price - ma20) / ma20) * 100, 2)
        signals['price_vs_ma50_pct'] = round(((price - ma50) / ma50) * 100, 2)
        signals['ma20_vs_ma50_pct'] = round(((ma20 - ma50) / ma50) * 100, 2)
        
        # SMA趋势判断
        if price > ma20 > ma50:
            signals['trend'] = 'uptrend'
        elif price < ma20 < ma50:
            signals['trend'] = 'downtrend'
        elif ma20 > ma50 and price < ma20:
            signals['trend'] = 'uptrend_pullback'
        elif ma20 < ma50 and price > ma20:
            signals['trend'] = 'downtrend_rebound'
        else:
            signals['trend'] = 'sideways'
    
    # EMA均线位置关系
    if ema20 and ema50 and price:
        signals['price_vs_ema20_pct'] = round(((price - ema20) / ema20) * 100, 2)
        signals['price_vs_ema50_pct'] = round(((price - ema50) / ema50) * 100, 2)
        signals['ema20_vs_ema50_pct'] = round(((ema20 - ema50) / ema50) * 100, 2)
        
        # EMA趋势判断（更敏感）
        if price > ema20 > ema50:
            signals['ema_trend'] = 'uptrend'
        elif price < ema20 < ema50:
            signals['ema_trend'] = 'downtrend'
        elif ema20 > ema50 and price < ema20:
            signals['ema_trend'] = 'uptrend_pullback'
        elif ema20 < ema50 and price > ema20:
            signals['ema_trend'] = 'downtrend_rebound'
        else:
            signals['ema_trend'] = 'sideways'
    
    # VWAP位置关系（反映平均成本）
    if vwap and price:
        signals['price_vs_vwap_pct'] = round(((price - vwap) / vwap) * 100, 2)
        if price > vwap:
            signals['vwap_position'] = 'above_vwap'  # 价格高于平均成本，可能偏强
        else:
            signals['vwap_position'] = 'below_vwap'  # 价格低于平均成本，可能偏弱

    # 3. 成交量比率
    vol_ratio = volume_spike(klines)
    signals['volume_ratio'] = round(vol_ratio, 2)
    if vol_ratio > 3.0:
        signals['volume_status'] = 'extreme_spike'
    elif vol_ratio > 2.0:
        signals['volume_status'] = 'spike'
    elif vol_ratio > 1.5:
        signals['volume_status'] = 'elevated'
    elif vol_ratio < 0.5:
        signals['volume_status'] = 'low'
    else:
        signals['volume_status'] = 'normal'

    # 布林带状态（20周期）
    boll_width_pct = summary.get('boll_width_20_pct')
    boll_pct_b = summary.get('boll_pct_b_20')
    if boll_width_pct is not None:
        signals['boll_width_20_pct'] = round(float(boll_width_pct), 2)
        if boll_width_pct < 5:
            signals['boll_regime_20'] = 'squeeze'
        elif boll_width_pct > 15:
            signals['boll_regime_20'] = 'expansion'
        else:
            signals['boll_regime_20'] = 'normal'
    if boll_pct_b is not None:
        signals['boll_pct_b_20'] = round(float(boll_pct_b), 2)
        if boll_pct_b < 0:
            signals['boll_position_20'] = 'below_band'
        elif boll_pct_b < 0.2:
            signals['boll_position_20'] = 'near_lower'
        elif boll_pct_b < 0.8:
            signals['boll_position_20'] = 'middle'
        elif boll_pct_b <= 1:
            signals['boll_position_20'] = 'near_upper'
        else:
            signals['boll_position_20'] = 'above_band'

    macd_dif = summary.get('macd_dif')
    macd_dea = summary.get('macd_dea')
    macd_hist = summary.get('macd_hist')
    if macd_dif is not None and macd_dea is not None:
        if macd_dif > macd_dea:
            signals['macd_bias'] = 'bullish'
        elif macd_dif < macd_dea:
            signals['macd_bias'] = 'bearish'
        else:
            signals['macd_bias'] = 'neutral'
        if macd_hist is not None:
            if macd_hist > 0:
                signals['macd_momentum_side'] = 'bullish'
            elif macd_hist < 0:
                signals['macd_momentum_side'] = 'bearish'
            else:
                signals['macd_momentum_side'] = 'neutral'
    if klines and len(klines) >= 2:
        ordered = sorted(klines, key=lambda k: k.get('open_time', 0))
        prev = ordered[-2]
        last_k = ordered[-1]
        d0 = prev.get('macd_dif')
        e0 = prev.get('macd_dea')
        d1 = last_k.get('macd_dif')
        e1 = last_k.get('macd_dea')
        if d0 is not None and e0 is not None and d1 is not None and e1 is not None:
            if d0 <= e0 and d1 > e1:
                signals['macd_cross'] = 'bullish_cross'
            elif d0 >= e0 and d1 < e1:
                signals['macd_cross'] = 'bearish_cross'
        h0 = prev.get('macd_hist')
        h1 = last_k.get('macd_hist')
        if h0 is not None and h1 is not None:
            hist_change = h1 - h0
            signals['macd_hist_change'] = round(hist_change, 8)
            if h1 > 0 and hist_change > 0:
                signals['macd_hist_trend'] = 'bullish_expansion'
            elif h1 > 0 and hist_change < 0:
                signals['macd_hist_trend'] = 'bullish_contraction'
            elif h1 < 0 and hist_change < 0:
                signals['macd_hist_trend'] = 'bearish_expansion'
            elif h1 < 0 and hist_change > 0:
                signals['macd_hist_trend'] = 'bearish_contraction'
    
    summary['signals'] = signals
    return summary


def summarize(payload: Dict[str, Any]) -> Dict[str, Any]:
    """提取客观技术指标和市场数据"""
    klines = payload.get("klines", [])
    last = latest_kline(klines)
    ticker = payload.get("ticker_24hr", {})
    funding = payload.get("funding_rate", {})
    open_interest = payload.get("open_interest", {})
    order_book = payload.get("order_book", {})
    current_price_data = payload.get("current_price", {})

    # 优先使用实时价格，如果没有则使用最后一根K线的收盘价
    price = current_price_data.get("price")
    if price is None:
        price = float(last.get("close", 0))

    summary = {
        "symbol": last.get("symbol") or ticker.get("symbol") or current_price_data.get("symbol") or payload.get("exchange", "unknown"),
        "current_price": price,
        "kline_close": float(last.get("close", 0)),
        "open": float(last.get("open", 0)),
        "high": float(last.get("high", 0)),
        "low": float(last.get("low", 0)),
        "ma20": last.get("ma20"),
        "ma50": last.get("ma50"),
        "ema20": last.get("ema20"),
        "ema50": last.get("ema50"),
        "vwap": last.get("vwap"),
        "rsi14": last.get("rsi14"),
        "atr14": last.get("atr14"),
        "atr14_pct": last.get("atr14_pct"),
        "volatility_20_pct": last.get("volatility_20_pct"),
        "boll_upper_20": last.get("boll_upper_20"),
        "boll_lower_20": last.get("boll_lower_20"),
        "boll_width_20": last.get("boll_width_20"),
        "boll_width_20_pct": last.get("boll_width_20_pct"),
        "boll_pct_b_20": last.get("boll_pct_b_20"),
        "macd_dif": last.get("macd_dif"),
        "macd_dea": last.get("macd_dea"),
        "macd_hist": last.get("macd_hist"),
        "change_24h_pct": ticker.get("priceChangePercent"),
        "high_24h": ticker.get("highPrice"),
        "low_24h": ticker.get("lowPrice"),
        "volume_24h": ticker.get("volume"),
        "quote_volume_24h": ticker.get("quoteVolume"),
        "funding_rate": funding.get("lastFundingRate") or funding.get("fundingRate"),
        "next_funding_time": funding.get("nextFundingTime"),
        "open_interest": open_interest.get("openInterest"),
        "order_book_imbalance": order_book_imbalance(order_book),
    }
    
    # 添加客观信号分析
    summary = analyze_signals(summary, klines)
    
    return summary


def format_summary(summary: Dict[str, Any]) -> str:
    """格式化为结构化的技术指标输出"""
    lines = [
        "=" * 60,
        f"Symbol: {summary['symbol']}",
        "=" * 60,
    ]
    
    # 价格信息
    lines.append("\n[PRICE]")
    lines.append(f"Current: {summary.get('current_price', 0)}")
    if summary.get('kline_close') and abs(summary.get('current_price', 0) - summary.get('kline_close', 0)) > 0.0001:
        lines.append(f"K-line Close: {summary.get('kline_close')}")
    lines.append(f"24h Change: {summary.get('change_24h_pct')}%")
    
    # 技术指标
    lines.append("\n[TECHNICAL INDICATORS]")
    lines.append(f"RSI(14): {summary.get('rsi14')}")
    lines.append(f"MA20: {summary.get('ma20')}")
    lines.append(f"MA50: {summary.get('ma50')}")
    if summary.get('ema20'):
        lines.append(f"EMA20: {summary.get('ema20')}")
    if summary.get('ema50'):
        lines.append(f"EMA50: {summary.get('ema50')}")
    if summary.get('vwap'):
        lines.append(f"VWAP: {summary.get('vwap')}")
    if summary.get("boll_pct_b_20") is not None:
        lines.append(f"BOLL(20,2) %B: {summary.get('boll_pct_b_20')}")
    if summary.get("boll_width_20_pct") is not None:
        lines.append(f"BOLL Width%: {summary.get('boll_width_20_pct')}")
    if summary.get("macd_dif") is not None:
        lines.append(f"MACD DIF: {summary.get('macd_dif')}")
        lines.append(f"MACD DEA: {summary.get('macd_dea')}")
        lines.append(f"MACD Hist: {summary.get('macd_hist')}")
    
    # 信号分析
    signals = summary.get('signals', {})
    if signals:
        lines.append("\n[SIGNALS]")
        for key, value in signals.items():
            lines.append(f"{key}: {value}")
    
    # 市场数据
    lines.append("\n[MARKET DATA]")
    lines.append(f"Funding Rate: {summary.get('funding_rate')}")
    lines.append(f"Open Interest: {summary.get('open_interest')}")
    lines.append(f"Order Book Imbalance: {summary.get('order_book_imbalance'):.4f}")
    
    # ATR波动率
    if summary.get('atr14'):
        lines.append(f"ATR(14): {summary.get('atr14')}")
    if summary.get('atr14_pct'):
        lines.append(f"ATR(14) %: {summary.get('atr14_pct')}%")

    return "\n".join(lines)
