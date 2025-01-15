import streamlit as st
import pandas as pd
import numpy as np
import requests
from datetime import datetime
import time
from openai import OpenAI

# 设置页面标题和说明
st.title("加密货币多周期分析系统")
st.markdown("""
### 使用说明
- 输入交易对代码（例如：BTC、ETH、PEPE等）
- 系统将自动分析多个时间周期的市场状态
- 提供专业的趋势分析和预测
""")

# 内置 OpenAI API 配置
OPENAI_API_KEY = "sk-3wLvIb4VOjTtdthRMjysXgMvhERhyb4vTA2vvfLRAb9YHwvm"  # 替换为您的 API key
client = OpenAI(
    api_key=OPENAI_API_KEY,
    base_url="https://api.tu-zi.com/v1"
)

# Binance API 端点
BINANCE_API_URL = "https://api.binance.com/api/v3"

# 定义时间周期
TIMEFRAMES = {
    "5m": {"interval": "5m", "name": "5分钟"},
    "15m": {"interval": "15m", "name": "15分钟"},
    "1h": {"interval": "1h", "name": "1小时"},
    "4h": {"interval": "4h", "name": "4小时"},
    "1d": {"interval": "1d", "name": "日线"}
}


def check_symbol_exists(symbol):
    """检查交易对是否存在"""
    try:
        info_url = f"{BINANCE_API_URL}/exchangeInfo"
        response = requests.get(info_url)
        response.raise_for_status()
        symbols = [s['symbol'] for s in response.json()['symbols']]
        return f"{symbol}USDT" in symbols
    except Exception as e:
        st.error(f"检查交易对时发生错误: {str(e)}")
        return False


def get_klines_data(symbol, interval, limit=200):
    """获取K线数据"""
    try:
        klines_url = f"{BINANCE_API_URL}/klines"
        params = {
            "symbol": f"{symbol}USDT",
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


def calculate_indicators(df):
    """计算技术指标"""
    # 计算MA20
    df['ma20'] = df['close'].rolling(window=20).mean()

    # 计算BOLL指标
    df['boll_mid'] = df['close'].rolling(window=20).mean()
    df['boll_std'] = df['close'].rolling(window=20).std()
    df['boll_up'] = df['boll_mid'] + 2 * df['boll_std']
    df['boll_down'] = df['boll_mid'] - 2 * df['boll_std']

    # 计算MA20趋势
    df['ma20_trend'] = df['ma20'].diff().rolling(window=5).mean()

    return df


def analyze_trend(df):
    """分析趋势"""
    current_price = df['close'].iloc[-1]
    ma20_trend = "上升" if df['ma20_trend'].iloc[-1] > 0 else "下降"

    # BOLL带支撑阻力
    boll_up = df['boll_up'].iloc[-1]
    boll_mid = df['boll_mid'].iloc[-1]
    boll_down = df['boll_down'].iloc[-1]

    return {
        "current_price": current_price,
        "ma20_trend": ma20_trend,
        "support_resistance": {
            "strong_resistance": boll_up,
            "middle_line": boll_mid,
            "strong_support": boll_down
        }
    }


def get_ai_analysis(symbol, analysis_data):
    """获取 AI 分析结果"""
    try:
        # 准备多周期分析数据
        prompt = f"""
        作为一位专业的加密货币分析师，请基于以下{symbol}的多周期分析数据提供详细的市场报告：

        各周期趋势分析：
        {analysis_data}

        请提供以下分析（使用markdown格式）：

        ## 市场综述
        [在多周期分析框架下的整体判断]

        ## 趋势分析
        - 短期趋势（5分钟-15分钟）：
        - 中期趋势（1小时-4小时）：
        - 长期趋势（日线）：
        - 趋势协同性分析：

        ## 关键价位
        - 主要阻力位：
        - 主要支撑位：
        - 当前价格位置分析：

        ## 未来目标预测
        1. 24小时目标：
        2. 3天目标：
        3. 7天目标：

        ## 操作建议
        - 短线操作：
        - 中线布局：
        - 风险提示：

        请确保分析专业、客观，并注意不同时间框架的趋势关系。
        """

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[{"role": "user", "content": prompt}]
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI 分析生成失败: {str(e)}"


# 主界面
# 创建两列布局
col1, col2 = st.columns([2, 1])

with col1:
    # 用户输入代币代码
    symbol = st.text_input("输入代币代码（例如：BTC、ETH、PEPE）", value="BTC").upper()

with col2:
    # 分析按钮
    analyze_button = st.button("开始分析", type="primary")

# 添加分割线
st.markdown("---")

if analyze_button:
    # 检查代币是否存在
    if check_symbol_exists(symbol):
        with st.spinner(f'正在分析 {symbol} 的市场状态...'):
            all_timeframe_analysis = {}

            # 获取各个时间周期的数据并分析
            for tf, info in TIMEFRAMES.items():
                df = get_klines_data(symbol, info['interval'])
                if df is not None:
                    df = calculate_indicators(df)
                    analysis = analyze_trend(df)
                    all_timeframe_analysis[info['name']] = analysis

            # 显示当前价格
            current_price = all_timeframe_analysis['日线']['current_price']
            st.metric(
                label=f"{symbol}/USDT 当前价格",
                value=f"${current_price:,.8f}" if current_price < 0.1 else f"${current_price:,.2f}"
            )

            # 获取并显示 AI 分析
            st.subheader("多周期分析报告")
            analysis = get_ai_analysis(symbol, all_timeframe_analysis)
            st.markdown(analysis)

            # 添加时间戳
            st.caption(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    else:
        st.error(f"错误：{symbol}USDT 交易对在 Binance 上不存在，请检查代币代码是否正确。")

# 自动刷新选项移到侧边栏
with st.sidebar:
    st.subheader("设置")
    auto_refresh = st.checkbox("启用自动刷新")
    if auto_refresh:
        refresh_interval = st.slider("刷新间隔（秒）", 30, 300, 60)
        st.caption(f"每 {refresh_interval} 秒自动刷新一次")
        time.sleep(refresh_interval)
        st.experimental_rerun()

# 添加页脚
st.markdown("---")
st.caption("免责声明：本分析仅供参考，不构成投资建议。加密货币市场风险较大，请谨慎决策。")
