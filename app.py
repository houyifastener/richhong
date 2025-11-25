import streamlit as st
from google import genai
from google.genai import types
import json
import pandas as pd
import plotly.graph_objects as go
import os

# --- 設定頁面資訊 ---
st.set_page_config(
    page_title="洪董帶我躺著數錢",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- CSS 樣式 hack (為了還原洪董的質感) ---
st.markdown("""
<style>
    /* 全站字體優化 */
    .stApp {
        font-family: "Noto Sans TC", sans-serif;
    }
    /* 標題樣式 */
    h1 {
        color: #1E3A8A;
        font-weight: 800 !important;
    }
    /* 指標卡片優化 */
    div[data-testid="stMetricValue"] {
        font-size: 24px;
        font-weight: bold;
    }
    /* 自訂背景 (首頁狀態) */
    .bed-bg {
        background-image: url("https://images.unsplash.com/photo-1540518614846-7eded433c457?q=80&w=2073&auto=format&fit=crop");
        background-size: cover;
        padding: 100px 20px;
        border-radius: 20px;
        text-align: center;
        color: white;
        margin-bottom: 30px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }
    .bed-title {
        font-size: 60px;
        font-weight: 900;
        text-shadow: 2px 2px 10px rgba(0,0,0,0.8);
        margin-bottom: 10px;
    }
    .bed-subtitle {
        font-size: 24px;
        font-weight: 400;
        text-shadow: 1px 1px 5px rgba(0,0,0,0.8);
        margin-bottom: 30px;
        color: #f3f4f6;
    }
</style>
""", unsafe_allow_html=True)

# --- 側邊欄設定 ---
with st.sidebar:
    st.title("💰 洪董操作台")
    
    # API Key 輸入區 (讓使用者不用搞環境變數也能跑)
    api_key = st.text_input("輸入 Gemini API Key", type="password", help="請輸入 AIza 開頭的金鑰")
    
    st.markdown("---")
    st.markdown("### 關於洪董")
    st.info("專為 50-500 萬散戶打造的 AI 投資助理，運用安全邊際法則，提供清晰的進出場建議。")
    st.markdown("---")
    st.caption("本工具僅供參考，投資請自負風險。")

# --- 核心功能：抓取資料 ---
def get_stock_analysis(symbol, key):
    client = genai.Client(api_key=key)
    
    # 定義 JSON Schema (沿用之前的邏輯)
    schema = {
        "type": "OBJECT",
        "properties": {
            "stockCode": {"type": "STRING"},
            "stockName": {"type": "STRING"},
            "overview": {
                "type": "OBJECT",
                "properties": {
                    "industry": {"type": "STRING"},
                    "productSummary": {"type": "STRING"}
                }
            },
            "metrics": {
                "type": "OBJECT",
                "properties": {
                    "currentPrice": {"type": "NUMBER"},
                    "pb": {"type": "NUMBER"},
                    "pe": {"type": "NUMBER"},
                    "peg": {"type": "NUMBER"},
                    "grossMarginTrend": {
                        "type": "ARRAY",
                        "items": {
                            "type": "OBJECT",
                            "properties": {
                                "quarter": {"type": "STRING"},
                                "value": {"type": "NUMBER"}
                            }
                        }
                    },
                    "contractLiabilities": {"type": "STRING"},
                    "liabilityRatio": {"type": "NUMBER"},
                    "yoy": {"type": "NUMBER"},
                    "yield": {"type": "NUMBER"},
                    "dividend": {"type": "NUMBER"}
                }
            },
            "technical": {
                "type": "OBJECT",
                "properties": {
                    "ma60": {"type": "NUMBER"},
                    "priceToMa60": {"type": "STRING", "enum": ["above", "below", "near"]},
                    "weekK": {"type": "NUMBER"},
                    "weekD": {"type": "NUMBER"},
                    "kTrend": {"type": "STRING"},
                    "dTrend": {"type": "STRING"}
                }
            },
            "analysis": {
                "type": "OBJECT",
                "properties": {
                    "pros": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "cons": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "valuationLevel": {"type": "STRING"},
                    "industryGrowth": {"type": "STRING"},
                    "industryGrowthScore": {"type": "NUMBER"}
                }
            },
            "strategy": {
                "type": "OBJECT",
                "properties": {
                    "isRecommended": {"type": "BOOLEAN"},
                    "mosLow": {"type": "NUMBER"},
                    "mosHigh": {"type": "NUMBER"},
                    "entryStrategy": {"type": "STRING"},
                    "exitStrategy": {"type": "STRING"},
                    "allocationAdvice": {"type": "STRING"}
                }
            }
        }
    }

    # 步驟 1: 搜尋即時資訊
    search_prompt = f"""
    請查詢台灣股票「{symbol}」的最新即時資訊，包含：
    1. 正確公司名稱與代號
    2. 即時股價、漲跌幅
    3. 最新本益比、殖利率、EPS
    4. 近期重大新聞
    5. 技術面季線位置
    """
    
    with st.spinner(f"🔍 洪董正在幫你打聽 {symbol} 的小道消息 (連網搜尋中)..."):
        search_response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=search_prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())]
            )
        )
        real_time_context = search_response.text

    # 步驟 2: 生成結構化報告
    analysis_prompt = f"""
    你現在是「洪董」，一位講話接地氣、幽默但專業穩健的台股分析師。
    請根據以下即時搜尋到的資訊，分析股票「{symbol}」。
    
    【即時資訊】：
    {real_time_context}
    
    請嚴格依照 JSON 格式輸出，重點：
    1. 確認代號名稱正確。
    2. 價格必須使用即時資訊中的價格。
    3. 針對 50-500 萬資金給出具體配置建議。
    4. 只有在安全邊際足夠時才推薦買進。
    """

    with st.spinner("📊 正在精算安全邊際與估值模型..."):
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=analysis_prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema
            )
        )
        return json.loads(response.text)

# --- UI 邏輯 ---

# 狀態管理
if 'analyzed' not in st.session_state:
    st.session_state.analyzed = False
if 'data' not in st.session_state:
    st.session_state.data = None

# 首頁 / 搜尋區
if not st.session_state.analyzed:
    st.markdown("""
    <div class="bed-bg">
        <div class="bed-title">洪董帶我躺著數錢</div>
        <div class="bed-subtitle">投資不用忙，這張床留給你睡，錢讓 AI 幫你數</div>
    </div>
    """, unsafe_allow_html=True)

query = st.text_input("輸入股票代號或名稱 (例如: 2330)", placeholder="請輸入股票代號...")

if st.button("開始分析", type="primary", use_container_width=True):
    if not api_key:
        st.error("請先在側邊欄輸入 API Key！")
    elif not query:
        st.warning("請輸入股票代號！")
    else:
        try:
            data = get_stock_analysis(query, api_key)
            st.session_state.data = data
            st.session_state.analyzed = True
            st.rerun()
        except Exception as e:
            st.error(f"分析失敗，請稍後再試。\n錯誤訊息: {str(e)}")

# 結果顯示區
if st.session_state.analyzed and st.session_state.data:
    data = st.session_state.data
    
    # 頂部導覽
    if st.button("← 搜尋其他股票"):
        st.session_state.analyzed = False
        st.session_state.data = None
        st.rerun()

    # 標題區
    col1, col2 = st.columns([2, 1])
    with col1:
        st.title(f"{data['stockCode']} {data['stockName']}")
        st.markdown(f"**產業類別**: {data['overview']['industry']}")
    with col2:
        st.metric("即時參考股價", f"NT$ {data['metrics']['currentPrice']}", 
                 delta=f"{data['metrics']['yoy']}% YoY (營收)", delta_color="normal")

    st.info(f"📢 **洪董短評**：{data['overview']['productSummary']}")

    st.divider()

    # 核心指標
    st.subheader("📈 核心財務指標")
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("本益比 (P/E)", data['metrics']['pe'], f"PEG: {data['metrics']['peg']}")
    m2.metric("股價淨值比 (P/B)", data['metrics']['pb'])
    m3.metric("殖利率", f"{data['metrics']['yield']}%", f"股利: {data['metrics']['dividend']}元")
    
    lia_ratio = data['metrics']['liabilityRatio']
    lia_color = "normal" if lia_ratio < 30 else "inverse" # 紅色代表高訂單
    m4.metric("合約負債佔比", f"{lia_ratio}%", data['metrics']['contractLiabilities'], delta_color=lia_color)

    # 圖表區
    c1, c2 = st.columns([2, 1])
    with c1:
        st.subheader("毛利率趨勢")
        chart_data = pd.DataFrame(data['metrics']['grossMarginTrend'])
        st.bar_chart(chart_data, x="quarter", y="value", color="#2563eb")
    
    with c2:
        st.subheader("技術面掃描")
        tech = data['technical']
        
        st.write(f"**季線 (60MA)**: {tech['ma60']}")
        if tech['priceToMa60'] == 'above':
            st.success("股價強勢 (季線上) 🚀")
        elif tech['priceToMa60'] == 'below':
            st.error("股價弱勢 (季線下) 🐻")
        else:
            st.warning("季線糾結 🥨")
            
        st.write("---")
        st.write(f"**周 KD**: K({tech['weekK']}) / D({tech['weekD']})")
        if tech['weekK'] > tech['weekD']:
            st.caption("呈現黃金交叉態勢")
        else:
            st.caption("呈現死亡交叉態勢")

    st.divider()

    # 利多利空
    p_col, c_col = st.columns(2)
    with p_col:
        st.subheader("🟢 股價利多")
        for p in data['analysis']['pros']:
            st.markdown(f"- {p}")
    with c_col:
        st.subheader("🔴 風險警示")
        for c in data['analysis']['cons']:
            st.markdown(f"- {c}")

    # 估值儀表板 (簡單版)
    st.subheader("⚖️ 產業估值位階")
    val_level = data['analysis']['valuationLevel']
    if val_level == 'cheap':
        st.success(f"目前評價：便宜 (低估) - {data['analysis']['industryGrowth']}")
    elif val_level == 'expensive':
        st.error(f"目前評價：昂貴 (高估) - {data['analysis']['industryGrowth']}")
    else:
        st.warning(f"目前評價：合理區間 - {data['analysis']['industryGrowth']}")
        
    st.progress(data['analysis']['industryGrowthScore'] / 10, text="產業成長潛力分數")

    st.divider()

    # 投資策略 (重點)
    st.subheader("💰 洪董錦囊：投資決策建議")
    
    strat = data['strategy']
    
    if strat['isRecommended']:
        with st.container(border=True):
            st.markdown("### ✅ 推薦佈局")
            c_strat1, c_strat2 = st.columns(2)
            
            c_strat1.metric("安全邊際買進區間", f"{strat['mosLow']} ~ {strat['mosHigh']} 元")
            
            with c_strat2:
                st.markdown("**資金配置 (50-500萬)**")
                st.write(strat['allocationAdvice'])
            
            st.markdown("---")
            st.markdown(f"**📥 進場策略**：{strat['entryStrategy']}")
            st.markdown(f"**📤 停利目標**：{strat['exitStrategy']}")
    else:
        st.container(border=True).warning(
            f"🚧 **目前建議觀望**\n\n根據安全邊際法則，目前股價尚未進入甜蜜點。\n建議等待回檔至 {strat['mosLow']} 元附近再重新評估。"
        )

    st.caption("免責聲明：本內容由 AI 生成，僅供研究參考，不代表投資建議。")