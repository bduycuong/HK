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

# --- 1. CẤU HÌNH TRANG ---
st.set_page_config(
    page_title="HuyK AI Creator", 
    page_icon="💎", 
    layout="wide",
    initial_sidebar_state="collapsed" # Ẩn sidebar mặc định vì đã đưa ra ngoài
)

# --- 2. ĐỊNH NGHĨA TUYẾN NỘI DUNG ---
PILLAR_DEFINITIONS = {
    "A1: Traffic - Mẹo & Tin tức": """
    - Mục tiêu: Thu hút người xem, viral.
    - Nội dung: Chia sẻ mẹo vặt (đánh sáng, cài khuy), câu hỏi thú vị (vàng ăn được không?), soi đồ người nổi tiếng, tin tức ngành kim hoàn.
    - Phong cách: Nhanh, gọn, gây tò mò, ngôn ngữ đời thường.
    """,
    "A2: Kiến thức - Chuyên gia": """
    - Mục tiêu: Thể hiện sự hiểu biết, chuyên gia.
    - Nội dung: Lịch sử thương hiệu, thuật ngữ (Phật giáo mật tông, Hư Không Tạng...), phân biệt chất liệu (vàng/bạc/bạch kim), dạy nghề kim hoàn.
    - Phong cách: Trầm ổn, sâu sắc, giải thích dễ hiểu, uy tín.
    """,
    "A3: Uy tín - Niềm tin": """
    - Mục tiêu: Xây dựng lòng tin.
    - Nội dung: Hoạt động cửa hàng, giải thưởng, từ thiện, giao hàng, kể chuyện bảo hành/sửa chữa, đọc comment tư vấn, tâm sự nghề.
    - Phong cách: Chân thành, kể chuyện (storytelling), tự hào.
    """,
    "A4: Chuyển đổi - Bán hàng": """
    - Mục tiêu: Thúc đẩy mua hàng, chốt đơn.
    - Nội dung: Top list (nhẫn nam dưới 10tr, bán chạy...), tâm sự cảm xúc (buồn/vui cùng khách), trả lời comment bán hàng, tư vấn theo tuổi/nghề nghiệp, gợi ý ngân sách (500k mua gì, combo 40tr), so sánh giá trị.
    - Phong cách: Kêu gọi hành động (Call to action), nhấn mạnh lợi ích, khơi gợi nhu cầu.
    """,
    "A5: Tổng hợp - Branding & Sales": """
    - Mục tiêu: Kết hợp kiến thức, uy tín và bán hàng.
    - Nội dung: Tổng hợp các yếu tố từ A1-A4. Chia sẻ kiến thức đi kèm sự uy tín và khéo léo lồng ghép sản phẩm vào cuối.
    - Phong cách: Linh hoạt, dẫn dắt khéo léo từ thông tin sang sản phẩm.
    """
}

# --- 3. SESSION STATE ---
if 'processing_done' not in st.session_state: st.session_state.processing_done = False
if 'product_df' not in st.session_state: st.session_state.product_df = None
if 'data' not in st.session_state: 
    st.session_state.data = {
        "videoTitle": "", "originalTranscript": "", 
        "rewrittenScript": "", "generatedAudio": None
    }

# --- 4. CSS TINH CHỈNH GIAO DIỆN ---
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .stApp { background-color: #f8fafc; color: #0f172a; }
    header, footer { display: none !important; }
    .block-container { padding-top: 1rem !important; max-width: 1400px !important; }

    /* Navbar */
    .nav-container {
        background: white; border-bottom: 1px solid #e2e8f0;
        padding: 0.8rem 1rem; margin-bottom: 2rem; border-radius: 16px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
        display: flex; justify-content: space-between; align-items: center;
    }
    .logo-box { background: #0f172a; color: white; border-radius: 8px; width: 32px; height: 32px; display: flex; align-items: center; justify-content: center; font-size: 18px; }
    .brand-text { font-size: 16px; font-weight: 700; color: #0f172a; }
    
    /* Input & Button */
    div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {
        border-radius: 12px; border: 1px solid #e2e8f0; height: 45px;
    }
    .stButton > button {
        background-color: #2563eb; color: white; border-radius: 12px; height: 50px; font-weight: 600;
        width: 100%; transition: all 0.2s;
    }
    .stButton > button:hover { background-color: #1d4ed8; transform: translateY(-1px); }

    /* Cards */
    .card { background: white; border-radius: 20px; border: 1px solid #e2e8f0; padding: 20px; box-shadow: 0 4px 6px -2px rgba(0, 0, 0, 0.03); height: 100%; }
    .card-title { font-weight: 700; color: #334155; font-size: 1rem; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;}
    
    /* Strategy Box Style */
    .strategy-box {
        background-color: #fff;
        border: 1px solid #cbd5e1;
        border-radius: 16px;
        padding: 1.5rem;
        height: 100%;
    }
</style>
""", unsafe_allow_html=True)

# --- 5. CONFIG & FUNCTIONS ---
CONFIG_FILE = "app_config.txt"
DEFAULT_PROMPT = """Nhiệm vụ: Viết lại nội dung video TikTok theo phong cách HuyK."""

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

# --- KHAI BÁO HÀM SETTINGS SỚM ĐỂ FIX LỖI ---
@st.dialog("⚙️ Cài đặt hệ thống")
def open_settings():
    st.caption("Cấu hình API Key để sử dụng tính năng.")
    new_gemini = st.text_input("Gemini API Key", value=config["gemini_key"], type="password")
    new_mm_key = st.text_input("Minimax API Key", value=config["minimax_key"], type="password")
    c1, c2 = st.columns(2)
    with c1: 
        model_options = ["speech-2.6-hd", "speech-01-turbo", "speech-01-hd", "speech-02"]
        current = config.get("minimax_model", "speech-2.6-hd")
        new_mm_model = st.selectbox("Model", model_options, index=model_options.index(current) if current in model_options else 0)
    with c2: new_mm_voice = st.text_input("Voice ID", value=config["minimax_voice"])
    st.markdown("**Prompt Gốc (Base)**")
    new_prompt = st.text_area("Prompt", value=config["prompt"], height=100)
    if st.button("Lưu cài đặt", type="primary"):
        save_config(new_gemini, new_mm_key, config["minimax_group"], new_mm_voice, new_mm_model, new_prompt)
        st.rerun()

def download_audio(url):
    output_filename = "downloaded_audio.mp3"
    if os.path.exists(output_filename): os.remove(output_filename)
    if shutil.which("ffmpeg") is None:
        if os.path.exists(r"C:\ffmpeg\bin"): os.environ["PATH"] += os.pathsep + r"C:\ffmpeg\bin"

    ydl_opts = {
        'format': 'bestaudio/best', 'outtmpl': 'downloaded_audio.%(ext)s',
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
    except Exception as e: raise Exception(f"Lỗi tải video: {str(e)}")

@st.cache_resource
def load_whisper_model(): return whisper.load_model("base")

def transcribe_audio(file_path, model):
    result = model.transcribe(file_path)
    return result["text"]

def rewrite_with_gemini(original_text, pillar, product_info=""):
    if not config["gemini_key"]: return "⚠️ Vui lòng nhập API Key trong cài đặt."
    
    pillar_instruction = PILLAR_DEFINITIONS.get(pillar, "")
    
    system_instruction = f"""
    {config["prompt"]}
    
    --- YÊU CẦU CỤ THỂ CHO BÀI NÀY ---
    1. TUYẾN NỘI DUNG: {pillar}
    {pillar_instruction}
    
    2. SẢN PHẨM CẦN LỒNG GHÉP (Nếu có):
    {product_info if product_info else "Không có sản phẩm cụ thể, tập trung vào nội dung chính."}
    
    3. QUY TẮC VIẾT:
    - Nếu là tuyến A4, A5: Bắt buộc phải nhắc đến thông tin sản phẩm ở trên một cách khéo léo, tự nhiên.
    - Giọng văn: Chân thật, trầm, tâm sự (style HuyK).
    - Xưng hô: "HuyK", gọi khách là "anh chị".
    - Độ dài: Phù hợp kịch bản video ngắn (khoảng 40s - 90s).
    """

    try:
        genai.configure(api_key=config["gemini_key"])
        model = genai.GenerativeModel('gemini-2.5-flash', system_instruction=system_instruction) 
        response = model.generate_content(f"Đây là nội dung gốc/ý tưởng thô:\n'{original_text}'\n\nHãy viết lại kịch bản chi tiết.")
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
        return None, f"Lỗi HTTP {response.status_code}"
    except Exception as e: return None, f"Lỗi: {str(e)}"

# --- 7. UI CHÍNH (MAIN) ---
st.markdown(f"""
<div class="nav-container">
    <div style="display:flex;align-items:center;gap:10px"><div class="logo-box">💎</div><span class="brand-text">HuyK AI Studio</span></div>
    <div style="display:flex; gap:12px; align-items:center;">
        <div class="status-badge" style="{'background:#dcfce7; color:#166534' if config['gemini_key'] else ''}">Gemini</div>
        <div class="status-badge" style="{'background:#dcfce7; color:#166534' if config['minimax_key'] else ''}">Minimax</div>
    </div>
</div>
""", unsafe_allow_html=True)

# === LAYOUT 2 CỘT: TRÁI (CHIẾN LƯỢC) - PHẢI (MAIN APP) ===
col_strategy, col_main = st.columns([3.5, 6.5], gap="large")

# --- CỘT TRÁI: CHIẾN LƯỢC (LUÔN HIỆN) ---
with col_strategy:
    st.markdown('<div class="strategy-box">', unsafe_allow_html=True)
    st.subheader("🛠️ Chiến lược Content")
    
    # 1. Chọn tuyến nội dung
    st.markdown("**1. Tuyến nội dung**")
    selected_pillar = st.selectbox(
        "Hướng triển khai:",
        list(PILLAR_DEFINITIONS.keys()),
        index=0,
        label_visibility="collapsed"
    )
    with st.expander("ℹ️ Chi tiết tuyến này", expanded=True):
        st.info(PILLAR_DEFINITIONS[selected_pillar])
        
    st.divider()
    
    # 2. Kho sản phẩm
    st.markdown("**2. Kho Sản phẩm**")
    uploaded_products = st.file_uploader("Upload danh sách (Excel/CSV)", type=['xlsx', 'csv'], label_visibility="collapsed")
    
    product_options = []
    if uploaded_products:
        try:
            if uploaded_products.name.endswith('.csv'):
                df = pd.read_csv(uploaded_products)
            else:
                df = pd.read_excel(uploaded_products)
            
            # Chuẩn hóa tên cột
            df.columns = [c.strip().lower() for c in df.columns]
            # Map cột
            col_code = next((c for c in df.columns if 'mã' in c or 'code' in c), df.columns[0])
            col_name = next((c for c in df.columns if 'tên' in c or 'name' in c), df.columns[1])
            col_desc = next((c for c in df.columns if 'mô tả' in c or 'desc' in c), df.columns[-1])
            
            st.session_state.product_df = df[[col_code, col_name, col_desc]].copy()
            st.success(f"✅ Đã tải {len(df)} sản phẩm")
            
            st.session_state.product_df['display'] = st.session_state.product_df[col_code].astype(str) + " - " + st.session_state.product_df[col_name].astype(str)
            product_options = st.session_state.product_df['display'].tolist()
        except Exception as e:
            st.error(f"Lỗi đọc file: {e}")

    selected_products_display = st.multiselect("Chọn sản phẩm lồng ghép:", product_options)
    
    selected_product_info_str = ""
    if selected_products_display and st.session_state.product_df is not None:
        selected_rows = st.session_state.product_df[st.session_state.product_df['display'].isin(selected_products_display)]
        info_list = []
        for index, row in selected_rows.iterrows():
            cols = selected_rows.columns
            info = f"- MÃ: {row[cols[0]]}\n  TÊN: {row[cols[1]]}\n  MÔ TẢ CHI TIẾT: {row[cols[2]]}"
            info_list.append(info)
        selected_product_info_str = "\n".join(info_list)
        
    st.divider()
    if st.button("⚙️ Cài đặt API Key", use_container_width=True):
        open_settings()
    st.markdown('</div>', unsafe_allow_html=True)


# --- CỘT PHẢI: XỬ LÝ CHÍNH ---
with col_main:
    if not st.session_state.processing_done:
        st.markdown("""
        <h1 class="hero-title">Biến Video thành <span class="highlight">Viral Content</span></h1>
        <p class="hero-desc">Công cụ hỗ trợ viết lại kịch bản, lồng ghép sản phẩm và tạo giọng đọc HuyK.</p>
        """, unsafe_allow_html=True)
        
        if "A4" in selected_pillar or "A5" in selected_pillar:
            if not selected_product_info_str:
                st.warning("⚠️ Tuyến này cần bán hàng. Hãy chọn sản phẩm ở cột bên trái.")

        tab1, tab2, tab3 = st.tabs(["📄 Ý tưởng / Văn bản", "☁️ File Upload", "🔗 Link Video"])
        
        with tab1:
            raw_input = st.text_area("Nhập ý tưởng thô...", height=150, placeholder="Ví dụ: Khách hỏi 500k mua được nhẫn bạc nào tặng người yêu...")
            if st.button("✨ Phân tích & Viết bài", type="primary"):
                if raw_input:
                    with st.status("🚀 Đang xử lý...", expanded=True):
                        rewrite = rewrite_with_gemini(raw_input, selected_pillar, selected_product_info_str)
                        st.session_state.data.update({"videoTitle": "Văn bản nhập tay", "originalTranscript": raw_input, "rewrittenScript": rewrite, "generatedAudio": None})
                        st.session_state.processing_done = True
                        st.rerun()
                else: st.toast("Nhập nội dung đi bạn ơi!", icon="⚠️")

        with tab2:
            uploaded_file = st.file_uploader("Upload Video/Audio", type=['mp4', 'mp3', 'wav'])
            if st.button("🚀 Xử lý File", type="primary", key="btn_file"):
                if uploaded_file:
                    with st.status("🚀 Đang xử lý...", expanded=True):
                        try:
                            with open("temp.mp3", "wb") as f: f.write(uploaded_file.getbuffer())
                            st.write("🎧 Đang tách giọng (Whisper)...")
                            raw = transcribe_audio("temp.mp3", load_whisper_model())
                            st.write(f"💎 Đang viết theo tuyến: {selected_pillar}...")
                            rewrite = rewrite_with_gemini(raw, selected_pillar, selected_product_info_str)
                            st.session_state.data.update({"videoTitle": uploaded_file.name, "originalTranscript": raw, "rewrittenScript": rewrite, "generatedAudio": None})
                            st.session_state.processing_done = True
                            st.rerun()
                        except Exception as e: st.error(str(e))

        with tab3:
            c_in, c_btn = st.columns([3.5, 1.5], vertical_alignment="bottom")
            url = c_in.text_input("Link Video", placeholder="TikTok / YouTube Shorts...", label_visibility="collapsed")
            if c_btn.button("Phân tích", type="primary", key="btn_link"):
                if url:
                    with st.status("🚀 Đang xử lý...", expanded=True):
                        try:
                            st.write("📥 Tải video...")
                            path, title = download_audio(url)
                            st.write("🎧 Tách giọng...")
                            raw = transcribe_audio(path, load_whisper_model())
                            st.write(f"💎 Đang viết theo tuyến: {selected_pillar}...")
                            rewrite = rewrite_with_gemini(raw, selected_pillar, selected_product_info_str)
                            st.session_state.data.update({"videoTitle": title, "originalTranscript": raw, "rewrittenScript": rewrite, "generatedAudio": None})
                            st.session_state.processing_done = True
                            st.rerun()
                        except Exception as e: st.error(str(e))

    else:
        # --- KẾT QUẢ HIỂN THỊ NGAY BÊN PHẢI ---
        c_back, c_title = st.columns([1.5, 8], vertical_alignment="center")
        if c_back.button("← Quay lại"): 
            st.session_state.processing_done = False
            st.rerun()
        c_title.markdown(f"### 🎯 Kết quả xử lý")
        
        st.divider()
        
        # Transcript gốc
        with st.expander("📄 Xem nội dung gốc (Transcript)", expanded=False):
            st.text_area("Original", value=st.session_state.data["originalTranscript"], height=200)

        # Kịch bản mới
        st.markdown(f"**✨ Kịch bản HuyK ({selected_pillar})**")
        new_script = st.text_area("Editor", value=st.session_state.data["rewrittenScript"], height=400, label_visibility="collapsed")
        if new_script != st.session_state.data["rewrittenScript"]: st.session_state.data["rewrittenScript"] = new_script
        
        # Audio Player
        st.markdown('<div class="card" style="margin-top:20px; background:#f8fafc">', unsafe_allow_html=True)
        if not st.session_state.data["generatedAudio"]:
            if st.button("🎙️ Tạo giọng đọc AI", type="primary", use_container_width=True):
                with st.spinner("Đang khởi tạo voice..."):
                    path, err = generate_minimax_audio(st.session_state.data["rewrittenScript"])
                    if path: st.session_state.data["generatedAudio"] = path; st.rerun()
                    else: st.error(err)
        else:
            st.success("✅ Voice đã sẵn sàng")
            st.audio(st.session_state.data["generatedAudio"], format="audio/mp3")
            c_dl, c_re = st.columns(2)
            with c_dl:
                with open(st.session_state.data["generatedAudio"], "rb") as f:
                    st.download_button("⬇️ Tải file MP3", f, file_name="voice.mp3", mime="audio/mpeg", use_container_width=True)
            with c_re:
                if st.button("↺ Tạo lại voice", use_container_width=True):
                    st.session_state.data["generatedAudio"] = None
                    st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)
