import streamlit as st
import google.generativeai as genai
from PIL import Image
import edge_tts
import asyncio
import io
import re

# ==========================================
# 1. AYARLAR & CSS SİHİRBAZLIĞI 🎨
# ==========================================
st.set_page_config(page_title="Kafadar", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fcfdfd; }
    h1 { color: #2E86C1; font-family: 'Comic Sans MS', sans-serif; text-align: center; }
    
    /* Mesaj Baloncukları */
    .stChatMessage { border-radius: 15px; }
    
    /* --- MİKROFONU AŞAĞIYA SABİTLEME (FLOAT) --- */
    /* Ses giriş widget'ını yakala ve aşağıya çivile */
    [data-testid="stAudioInput"] {
        position: fixed;
        bottom: 80px; /* Yazı kutusunun hemen üstü */
        left: 50%;
        transform: translateX(-50%);
        width: 100%;
        max-width: 700px; /* Mobilde taşmasın */
        z-index: 999;
        background-color: rgba(252, 253, 253, 0.9); /* Arka planı hafif şeffaf yap */
        padding: 5px 20px;
        border-radius: 20px 20px 0 0;
        backdrop-filter: blur(5px);
    }
    
    /* Mesajların mikrofonun altında kalmaması için alt boşluk */
    .block-container {
        padding-bottom: 180px !important;
    }
    
    /* Buton Tasarımı */
    .stButton>button {
        background-color: #F4D03F; color: #17202A; border-radius: 15px;
        font-weight: bold; border: none; padding: 12px 24px; transition: all 0.3s;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #F1C40F; transform: scale(1.02); box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Footer (Artık sayfa akışında en sonda, ezilmez) */
    .footer {
        text-align: center; color: #888; font-size: 12px; margin-top: 50px;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API ANAHTARI
# ==========================================
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("🚨 API Anahtarı Bulunamadı!")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 3. FONKSİYONLAR
# ==========================================

def compress_image(image):
    img = image.copy()
    if img.width > 800 or img.height > 800:
        img.thumbnail((800, 800))
    return img

if "messages" not in st.session_state: st.session_state.messages = []
if "chat_session" not in st.session_state: st.session_state.chat_session = None
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False
if 'ses_aktif' not in st.session_state: st.session_state.ses_aktif = True

def sifirla():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False

def metni_temizle_tts_icin(text):
    text = re.sub(r'(?i)cevap', 'yanıt', text)
    text = re.sub(r'(?i)cevab', 'yanıt', text)
    text = text.replace("#", "").replace("*", "")
    temiz_text = re.sub(r"[^a-zA-Z0-9çğıöşüÇĞIÖŞÜ\s\.,!\?\-':;]", "", text)
    return temiz_text.strip()

def sesi_yaziya_cevir(audio_bytes):
    try:
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content([
            "Söylenenleri aynen yaz.",
            {"mime_type": "audio/wav", "data": audio_bytes}
        ])
        return response.text.strip()
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
        temiz_metin = metni_temizle_tts_icin(metin)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        ses_dosyasi = loop.run_until_complete(seslendir_async(temiz_metin))
        return ses_dosyasi
    except:
        return None

# ==========================================
# 4. ARAYÜZ
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
# 5. BAŞLATMA
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
        st.success("✅ Resim alındı!")
        st.image(uploaded_image, width=200, caption="Seçilen Soru")
        
        if st.button("🚀 KAFADAR İNCELE VE SOHBETİ BAŞLAT", type="primary"):
            if not isim:
                st.warning("⚠️ Lütfen adını yaz.")
            else:
                with st.spinner("Kafadar hazırlanıyor..."):
                    try:
                        compressed_img = compress_image(uploaded_image)
                        system_prompt = f"""
                        Senin adın 'Kafadar'. Sen {sinif} öğrencisi {isim}'in çalışma arkadaşısın.
                        GÖREVLERİN:
                        1. Görüntüdeki dersi/konuyu anla.
                        2. Soru boşsa: Çözüm yolunu anlat ama CEVABI DİREKT VERME.
                        3. Soru çözülmüşse: Kontrol et, yanlışsa ipucu ver.
                        ODAK KURALI: Ders dışı sohbete girme.
                        TONU: Samimi, emojili, motive edici. {isim} diye hitap et.
                        """
                        model = genai.GenerativeModel("gemini-flash-latest")
                        st.session_state.chat_session = model.start_chat(
                            history=[{"role": "user", "parts": [system_prompt, compressed_img]}]
                        )
                        response = st.session_state.chat_session.send_message("Hadi incele.")
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                        if st.session_state.ses_aktif:
                            ses = metni_oku(response.text)
                            if ses: st.session_state.messages.append({"role": "audio", "content": ses})
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")

# ==========================================
# 6. SOHBET & INPUT ALANI
# ==========================================
else:
    # 1. Sohbet Geçmişi
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

    # 2. FOOTER (Sohbetin sonuna eklenir, kaybolmaz)
    st.markdown("""
    <div class="footer">
        © Kafadar uygulaması <b>Sinan Sayılır</b> tarafından geliştirilmiştir.
    </div>
    """, unsafe_allow_html=True)

    # 3. GİRİŞ ALANLARI (En alta sabitlenir)
    user_input = None
    
    # --- MİKROFONU BURAYA KOYUYORUZ (CSS İLE EN ALTA GİDECEK) ---
    audio_input = st.audio_input("🎤 Sesli Sor", label_visibility="collapsed")
    
    # --- YAZI KUTUSU (STREAMLIT BUNU OTOMATİK EN ALTA KOYAR) ---
    text_input = st.chat_input("Anlamadığın yeri yaz...")
    
    # Hangisi doluysa onu al
    if text_input: user_input = text_input
    if audio_input:
        with st.spinner("Ses algılanıyor..."):
            audio_bytes = audio_input.read()
            transcribed_text = sesi_yaziya_cevir(audio_bytes)
            if transcribed_text: user_input = transcribed_text
            else: st.error("Ses anlaşılamadı.")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        st.rerun() # Sayfayı yenile ki mesaj hemen görünsün

    # Cevap varsa işle (Rerun sonrası çalışır)
    if st.session_state.messages and st.session_state.messages[-1]["role"] == "user":
        with st.spinner("Kafadar düşünüyor..."):
            try:
                last_user_msg = st.session_state.messages[-1]["content"]
                response = st.session_state.chat_session.send_message(last_user_msg)
                
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                
                if st.session_state.ses_aktif:
                    ses_verisi = metni_oku(response.text)
                    if ses_verisi:
                        st.session_state.messages.append({"role": "audio", "content": ses_verisi})
                
                st.rerun() # Tekrar yenile ki cevap görünsün
            except Exception as e:
                st.error(f"Bağlantı hatası: {e}")
