import streamlit as st
import yt_dlp
import os
import google.generativeai as genai
import requests
import time
import shutil
import json

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="HuyK AI Creator", 
    page_icon="💎", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. SESSION STATE ---
if 'processing_done' not in st.session_state: st.session_state.processing_done = False
if 'data' not in st.session_state: 
    st.session_state.data = {
        "videoTitle": "", "originalTranscript": "", 
        "rewrittenScript": "", "generatedAudio": None
    }

# --- 3. CSS TINH TẾ ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; color: #0f172a; }
    header, footer { display: none !important; }
    .block-container { padding-top: 1rem !important; max-width: 1200px !important; }

    /* NAVBAR */
    .nav-container {
        display: flex; justify-content: space-between; align-items: center;
        padding-bottom: 1rem; border-bottom: 1px solid #e2e8f0; margin-bottom: 2rem;
    }
    .brand { display: flex; align-items: center; gap: 10px; }
    .logo-box {
        background: #0f172a; color: white; border-radius: 8px;
        width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-size: 18px;
    }
    .brand-text { font-size: 16px; font-weight: 700; color: #0f172a; }
    
    .status-badge {
        display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px;
        background: #f1f5f9; border-radius: 99px; font-size: 12px; font-weight: 500; color: #64748b;
    }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; background: #cbd5e1; }
    .status-dot.active { background: #22c55e; }

    /* HERO */
    .hero-title {
        font-size: 2.5rem; font-weight: 800; text-align: center; color: #0f172a;
        margin-bottom: 0.5rem; letter-spacing: -0.025em; line-height: 1.2;
    }
    .highlight { color: #2563eb; }
    .hero-desc {
        text-align: center; color: #64748b; font-size: 1rem; 
        max-width: 600px; margin: 0 auto 2rem auto; line-height: 1.5;
    }

    /* INPUTS & BUTTONS */
    div[data-testid="stTextInput"] input {
        border-radius: 10px; border: 1px solid #e2e8f0;
        padding: 10px 15px; font-size: 15px; color: #0f172a; background: white;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        height: 42px;
    }
    div[data-testid="stTextInput"] input:focus {
        border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.1);
    }

    .stButton > button {
        background-color: #2563eb; color: white; border: none;
        border-radius: 10px; font-weight: 600; font-size: 14px;
        height: 42px;
        box-shadow: 0 1px 2px 0 rgba(0, 0, 0, 0.05);
        width: 100%; transition: all 0.2s;
    }
    .stButton > button:hover {
        background-color: #1d4ed8; transform: translateY(-1px);
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2);
    }
    
    div[data-testid="stHorizontalBlock"] button[kind="secondary"] {
        background-color: transparent; color: #64748b; border: 1px solid #e2e8f0;
    }
    div[data-testid="stHorizontalBlock"] button[kind="secondary"]:hover {
        background-color: #f1f5f9; color: #0f172a;
    }

    /* TABS */
    .stTabs [data-baseweb="tab-list"] {
        justify-content: center; gap: 8px; margin-bottom: 2rem;
    }
    .stTabs [data-baseweb="tab"] {
        height: 36px; border-radius: 8px; padding: 0 16px; font-weight: 500; font-size: 13px;
        border: none; background-color: transparent; color: #64748b;
    }
    .stTabs [aria-selected="true"] {
        background-color: #eff6ff; color: #2563eb;
    }

    /* CARDS */
    .card {
        background: white; border-radius: 16px; border: 1px solid #e2e8f0;
        box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.1); overflow: hidden;
        height: 100%; display: flex; flex-direction: column;
    }
    .card-header {
        padding: 1rem 1.25rem; border-bottom: 1px solid #f8fafc;
        display: flex; align-items: center; gap: 10px; background: #fff;
    }
    .icon-box {
        padding: 6px; border-radius: 8px; display: flex; align-items: center; justify-content: center;
        width: 32px; height: 32px; font-size: 16px;
    }
    .card-title { font-weight: 600; color: #1e293b; font-size: 0.95rem; margin: 0; }
    
    .stTextArea textarea {
        border-radius: 12px; border: 1px solid #e2e8f0; background: #f8fafc;
        padding: 12px; font-size: 14px; line-height: 1.6; color: #334155;
    }
    .stTextArea textarea:focus { background: white; border-color: #93c5fd; box-shadow: 0 0 0 3px rgba(59,130,246,0.1); }

    /* Upload Box */
    div[data-testid="stFileUploader"] {
        padding: 1rem; border: 1px dashed #cbd5e1; border-radius: 12px;
        background-color: white;
    }
    section[data-testid="stFileUploaderDropzone"] { background-color: transparent; }
</style>
""", unsafe_allow_html=True)

# --- 4. CONFIG ---
CONFIG_FILE = "app_config.txt"
DEFAULT_PROMPT = """Nhiệm vụ: Viết lại nội dung theo phong cách "Giọng văn HuyK".
Quy tắc:
- Chân thật, trầm, chậm, như người thợ tâm sự.
- Câu ngắn, ngắt dòng tạo khoảng thở.
- Xưng hô: "HuyK", gọi khách là "anh chị".
- Tập trung vào quá trình làm nghề, công sức, sự tỉ mỉ."""

def load_config():
    config = {
        "gemini_key": "", "minimax_key": "", "minimax_group": "", 
        "minimax_voice": "", "minimax_model": "speech-2.6-hd", "prompt": DEFAULT_PROMPT
    }
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line:
                        k, v = line.strip().split("=", 1)
                        config[k] = v.replace("\\n", "\n").strip()
        except: pass
    return config

def save_config(gemini, mm_key, mm_group, mm_voice, mm_model, prompt):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        clean_prompt = prompt.replace("\n", "\\n")
        f.write(f"gemini_key={gemini.strip()}\nminimax_key={mm_key.strip()}\nminimax_group={mm_group.strip()}\nminimax_voice={mm_voice.strip()}\nminimax_model={mm_model.strip()}\nprompt={clean_prompt}\n")

config = load_config()

# --- 5. LOGIC CORE ---
def download_audio(url):
    output_filename = "downloaded_audio.mp3"
    if os.path.exists(output_filename): os.remove(output_filename)
    if not shutil.which("ffmpeg"): os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

    ydl_opts_mobile = {
        'format': 'bestaudio/best', 'outtmpl': 'downloaded_audio.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True,
        'http_headers': {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_8 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.2 Mobile/15E148 Safari/604.1'}
    }
    ydl_opts_chrome = ydl_opts_mobile.copy()
    ydl_opts_chrome['cookiesfrombrowser'] = ('chrome',)
    ydl_opts_chrome['http_headers']['User-Agent'] = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'

    try:
        print("Đang thử tải (Cách 1: Mobile UA)...")
        with yt_dlp.YoutubeDL(ydl_opts_mobile) as ydl:
            info = ydl.extract_info(url, download=True)
            return output_filename, info.get('title', 'TikTok Audio')
    except Exception as e:
        print(f"Cách 1 thất bại: {e}")
        try:
            print("Đang thử tải (Cách 2: Chrome Cookies)...")
            with yt_dlp.YoutubeDL(ydl_opts_chrome) as ydl:
                info = ydl.extract_info(url, download=True)
                return output_filename, info.get('title', 'TikTok Audio')
        except Exception as e2:
            raise Exception(f"Không thể tải video. TikTok chặn quá gắt! Lỗi: {e2}")

@st.cache_resource
def load_whisper_model(): return whisper.load_model("base")
import whisper 

def transcribe_audio(file_path, model):
    result = model.transcribe(file_path)
    return result["text"]

def rewrite_with_gemini(original_text):
    if not config["gemini_key"]: return "⚠️ Vui lòng nhập API Key trong cài đặt."
    try:
        genai.configure(api_key=config["gemini_key"])
        model = genai.GenerativeModel('gemini-2.5-flash') 
        response = model.generate_content(config["prompt"] + f"\n\n'{original_text}'")
        return response.text
    except Exception as e: return f"Lỗi Gemini: {e}"

# --- HÀM MINIMAX (ĐÃ SỬA LỖI GIẢI MÃ HEX) ---
def generate_minimax_audio(text):
    api_key = config["minimax_key"].strip()
    if api_key.lower().startswith("bearer "): api_key = api_key[7:].strip()
        
    voice_id = config["minimax_voice"].strip()
    model_id = config.get("minimax_model", "speech-2.6-hd").strip()

    if not api_key: return None, "Thiếu API Key"
    
    # URL CHUẨN MỚI
    url = "https://api.minimax.io/v1/t2a_v2"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    # Payload chuẩn có output_format="hex"
    data = {
        "model": model_id,
        "text": text,
        "stream": False,
        "output_format": "hex", # Quan trọng để API trả về đúng định dạng ta xử lý
        "voice_setting": {
            "voice_id": voice_id,
            "speed": 1.0,
            "vol": 1.0,
            "pitch": 0
        },
        "audio_setting": {
            "sample_rate": 32000,
            "format": "mp3",
            "channel": 1
        }
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            resp_json = response.json()
            
            # Check lỗi logic từ server
            if "base_resp" in resp_json and resp_json["base_resp"]["status_code"] != 0:
                return None, f"Lỗi Minimax: {resp_json['base_resp']['status_msg']} (Code {resp_json['base_resp']['status_code']})"
            
            # GIẢI MÃ HEX -> BINARY
            if "data" in resp_json and "audio" in resp_json["data"]:
                hex_data = resp_json["data"]["audio"]
                output_path = f"huyk_voice_{int(time.time())}.mp3"
                
                try:
                    # Đây là bước quan trọng nhất: Chuyển chuỗi Hex thành File MP3 thật
                    audio_bytes = bytes.fromhex(hex_data)
                    with open(output_path, "wb") as f:
                        f.write(audio_bytes)
                    return output_path, None
                except ValueError:
                    return None, "Lỗi giải mã dữ liệu âm thanh từ server."
            
            return None, "Không tìm thấy dữ liệu audio trong phản hồi."
        
        if response.status_code == 401: return None, "❌ 401: Sai API Key."
        
        return None, f"Lỗi HTTP {response.status_code}: {response.text}"
        
    except Exception as e: return None, f"Lỗi kết nối: {str(e)}"

# --- 6. SETTINGS MODAL ---
@st.dialog("⚙️ Cài đặt hệ thống")
def open_settings():
    st.markdown("**Google Gemini**")
    new_gemini = st.text_input("API Key", value=config["gemini_key"], type="password", key="gem", label_visibility="collapsed")
    
    st.markdown("**Minimax TTS**")
    new_mm_key = st.text_input("API Key", value=config["minimax_key"], type="password", key="mm", label_visibility="collapsed")
    
    c1, c2 = st.columns(2)
    with c1: 
        model_options = ["speech-2.6-hd", "speech-01-turbo", "speech-01-hd", "speech-02"]
        current = config.get("minimax_model", "speech-2.6-hd")
        if current not in model_options: current = "speech-2.6-hd"
        new_mm_model = st.selectbox("Model", model_options, index=model_options.index(current))
        
    with c2: new_mm_voice = st.text_input("Voice ID", value=config["minimax_voice"])
    
    new_mm_group = config["minimax_group"] 

    st.markdown("**Prompt Mẫu**")
    new_prompt = st.text_area("Prompt", value=config["prompt"], height=100, label_visibility="collapsed")
    
    if st.button("Lưu cài đặt", type="primary", use_container_width=True):
        save_config(new_gemini, new_mm_key, new_mm_group, new_mm_voice, new_mm_model, new_prompt)
        st.toast("✅ Đã lưu!", icon="💾")
        time.sleep(1)
        st.rerun()

# --- 7. GIAO DIỆN CHÍNH ---

# NAVBAR
col_brand, col_status, col_set = st.columns([2, 4, 1], vertical_alignment="center")
with col_brand:
    st.markdown("""
    <div class="brand">
        <div class="logo-box">💎</div>
        <span class="brand-text">HuyK AI</span>
    </div>
    """, unsafe_allow_html=True)

with col_status:
    st.markdown(f"""
    <div style="display:flex; justify-content:center; gap:10px;">
        <div class="status-badge"><div class="status-dot {'active' if config['gemini_key'] else ''}"></div> Gemini</div>
        <div class="status-badge"><div class="status-dot {'active' if config['minimax_key'] else ''}"></div> Voice</div>
    </div>
    """, unsafe_allow_html=True)

with col_set:
    c_null, c_btn = st.columns([1, 1])
    with c_btn:
        if st.button("⚙️", help="Cài đặt", use_container_width=True):
            open_settings()

st.markdown("<div style='border-bottom:1px solid #f1f5f9; margin-bottom:2rem;'></div>", unsafe_allow_html=True)

# MAIN CONTENT
if not st.session_state.processing_done:
    st.markdown("""
    <div style="text-align: center; margin-bottom: 2rem;">
        <h1 class="hero-title">Chuyển đổi nội dung thành <span style="color: #2563eb;">Viral Content</span></h1>
        <div style="display: flex; justify-content: center;">
            <p class="hero-desc" style="max-width: 700px;">
                Tự động phân tích Video/Âm thanh và tạo giọng đọc tự nhiên.
            </p>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    c_center = st.columns([1, 2, 1])[1]
    with c_center:
        tab1, tab2, tab3 = st.tabs(["📄 Văn bản", "☁️ File (Real)", "▶️ Link (Demo)"])
        
        with tab1:
            raw_input = st.text_area("Nhập văn bản...", height=150, label_visibility="collapsed", placeholder="Dán nội dung vào đây...")
            if st.button("✨ Viết lại Nội dung", type="primary", use_container_width=True):
                if raw_input:
                    with st.status("🚀 Đang xử lý...", expanded=True) as status:
                        rewrite = rewrite_with_gemini(raw_input)
                        st.session_state.data.update({"videoTitle": "Văn bản nhập tay", "originalTranscript": raw_input, "rewrittenScript": rewrite, "generatedAudio": None})
                        st.session_state.processing_done = True
                        status.update(label="Xong!", state="complete", expanded=False)
                        st.rerun()
                else: st.toast("Nhập nội dung!")

        with tab2:
            uploaded_file = st.file_uploader("Upload", type=['mp4', 'mp3', 'wav'], label_visibility="collapsed")
            if st.button("🚀 Phân tích File", type="primary", use_container_width=True):
                if uploaded_file:
                    with st.status("🚀 Đang xử lý...", expanded=True) as status:
                        try:
                            with open("temp.mp3", "wb") as f: f.write(uploaded_file.getbuffer())
                            st.write("🎧 Đang tách văn bản...")
                            w_model = load_whisper_model()
                            raw = transcribe_audio("temp.mp3", w_model)
                            st.write("💎 Đang viết kịch bản...")
                            rewrite = rewrite_with_gemini(raw)
                            shutil.copy("temp.mp3", "downloaded_audio.mp3")
                            st.session_state.data.update({"videoTitle": uploaded_file.name, "originalTranscript": raw, "rewrittenScript": rewrite, "generatedAudio": None})
                            st.session_state.processing_done = True
                            status.update(label="Xong!", state="complete", expanded=False)
                            st.rerun()
                        except Exception as e: st.error(f"Lỗi: {e}")
                else: st.toast("Chọn file!")

        with tab3:
            c_in, c_btn = st.columns([3.5, 1], gap="small", vertical_alignment="bottom")
            with c_in:
                url = st.text_input("Link", placeholder="🔗 Dán link video...", label_visibility="hidden")
            with c_btn:
                if st.button("Phân tích", type="primary", use_container_width=True):
                    if url:
                        with st.status("🚀 Đang xử lý...", expanded=True) as status:
                            try:
                                st.write("📥 Tải video...")
                                path, title = download_audio(url)
                                st.write("🎧 Tách chữ...")
                                w_model = load_whisper_model()
                                raw = transcribe_audio(path, w_model)
                                st.write("💎 Viết bài...")
                                rewrite = rewrite_with_gemini(raw)
                                st.session_state.data.update({"videoTitle": title, "originalTranscript": raw, "rewrittenScript": rewrite, "generatedAudio": None})
                                st.session_state.processing_done = True
                                status.update(label="Xong!", state="complete", expanded=False)
                                st.rerun()
                            except Exception as e: st.error(f"Lỗi: {e}")
                    else: st.toast("Nhập link đi!")

else:
    c_head, c_act = st.columns([6, 1], vertical_alignment="center")
    with c_head: st.caption(f"Kết quả: {st.session_state.data['videoTitle']}")
    with c_act: 
        if st.button("🔄 Tạo mới", use_container_width=True): 
            st.session_state.processing_done = False
            st.rerun()
            
    st.write("")

    col_left, col_right = st.columns(2, gap="large")

    with col_left:
        st.markdown("""
        <div class="card">
            <div class="card-header">
                <div class="icon-box" style="background:#eff6ff; color:#2563eb;">📄</div>
                <h3 class="card-title">Transcript Gốc</h3>
            </div>
        """, unsafe_allow_html=True)
        
        if os.path.exists("downloaded_audio.mp3"):
            st.audio("downloaded_audio.mp3", format="audio/mp3")
        
        st.text_area("Transcript", value=st.session_state.data["originalTranscript"], height=400, label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("""
        <div class="card">
            <div class="card-header">
                <div class="icon-box" style="background:#f5f3ff; color:#7c3aed;">✨</div>
                <h3 class="card-title">Kịch bản HuyK</h3>
            </div>
        """, unsafe_allow_html=True)
        
        new_script = st.text_area("Editor", value=st.session_state.data["rewrittenScript"], height=320, label_visibility="collapsed", key="editor_content")
        if new_script != st.session_state.data["rewrittenScript"]:
            st.session_state.data["rewrittenScript"] = new_script

        st.markdown("<div style='margin-top:16px;'></div>", unsafe_allow_html=True)

        if not st.session_state.data["generatedAudio"]:
            if st.button("🎙️ Tạo giọng đọc AI", type="primary", use_container_width=True):
                with st.spinner("Đang tạo..."):
                    path, err = generate_minimax_audio(st.session_state.data["rewrittenScript"])
                    if path:
                        st.session_state.data["generatedAudio"] = path
                        st.rerun()
                    else: st.error(err)
        else:
            st.audio(st.session_state.data["generatedAudio"], format="audio/mp3")
            
            c_dl, c_retry = st.columns([3, 1])
            with c_dl:
                with open(st.session_state.data["generatedAudio"], "rb") as f:
                    st.download_button("⬇️ Tải MP3", f, file_name="voice_ai.mp3", mime="audio/mpeg", use_container_width=True)
            with c_retry:
                if st.button("↺", help="Tạo lại"):
                    st.session_state.data["generatedAudio"] = None
                    st.rerun()
        
        st.markdown('</div></div>', unsafe_allow_html=True)