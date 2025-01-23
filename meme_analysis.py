import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import pandas_ta as ta
import requests
from datetime import datetime

# Binance API 配置
BINANCE_API_URL = "https://api.binance.com/api/v3"

def get_meme_coin_data(coin):
    """获取meme币的基础数据"""
    try:
        # 获取24小时行情数据
        ticker_url = f"{BINANCE_API_URL}/ticker/24hr?symbol={coin}USDT"
        response = requests.get(ticker_url)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        st.error(f"获取{coin}数据时发生错误: {str(e)}")
        return None

def get_klines_data(coin, interval, limit=24):
    """获取K线数据"""
    try:
        klines_url = f"{BINANCE_API_URL}/klines"
        params = {
            "symbol": f"{coin}USDT",
            "interval": interval,
            "limit": limit
        }
        response = requests.get(klines_url, params=params)
        response.raise_for_status()

        # 处理K线数据
        df = pd.DataFrame(response.json(), columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_volume', 'trades', 'taker_buy_base',
            'taker_buy_quote', 'ignore'
        ])

        # 转换数据类型
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'volume']:
            df[col] = df[col].astype(float)

        return df
    except Exception as e:
        st.error(f"获取K线数据时发生错误: {str(e)}")
        return None

def calculate_technical_indicators(df):
    """计算技术指标"""
    try:
        # 计算RSI
        df['rsi'] = df.ta.rsi(length=14)
        # 计算EMA
        df['ema20'] = df.ta.ema(length=20)
        return df
    except Exception as e:
        st.error(f"计算技术指标时发生错误: {str(e)}")
        return df

def plot_price_chart(df, coin):
    """绘制价格走势图"""
    try:
        fig, ax = plt.subplots(figsize=(12, 6))
        ax.plot(df['timestamp'], df['close'], label='价格')
        ax.plot(df['timestamp'], df['ema20'], label='20周期EMA', linestyle='--')
        ax.fill_between(df['timestamp'], 
                      df['low'], df['high'],
                      color='gray', alpha=0.2, label='价格区间')
        ax.set_xlabel('时间')
        ax.set_ylabel(f'{coin} 价格 (USDT)')
        ax.legend()
        return fig
    except Exception as e:
        st.error(f"绘制图表时发生错误: {str(e)}")
        return None

def display_risk_analysis(df):
    """显示风险分析"""
    try:
        volatility = df['close'].pct_change().std() * 100
        st.metric("24小时波动率", f"{volatility:.2f}%")
    except Exception as e:
        st.error(f"计算波动率时发生错误: {str(e)}")

def display_trading_strategy(df):
    """显示交易策略"""
    try:
        if df['rsi'].iloc[-1] < 30:
            st.success("RSI显示超卖，可考虑逢低买入")
        elif df['rsi'].iloc[-1] > 70:
            st.warning("RSI显示超买，可考虑逢高卖出")
        else:
            st.info("当前处于中性区域，建议观望")
    except Exception as e:
        st.error(f"生成交易策略时发生错误: {str(e)}")

def analyze_meme_coins():
    """分析所有meme币数据"""
    meme_coins = ["DOGE", "SHIB", "PEPE", "FLOKI", "BONK"]
    results = []
    
    for coin in meme_coins:
        # 获取基础数据
        ticker_data = get_meme_coin_data(coin)
        if ticker_data is None:
            continue
            
        # 获取K线数据
        klines = get_klines_data(coin, "1h", 24)
        if klines is None:
            continue
            
        # 计算技术指标
        klines = calculate_technical_indicators(klines)
        
        # 收集分析结果
        result = {
            "coin": coin,
            "price": float(ticker_data['lastPrice']),
            "change": float(ticker_data['priceChangePercent']),
            "volume": float(ticker_data['quoteVolume']),
            "rsi": klines['rsi'].iloc[-1],
            "ema20": klines['ema20'].iloc[-1],
            "volatility": klines['close'].pct_change().std() * 100
        }
        results.append(result)
    
    return pd.DataFrame(results)

def generate_sentiment_chart(df):
    """生成市场情绪图表"""
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(df['coin'], df['change'], color=['green' if x >= 0 else 'red' for x in df['change']])
    ax.set_xlabel('币种')
    ax.set_ylabel('24小时涨跌幅 (%)')
    ax.set_title('Meme币市场情绪')
    return fig

def generate_trading_recommendations(df):
    """生成交易建议"""
    recommendations = []
    for _, row in df.iterrows():
        if row['rsi'] < 30:
            rec = f"{row['coin']}: 超卖区域，可考虑逢低买入"
        elif row['rsi'] > 70:
            rec = f"{row['coin']}: 超买区域，可考虑逢高卖出"
        else:
            rec = f"{row['coin']}: 中性区域，建议观望"
        recommendations.append(rec)
    return "\n".join(recommendations)

def generate_risk_warnings(df):
    """生成风险提示"""
    warnings = []
    for _, row in df.iterrows():
        if row['volatility'] > 10:
            warn = f"{row['coin']}: 高波动性 ({row['volatility']:.1f}%)，注意风险"
        else:
            warn = f"{row['coin']}: 正常波动性 ({row['volatility']:.1f}%)"
        warnings.append(warn)
    return "\n".join(warnings)

def meme_coin_analysis():
    """Meme币分析主函数"""
    # 获取所有meme币数据
    df = analyze_meme_coins()
    if df.empty:
        return None
        
    # 按交易量排序
    df = df.sort_values('volume', ascending=False)
    
    return {
        "top_memes": df[['coin', 'price', 'change', 'volume']],
        "sentiment_chart": generate_sentiment_chart(df),
        "trading_recommendations": generate_trading_recommendations(df),
        "risk_warnings": generate_risk_warnings(df)
    }
