"""
波动率转换分析模块

用于判断币种是否可能从低波动率转换到高波动率。
基于历史数据和技术指标，不依赖未来信息（无提前量）。
"""
from typing import Any, Dict, List, Optional, Tuple
import json

def calculate_volatility_regime(klines: List[Dict[str, Any]], lookback: int = 20) -> Dict[str, Any]:
    """
    计算当前波动率状态和趋势。
    
    Args:
        klines: K线数据列表（需包含atr14_pct或volatility_20_pct）
        lookback: 回看周期数，用于计算历史波动率分位数
    
    Returns:
        包含波动率状态、趋势、转换信号等的字典
    """
    if not klines or len(klines) < lookback:
        return {
            "status": "insufficient_data",
            "message": f"数据不足，需要至少{lookback}根K线"
        }
    
    # 获取最近的K线数据
    recent = klines[-lookback:]
    latest = klines[-1]
    
    # 提取波动率指标（优先使用ATR百分比，其次使用标准差）
    volatility_key = "atr14_pct" if "atr14_pct" in latest else "volatility_20_pct"
    if volatility_key not in latest:
        return {
            "status": "no_volatility_data",
            "message": "K线数据中缺少波动率指标，请先运行calculate_indicators"
        }
    
    # 收集历史波动率值
    historical_vol = [
        k.get(volatility_key, 0) 
        for k in recent 
        if k.get(volatility_key) is not None
    ]
    
    if not historical_vol:
        return {
            "status": "no_volatility_data",
            "message": "无法提取历史波动率数据"
        }
    
    current_vol = latest.get(volatility_key, 0)
    avg_vol = sum(historical_vol) / len(historical_vol)
    max_vol = max(historical_vol)
    min_vol = min(historical_vol)
    
    # 计算波动率分位数（当前波动率在历史中的位置）
    sorted_vol = sorted(historical_vol)
    percentile = (sum(1 for v in sorted_vol if v <= current_vol) / len(sorted_vol)) * 100
    
    # 判断波动率状态
    if current_vol < avg_vol * 0.7:
        regime = "low_volatility"
    elif current_vol > avg_vol * 1.3:
        regime = "high_volatility"
    else:
        regime = "normal_volatility"
    
    # 计算短期趋势（最近5根K线的波动率变化）
    short_term_vol = [
        k.get(volatility_key, 0) 
        for k in klines[-5:] 
        if k.get(volatility_key) is not None
    ]
    vol_trend = "increasing" if len(short_term_vol) >= 2 and short_term_vol[-1] > short_term_vol[0] else "decreasing"
    
    return {
        "status": "ok",
        "current_volatility": round(current_vol, 4),
        "average_volatility": round(avg_vol, 4),
        "max_volatility": round(max_vol, 4),
        "min_volatility": round(min_vol, 4),
        "volatility_percentile": round(percentile, 2),
        "regime": regime,
        "volatility_trend": vol_trend,
        "volatility_key": volatility_key
    }


def detect_volatility_expansion_signals(
    klines: List[Dict[str, Any]], 
    ticker_24hr: Optional[Dict[str, Any]] = None,
    funding_rate: Optional[Dict[str, Any]] = None,
    open_interest: Optional[Dict[str, Any]] = None,
    order_book: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    检测可能从低波动转换到高波动的信号。
    
    基于以下维度：
    1. 波动率压缩后的突破信号（布林带收缩）
    2. 成交量放大
    3. 价格突破关键位置
    4. 市场情绪变化（资金费率、持仓量）
    5. 订单簿失衡
    6. RSI极端值后的反转
    
    Returns:
        包含信号强度、具体信号列表、综合判断的字典
    """
    if not klines or len(klines) < 20:
        return {
            "status": "insufficient_data",
            "signals": [],
            "signal_strength": 0
        }
    
    signals = []
    signal_strength = 0
    
    # 1. 波动率状态分析
    vol_analysis = calculate_volatility_regime(klines)
    if vol_analysis.get("status") != "ok":
        return {
            "status": vol_analysis.get("status"),
            "signals": [],
            "signal_strength": 0
        }
    
    current_regime = vol_analysis.get("regime")
    vol_percentile = vol_analysis.get("volatility_percentile", 50)
    vol_trend = vol_analysis.get("volatility_trend")
    
    # 信号1: 当前处于低波动状态，但波动率开始上升
    if current_regime == "low_volatility" and vol_trend == "increasing":
        signals.append({
            "type": "volatility_trend_reversal",
            "description": "低波动状态但波动率开始上升",
            "strength": 2
        })
        signal_strength += 2
    
    # 信号2: 波动率压缩（当前波动率处于历史低位，但价格开始突破）
    if vol_percentile < 30:  # 波动率处于历史30%分位以下
        latest = klines[-1]
        prev = klines[-2] if len(klines) >= 2 else None
        
        # 检查价格是否开始突破（涨幅或跌幅增大）
        if prev:
            current_change = abs(latest.get("price_change_pct", 0))
            prev_change = abs(prev.get("price_change_pct", 0))
            if current_change > prev_change * 1.5:  # 当前波动明显大于前一根
                signals.append({
                    "type": "volatility_compression_breakout",
                    "description": f"波动率压缩后价格突破（当前涨跌幅{current_change:.2f}% vs 前一根{prev_change:.2f}%）",
                    "strength": 3
                })
                signal_strength += 3
    
    # 信号3: 成交量放大（需要至少2根K线对比）
    if len(klines) >= 2:
        recent_volumes = [k.get("volume", 0) for k in klines[-5:]]
        avg_volume = sum(recent_volumes) / len(recent_volumes)
        latest_volume = klines[-1].get("volume", 0)
        
        if latest_volume > avg_volume * 1.5:  # 最新成交量比近期平均高50%以上
            signals.append({
                "type": "volume_expansion",
                "description": f"成交量放大（最新{latest_volume:.2f} vs 平均{avg_volume:.2f}）",
                "strength": 2
            })
            signal_strength += 2
    
    # 信号4: RSI极端值后的反转信号
    latest = klines[-1]
    rsi = latest.get("rsi14")
    if rsi is not None:
        if rsi < 30:  # 超卖
            signals.append({
                "type": "rsi_oversold",
                "description": f"RSI超卖（{rsi:.2f}），可能反弹带来波动",
                "strength": 1
            })
            signal_strength += 1
        elif rsi > 70:  # 超买
            signals.append({
                "type": "rsi_overbought",
                "description": f"RSI超买（{rsi:.2f}），可能回调带来波动",
                "strength": 1
            })
            signal_strength += 1
    
    # 信号5: 价格突破移动平均线
    if len(klines) >= 20:
        latest = klines[-1]
        prev = klines[-2] if len(klines) >= 2 else None
        ma20 = latest.get("ma20")
        ma50 = latest.get("ma50")
        close = latest.get("close")
        
        if ma20 and close and prev:
            prev_close = prev.get("close")
            # 价格从MA20下方突破到上方，或反之
            if prev_close < ma20 and close > ma20:
                signals.append({
                    "type": "price_breakout_ma20",
                    "description": "价格突破MA20，可能引发波动",
                    "strength": 2
                })
                signal_strength += 2
            elif prev_close > ma20 and close < ma20:
                signals.append({
                    "type": "price_breakdown_ma20",
                    "description": "价格跌破MA20，可能引发波动",
                    "strength": 2
                })
                signal_strength += 2
    
    # 信号6: 市场情绪变化（资金费率）
    if funding_rate:
        funding = funding_rate.get("lastFundingRate") or funding_rate.get("fundingRate")
        if funding is not None:
            # 资金费率绝对值较大，说明市场情绪极端
            if abs(funding) > 0.05:  # 0.05%以上
                signals.append({
                    "type": "extreme_funding_rate",
                    "description": f"资金费率极端（{funding*100:.4f}%），可能引发反向波动",
                    "strength": 2
                })
                signal_strength += 2
    
    # 信号7: 持仓量变化
    if open_interest:
        oi = open_interest.get("openInterest")
        if oi and len(klines) >= 2:
            # 持仓量快速增加通常伴随波动
            # 注意：这里需要历史持仓量数据才能判断趋势，当前只能判断绝对值
            signals.append({
                "type": "open_interest_present",
                "description": f"持仓量：{oi}（需结合历史趋势判断）",
                "strength": 1
            })
            signal_strength += 1
    
    # 信号8: 订单簿失衡
    if order_book:
        bids = order_book.get("bids", [])
        asks = order_book.get("asks", [])
        if bids and asks:
            bid_value = sum(float(price) * float(qty) for price, qty in bids[:10])
            ask_value = sum(float(price) * float(qty) for price, qty in asks[:10])
            total = bid_value + ask_value
            if total > 0:
                imbalance = (bid_value - ask_value) / total
                if abs(imbalance) > 0.3:  # 买卖盘失衡超过30%
                    signals.append({
                        "type": "order_book_imbalance",
                        "description": f"订单簿失衡（{'买盘' if imbalance > 0 else '卖盘'}压力{abs(imbalance)*100:.1f}%）",
                        "strength": 2
                    })
                    signal_strength += 2
    
    # 信号9: 24小时涨跌幅较大（市场已经活跃）
    if ticker_24hr:
        change_24h = ticker_24hr.get("priceChangePercent", 0)
        if abs(change_24h) > 5:  # 24小时涨跌幅超过5%
            signals.append({
                "type": "high_24h_volatility",
                "description": f"24小时涨跌幅{change_24h:.2f}%，市场已活跃",
                "strength": 1
            })
            signal_strength += 1
    
    # 综合判断
    if signal_strength >= 6:
        conclusion = "high_probability"
        conclusion_text = "高概率：多个信号叠加，从低波动转换到高波动的可能性较大"
    elif signal_strength >= 4:
        conclusion = "medium_probability"
        conclusion_text = "中等概率：存在一些转换信号，值得关注"
    elif signal_strength >= 2:
        conclusion = "low_probability"
        conclusion_text = "低概率：信号较弱，需要更多确认"
    else:
        conclusion = "no_signal"
        conclusion_text = "无明确信号：当前处于稳定状态，转换可能性较低"
    
    return {
        "status": "ok",
        "volatility_analysis": vol_analysis,
        "signals": signals,
        "signal_strength": signal_strength,
        "conclusion": conclusion,
    }


def format_volatility_analysis(result: Dict[str, Any]) -> str:
    """以 JSON 字符串形式返回结构化的波动率分析结果，用于调试/日志。"""
    # 直接序列化整个结果字典，避免额外的人类可读文案逻辑
    try:
        return json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True)
    except TypeError:
        # 回退到 repr，保证不会因为个别不可序列化字段而报错
        return repr(result)

