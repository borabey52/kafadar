import streamlit as st
import google.generativeai as genai
from PIL import Image
import edge_tts
import asyncio
import io
import re
import random
import time

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
    [data-testid="stTextInput"], [data-testid="stSelectbox"] { border: 2px solid #EAECEE; border-radius: 10px; }
    [data-testid="stAudioInput"] { margin-top: 10px; }
    
    /* Footer Tasarımı */
    .footer {
        position: fixed;
        left: 0;
        bottom: 0;
        width: 100%;
        background-color: #fcfdfd;
        color: #888;
        text-align: center;
        font-size: 12px;
        padding: 10px;
        border-top: 1px solid #eee;
        z-index: 99;
    }
    /* Chat input footer'ın altında kalmasın diye padding */
    .block-container {
        padding-bottom: 60px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. ÇOKLU API ANAHTARI YÖNETİMİ
# ==========================================
def get_api_keys():
    keys = [v for k, v in st.secrets.items() if "GOOGLE_API_KEY" in k]
    if not keys and "GOOGLE_API_KEY" in st.secrets:
        keys.append(st.secrets["GOOGLE_API_KEY"])
    return keys

API_KEYS = get_api_keys()

if not API_KEYS:
    st.error("🚨 Hiçbir API Anahtarı bulunamadı! Lütfen secrets ayarlarını kontrol et.")
    st.stop()

# ==========================================
# 3. HAFIZA VE FONKSİYONLAR
# ==========================================
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_session" not in st.session_state: st.session_state.chat_session = None
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False
if 'ses_aktif' not in st.session_state: st.session_state.ses_aktif = True

def sifirla():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False

# --- KELİME DEĞİŞTİRME ROBOTU ---
def metni_temizle_tts_icin(text):
    text = re.sub(r'(?i)cevap', 'yanıt', text)
    text = re.sub(r'(?i)cevab', 'yanıt', text)
    text = text.replace("#", "").replace("*", "")
    temiz_text = re.sub(r"[^a-zA-Z0-9çğıöşüÇĞIÖŞÜ\s\.,!\?\-':;]", "", text)
    return temiz_text.strip()

# --- SESİ YAZIYA ÇEVİR (STT) ---
def sesi_yaziya_cevir(audio_bytes):
    random.shuffle(API_KEYS)
    for key in API_KEYS:
        try:
            genai.configure(api_key=key)
            model = genai.GenerativeModel("gemini-flash-latest")
            response = model.generate_content([
                "Bu ses kaydında söylenenleri kelimesi kelimesine aynen yaz. Ekstra yorum yapma.",
                {"mime_type": "audio/wav", "data": audio_bytes}
            ])
            return response.text.strip()
        except:
            continue
    return None

# --- YAZIYI SESE ÇEVİR (EDGE TTS - KADIN SESİ) ---
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
        temiz_metin = metni_temizle_tts_icin(metin)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ses_dosyasi = loop.run_until_complete(seslendir_async(temiz_metin))
        return ses_dosyasi
    except Exception as e:
        return None

# ==========================================
# 4. ARAYÜZ BAŞLANGICI
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
# 5. FOTOĞRAF VE BAŞLATMA MANTIĞI
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
                    # Prompt Hazırlığı
                    system_prompt = f"""
                    Senin adın 'Kafadar'. Sen {sinif} öğrencisi {isim}'in çalışma arkadaşısın.
                    GÖREVLERİN:
                    1. Görüntüdeki dersi/konuyu anla.
                    2. Soru boşsa: Çözüm yolunu anlat ama CEVABI DİREKT VERME.
                    3. Soru çözülmüşse: Kontrol et, yanlışsa ipucu ver.
                    ODAK KURALI: Ders dışı sohbete girme.
                    TONU: Samimi, emojili, motive edici. {isim} diye hitap et.
                    """
                    
                    # API Key Rotasyonu ile Bağlantı Denemesi
                    basarili = False
                    random.shuffle(API_KEYS)
                    
                    for key in API_KEYS:
                        try:
                            genai.configure(api_key=key)
                            model = genai.GenerativeModel("gemini-flash-latest")
                            st.session_state.chat_session = model.start_chat(
                                history=[{"role": "user", "parts": [system_prompt, uploaded_image]}]
                            )
                            response = st.session_state.chat_session.send_message("Hadi incele.")
                            st.session_state.messages.append({"role": "assistant", "content": response.text})
                            
                            if st.session_state.ses_aktif:
                                ses = metni_oku(response.text)
                                if ses: st.session_state.messages.append({"role": "audio", "content": ses})
                            
                            basarili = True
                            break 
                        except:
                            continue
                    
                    if not basarili:
                        st.error("⚠️ Sistem yoğun, lütfen tekrar dene.")
                    else:
                        st.rerun()

# ==========================================
# 6. SOHBET DÖNGÜSÜ
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
            except:
                st.error("Bağlantı hatası.")

# ==========================================
# 7. FOOTER (İMZA)
# ==========================================
st.markdown("""
<div style="text-align: center; margin-top: 50px; padding: 20px; color: #999; font-size: 12px;">
    © Kafadar uygulaması <b>Sinan Sayılır</b> tarafından geliştirilmiştir.
</div>
""", unsafe_allow_html=True)
