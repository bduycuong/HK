import streamlit as st
import yt_dlp
import os
import google.generativeai as genai
import requests
import time
import shutil
import json
import whisper

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

# --- 3. CSS TINH CHỈNH GIAO DIỆN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; color: #0f172a; }
    header, footer { display: none !important; }
    .block-container { padding-top: 1rem !important; max-width: 1000px !important; }

    /* Navbar */
    .nav-container {
        background: white; border-bottom: 1px solid #e2e8f0;
        padding: 0.8rem 1rem; margin-bottom: 2rem; border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        display: flex; justify-content: space-between; align-items: center;
    }
    .logo-section { display: flex; align-items: center; gap: 10px; }
    .logo-box {
        background: #0f172a; color: white; border-radius: 8px;
        width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-size: 18px;
    }
    .brand-text { font-size: 16px; font-weight: 700; color: #0f172a; }
    .status-badge {
        display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px;
        background: #f1f5f9; border-radius: 99px; font-size: 12px; font-weight: 500; color: #64748b;
        border: 1px solid #e2e8f0;
    }
    .status-dot { width: 6px; height: 6px; border-radius: 50%; background: #cbd5e1; }
    .status-dot.active { background: #22c55e; box-shadow: 0 0 6px rgba(34, 197, 94, 0.4); }

    /* Hero */
    .hero-title { font-size: 2.5rem; font-weight: 800; text-align: center; color: #0f172a; margin-bottom: 0.5rem; }
    .highlight { color: #2563eb; }
    .hero-desc { text-align: center; color: #64748b; font-size: 1rem; max-width: 600px; margin: 0 auto 2rem auto; }

    /* Input & Button */
    div[data-testid="stTextInput"] input {
        border: 1px solid #e2e8f0; background: white; padding: 0 16px;
        border-radius: 12px; font-size: 15px; color: #0f172a; height: 50px; 
        box-shadow: 0 2px 4px rgba(0,0,0,0.02);
    }
    div[data-testid="stTextInput"] input:focus { border-color: #3b82f6; box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1); }

    .stButton > button {
        background-color: #2563eb; color: white; border: none; border-radius: 12px;
        height: 50px; font-weight: 600; font-size: 15px; width: 100%;
        box-shadow: 0 4px 6px -1px rgba(37, 99, 235, 0.2); transition: all 0.2s;
    }
    .stButton > button:hover { background-color: #1d4ed8; transform: translateY(-1px); }
    
    /* Secondary Button Override */
    div[data-testid="stVerticalBlock"] > div > .stButton > button:not([kind="primary"]) {
        background: white !important; color: #64748b !important; 
        border: 1px solid #e2e8f0 !important; box-shadow: none !important;
        height: 40px; border-radius: 10px;
    }
    div[data-testid="stVerticalBlock"] > div > .stButton > button:not([kind="primary"]):hover {
        background-color: #f8fafc !important; color: #0f172a !important; border-color: #cbd5e1 !important;
    }

    /* Tabs & Cards */
    .stTabs [data-baseweb="tab-list"] { justify-content: center; gap: 8px; background-color: white; padding: 4px; border-radius: 12px; border: 1px solid #e2e8f0; width: fit-content; margin: 0 auto 2rem auto; }
    .stTabs [data-baseweb="tab"] { height: 36px; border-radius: 8px; padding: 0 20px; font-weight: 600; font-size: 14px; }
    .stTabs [aria-selected="true"] { background-color: #eff6ff; color: #2563eb; }

    .card { background: white; border-radius: 20px; border: 1px solid #e2e8f0; box-shadow: 0 4px 6px -2px rgba(0, 0, 0, 0.03); overflow: hidden; height: 100%; display: flex; flex-direction: column; }
    .card-header { padding: 1rem 1.5rem; border-bottom: 1px solid #f1f5f9; display: flex; align-items: center; gap: 10px; background: #fafafa; }
    .icon-box { width: 32px; height: 32px; border-radius: 8px; display: flex; align-items: center; justify-content: center; font-size: 16px; }
    .card-title { font-weight: 700; color: #334155; font-size: 1rem; margin: 0; }
    .stTextArea textarea { border-radius: 12px; border: 1px solid #e2e8f0; background: #fff; padding: 1rem; font-size: 15px; line-height: 1.6; color: #334155; }
    .audio-box { background: #1e293b; border-radius: 16px; padding: 1rem; color: white; margin-top: 1rem; }
    div[data-testid="stFileUploader"] { padding: 2rem; border: 2px dashed #cbd5e1; border-radius: 16px; background-color: #f8fafc; text-align: center; }
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
    
    # Check ffmpeg - Trên Cloud sẽ dùng packages hệ thống, dưới local check path
    if shutil.which("ffmpeg") is None:
        # Nếu chạy local mà chưa có ffmpeg trong path, thêm path tạm (nếu cần)
        if os.path.exists(r"C:\ffmpeg\bin"):
            os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'downloaded_audio.%(ext)s',
        'postprocessors': [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}],
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True, 'ignoreerrors': True,
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'referer': 'https://www.tiktok.com/'
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            if not info: raise Exception("Không lấy được thông tin video.")
            return output_filename, info.get('title', 'TikTok Audio')
    except Exception as e:
        print(f"Lỗi chi tiết: {e}")
        raise Exception("Không tải được video. Thử lại hoặc cập nhật yt-dlp.")

@st.cache_resource
def load_whisper_model(): return whisper.load_model("base")

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

def generate_minimax_audio(text):
    api_key = config["minimax_key"].strip()
    if api_key.lower().startswith("bearer "): api_key = api_key[7:].strip()
    voice_id = config["minimax_voice"].strip()
    model_id = config.get("minimax_model", "speech-2.6-hd").strip()

    if not api_key: return None, "Thiếu API Key"
    
    url = "https://api.minimax.io/v1/t2a_v2"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    data = {
        "model": model_id, "text": text, "stream": False,
        "voice_setting": {"voice_id": voice_id, "speed": 1.0, "vol": 1.0, "pitch": 0},
        "audio_setting": {"sample_rate": 32000, "format": "mp3", "channel": 1}
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        if response.status_code == 200:
            resp_json = response.json()
            if "base_resp" in resp_json and resp_json["base_resp"]["status_code"] != 0:
                return None, f"Lỗi: {resp_json['base_resp']['status_msg']}"
            if "data" in resp_json and "audio" in resp_json["data"]:
                hex_data = resp_json["data"]["audio"]
                output_path = f"huyk_voice_{int(time.time())}.mp3"
                with open(output_path, "wb") as f: f.write(bytes.fromhex(hex_data))
                return output_path, None
            return None, "Không có dữ liệu audio."
        if response.status_code == 401: return None, "❌ Sai API Key."
        return None, f"Lỗi HTTP {response.status_code}: {response.text}"
    except Exception as e: return None, f"Lỗi: {str(e)}"

# --- 6. SETTINGS ---
@st.dialog("⚙️ Cài đặt hệ thống")
def open_settings():
    st.caption("Cấu hình API Key để sử dụng tính năng.")
    new_gemini = st.text_input("Gemini API Key", value=config["gemini_key"], type="password")
    new_mm_key = st.text_input("Minimax API Key", value=config["minimax_key"], type="password")
    
    c1, c2 = st.columns(2)
    with c1: 
        model_options = ["speech-2.6-hd", "speech-01-turbo", "speech-01-hd", "speech-02"]
        current = config.get("minimax_model", "speech-2.6-hd")
        if current not in model_options: current = "speech-2.6-hd"
        new_mm_model = st.selectbox("Model", model_options, index=model_options.index(current))
    with c2: new_mm_voice = st.text_input("Voice ID", value=config["minimax_voice"])
    
    st.markdown("**Prompt Mẫu**")
    new_prompt = st.text_area("Prompt", value=config["prompt"], height=100, label_visibility="collapsed")
    
    st.write("")
    if st.button("Lưu cài đặt", type="primary", use_container_width=True):
        save_config(new_gemini, new_mm_key, config["minimax_group"], new_mm_voice, new_mm_model, new_prompt)
        st.toast("✅ Đã lưu!", icon="💾")
        time.sleep(1)
        st.rerun()

# --- 7. UI CHÍNH ---
st.markdown(f"""
<div class="nav-container">
    <div class="logo-section"><div class="logo-box">💎</div><span class="brand-text">HuyK AI Studio</span></div>
    <div style="display:flex; gap:12px; align-items:center;">
        <div class="status-badge"><div class="status-dot {'active' if config['gemini_key'] else ''}"></div> Gemini</div>
        <div class="status-badge"><div class="status-dot {'active' if config['minimax_key'] else ''}"></div> Minimax</div>
    </div>
</div>
""", unsafe_allow_html=True)

with st.container():
    col_spacer, col_set = st.columns([20, 1])
    with col_set:
        # SỬA LỖI Ở ĐÂY: Xóa kind="secondary"
        if st.button("⚙️", help="Cài đặt", use_container_width=True):
            open_settings()

if not st.session_state.processing_done:
    st.markdown("<div style='height: 20px'></div>", unsafe_allow_html=True)
    st.markdown("""
    <h1 class="hero-title">Biến Video thành <span class="highlight">Viral Content</span></h1>
    <p class="hero-desc">Công cụ tự động trích xuất nội dung, viết lại kịch bản theo phong cách riêng và tạo giọng đọc AI cảm xúc.</p>
    """, unsafe_allow_html=True)
    
    c_spacer_l, c_main, c_spacer_r = st.columns([1, 6, 1])
    with c_main:
        tab1, tab2, tab3 = st.tabs(["📄 Văn bản", "☁️ File Upload", "🔗 Link Video"])
        
        with tab1:
            raw_input = st.text_area("Nhập văn bản...", height=120, label_visibility="collapsed", placeholder="Dán nội dung thô vào đây...")
            st.write("")
            if st.button("✨ Phân tích văn bản", type="primary", use_container_width=True):
                if raw_input:
                    with st.status("🚀 Đang xử lý...", expanded=True) as status:
                        rewrite = rewrite_with_gemini(raw_input)
                        st.session_state.data.update({"videoTitle": "Văn bản nhập tay", "originalTranscript": raw_input, "rewrittenScript": rewrite, "generatedAudio": None})
                        st.session_state.processing_done = True
                        status.update(label="Hoàn tất!", state="complete", expanded=False)
                        st.rerun()
                else: st.toast("Vui lòng nhập nội dung!", icon="⚠️")

        with tab2:
            uploaded_file = st.file_uploader("Upload", type=['mp4', 'mp3', 'wav'], label_visibility="collapsed")
            st.write("")
            if st.button("🚀 Xử lý File", type="primary", use_container_width=True):
                if uploaded_file:
                    with st.status("🚀 Đang phân tích file...", expanded=True) as status:
                        try:
                            with open("temp.mp3", "wb") as f: f.write(uploaded_file.getbuffer())
                            st.write("🎧 Tách giọng nói (Whisper)...")
                            w_model = load_whisper_model()
                            raw = transcribe_audio("temp.mp3", w_model)
                            st.write("💎 Sáng tạo nội dung (Gemini)...")
                            rewrite = rewrite_with_gemini(raw)
                            shutil.copy("temp.mp3", "downloaded_audio.mp3")
                            st.session_state.data.update({"videoTitle": uploaded_file.name, "originalTranscript": raw, "rewrittenScript": rewrite, "generatedAudio": None})
                            st.session_state.processing_done = True
                            status.update(label="Hoàn tất!", state="complete", expanded=False)
                            st.rerun()
                        except Exception as e: st.error(f"Lỗi: {e}")
                else: st.toast("Vui lòng chọn file!", icon="⚠️")

        with tab3:
            c_in, c_btn = st.columns([4, 1], gap="small", vertical_alignment="bottom")
            with c_in:
                url = st.text_input("Link Video", placeholder="Dán link TikTok / Facebook / YouTube...", label_visibility="collapsed")
            with c_btn:
                if st.button("Phân tích", type="primary", use_container_width=True):
                    if url:
                        with st.status("🚀 Đang tải & Xử lý...", expanded=True) as status:
                            try:
                                st.write("📥 Tải video về server...")
                                path, title = download_audio(url)
                                st.write("🎧 Tách nội dung (Whisper)...")
                                w_model = load_whisper_model()
                                raw = transcribe_audio(path, w_model)
                                st.write("💎 Viết lại kịch bản (Gemini)...")
                                rewrite = rewrite_with_gemini(raw)
                                st.session_state.data.update({"videoTitle": title, "originalTranscript": raw, "rewrittenScript": rewrite, "generatedAudio": None})
                                st.session_state.processing_done = True
                                status.update(label="Hoàn tất!", state="complete", expanded=False)
                                st.rerun()
                            except Exception as e: st.error(f"Lỗi: {e}")
                    else: st.toast("Vui lòng nhập link video!", icon="⚠️")

else:
    col_back, col_title, col_new = st.columns([1, 10, 2], vertical_alignment="center")
    with col_title:
        st.markdown(f'<h3 style="margin:0; font-size:1.2rem;">📂 Kết quả: <span style="color:#2563eb">{st.session_state.data["videoTitle"]}</span></h3>', unsafe_allow_html=True)
    with col_new:
        if st.button("🔄 Tạo mới", use_container_width=True): 
            st.session_state.processing_done = False
            st.rerun()
    st.divider()

    col_left, col_right = st.columns(2, gap="medium")
    with col_left:
        st.markdown("""<div class="card"><div class="card-header"><div class="icon-box" style="background:#eff6ff; color:#2563eb;">📄</div><h3 class="card-title">Transcript Gốc</h3></div>""", unsafe_allow_html=True)
        if os.path.exists("downloaded_audio.mp3"): st.audio("downloaded_audio.mp3", format="audio/mp3")
        st.text_area("Nội dung gốc", value=st.session_state.data["originalTranscript"], height=400, label_visibility="collapsed")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_right:
        st.markdown("""<div class="card"><div class="card-header"><div class="icon-box" style="background:#f5f3ff; color:#7c3aed;">✨</div><h3 class="card-title">Kịch bản HuyK</h3></div>""", unsafe_allow_html=True)
        new_script = st.text_area("Editor", value=st.session_state.data["rewrittenScript"], height=320, label_visibility="collapsed", key="editor_content")
        if new_script != st.session_state.data["rewrittenScript"]: st.session_state.data["rewrittenScript"] = new_script

        st.markdown('<div class="audio-box">', unsafe_allow_html=True)
        if not st.session_state.data["generatedAudio"]:
            c_info, c_act = st.columns([2, 1.5], vertical_alignment="center")
            with c_info: st.markdown('<span style="font-size:14px; opacity:0.8">Chưa có giọng đọc</span>', unsafe_allow_html=True)
            with c_act:
                if st.button("🎙️ Tạo giọng đọc", type="primary", use_container_width=True):
                    with st.spinner("Đang khởi tạo AI Voice..."):
                        path, err = generate_minimax_audio(st.session_state.data["rewrittenScript"])
                        if path: st.session_state.data["generatedAudio"] = path; st.rerun()
                        else: st.error(err)
        else:
            st.markdown('<div style="margin-bottom:10px; font-weight:600; font-size:14px; color:#4ade80;">✅ Voice AI đã sẵn sàng</div>', unsafe_allow_html=True)
            st.audio(st.session_state.data["generatedAudio"], format="audio/mp3")
            c_dl, c_re = st.columns([2, 1])
            with c_dl:
                with open(st.session_state.data["generatedAudio"], "rb") as f:
                    st.download_button("⬇️ Tải về máy", f, file_name="voice_ai.mp3", mime="audio/mpeg", use_container_width=True)
            with c_re:
                if st.button("↺ Tạo lại", use_container_width=True):
                    st.session_state.data["generatedAudio"] = None
                    st.rerun()
        st.markdown('</div></div>', unsafe_allow_html=True)