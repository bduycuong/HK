import streamlit as st
import yt_dlp
import os
import google.generativeai as genai
import requestse
import time
import shutil
import json
import whisper
import pandas as pd

# --- 1. CẤU HÌNH TRANG & ICON ---
TAB_ICON_URL = "https://i.ibb.co/5grLnPjW/logohk.png" 
st.set_page_config(
    page_title="HuyK AI Studio", 
    page_icon=TAB_ICON_URL,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CẤU HÌNH LOGO ---
LOGO_URL = "https://i.ibb.co/5grLnPjW/logohk.png" 

# --- 3. ĐỊNH NGHĨA TUYẾN NỘI DUNG ---
PILLAR_DEFINITIONS = {
    "A1: Traffic - Mẹo & Tin tức": """
    - Mục tiêu: Thu hút người xem, viral.
    - Nội dung: Chia sẻ mẹo vặt, câu hỏi thú vị, soi đồ người nổi tiếng, tin tức ngành.
    - Phong cách: Nhanh, gọn, gây tò mò, ngôn ngữ đời thường.
    - Lồng ghép được HuyK vào trong nội dung mẹo/tin tức.
    """,
    "A2: Kiến thức - Chuyên gia": """
    - Mục tiêu: Thể hiện sự hiểu biết, chuyên gia.
    - Nội dung: Lịch sử thương hiệu, thuật ngữ chuyên ngành, phân biệt chất liệu, dạy nghề.
    - Phong cách: Trầm ổn, sâu sắc, giải thích dễ hiểu, uy tín.
    - Lồng ghép được HuyK vào trong nội dung kiến thức.
    """,
    "A3: Uy tín - Niềm tin": """
    - Mục tiêu: Xây dựng lòng tin.
    - Nội dung: Hoạt động cửa hàng, giải thưởng, giao hàng, kể chuyện bảo hành, tâm sự nghề.
    - Phong cách: Chân thành, kể chuyện (storytelling), tự hào.
    - Lồng ghép được HuyK vào trong nội dung uy tín.
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

# --- 4. SESSION STATE ---
if 'processing_done' not in st.session_state: st.session_state.processing_done = False
if 'product_df' not in st.session_state: st.session_state.product_df = None
if 'data' not in st.session_state: 
    st.session_state.data = {
        "videoTitle": "", "originalTranscript": "", 
        "rewrittenScript": "", "generatedAudio": None
    }

# --- 5. CSS GIAO DIỆN ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    * {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: #f8fafc; color: #0f172a; }}
    header, footer {{ display: none !important; }}
    .block-container {{ padding-top: 1rem !important; max-width: 1400px !important; }}

    /* Navbar */
    .nav-container {{
        background: white; border-bottom: 1px solid #e2e8f0;
        padding: 0.8rem 1.5rem; margin-bottom: 1.5rem;
        border-radius: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        display: flex; justify-content: space-between; align-items: center;
    }}
    .logo-img {{ width: 40px; height: 40px; object-fit: contain; border-radius: 6px; }}
    .brand-text {{ font-size: 18px; font-weight: 700; color: #0f172a; margin-left: 10px; }}
    
    /* Input & Button */
    div[data-testid="stTextInput"] input, div[data-testid="stSelectbox"] > div > div {{
        border-radius: 12px; border: 1px solid #e2e8f0; height: 45px;
    }}
    .stButton > button {{
        background-color: #2563eb; color: white; border-radius: 12px; height: 35px; font-weight: 600;
        width: 100%; transition: all 0.2s; border: none;
    }}
    .stButton > button:hover {{ background-color: #1d4ed8; transform: translateY(-1px); }}

    /* Cards */
    .card {{ background: white; border-radius: 20px; border: 1px solid #e2e8f0; padding: 20px; box-shadow: 0 4px 6px -2px rgba(0, 0, 0, 0.03); height: 100%; }}
    .card-title {{ font-weight: 700; color: #334155; font-size: 1rem; margin-bottom: 10px; display: flex; align-items: center; gap: 8px;}}
</style>
""", unsafe_allow_html=True)

# --- 6. CONFIG & FUNCTIONS ---
CONFIG_FILE = "app_config.txt"
DEFAULT_PROMPT = """Nhiệm vụ: Viết lại nội dung video TikTok theo phong cách HuyK."""

def load_config():
    config = {
        "gemini_key": "", "minimax_key": "", "minimax_group": "", 
        "minimax_voice": "", "minimax_model": "speech-2.6-hd", 
        "prompt": DEFAULT_PROMPT,
        "memory": ""
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

def save_config(gemini, mm_key, mm_group, mm_voice, mm_model, prompt, memory):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        clean_prompt = prompt.replace("\n", "\\n")
        clean_memory = memory.replace("\n", "\\n")
        f.write(f"gemini_key={gemini.strip()}\nminimax_key={mm_key.strip()}\nminimax_group={mm_group.strip()}\nminimax_voice={mm_voice.strip()}\nminimax_model={mm_model.strip()}\nprompt={clean_prompt}\nmemory={clean_memory}\n")

config = load_config()

@st.dialog("⚙️ Cài đặt hệ thống")
def open_settings():
    st.caption("Cấu hình API & Bộ nhớ Agent.")
    new_gemini = st.text_input("Gemini API Key", value=config["gemini_key"], type="password")
    new_mm_key = st.text_input("Minimax API Key", value=config["minimax_key"], type="password")
    
    c1, c2 = st.columns(2)
    with c1: 
        model_options = ["speech-2.6-hd", "speech-01-turbo", "speech-01-hd", "speech-02"]
        current = config.get("minimax_model", "speech-2.6-hd")
        new_mm_model = st.selectbox("Model", model_options, index=model_options.index(current) if current in model_options else 0)
    with c2: new_mm_voice = st.text_input("Voice ID", value=config["minimax_voice"])
    
    st.divider()
    st.markdown("🧠 **Bộ nhớ Agent (Quy tắc riêng)**")
    new_memory = st.text_area("Quy tắc ghi nhớ", value=config.get("memory", ""), height=100, placeholder="Ví dụ: Không bao giờ báo giá trực tiếp...")

    with st.expander("📝 Prompt Gốc (Nâng cao)"):
        new_prompt = st.text_area("Base Prompt", value=config["prompt"], height=100)

    if st.button("Lưu cài đặt", type="primary"):
        save_config(new_gemini, new_mm_key, config["minimax_group"], new_mm_voice, new_mm_model, new_prompt, new_memory)
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
    memory_instruction = ""
    if config.get("memory"):
        memory_instruction = f"\n--- 🧠 BỘ NHỚ QUY TẮC RIÊNG ---\n{config['memory']}\n------------------------------\n"

    system_instruction = f"""
    {config["prompt"]}
    {memory_instruction}
    --- YÊU CẦU CỤ THỂ CHO BÀI NÀY ---
    1. TUYẾN NỘI DUNG: {pillar}
    {pillar_instruction}
    2. SẢN PHẨM CẦN LỒNG GHÉP (Nếu có):
    {product_info if product_info else "Không có sản phẩm cụ thể, tập trung vào nội dung chính."}
    3. QUY TẮC VIẾT:
    - Không cần mở đầu bằng xin chào
    - Nếu là tuyến A4: Tuyệt đối KHÔNG báo giá trực tiếp, KHÔNG kêu gọi "mua ngay". Hãy tập trung vào CÂU CHUYỆN KHÁCH HÀNG.
    - Giọng văn: Chân thật, trầm, tâm sự (style HuyK).
    - Xưng hô: "HuyK", gọi khách là "anh, chị, bạn, mọi người, anh khách, chị khách".
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

# --- 7. UI CHÍNH ---

st.markdown(f"""
<div class="nav-container">
    <div style="display:flex;align-items:center;gap:12px">
        <img src="{LOGO_URL}" class="logo-img">
        <span class="brand-text">HuyK AI Studio</span>
    </div>
    <div style="display:flex; gap:12px; align-items:center;">
        <div class="status-badge" style="background:#f1f5f9; padding:4px 10px; border-radius:20px; font-size:12px; border:1px solid #e2e8f0; color:{'#166534' if config['gemini_key'] else '#64748b'}; display:flex; align-items:center; gap:5px;">
            <div style="width:6px; height:6px; border-radius:50%; background:{'#22c55e' if config['gemini_key'] else '#cbd5e1'}"></div> Gemini
        </div>
        <div class="status-badge" style="background:#f1f5f9; padding:4px 10px; border-radius:20px; font-size:12px; border:1px solid #e2e8f0; color:{'#166534' if config['minimax_key'] else '#64748b'}; display:flex; align-items:center; gap:5px;">
            <div style="width:6px; height:6px; border-radius:50%; background:{'#22c55e' if config['minimax_key'] else '#cbd5e1'}"></div> Minimax
        </div>
    </div>
</div>
""", unsafe_allow_html=True)

col_strategy, col_main = st.columns([3, 7], gap="large")

with col_strategy:
    st.subheader("🔁Chiến lược Content")
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
    
    st.markdown("**2. Kho Sản phẩm**")
    uploaded_products = st.file_uploader("Upload danh sách (Excel/CSV)", type=['xlsx', 'csv'], label_visibility="collapsed")
    
    product_options = []
    if uploaded_products:
        try:
            if uploaded_products.name.endswith('.csv'):
                df = pd.read_csv(uploaded_products)
            else:
                df = pd.read_excel(uploaded_products)
            df.columns = [c.strip().lower() for c in df.columns]
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


with col_main:
    if not st.session_state.processing_done:
        st.markdown("""
        <h1 style="font-size:2.5rem; font-weight:800; color:#0f172a; margin-bottom:0.5rem; line-height:1.2;">
            Biến Video thành <span style="color:#2563eb;">Viral Content</span>
        </h1>
        <p style="color:#64748b; font-size:1rem; margin-bottom:2rem;">
            Công cụ hỗ trợ viết lại kịch bản, lồng ghép sản phẩm và tạo giọng đọc AI.
        </p>
        """, unsafe_allow_html=True)
        
        if "A4" in selected_pillar or "A5" in selected_pillar:
            if not selected_product_info_str:
                st.warning("⚠️ Tuyến này cần bán hàng. Hãy chọn sản phẩm ở cột bên trái.")

        tab1, tab2, tab3 = st.tabs(["📄 Ý tưởng / Văn bản", "☁️ File Upload", "🔗 Link Video"])
        
        with tab1:
            raw_input = st.text_area("Nhập ý tưởng thô...", height=150, placeholder="Ví dụ: Khách hỏi 500k mua được nhẫn bạc nào tặng người yêu...", label_visibility="collapsed")
            st.write("")
            if st.button("✨ Phân tích & Viết bài", type="primary"):
                if raw_input:
                    with st.status("🚀 Đang xử lý...", expanded=True):
                        rewrite = rewrite_with_gemini(raw_input, selected_pillar, selected_product_info_str)
                        st.session_state.data.update({"videoTitle": "Văn bản nhập tay", "originalTranscript": raw_input, "rewrittenScript": rewrite, "generatedAudio": None})
                        st.session_state.processing_done = True
                        st.rerun()
                else: st.toast("Nhập nội dung đi bạn ơi!", icon="⚠️")

        with tab2:
            uploaded_file = st.file_uploader("Upload Video/Audio", type=['mp4', 'mp3', 'wav'], label_visibility="collapsed")
            st.write("")
            if st.button("🚀 Xử lý File", type="primary", key="btn_file"):
                if uploaded_file:
                    with st.status("🚀 Đang xử lý...", expanded=True):
                        try:
                            with open("temp.mp3", "wb") as f: f.write(uploaded_file.getbuffer())
                            st.write("🎧 Đang tách giọng (Whisper)...")
                            raw = transcribe_audio("temp.mp3", load_whisper_model())
                            st.write(f"💎 Đang viết theo tuyến: {selected_pillar}...")
                            rewrite = rewrite_with_gemini(raw, selected_pillar, selected_product_info_str)
                            # COPY FILE ĐỂ DÙNG Ở TRANG KẾT QUẢ
                            shutil.copy("temp.mp3", "downloaded_audio.mp3") 
                            st.session_state.data.update({"videoTitle": uploaded_file.name, "originalTranscript": raw, "rewrittenScript": rewrite, "generatedAudio": None})
                            st.session_state.processing_done = True
                            st.rerun()
                        except Exception as e: st.error(str(e))

        with tab3:
            c_in, c_btn = st.columns([3.5, 1.5], vertical_alignment="bottom")
            url = c_in.text_input("Link Video", placeholder="TikTok / Reel / YouTube Shorts...", label_visibility="collapsed")
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
        c_back, c_title = st.columns([1.5, 8], vertical_alignment="center")
        if c_back.button("← Quay lại"): 
            st.session_state.processing_done = False
            st.rerun()
        c_title.markdown(f"### 🎯 Kết quả xử lý")
        st.divider()
        
        # --- HIỂN THỊ FILE GỐC ---
        if os.path.exists("downloaded_audio.mp3"):
            st.markdown("**🔊 Audio/Video Gốc:**")
            st.audio("downloaded_audio.mp3", format="audio/mp3")
        # -------------------------
        
        with st.expander("📄 Xem nội dung gốc (Transcript)", expanded=False):
            st.text_area("Original", value=st.session_state.data["originalTranscript"], height=200)
        
        st.markdown(f"**✨ Kịch bản HuyK ({selected_pillar})**")
        new_script = st.text_area("Editor", value=st.session_state.data["rewrittenScript"], height=400, label_visibility="collapsed")
        if new_script != st.session_state.data["rewrittenScript"]: st.session_state.data["rewrittenScript"] = new_script
        
        # --- HIỂN THỊ SỐ KÝ TỰ ---
        char_count = len(st.session_state.data["rewrittenScript"])
        st.caption(f"📝 Số ký tự: {char_count} | ⏳ Ước tính audio: ~{int(char_count/15)} giây")
        # -------------------------

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




