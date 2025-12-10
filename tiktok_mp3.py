import streamlit as st
import yt_dlp
import os
import google.generativeai as genai
import requests
import time
import shutil
import json
import whisper
import pandas as pd

# --- 1. CẤU HÌNH TRANG & ICON ---
TAB_ICON_URL = "https://cdn-icons-png.flaticon.com/512/4712/4712109.png" 
st.set_page_config(
    page_title="HuyK AI Studio", 
    page_icon=TAB_ICON_URL,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CẤU HÌNH LOGO ---
LOGO_URL = "https://cdn-icons-png.flaticon.com/512/4712/4712109.png" 

# ==========================================
# 🔐 HỆ THỐNG ĐĂNG NHẬP
# ==========================================
def check_login():
    if st.session_state.get('logged_in', False):
        return True

    # CSS riêng cho màn hình Login
    st.markdown(f"""
        <style>
            .login-container {{ text-align: center; margin-top: 50px; }}
            .login-logo {{ width: 80px; border-radius: 10px; margin-bottom: 10px; }}
            /* Fix lỗi Dark Mode cho màn login */
            .stTextInput input {{ background-color: white !important; color: #333 !important; }}
        </style>
        <div class="login-container">
            <img src="{LOGO_URL}" class="login-logo">
            <h2 style="color:#333;">HuyK AI Studio</h2>
            <p style="color:#666;">Vui lòng đăng nhập để sử dụng hệ thống</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        with st.form("login_form"):
            username = st.text_input("Tài khoản")
            password = st.text_input("Mật khẩu", type="password")
            submit = st.form_submit_button("Đăng nhập", use_container_width=True)
            
            if submit:
                users_db = st.secrets.get("users", {})
                if username in users_db and users_db[username] == password:
                    st.session_state.logged_in = True
                    st.session_state.current_user = username
                    st.success("✅ Đăng nhập thành công!")
                    time.sleep(0.5)
                    st.rerun()
                else:
                    st.error("❌ Sai tài khoản hoặc mật khẩu")
    return False

if not check_login():
    st.stop()

# ==========================================
# 🚀 PHẦN CODE CHÍNH
# ==========================================

# --- 3. ĐỊNH NGHĨA TUYẾN NỘI DUNG ---
PILLAR_DEFINITIONS = {
    "A1: Traffic - Mẹo & Tin tức": """
    - Mục tiêu: Thu hút người xem, viral.
    - Nội dung: Chia sẻ mẹo vặt, câu hỏi thú vị, soi đồ người nổi tiếng, tin tức ngành.
    - Phong cách: Nhanh, gọn, gây tò mò, ngôn ngữ đời thường.
    """,
    "A2: Kiến thức - Chuyên gia": """
    - Mục tiêu: Thể hiện sự hiểu biết, chuyên gia.
    - Nội dung: Lịch sử thương hiệu, thuật ngữ chuyên ngành, phân biệt chất liệu, dạy nghề.
    - Phong cách: Trầm ổn, sâu sắc, giải thích dễ hiểu, uy tín.
    """,
    "A3: Uy tín - Niềm tin": """
    - Mục tiêu: Xây dựng lòng tin.
    - Nội dung: Hoạt động cửa hàng, giải thưởng, giao hàng, kể chuyện bảo hành, tâm sự nghề.
    - Phong cách: Chân thành, kể chuyện (storytelling), tự hào.
    """,
    "A4: Chuyển đổi - Kể chuyện khách hàng": """
    - Mục tiêu: Bán hàng khéo léo (Soft Sell), chạm vào cảm xúc người xem. TUYỆT ĐỐI KHÔNG kêu gọi mua hàng thô thiển, KHÔNG báo giá trực tiếp.
    - Nội dung: Kể lại câu chuyện của khách hàng (ví dụ: Anh trai mua tặng em gái, chồng mua tặng vợ kỷ niệm ngày cưới...), tâm sự về ý nghĩa món quà, giải quyết nỗi đau/vấn đề của khách bằng sản phẩm.
    - Phong cách: Kể chuyện (Storytelling), thủ thỉ, tâm tình, sâu sắc, dẫn dắt tự nhiên để người xem tự cảm thấy muốn mua.
    """,
    "A5: Tổng hợp - Branding & Sales": """
    - Mục tiêu: Kết hợp kiến thức, uy tín và bán hàng.
    - Nội dung: Tổng hợp A1-A4. Chia sẻ kiến thức đi kèm uy tín và lồng ghép sản phẩm.
    - Phong cách: Linh hoạt, dẫn dắt khéo léo sang sản phẩm.
    """
}

# --- 4. KHỞI TẠO SESSION STATE ---
if 'processing_done' not in st.session_state: st.session_state.processing_done = False
if 'product_df' not in st.session_state: st.session_state.product_df = None
if 'user_gemini_key' not in st.session_state: st.session_state.user_gemini_key = ""
if 'user_minimax_key' not in st.session_state: st.session_state.user_minimax_key = ""
if 'user_voice_id' not in st.session_state: st.session_state.user_voice_id = "speech-01-hd"
if 'user_memory' not in st.session_state: st.session_state.user_memory = ""

if 'data' not in st.session_state: 
    st.session_state.data = {
        "videoTitle": "", "originalTranscript": "", 
        "rewrittenScript": "", "generatedAudio": None
    }

# --- 5. CSS GIAO DIỆN (ĐÃ TỐI ƯU MOBILE & DARK MODE) ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    /* 1. FORCE LIGHT MODE & FONT */
    * {{ font-family: 'Inter', sans-serif; }}
    
    /* Ép nền trắng/xám sáng cho toàn bộ app, bất chấp chế độ trình duyệt */
    .stApp {{ 
        background-color: #f8fafc !important; 
        color: #0f172a !important; 
    }}
    
    /* Fix chữ trong các input của Streamlit khi ở Dark Mode */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"] {{
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #e2e8f0 !important;
    }}
    .stMarkdown, .stText, h1, h2, h3, p {{
        color: #0f172a !important;
    }}

    header, footer {{ display: none !important; }}
    .block-container {{ padding-top: 1rem !important; max-width: 1400px !important; }}

    /* 2. NAVBAR RESPONSIVE */
    .nav-container {{
        background: white; 
        border-bottom: 1px solid #e2e8f0;
        padding: 0.8rem 1.5rem; 
        margin-bottom: 1.5rem;
        border-radius: 16px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        display: flex; 
        justify-content: space-between; 
        align-items: center;
        flex-wrap: wrap; /* Cho phép xuống dòng trên mobile */
        gap: 10px;
    }}
    .logo-section {{ display: flex; align-items: center; gap: 12px; }}
    .logo-img {{ width: 40px; height: 40px; object-fit: contain; border-radius: 6px; }}
    .brand-text {{ font-size: 18px; font-weight: 700; color: #0f172a; }}
    
    .status-group {{ display: flex; gap: 12px; align-items: center; }}
    
    /* 3. INPUT & BUTTON */
    div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {{
        border-radius: 12px; height: 45px;
    }}
    .stButton > button {{
        background-color: #2563eb !important; 
        color: white !important; 
        border-radius: 12px; 
        height: 50px; 
        font-weight: 600;
        width: 100%; 
        transition: all 0.2s; 
        border: none;
    }}
    .stButton > button:hover {{ background-color: #1d4ed8 !important; transform: translateY(-1px); }}

    /* 4. CARDS */
    .card {{ 
        background: white; 
        border-radius: 20px; 
        border: 1px solid #e2e8f0; 
        padding: 20px; 
        box-shadow: 0 4px 6px -2px rgba(0, 0, 0, 0.03); 
        height: 100%; 
    }}
    
    /* 5. MOBILE OPTIMIZATION (Media Queries) */
    @media (max-width: 640px) {{
        .nav-container {{
            padding: 0.8rem;
            flex-direction: column; /* Xếp dọc trên mobile */
            align-items: flex-start;
        }}
        .status-group {{
            width: 100%;
            justify-content: space-between;
            margin-top: 5px;
        }}
        .brand-text {{ font-size: 16px; }}
        
        /* Chỉnh lại padding của các container */
        .block-container {{ padding-left: 1rem !important; padding-right: 1rem !important; }}
    }}
</style>
""", unsafe_allow_html=True)

# --- 6. CẤU HÌNH & HÀM XỬ LÝ ---
CONFIG_FILE = "app_config.txt"
DEFAULT_PROMPT = """Nhiệm vụ: Viết lại nội dung video TikTok theo phong cách HuyK."""

def load_config():
    config = {"minimax_voice": "", "minimax_model": "speech-2.6-hd", "prompt": DEFAULT_PROMPT, "memory": ""}
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        if "key" not in k.lower(): config[k] = v.replace("\\n", "\n").strip()
        except: pass
    return config

def save_config(mm_voice, mm_model, prompt, memory):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        clean_prompt = prompt.replace("\n", "\\n")
        clean_memory = memory.replace("\n", "\\n")
        f.write(f"minimax_voice={mm_voice.strip()}\nminimax_model={mm_model.strip()}\nprompt={clean_prompt}\nmemory={clean_memory}\n")

config = load_config()

@st.dialog("⚙️ Cài đặt Cá nhân")
def open_settings():
    st.caption("🔑 Nhập API Key của riêng bạn để sử dụng.")
    gemini_input = st.text_input("Gemini API Key", value=st.session_state.user_gemini_key, type="password", help="Trình duyệt sẽ tự gợi ý lưu mật khẩu.")
    minimax_input = st.text_input("Minimax API Key", value=st.session_state.user_minimax_key, type="password")
    c1, c2 = st.columns(2)
    with c1: 
        model_options = ["speech-2.6-hd", "speech-01-turbo", "speech-01-hd", "speech-02"]
        current = config.get("minimax_model", "speech-2.6-hd")
        idx = model_options.index(current) if current in model_options else 0
        model_input = st.selectbox("Model", model_options, index=idx)
    with c2: voice_input = st.text_input("Voice ID", value=st.session_state.user_voice_id)
    st.divider()
    st.markdown("🧠 **Bộ nhớ Agent**")
    memory_input = st.text_area("Quy tắc ghi nhớ", value=st.session_state.user_memory, height=100)
    if st.button("Lưu cấu hình", type="primary"):
        st.session_state.user_gemini_key = gemini_input
        st.session_state.user_minimax_key = minimax_input
        st.session_state.user_voice_id = voice_input
        st.session_state.user_memory = memory_input
        save_config(voice_input, model_input, config["prompt"], memory_input)
        st.success("✅ Đã cập nhật!"); time.sleep(1); st.rerun()

def download_media(url):
    video_path = "downloaded_video.mp4"
    audio_path = "downloaded_audio.mp3"
    
    if os.path.exists(video_path): os.remove(video_path)
    if os.path.exists(audio_path): os.remove(audio_path)
    
    if shutil.which("ffmpeg") is None:
        if os.path.exists(r"C:\ffmpeg\bin"): os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

    ydl_opts = {
        'format': 'best',
        'outtmpl': 'downloaded_video.%(ext)s',
        'postprocessors': [{'key': 'FFmpegVideoConvertor', 'preferedformat': 'mp4'}],
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True, 'ignoreerrors': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.tiktok.com/'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info: raise Exception("Không lấy được thông tin video.")
            title = info.get('title', 'Video Content')
            os.system(f'ffmpeg -i "{video_path}" -vn -acodec libmp3lame -q:a 2 "{audio_path}" -y -loglevel quiet')
            return video_path, audio_path, title
    except Exception as e: raise Exception(f"Lỗi tải: {str(e)}")

@st.cache_resource
def load_whisper_model(): return whisper.load_model("base")

def transcribe_audio(file_path, model):
    result = model.transcribe(file_path)
    return result["text"]

def rewrite_with_gemini(original_text, pillar, product_info=""):
    api_key = st.session_state.user_gemini_key
    if not api_key: return "⚠️ CHƯA NHẬP KEY! Hãy vào Cài đặt để nhập."
    
    pillar_instr = PILLAR_DEFINITIONS.get(pillar, "")
    mem_instr = f"\n--- 🧠 BỘ NHỚ --- \n{st.session_state.user_memory}\n" if st.session_state.user_memory else ""
    
    prompt = f"""
    {config["prompt"]}
    {mem_instr}
    --- YÊU CẦU ---
    1. TUYẾN: {pillar}
    {pillar_instr}
    2. SẢN PHẨM:
    {product_info}
    3. QUY TẮC:
    - Nếu là A4: KHÔNG báo giá trực tiếp, tập trung kể chuyện.
    - Giọng văn: Chân thật, trầm, tâm sự.
    - Xưng hô: "HuyK", gọi khách là "anh chị".
    """
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=prompt) 
        return model.generate_content(f"Nội dung gốc:\n'{original_text}'\n\nViết lại kịch bản chi tiết.").text
    except Exception as e: return f"Lỗi Gemini: {e}"

def generate_minimax_audio(text):
    api_key = st.session_state.user_minimax_key
    if not api_key: return None, "Thiếu Key Minimax"
    if api_key.lower().startswith("bearer "): api_key = api_key[7:].strip()
    
    url = "https://api.minimax.io/v1/t2a_v2"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": config.get("minimax_model", "speech-2.6-hd"), "text": text, "stream": False,
        "voice_setting": {"voice_id": st.session_state.user_voice_id or "speech-01-hd", "speed": 1.0, "vol": 1.0, "pitch": 0},
        "audio_setting": {"sample_rate": 32000, "format": "mp3", "channel": 1}
    }
    try:
        res = requests.post(url, headers=headers, json=data)
        if res.status_code == 200:
            js = res.json()
            if js.get("base_resp", {}).get("status_code") != 0: return None, js["base_resp"]["status_msg"]
            if "data" in js and "audio" in js["data"]:
                path = f"huyk_voice_{int(time.time())}.mp3"
                with open(path, "wb") as f: f.write(bytes.fromhex(js["data"]["audio"]))
                return path, None
            return None, "Không có audio"
        return None, f"HTTP {res.status_code}"
    except Exception as e: return None, str(e)

# --- 7. UI CHÍNH ---
with st.sidebar:
    if 'logged_in' in st.session_state and st.session_state.logged_in:
        st.write(f"👤 Hi, **{st.session_state.current_user}**")
        if st.button("Đăng xuất", use_container_width=True):
            st.session_state.logged_in = False
            st.rerun()

st.markdown(f"""
<div class="nav-container">
    <div class="logo-section">
        <img src="{LOGO_URL}" class="logo-img">
        <span class="brand-text">HuyK AI Studio</span>
    </div>
    <div class="status-group">
        <div class="status-badge" style="background:#f1f5f9; padding:4px 10px; border-radius:20px; font-size:12px; border:1px solid #e2e8f0; color:{'#166534' if st.session_state.user_gemini_key else '#64748b'};"><div style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{'#22c55e' if st.session_state.user_gemini_key else '#cbd5e1'};margin-right:5px;"></div>Gemini</div>
        <div class="status-badge" style="background:#f1f5f9; padding:4px 10px; border-radius:20px; font-size:12px; border:1px solid #e2e8f0; color:{'#166534' if st.session_state.user_minimax_key else '#64748b'};"><div style="display:inline-block;width:6px;height:6px;border-radius:50%;background:{'#22c55e' if st.session_state.user_minimax_key else '#cbd5e1'};margin-right:5px;"></div>Minimax</div>
    </div>
</div>
""", unsafe_allow_html=True)

col_l, col_r = st.columns([3, 7], gap="large")

with col_l:
    st.subheader("🛠️ Chiến lược Content")
    pillar = st.selectbox("Hướng triển khai:", list(PILLAR_DEFINITIONS.keys()))
    with st.expander("ℹ️ Chi tiết"): st.info(PILLAR_DEFINITIONS[pillar])
    st.divider()
    st.markdown("**2. Kho Sản phẩm**")
    up_prod = st.file_uploader("Upload danh sách (Excel/CSV)", type=['xlsx', 'csv'], label_visibility="collapsed")
    prod_opts = []
    if up_prod:
        try:
            df = pd.read_csv(up_prod) if up_prod.name.endswith('.csv') else pd.read_excel(up_prod)
            df.columns = [c.strip().lower() for c in df.columns]
            c_code = next((c for c in df.columns if '
