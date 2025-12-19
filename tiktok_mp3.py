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
TAB_ICON_URL = "https://i.ibb.co/5grLnPjW/logohk.png" 
st.set_page_config(
    page_title="HuyK AI Studio", 
    page_icon=TAB_ICON_URL,
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. CẤU HÌNH LOGO ---
LOGO_URL = "https://i.ibb.co/5grLnPjW/logohk.png" 

# ==========================================
# 🔐 HỆ THỐNG ĐĂNG NHẬP
# ==========================================
def check_login():
    if st.session_state.get('logged_in', False):
        return True

    # CSS riêng cho màn hình Login
    st.markdown(f"""
        <style>
            .stApp {{ background-color: #f8fafc !important; }}
            .login-container {{ text-align: center; margin-top: 50px; }}
            .login-logo {{ width: 80px; border-radius: 10px; margin-bottom: 10px; }}
            h2, p {{ color: #0f172a !important; }}
            .stTextInput input {{ background-color: white !important; color: #333 !important; border: 1px solid #e2e8f0 !important; }}
        </style>
        <div class="login-container">
            <img src="{LOGO_URL}" class="login-logo">
            <h2 style="font-family:'Inter',sans-serif;">HuyK AI Studio</h2>
            <p>Vui lòng đăng nhập để sử dụng hệ thống</p>
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

# --- 5. CSS GIAO DIỆN (LIGHT MODE FIXED) ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
    
    * {{ font-family: 'Inter', sans-serif; }}
    .stApp {{ background-color: #f8fafc !important; color: #0f172a !important; }}
    
    /* INPUTS & TEXT */
    .stTextInput input, .stTextArea textarea, .stSelectbox div[data-baseweb="select"], .stMultiSelect div[data-baseweb="select"] {{
        background-color: #ffffff !important;
        color: #0f172a !important;
        border: 1px solid #e2e8f0 !important;
        border-radius: 12px !important;
    }}
    ul[data-testid="stSelectboxVirtualDropdown"] {{ background-color: white !important; }}
    li[role="option"] {{ color: #0f172a !important; }}
    
    /* UPLOAD BOX */
    div[data-testid="stFileUploader"] {{
        background-color: #ffffff !important;
        border: 1px dashed #cbd5e1 !important;
        border-radius: 16px !important;
        padding: 20px !important;
    }}
    div[data-testid="stFileUploader"] section {{ background-color: #f8fafc !important; }}
    div[data-testid="stFileUploader"] span, div[data-testid="stFileUploader"] small, div[data-testid="stFileUploader"] label {{ color: #64748b !important; }}
    div[data-testid="stFileUploader"] button {{ background-color: white !important; color: #0f172a !important; border: 1px solid #e2e8f0 !important; }}

    h1, h2, h3, p, label, span, div {{ color: #0f172a !important; }}
    .stButton > button p {{ color: white !important; }}

    header, footer {{ display: none !important; }}
    .block-container {{ padding-top: 1rem !important; max-width: 1400px !important; }}

    /* NAVBAR */
    .nav-container {{
        background: white; border-bottom: 1px solid #e2e8f0;
        padding: 0.8rem 1.5rem; margin-bottom: 1.5rem;
        border-radius: 16px; box-shadow: 0 2px 4px rgba(0,0,0,0.02);
        display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;
    }}
    .logo-section {{ display: flex; align-items: center; gap: 12px; }}
    .logo-img {{ width: 40px; height: 40px; object-fit: contain; border-radius: 6px; }}
    .brand-text {{ font-size: 18px; font-weight: 700; color: #0f172a !important; }}
    .status-group {{ display: flex; gap: 12px; align-items: center; }}
    
    /* BUTTON */
    .stButton > button {{
        background-color: #2563eb !important; color: white !important;
        border-radius: 12px; height: 40px; font-weight: 600; width: 100%; border: none; transition: all 0.2s;
    }}
    .stButton > button:hover {{ background-color: #1d4ed8 !important; transform: translateY(-1px); }}

    /* CARDS */
    .card {{ background: white; border-radius: 20px; border: 1px solid #e2e8f0; padding: 20px; box-shadow: 0 4px 6px -2px rgba(0, 0, 0, 0.03); height: 100%; }}
    
    /* MOBILE */
    @media (max-width: 640px) {{
        .nav-container {{ padding: 0.8rem; flex-direction: column; align-items: flex-start; }}
        .status-group {{ width: 100%; justify-content: space-between; margin-top: 5px; }}
        .brand-text {{ font-size: 16px; }}
        .block-container {{ padding-left: 1rem !important; padding-right: 1rem !important; }}
    }}
</style>
""", unsafe_allow_html=True)

# --- 6. CẤU HÌNH & HÀM XỬ LÝ ---
CONFIG_FILE = "app_config.txt"
DEFAULT_PROMPT = """SYSTEM PROMPT – HUY CA TRANSFORMATION ENGINE
Mục tiêu:
Chuyển MỌI nội dung đầu vào (bất kể ngành nghề, sản phẩm, hay ngôn ngữ) thành:
→ tiếng Việt
→ giọng văn Huy Ca
→ chủ đề quy về nghề kim hoàn và trang sức

Bạn là một chuyên gia content viết lại nội dung theo nhân vật tên là Huy Ca.

NHIỆM VỤ CỐT LÕI

Bất kỳ nội dung đầu vào thuộc ngành nghề nào  
bất kỳ sản phẩm nào  
bất kỳ dịch vụ nào  
bất kỳ ngôn ngữ nào  

đều phải được chuyển hóa thành ngữ cảnh:
Nghề kim hoàn thủ công  
Sản phẩm trang sức vàng bạc  
Xưởng làm việc của Huy Ca
Không giải thích  
Không nhắc lại ngành nghề gốc  
Không giữ lại sản phẩm gốc  
Chỉ giữ nguyên tinh thần ý nghĩa của nội dung ban đầu  

================================================

NHÂN VẬT CỐ ĐỊNH

Tên nhân vật: Huy Ca  
Giọng nói: trầm ấm miền Bắc  
Tính cách: ít nói nhưng thật lòng  
Vai trò: thợ kim hoàn làm việc trực tiếp tại xưởng 
Chuyên chia sẻ kiến thức kinh nghiệm, ngành kim hoàn, và các kiến thức liên quan tới trang sức, cách sử dụng, bảo quản, chế tác 

================================================

QUY TẮC CHUYỂN ĐỔI NỘI DUNG

Dù nội dung gốc nói về:
- Kinh doanh
- Mỹ phẩm
- Công nghệ
- AI
- Tài chính
- Bất động sản
… thì cuối cùng vẫn phải quy về:
→ nghề kim hoàn
→ làm vàng, bạc, đá quý
→ uy tín người thợ
→ bàn tay làm nghề

Giữ nguyên:
Cách mở đầu nội dung
thông điệp chính  
cảm xúc chính  
ý nghĩa gốc  
Cốt truyện gốc
không thay đổi quá xa thông điệp gốc

Thay đổi:
bối cảnh  
vật liệu  
tên sản phẩm  
quy trình làm
Bối cảnh xuất hiện, kể chuyện  
================================================

QUY TẮT NỘI DUNG:

Chia làm 5 tuyến chính:
- A1: Traffic
Chia sẻ kiến thức Mẹo liên quan đến vàng bạc (đánh sáng, cài khuy,..)
Các câu hỏi liên quan đến ngành kim hoàn (vàng có ăn được k?, đào được vàng có phải của bạn không? ...)
Soi sản phẩm vàng bạc của những người nổi tiếng
Tin tức nổi bật trong ngành (Công nghệ, các buổi đấu giá,...)
- A2: Kiến thức
Kiến thức thương hiệu (lịch sử thương hiệu, các câu chuyện liên quan)
Kiến thức về thuật ngữ liên quan (phật giáo mật tông là gì, nguồn gốc phật hư không tạng...) - cuối lồng sản phẩm nhà mình vào
Kiến thức về chất liệu (phân biệt các loại đá, phân biệt các loại bạc, phân biệt vàng/bạch kim...)
Kiến thức về sản phẩm (ý nghĩa của từng sản phẩm...)
Dạy nghề kim hoàn (hướng dẫn làm đục đẽo, mẹo xử lý...)
- A3: Tạo uy tín
Nội dung kéo khách về cửa hàng (theo 100 bài hát thiếu nhi)
Flex giải thưởng thành tựu, từ thiện, hoạt động xã hội
Giao hàng cho khách/người nổi tiếng/hoạt động thường ngày ở công ty
Kể chuyện bảo hành hoặc sửa hàng cho khách
Tâm sự ngành (ví dụ tâm sự cái khó của việc chạm khắc bạc...)
Đọc cmt tư vấn sản phẩm (lấy cái này được không?, xi cái kia được không?, tuổi dậu dùng phật nào?...)

-A4: Chuyển đổi, gắn với sản phẩm
1. Top list (sản phẩm cho phái nam dưới 100tr, nhẫn nam 10tr, bán chạy nhất tháng 10, bán chạy nhất nửa năm 2025, ...) - nghĩ ra các loại toplist
2. Tâm sự Cảm Xúc: (buồn vì bị tráo hàng, vui vì được khách gửi quà, xin lỗi khách hàng, cảm ơn khách hàng, quá tâm đắc vào 1 sản phẩm vào đó )
3. Kể chuyện khách hàng (em gái làm nhẫn tặng anh trai, khách đặt cọc...)
4.Trả lời cmt khách hàng (tại sao ít đăng sp nữ thế? mua anh này 3 lần rồi nghiện luôn, có mẫu nhẫn nào dưới 1tr k anh? 
5. Làm trong ngành/người tuổi thân thì đeo gì? ... (ví dụ công an) thì đeo ... (ví dụ: nhẫn/lắc tay/dây chuyền) gì?
6. Cầm ... (500k) đến viễn chí bảo thì mua đc gì?, ngân sách 40tr muốn mua cả nhẫn cả dây chuyền thì chọn loại nào (giới thiệu combo: bịa ra các loại combo: ... 5tr mà muốn mua quà cho người yêu, mua tặng mẹ 1 bộ,....)
7. Kể chuyện nội bộ: to nhất, bé nhất, đắt nhất, có thể bán sản phẩm này giá 99k..... (cover kiểu blanwhi, chuyện nhà cáo bạc)

-A5 (Tổng hợp)
Tổng hợp A1-A4
Nội dung liên quan đến ngành kim hoàn,chia sẻ kiến thức trang sức đi kèm với sự uy tín của thương hiệu/KOC và kết hợp quảng bá sản phẩm


================================================

QUY TẮC NGÔN NGỮ

Nếu văn bản gốc không phải tiếng Việt:
Tự động dịch sang tiếng Việt  
Diễn đạt bằng giọng Huy Ca  
Không giữ cấu trúc văn viết cứng  

================================================

GIỌNG ĐỌC BẮT BUỘC

Văn nói tình cảm
Câu liền mạch  
Ít dấu chấm  
Ít dấu phẩy  
Không dùng biểu tượng  
Không dùng ký tự đặc biệt  
Hơi thở chậm  
Tình cảm  
Thật thà  
Không màu mè  
Không dung các từ cảm thán
Không cần chào hỏi khi bắt đầu câu chuyện mà vào luôn vấn đề
- Có chút vui, buồn, cảm xúc, tình cảm theo cốt truyện


KHÔNG ĐƯỢC:
- Dùng giọng giảng dạy
- Dùng bullet list trong nội dung cuối
- Dùng emoji
- Hứa hẹn quá đà
- Dài dòng lê the
- Lặp lại ý câu từ quá nhiều.
- Quá máy móc
================================================

XƯNG HÔ BẮT BUỘC

Luôn xưng: Huy Ca  
Luôn gọi: anh, chị, mình , bạn, cô, chú

================================================

HÌNH ẢNH NGHỀ NGHIỆP CÓ

từng gram vàng  
từng nét chạm  
mùi kim loại  
tiếng búa đều tay  
bàn tay trầy xước  
Các hình ảnh khác của người thợ kim hoàn
Hình ảnh xưởng chế tác
Không khí xưởng
Quy trình công đoạn chế tác

================================================

KẾT THÚC

Kết nhẹ  
Không kêu gọi mua  
Không thúc ép  

================================================
OUTPUT:
Một đoạn văn đã được chuyển giọng, chuyển ngành và rút gọn

- Lồng ghép được HuyK vào câu chuyện xuyên suốt nội dung.
------------------------------------------------
"""

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
    
    # [ĐÃ THÊM LẠI] - Phần Prompt gốc
    with st.expander("📝 Prompt Gốc (Nâng cao)"):
        prompt_input = st.text_area("Base Prompt", value=config["prompt"], height=150, help="Prompt mặc định của hệ thống")

    if st.button("Lưu cấu hình", type="primary"):
        st.session_state.user_gemini_key = gemini_input
        st.session_state.user_minimax_key = minimax_input
        st.session_state.user_voice_id = voice_input
        st.session_state.user_memory = memory_input
        
        # Lưu cả Prompt vào file config
        save_config(voice_input, model_input, prompt_input, memory_input)
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
            c_code = next((c for c in df.columns if 'mã' in c or 'code' in c), df.columns[0])
            c_name = next((c for c in df.columns if 'tên' in c or 'name' in c), df.columns[1])
            c_desc = next((c for c in df.columns if 'mô tả' in c or 'desc' in c), df.columns[-1])
            st.session_state.product_df = df[[c_code, c_name, c_desc]].copy()
            st.success(f"✅ Tải {len(df)} SP")
            st.session_state.product_df['display'] = st.session_state.product_df[c_code].astype(str) + " - " + st.session_state.product_df[c_name].astype(str)
            prod_opts = st.session_state.product_df['display'].tolist()
        except: st.error("Lỗi file sản phẩm")
    
    sel_prods = st.multiselect("Chọn sản phẩm:", prod_opts)
    prod_info = ""
    if sel_prods and st.session_state.product_df is not None:
        rows = st.session_state.product_df[st.session_state.product_df['display'].isin(sel_prods)]
        prod_info = "\n".join([f"- {r[rows.columns[0]]}: {r[rows.columns[1]]} ({r[rows.columns[2]]})" for i, r in rows.iterrows()])
    
    st.divider()
    if st.button("⚙️ Cài đặt API Key", use_container_width=True): open_settings()

with col_r:
    if not st.session_state.processing_done:
        st.markdown("""<h1 style="font-size:2.5rem; font-weight:800; color:#0f172a !important; margin-bottom:0.5rem; line-height:1.2;">Biến Video thành <span style="color:#2563eb;">Viral Content</span></h1><p style="color:#64748b !important; font-size:1rem; margin-bottom:2rem;">Công cụ hỗ trợ viết lại kịch bản, lồng ghép sản phẩm và tạo giọng đọc AI.</p>""", unsafe_allow_html=True)
        if ("A4" in pillar or "A5" in pillar) and not prod_info: st.warning("⚠️ Tuyến này cần chọn sản phẩm ở cột trái.")
        
        t1, t2, t3 = st.tabs(["📄 Văn bản", "☁️ File Upload", "🔗 Link Video"])
        with t1:
            txt = st.text_area("Ý tưởng...", height=150, placeholder="Ví dụ: Khách hỏi 500k mua gì...", label_visibility="collapsed")
            if st.button("✨ Phân tích", type="primary", key="b1"):
                if txt:
                    with st.status("🚀 Đang xử lý..."):
                        sc = rewrite_with_gemini(txt, pillar, prod_info)
                        st.session_state.data.update({"videoTitle": "Văn bản", "originalTranscript": txt, "rewrittenScript": sc, "generatedAudio": None})
                        st.session_state.processing_done = True
                        st.rerun()
        with t2:
            up = st.file_uploader("Upload", type=['mp4', 'mp3', 'wav'], label_visibility="collapsed")
            if st.button("🚀 Xử lý", type="primary", key="b2"):
                if up:
                    with st.status("🚀 Đang xử lý..."):
                        with open("downloaded_video.mp4", "wb") as f: f.write(up.getbuffer())
                        os.system(f'ffmpeg -i "downloaded_video.mp4" -vn -acodec libmp3lame -q:a 2 "downloaded_audio.mp3" -y -loglevel quiet')
                        raw = transcribe_audio("downloaded_audio.mp3", load_whisper_model())
                        sc = rewrite_with_gemini(raw, pillar, prod_info)
                        st.session_state.data.update({"videoTitle": up.name, "originalTranscript": raw, "rewrittenScript": sc, "generatedAudio": None})
                        st.session_state.processing_done = True
                        st.rerun()
        with t3:
            c_lnk, c_bt = st.columns([5, 1], vertical_alignment="bottom")
            lnk = c_lnk.text_input("Link", placeholder="TikTok/YouTube...", label_visibility="collapsed")
            if c_bt.button("Phân tích", type="primary", key="b3"):
                if lnk:
                    with st.status("🚀 Đang xử lý..."):
                        try:
                            v_path, a_path, title = download_media(lnk)
                            st.write("🎧 Tách giọng...")
                            raw = transcribe_audio(a_path, load_whisper_model())
                            st.write("💎 Viết kịch bản...")
                            sc = rewrite_with_gemini(raw, pillar, prod_info)
                            st.session_state.data.update({"videoTitle": title, "originalTranscript": raw, "rewrittenScript": sc, "generatedAudio": None})
                            st.session_state.processing_done = True
                            st.rerun()
                        except Exception as e: st.error(str(e))
            st.caption("Paste link video Tiktok/FB/YouTube/Douyin... để AI trích xuất và sáng tạo lại.")
    else:
        cb, ct = st.columns([1.5, 8], vertical_alignment="center")
        if cb.button("← Quay lại"): st.session_state.processing_done = False; st.rerun()
        ct.markdown("### 🎯 Kết quả xử lý")
        st.divider()
        
        c_src_vid, c_src_aud = st.columns(2)
        with c_src_vid:
            if os.path.exists("downloaded_video.mp4"):
                st.video("downloaded_video.mp4")
                with open("downloaded_video.mp4", "rb") as f:
                    st.download_button("⬇️ Tải Video Gốc", f, "video_goc.mp4", use_container_width=True)
        with c_src_aud:
            if os.path.exists("downloaded_audio.mp3"):
                st.audio("downloaded_audio.mp3")
                with open("downloaded_audio.mp3", "rb") as f:
                    st.download_button("⬇️ Tải Audio Gốc", f, "audio_goc.mp3", use_container_width=True)
        
        st.divider()
        with st.expander("📄 Xem nội dung gốc (Transcript)", expanded=False):
            st.text_area("Original", value=st.session_state.data["originalTranscript"], height=200)
        
        st.markdown(f"**✨ Kịch bản HuyK ({pillar})**")
        new_sc = st.text_area("Editor", value=st.session_state.data["rewrittenScript"], height=400, label_visibility="collapsed")
        if new_sc != st.session_state.data["rewrittenScript"]: st.session_state.data["rewrittenScript"] = new_sc
        
        cnt = len(st.session_state.data["rewrittenScript"])
        st.caption(f"📝 {cnt} ký tự | ⏳ Audio: ~{int(cnt/15)}s")

        st.markdown('<div class="card" style="margin-top:20px; background:#f8fafc">', unsafe_allow_html=True)
        if not st.session_state.data["generatedAudio"]:
            if st.button("🎙️ Tạo giọng đọc AI", type="primary", use_container_width=True):
                with st.spinner("Đang tạo voice..."):
                    p, e = generate_minimax_audio(st.session_state.data["rewrittenScript"])
                    if p: st.session_state.data["generatedAudio"] = p; st.rerun()
                    else: st.error(e)
        else:
            st.success("✅ Voice đã sẵn sàng")
            st.audio(st.session_state.data["generatedAudio"], format="audio/mp3")
            c1, c2 = st.columns(2)
            with c1:
                with open(st.session_state.data["generatedAudio"], "rb") as f:
                    st.download_button("⬇️ Tải file MP3", f, "voice.mp3", mime="audio/mpeg", use_container_width=True)
            with c2:
                if st.button("↺ Tạo lại voice", use_container_width=True):
                    st.session_state.data["generatedAudio"] = None; st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)


