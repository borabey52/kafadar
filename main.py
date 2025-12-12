import streamlit as st
import google.generativeai as genai
from PIL import Image
import edge_tts
import asyncio
import io
import re

# ==========================================
# 1. AYARLAR & TASARIM
# ==========================================
st.set_page_config(page_title="Kafadar", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fcfdfd; }
    h1 { color: #2E86C1; font-family: 'Comic Sans MS', sans-serif; text-align: center; }
    
    .stChatMessage { border-radius: 10px; }
    
    .stButton>button {
        background-color: #F4D03F; color: #17202A; border-radius: 15px;
        font-weight: bold; border: none; padding: 12px 24px; transition: all 0.3s;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #F1C40F; transform: scale(1.02); box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    [data-testid="stTextInput"], [data-testid="stSelectbox"] {
        border: 2px solid #EAECEE; border-radius: 10px;
    }
    [data-testid="stAudioInput"] { margin-top: 10px; }
    </style>
""", unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("🔑 API Anahtarı Eksik!")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 2. HAFIZA VE FONKSİYONLAR
# ==========================================
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_session" not in st.session_state: st.session_state.chat_session = None
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False
if 'ses_aktif' not in st.session_state: st.session_state.ses_aktif = True

def sifirla():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False

# --- GELİŞMİŞ TEMİZLİK ROBOTU ---
def metni_temizle_tts_icin(text):
    # 1. Telaffuz Düzeltmeleri (ÖZEL AYAR)
    # "Cevap" kelimesini "Yanıt" ile değiştiriyoruz ki düzgün okusun.
    # "Cevab" kökünü de ekledik ki "Cevabı" -> "Yanıtı" olabilsin.
    text = text.replace("Cevap", "Yanıt").replace("cevap", "yanıt")
    text = text.replace("Cevab", "Yanıt").replace("cevab", "yanıt")
    
    # 2. Markdown İşaretlerini Temizle
    text = text.replace("#", "").replace("*", "")
    
    # 3. Emoji ve Garip Karakterleri Sil
    # Sadece harfler, rakamlar ve temel noktalama işaretleri kalır.
    temiz_text = re.sub(r"[^a-zA-Z0-9çğıöşüÇĞIÖŞÜ\s\.,!\?\-':;]", "", text)
    
    return temiz_text.strip()

# --- SESİ YAZIYA ÇEVİR (STT) ---
def sesi_yaziya_cevir(audio_bytes):
    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content([
            "Bu ses kaydında söylenenleri kelimesi kelimesine aynen yaz. Ekstra yorum yapma.",
            {"mime_type": "audio/wav", "data": audio_bytes}
        ])
        return response.text.strip()
    except Exception as e:
        return None

# --- YAZIYI SESE ÇEVİR (EDGE TTS - Kadın Sesi) ---
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
        # Önce metni temizle (Cevap -> Yanıt değişimi burada yapılıyor)
        temiz_metin = metni_temizle_tts_icin(metin)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ses_dosyasi = loop.run_until_complete(seslendir_async(temiz_metin))
        return ses_dosyasi
    except Exception as e:
        st.error(f"Ses hatası: {e}")
        return None

# ==========================================
# 3. ARAYÜZ
# ==========================================
st.title("🤖 Kafadar")
st.markdown("<h3 style='text-align: center; color: #566573; margin-bottom: 20px;'>Senin Zeki Çalışma Arkadaşın</h3>", unsafe_allow_html=True)

st.info("👇 Önce kendini tanıt, sonra sorunu yükle:")

col1, col2 = st.columns(2)
with col1:
    isim = st.text_input("Adın ne?", placeholder="Örn: Ali")
with col2:
    sinif = st.selectbox("Sınıfın kaç?", ["4. Sınıf", "5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf", "Lise"])

with st.expander("⚙️ Ses Ayarı", expanded=False):
    st.session_state.ses_aktif = st.toggle("🔊 Kafadar Sesli Konuşsun", value=True)

st.markdown("---")

# ==========================================
# 4. FOTOĞRAF VE BAŞLATMA
# ==========================================
if not st.session_state.chat_session:
    tab1, tab2 = st.tabs(["📂 Dosyadan Yükle", "📸 Kamerayı Kullan"])
    uploaded_image = None
    
    with tab1:
        dosya = st.file_uploader("Galeriden Seç", type=["jpg", "png", "jpeg"])
        if dosya: uploaded_image = Image.open(dosya)

    with tab2:
        if st.button("📸 Kamerayı Aç / Kapat", key="cam_toggle"):
            st.session_state.kamera_acik = not st.session_state.kamera_acik
            st.rerun()

        if st.session_state.kamera_acik:
            kamera_img = st.camera_input("Fotoğraf Çek", label_visibility="hidden")
            if kamera_img: uploaded_image = Image.open(kamera_img)

    if uploaded_image:
        st.success("✅ Resim alındı! Başlatabilirsin.")
        st.image(uploaded_image, width=200, caption="Seçilen Soru")
        
        if st.button("🚀 KAFADAR İNCELE VE SOHBETİ BAŞLAT", type="primary"):
            if not isim:
                st.warning("⚠️ Lütfen adını yaz.")
            else:
                with st.spinner("Kafadar hazırlanıyor..."):
                    model = genai.GenerativeModel("gemini-flash-latest")
                    
                    system_prompt = f"""
                    Senin adın 'Kafadar'. Sen {sinif} öğrencisi {isim}'in çalışma arkadaşısın.
                    
                    GÖREVLERİN:
                    1. Görüntüdeki dersi/konuyu anla.
                    2. Soru boşsa: Çözüm yolunu anlat ama CEVABI DİREKT VERME.
                    3. Soru çözülmüşse: Kontrol et, yanlışsa ipucu ver.
                    
                    ODAK KURALI:
                    - Ders dışı sohbete girme, nazikçe derse döndür.
                    
                    TONU:
                    - Samimi, emojili, motive edici.
                    - {isim} diye hitap et.
                    """
                    
                    st.session_state.chat_session = model.start_chat(
                        history=[{"role": "user", "parts": [system_prompt, uploaded_image]}]
                    )
                    
                    response = st.session_state.chat_session.send_message("Hadi incele.")
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    
                    if st.session_state.ses_aktif:
                        ses = metni_oku(response.text)
                        if ses: st.session_state.messages.append({"role": "audio", "content": ses})
                    
                    st.rerun()

# ==========================================
# 5. SOHBET DÖNGÜSÜ
# ==========================================
else:
    col_reset, col_dummy = st.columns([1, 2])
    with col_reset:
        if st.button("🔄 Yeni Soru Sor", on_click=sifirla, type="secondary"):
            pass

    for message in st.session_state.messages:
        if message["role"] == "audio":
            st.audio(message["content"], format="audio/mp3")
        else:
            with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])

    user_input = None
    
    text_input = st.chat_input("Anlamadığın yeri yaz...")
    if text_input: user_input = text_input

    audio_input = st.audio_input("🎤 Sesli Sor", label_visibility="collapsed")
    if audio_input:
        with st.spinner("Sesin yazıya çevriliyor..."):
            audio_bytes = audio_input.read()
            transcribed_text = sesi_yaziya_cevir(audio_bytes)
            if transcribed_text: user_input = transcribed_text
            else: st.error("Ses anlaşılamadı.")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        with st.spinner("Kafadar düşünüyor..."):
            try:
                response = st.session_state.chat_session.send_message(user_input)
                
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(response.text)
                
                if st.session_state.ses_aktif:
                    ses_verisi = metni_oku(response.text)
                    if ses_verisi:
                        st.audio(ses_verisi, format="audio/mp3", autoplay=True)
                        st.session_state.messages.append({"role": "audio", "content": ses_verisi})
                        
            except Exception as e:
                st.error("Bağlantı hatası.")
