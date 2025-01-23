import streamlit as st
import pandas as pd
import numpy as np
import requests
import os
from datetime import datetime
import time
from meme_analysis import meme_coin_analysis

# 设置页面配置
st.set_page_config(
    page_title="币安期货持仓分析系统",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# API配置
DEEPSEEK_API_KEY = "sk-245071aa3a1a4adf92b6e09e83878868"
DEEPSEEK_API_URL = "https://api.deepseek.com/v1"
TWITTER_BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAAFGqyQEAAAAARilveo%2BreTsyT9KXFtCkPjWfuQo%3D1V9dwajTmeAclBftkIUn42b6BAPHyxNYirmTYL4RoNEnpqZbs3"

def deepseek_request(prompt):
    """发送请求到DeepSeek API"""
    headers = {
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": "deepseek-chat",
        "messages": [{"role": "user", "content": prompt}]
    }
    try:
        response = requests.post(
            f"{DEEPSEEK_API_URL}/chat/completions",
            headers=headers,
            json=data
        )
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        return f"API请求失败: {str(e)}"

# 设置页面标题和说明
st.title("加密货币多周期分析系统")
st.markdown("""
### 使用说明
- 输入交易对代码（例如：BTC、ETH、PEPE等）
- 系统将自动分析多个时间周期的市场状态
- 提供专业的趋势分析和预测
- 分析整体市场情绪
- 提供详细的交易计划
- 生成多种风格的分析总结推文
""")

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

def get_price_change(symbol, period):
    """获取指定时间段的价格变化"""
    try:
        # 计算时间戳
        end_time = int(time.time() * 1000)
        if period == '7d':
            start_time = end_time - 7 * 24 * 60 * 60 * 1000
        elif period == '30d':
            start_time = end_time - 30 * 24 * 60 * 60 * 1000
        else:
            return 0.0

        # 获取历史K线数据
        klines_url = f"{BINANCE_API_URL}/klines"
        params = {
            "symbol": f"{symbol}USDT",
            "interval": "1d",
            "startTime": start_time,
            "endTime": end_time,
            "limit": 2
        }
        response = requests.get(klines_url, params=params)
        response.raise_for_status()
        
        # 计算价格变化百分比
        data = response.json()
        if len(data) < 2:
            return 0.0
            
        old_price = float(data[0][4])  # 第0条的收盘价
        new_price = float(data[-1][4]) # 最后一条的收盘价
        return ((new_price - old_price) / old_price) * 100

    except Exception as e:
        st.error(f"获取价格变化时发生错误: {str(e)}")
        return 0.0

def get_market_sentiment():
    """获取市场情绪"""
    try:
        info_url = f"{BINANCE_API_URL}/ticker/24hr"
        response = requests.get(info_url)
        response.raise_for_status()
        data = response.json()
        usdt_pairs = [item for item in data if item['symbol'].endswith('USDT')]
        total_pairs = len(usdt_pairs)
        if total_pairs == 0:
            return "无法获取USDT交易对数据"

        up_pairs = [item for item in usdt_pairs if float(item['priceChangePercent']) > 0]
        up_percentage = (len(up_pairs) / total_pairs) * 100

        # 分类情绪
        if up_percentage >= 80:
            sentiment = "极端乐观"
        elif up_percentage >= 60:
            sentiment = "乐观"
        elif up_percentage >= 40:
            sentiment = "中性"
        elif up_percentage >= 20:
            sentiment = "悲观"
        else:
            sentiment = "极端悲观"

        return f"市场情绪：{sentiment}（上涨交易对占比 {up_percentage:.2f}%）"
    except Exception as e:
        return f"获取市场情绪时发生错误: {str(e)}"

# Twitter API调用计数器
twitter_api_count = 0
twitter_cache = {}  # 添加缓存字典
last_api_call_time = 0  # 记录上次API调用时间

def get_twitter_data(symbols):
    """获取Twitter数据，支持批量请求"""
    global twitter_api_count, last_api_call_time
    
    # 检查缓存
    cached_results = {}
    symbols_to_fetch = []
    
    for symbol in symbols:
        if symbol in twitter_cache:
            cached_data, timestamp = twitter_cache[symbol]
            # 如果缓存未过期（1小时），直接使用缓存数据
            if time.time() - timestamp < 3600:
                cached_results[symbol] = cached_data
                continue
        symbols_to_fetch.append(symbol)
    
    # 如果没有需要获取的新数据，直接返回缓存结果
    if not symbols_to_fetch:
        return cached_results
    
    # 检查API调用次数
    if twitter_api_count >= 90:  # 设置90作为警告阈值
        st.warning("警告：Twitter API调用次数接近限制（100次/月）")
        return None
    elif twitter_api_count >= 100:
        st.error("错误：已达到Twitter API调用限制（100次/月）")
        return None
        
    # 速率限制检查
    current_time = time.time()
    if current_time - last_api_call_time < 2:  # 2秒间隔
        time.sleep(2 - (current_time - last_api_call_time))
    
    # 重试机制
    max_retries = 3
    retry_delay = 1  # 初始重试延迟1秒
    
    for attempt in range(max_retries):
        try:
            # 批量获取推文统计数据
            if not symbols_to_fetch:
                return {}
            
            # 分批处理symbols，每批最多5个
            batch_size = 5
            results = {}
            for i in range(0, len(symbols_to_fetch), batch_size):
                batch = symbols_to_fetch[i:i + batch_size]
                query = " OR ".join([f"${s}" for s in batch])
                url = f"https://api.twitter.com/2/tweets/counts/recent?query={query}&granularity=day"
                headers = {
                    "Authorization": f"Bearer {TWITTER_BEARER_TOKEN}"
                }
                
                # 添加速率限制
                current_time = time.time()
                if current_time - last_api_call_time < 2:  # 2秒间隔
                    time.sleep(2 - (current_time - last_api_call_time))
                
                # 添加超时设置
                response = requests.get(url, headers=headers, timeout=(5, 10))
                response.raise_for_status()
                
                # 检查响应数据格式
                data = response.json()
                if 'data' not in data:
                    raise ValueError("Invalid Twitter API response format")
                    
                # 增加API调用计数（一次调用获取多个symbol）
                twitter_api_count += 1
                last_api_call_time = time.time()
                
                # 处理返回数据
                for symbol in symbols_to_fetch:
                    symbol_data = [item for item in data['data'] if symbol in item['query']]
                    if symbol_data:
                        total_tweets = sum(item['tweet_count'] for item in symbol_data)
                        activity_level = "高" if total_tweets > 10000 else "中" if total_tweets > 1000 else "低"
                        
                        results[symbol] = {
                            "total_tweets": total_tweets,
                            "unique_users": len(set(user for item in symbol_data for user in item['users'])),
                            "top_hashtags": sorted(
                                (hashtag for item in symbol_data for hashtag in item['hashtags']),
                                key=lambda x: x['count'],
                                reverse=True
                            )[:3],
                            "tweet_counts": [item['tweet_count'] for item in symbol_data],
                            "activity_level": activity_level
                        }
                        # 缓存结果
                        twitter_cache[symbol] = (results[symbol], time.time())
                
                # 合并缓存结果和新获取的结果
                results.update(cached_results)
                return results
                
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
                continue
            st.error(f"获取Twitter数据失败: {str(e)}")
            return None
        except ValueError as e:
            st.error(f"Twitter API响应格式错误: {str(e)}")
            return None
        except Exception as e:
            st.error(f"获取Twitter数据时发生意外错误: {str(e)}")
            return None

def generate_trading_plan(symbol):
    """生成交易计划"""
    prompt = f"""
    请为交易对 {symbol}/USDT 提供一个详细的顺应趋势的交易计划。包括但不限于入场点、止损点、目标价位和资金管理策略。
    """
    return deepseek_request(prompt)

def generate_tweet(symbol, analysis_summary, style):
    """生成推文内容"""
    style_prompts = {
        "女生": "以女生的语气",
        "交易员": "以交易员的专业语气",
        "分析师": "以金融分析师的专业语气",
        "媒体": "以媒体报道的客观语气"
    }

    style_prompt = style_prompts.get(style, "")

    prompt = f"""
    {style_prompt} 请根据以下分析总结，为交易对 {symbol}/USDT 撰写一条简洁且专业的推文，适合发布在推特上。推文应包括当前价格、市场情绪、主要趋势以及操作建议。限制在280个字符以内。

    分析总结：
    {analysis_summary}
    """
    tweet = deepseek_request(prompt).strip()
    # 确保推文不超过280字符
    if len(tweet) > 280:
        tweet = tweet[:277] + "..."
    return tweet

def get_ai_analysis(symbol, analysis_data, trading_plan):
    """获取 AI 分析结果"""
    # 准备多周期分析数据
    prompt = f"""
    作为一位专业的加密货币分析师，请基于以下{symbol}的多周期分析数据提供详细的市场报告：

    各周期趋势分析：
    {analysis_data}

    详细交易计划：
    {trading_plan}

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
    return deepseek_request(prompt)

# 初始化当前页面
if 'current_page' not in st.session_state:
    st.session_state['current_page'] = "single"

# 创建侧边栏
with st.sidebar:
    st.header("功能导航")
    
    # 单列布局
    st.markdown("<div style='text-align: center; margin-bottom: 10px;'>", unsafe_allow_html=True)
    if st.button(":chart_with_upwards_trend: 单币种分析", 
                type="primary" if st.session_state['current_page'] == "single" else "secondary", 
                use_container_width=True):
        st.session_state['current_page'] = "single"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div style='text-align: center; margin-bottom: 10px;'>", unsafe_allow_html=True)
    if st.button(":clown_face: meme币分析", 
                type="primary" if st.session_state['current_page'] == "meme" else "secondary",
                use_container_width=True):
        st.session_state['current_page'] = "meme"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div style='text-align: center; margin-bottom: 10px;'>", unsafe_allow_html=True)
    if st.button(":face_with_monocle: 市场情绪分析", 
                type="primary" if st.session_state['current_page'] == "sentiment" else "secondary",
                use_container_width=True):
        st.session_state['current_page'] = "sentiment"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    
    st.markdown("<div style='text-align: center; margin-bottom: 10px;'>", unsafe_allow_html=True)
    if st.button(":test_tube: 交易策略回测", 
                type="primary" if st.session_state['current_page'] == "backtest" else "secondary",
                use_container_width=True):
        st.session_state['current_page'] = "backtest"
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("设置")
    auto_refresh = st.checkbox("启用自动刷新")
    if auto_refresh:
        refresh_interval = st.slider("刷新间隔（秒）", 30, 300, 60)
        st.caption(f"每 {refresh_interval} 秒自动刷新一次")
        time.sleep(refresh_interval)
        st.rerun()

    st.markdown("---")
    st.subheader("注意事项")
    st.write("请确保您的分析仅供参考，不构成投资建议。加密货币市场风险较大，请谨慎决策。")

# 主界面
if st.session_state['current_page'] == "single":
    # 创建两列布局
    col1, col2 = st.columns([2, 1])

    with col1:
        # 用户输入代币代码
        symbol = st.text_input("输入代币代码（例如：BTC、ETH、PEPE）", value="BTC").upper()
        
        # 分析按钮
        analyze_button = st.button(":mag: 开始分析", type="primary")

    # 添加分割线
    st.markdown("---")

    if analyze_button:
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

            # 生成交易计划
            trading_plan = generate_trading_plan(symbol)

            # 获取并显示 AI 分析
            st.subheader("多周期分析报告")
            analysis = get_ai_analysis(symbol, all_timeframe_analysis, trading_plan)
            st.markdown(analysis)

            # 添加市场情绪
            market_sentiment = get_market_sentiment()
            st.markdown("---")
            st.subheader("整体市场情绪")
            st.write(market_sentiment)

            # 生成推文
            st.markdown("---")
            st.subheader("多风格推文建议")

            analysis_summary = f"{analysis}\n市场情绪：{market_sentiment}"

            # 定义所有风格
            styles = {
                "女生风格": "女生",
                "交易员风格": "交易员",
                "分析师风格": "分析师",
                "媒体风格": "媒体"
            }

            # 创建两列布局来显示推文
            col1, col2 = st.columns(2)

            # 生成并显示所有风格的推文
            for i, (style_name, style) in enumerate(styles.items()):
                tweet = generate_tweet(symbol, analysis_summary, style)
                # 在左列显示前两个风格
                if i < 2:
                    with col1:
                        st.subheader(f"📝 {style_name}")
                        st.text_area(
                            label=f"{style_name} 推文内容",
                            value=tweet,
                            height=150,
                            key=f"tweet_{style}",
                            label_visibility="collapsed"
                        )
                # 在右列显示后两个风格
                else:
                    with col2:
                        st.subheader(f"📝 {style_name}")
                        st.text_area(
                            label=f"{style_name} 推文内容",
                            value=tweet,
                            height=150,
                            key=f"tweet_{style}",
                            label_visibility="collapsed"
                        )

            # 添加时间戳
            st.caption(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

elif st.session_state['current_page'] == "meme":
    # 创建两列布局
    col1, col2 = st.columns([2, 1])

    with col1:
        # 用户输入meme币代码
        symbol = st.text_input("输入meme币代码（例如：DOGE、SHIB、PEPE）", value="DOGE").upper()
        
        # 分析按钮
        analyze_button = st.button(":mag: 开始分析", type="primary")

    # 添加分割线
    st.markdown("---")

    if analyze_button:
        with st.spinner(f'正在获取 {symbol} 的实时数据...'):
            try:
                # 获取币种基本信息
                info_url = f"{BINANCE_API_URL}/exchangeInfo"
                response = requests.get(info_url)
                response.raise_for_status()
                symbol_info = next((s for s in response.json()['symbols'] if s['symbol'] == f"{symbol}USDT"), None)
                
                if symbol_info:
                    # 获取币种详细信息
                    ticker_url = f"{BINANCE_API_URL}/ticker/24hr?symbol={symbol}USDT"
                    ticker_response = requests.get(ticker_url)
                    ticker_response.raise_for_status()
                    ticker_data = ticker_response.json()
                    
                    # 显示币种基本信息
                    st.markdown("<h4 style='font-size:18px'>币种基本信息</h4>", unsafe_allow_html=True)
                    col1_info, col2_info = st.columns(2)
                    
                    with col1_info:
                        st.metric("币种名称", symbol_info['baseAsset'])
                        st.metric("代码", symbol)
                        st.metric("发行时间", "2013-12-12" if symbol == "DOGE" else 
                                            "2020-08-01" if symbol == "SHIB" else
                                            "2023-04-17" if symbol == "PEPE" else "N/A")
                    
                    with col2_info:
                        st.metric("当前价格", f"${float(ticker_data['lastPrice']):,.8f}")
                        st.metric("市值", f"${float(ticker_data['lastPrice']) * float(ticker_data['volume']):,.2f}")

                    # 添加分割线
                    st.markdown("---")
                    
                    # 显示市场交易信息
                    st.markdown("<h4 style='font-size:18px'>市场交易信息</h4>", unsafe_allow_html=True)
                    col1_market, col2_market = st.columns(2)
                    
                    with col1_market:
                        # 计算价格变化
                        price_change = float(ticker_data['priceChange'])
                        price_change_percent = float(ticker_data['priceChangePercent'])
                        st.metric("24小时变化", 
                                f"{price_change_percent:.2f}% (${price_change:,.4f})",
                                delta=f"{price_change_percent:.2f}%")
                        st.metric("24小时交易量", f"${float(ticker_data['volume']):,.0f}")
                    
                    with col2_market:
                        # 获取7天和30天价格变化
                        seven_day_change = get_price_change(symbol, '7d')
                        thirty_day_change = get_price_change(symbol, '30d')
                        st.metric("7天变化", f"{seven_day_change:.2f}%")
                        st.metric("30天变化", f"{thirty_day_change:.2f}%")
            
            except Exception as e:
                st.error(f"获取币种信息时发生错误: {str(e)}")
                st.stop()

            # 添加分割线
            st.markdown("---")
            
            # 技术指标分析
            st.markdown("<h4 style='font-size:18px'>技术指标分析</h4>", unsafe_allow_html=True)
            col1_tech, col2_tech, col3_tech = st.columns(3)
            
            with col1_tech:
                st.subheader("支持阻力位")
                st.markdown("""
                - 短期支撑：$0.1234
                - 短期阻力：$0.1456
                - 中期支撑：$0.1123
                - 中期阻力：$0.1567
                - 长期支撑：$0.0987
                - 长期阻力：$0.1678
                """)
            
            with col2_tech:
                st.subheader("技术指标")
                st.markdown("""
                - RSI: 56.7 (中性)
                - MA20: $0.1345
                - MA50: $0.1289
                - 布林带上轨：$0.1456
                - 布林带中轨：$0.1345
                - 布林带下轨：$0.1234
                """)
            
            with col3_tech:
                st.subheader("链上数据")
                st.markdown("""
                - 持币地址：1,234,567
                - 活跃地址：123,456
                - 24小时交易：56,789笔
                - 7天交易趋势：↑12.3%
                """)

            # 添加分割线
            st.markdown("---")
            
            # 基本面分析
            st.markdown("<h4 style='font-size:18px'>基本面分析</h4>", unsafe_allow_html=True)
            
            with st.expander("项目背景"):
                st.markdown("""
                - **背后团队和创始人**：
                    - 创始人：Billy Markus（狗狗币）
                    - 开发团队：社区驱动
                - **项目目标和愿景**：
                    - 创建有趣、友好的加密货币
                    - 促进小额支付和打赏文化
                """)
            
            with st.expander("技术特点"):
                st.markdown("""
                - **共识机制**：
                    - 采用Scrypt算法的工作量证明（PoW）
                - **技术创新点**：
                    - 快速区块生成时间（1分钟）
                    - 低交易费用
                    - 无限供应机制
                """)
            
            with st.expander("生态系统"):
                st.markdown("""
                - **去中心化应用**：
                    - 支持简单智能合约
                    - 主要用于支付场景
                - **主要合作伙伴**：
                    - 特斯拉、达拉斯小牛队等
                    - 多个电商平台支持
                """)
            
            with st.expander("竞争分析"):
                st.markdown("""
                - **主要竞争对手**：
                    - 以太坊（ETH）
                    - 币安币（BNB）
                - **竞争优势**：
                    - 强大的社区支持
                    - 高品牌知名度
                    - 低门槛参与
                - **竞争劣势**：
                    - 技术更新较慢
                    - 缺乏复杂智能合约支持
                """)

            # 添加分割线
            st.markdown("---")
            
            # 市场情绪分析
            st.markdown("<h4 style='font-size:18px'>市场情绪分析</h4>", unsafe_allow_html=True)
            
            with st.expander("社交媒体活跃度"):
                col1_social, col2_social = st.columns(2)
                
                with col1_social:
                    # 使用新函数获取Twitter数据
                    twitter_data = get_twitter_data([symbol])
                    if twitter_data and symbol in twitter_data:
                        data = twitter_data[symbol]
                        st.metric("24小时推文数量", f"{data['total_tweets']:,}")
                        st.metric("社区活跃度", "高" if data['total_tweets'] > 10000 else "中")
                        st.markdown(f"""
                        - 热门话题：{data['top_hashtags'][0] if data['top_hashtags'] else '无'}
                        - 社区规模：{data['unique_users']:,}人
                        """)
                
                with col2_social:
                    # 推文数量趋势图
                    try:
                        st.line_chart({
                            '推文数量': tweet_data['data']['tweet_counts']
                        })
                    except:
                        st.warning("无法获取推文趋势数据")
            
            with st.expander("舆情分析"):
                col1_sentiment, col2_sentiment = st.columns(2)
                
                with col1_sentiment:
                    # 获取舆情数据
                    try:
                        # 使用Twitter API获取舆情数据
                        twitter_data = get_twitter_data([symbol])
                        if twitter_data and symbol in twitter_data:
                            data = twitter_data[symbol]
                            positive = len([t for t in data['tweet_counts'] if t > 0])
                            negative = len([t for t in data['tweet_counts'] if t < 0])
                            total = len(data['tweet_counts'])
                            
                            st.metric("正面舆情", f"{(positive/total)*100:.1f}%")
                            st.metric("负面舆情", f"{(negative/total)*100:.1f}%")
                            st.markdown(f"""
                            - 热门话题：{data['top_hashtags'][0] if data['top_hashtags'] else '无'}
                            - 社区活跃度：{data['unique_users']:,}人
                            """)
                    except Exception as e:
                        st.error(f"获取舆情数据失败: {str(e)}")
                
                with col2_sentiment:
                    # 舆情饼图
                    try:
                        st.plotly_chart({
                            'values': [sentiment_data['positive'], sentiment_data['negative'], sentiment_data['neutral']],
                            'labels': ['正面', '负面', '中性'],
                            'type': 'pie'
                        })
                    except:
                        st.warning("无法生成舆情图表")
            
            with st.expander("资金流向"):
                col1_flow, col2_flow = st.columns(2)
                
                with col1_flow:
                    st.metric("24小时资金流入", "$1,234,567")
                    st.metric("24小时资金流出", "$987,654")
                    st.markdown("""
                    - 大额交易：123笔
                    - 鲸鱼地址：45个
                    """)
                
                with col2_flow:
                    # 资金流向图
                    st.bar_chart({
                        '资金流入': [1234567],
                        '资金流出': [987654]
                    })

    # 添加分割线
    st.markdown("---")

    if analyze_button:
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

            # 生成交易计划
            trading_plan = generate_trading_plan(symbol)

            # 获取并显示 AI 分析
            st.subheader("多周期分析报告")
            analysis = get_ai_analysis(symbol, all_timeframe_analysis, trading_plan)
            st.markdown(analysis)

            # 添加市场情绪
            market_sentiment = get_market_sentiment()
            st.markdown("---")
            st.subheader("整体市场情绪")
            st.write(market_sentiment)

            # 生成推文
            st.markdown("---")
            st.subheader("多风格推文建议")

            analysis_summary = f"{analysis}\n市场情绪：{market_sentiment}"

            # 定义所有风格
            styles = {
                "女生风格": "女生",
                "交易员风格": "交易员",
                "分析师风格": "分析师",
                "媒体风格": "媒体"
            }

            # 创建两列布局来显示推文
            col1, col2 = st.columns(2)

            # 生成并显示所有风格的推文
            for i, (style_name, style) in enumerate(styles.items()):
                tweet = generate_tweet(symbol, analysis_summary, style)
                # 在左列显示前两个风格
                if i < 2:
                    with col1:
                        st.subheader(f"📝 {style_name}")
                        st.text_area(
                            label=f"{style_name} 推文内容",
                            value=tweet,
                            height=150,
                            key=f"tweet_{style}",
                            label_visibility="collapsed"
                        )
                # 在右列显示后两个风格
                else:
                    with col2:
                        st.subheader(f"📝 {style_name}")
                        st.text_area(
                            label=f"{style_name} 推文内容",
                            value=tweet,
                            height=150,
                            key=f"tweet_{style}",
                            label_visibility="collapsed"
                        )

            # 添加时间戳
            st.caption(f"分析时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

# 添加页脚
st.markdown("---")
st.caption("免责声明：本分析仅供参考，不构成投资建议。加密货币市场风险较大，请谨慎决策。")
