import streamlit as st
from openai import OpenAI
from PIL import Image
import edge_tts
import asyncio
import io
import re
import base64

# ==========================================
# 1. AYARLAR & TASARIM
# ==========================================
st.set_page_config(
    page_title="Kafadar",
    page_icon="🤖",
    layout="centered"
)

st.markdown("""
<style>
.stApp { background-color: #fcfdfd; }
h1 { color: #2E86C1; font-family: 'Comic Sans MS', sans-serif; text-align: center; }
.stChatMessage { border-radius: 10px; }

.stButton>button {
    background-color: #F4D03F; color: #17202A; border-radius: 15px;
    font-weight: bold; border: none; padding: 12px 24px;
    width: 100%;
}
.footer {
    position: fixed; left: 0; bottom: 0; width: 100%;
    background-color: #fcfdfd; color: #888; text-align: center;
    font-size: 14px; padding: 10px; border-top: 1px solid #eee;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. OPENAI BAĞLANTISI
# ==========================================
if "OPENAI_API_KEY" not in st.secrets:
    st.error("🚨 OpenAI API Key bulunamadı!")
    st.stop()

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])

# ==========================================
# 3. YARDIMCI FONKSİYONLAR
# ==========================================
def compress_image(image):
    img = image.copy()
    img.thumbnail((800, 800))
    return img

def image_to_base64(img):
    if img.mode != "RGB":
        img = img.convert("RGB")   # 👈 KRİTİK SATIR
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=85)
    return base64.b64encode(buf.getvalue()).decode()


def metni_temizle(text):
    text = re.sub(r'(?i)cevap', 'yanıt', text)
    text = text.replace("#", "").replace("*", "")
    return text.strip()

def sesi_yaziya_cevir(audio_bytes):
    try:
        transcript = client.audio.transcriptions.create(
            file=audio_bytes,
            model="gpt-4o-transcribe"
        )
        return transcript.text
    except:
        return None

async def seslendir_async(metin, ses="tr-TR-EmelNeural"):
    communicate = edge_tts.Communicate(metin, ses)
    mp3_fp = io.BytesIO()
    async for chunk in communicate.stream():
        if chunk["type"] == "audio":
            mp3_fp.write(chunk["data"])
    mp3_fp.seek(0)
    return mp3_fp

def metni_oku(metin):
    try:
        temiz = metni_temizle(metin)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop.run_until_complete(seslendir_async(temiz))
    except:
        return None

# ==========================================
# 4. SESSION STATE
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []
if "ilk_karsilama" not in st.session_state:
    st.session_state.ilk_karsilama = False
if "ses_aktif" not in st.session_state:
    st.session_state.ses_aktif = True

def sifirla():
    st.session_state.clear()
    st.rerun()

# ==========================================
# 5. ARAYÜZ
# ==========================================
st.title("🤖 Kafadar")
st.markdown("### Yeni Nesil Öğrenci Koçu")

isim = st.text_input("Adın ne?")
sinif = st.selectbox("Sınıfın?", ["4", "5", "6", "7", "8", "Lise"])

st.session_state.ses_aktif = st.toggle("🔊 Sesli Konuşma", value=True)

uploaded_files = st.file_uploader(
    "📄 Çalışma / Sınav Kağıdı Yükle",
    type=["jpg", "png", "jpeg"],
    accept_multiple_files=True
)

# ==========================================
# 6. İNCELEME
# ==========================================
if uploaded_files and st.button("🚀 KAFADAR İNCELE"):
    images = [Image.open(f) for f in uploaded_files]

    hitap = (
        f"{isim}, merhaba! Ben Kafadar 😊"
        if not st.session_state.ilk_karsilama
        else f"Hadi yeni soruya bakalım {isim}!"
    )

    system_prompt = f"""
Senin adın Kafadar.
{sinif}. sınıf öğrencisi {isim} için konuşuyorsun.

GİRİŞ: {hitap}

GÖREVLER:
- Soruları analiz et
- Yazılı kağıtsa 100 üzerinden PUAN VER
- Boşsa çözüm yolunu anlat (cevabı direkt verme)
- Yanlış varsa ipucu ver

TON: Samimi, motive edici, emojili
"""

    content = [{"type": "text", "text": system_prompt}]
    for img in images:
        content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/jpeg;base64,{image_to_base64(compress_image(img))}"
            }
        })

    with st.spinner("🧠 Kafadar düşünüyor..."):
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": content}],
            max_tokens=800
        )

    cevap = response.choices[0].message.content
    st.session_state.messages.append({"role": "assistant", "content": cevap})
    st.session_state.ilk_karsilama = True

    st.markdown(cevap)

    if st.session_state.ses_aktif:
        ses = metni_oku(cevap)
        if ses:
            st.audio(ses, format="audio/mp3")

# ==========================================
# 7. FOOTER
# ==========================================
st.markdown("""
<div class="footer">
© Kafadar – Sinan Sayılır
</div>
""", unsafe_allow_html=True)
