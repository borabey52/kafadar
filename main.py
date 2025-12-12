import streamlit as st
import google.generativeai as genai
from PIL import Image
from gtts import gTTS
import io

# ==========================================
# 1. AYARLAR & TASARIM
# ==========================================
st.set_page_config(page_title="Kafadar", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fcfdfd; }
    h1 { color: #2E86C1; font-family: 'Comic Sans MS', sans-serif; text-align: center; }
    
    /* Mesaj Baloncukları */
    .stChatMessage { border-radius: 10px; }
    
    /* Buton Tasarımı */
    .stButton>button {
        background-color: #F4D03F; color: #17202A; border-radius: 15px;
        font-weight: bold; border: none; padding: 12px 24px; transition: all 0.3s;
        width: 100%;
    }
    .stButton>button:hover {
        background-color: #F1C40F; transform: scale(1.02); box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Input alanlarını belirginleştir */
    [data-testid="stTextInput"], [data-testid="stSelectbox"] {
        border: 2px solid #EAECEE; border-radius: 10px;
    }
    
    /* Ses Kaydedici Düzeni */
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
if 'ses_aktif' not in st.session_state: st.session_state.ses_aktif = True # Varsayılan olarak ses açık

def sifirla():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False

# --- SESİ YAZIYA ÇEVİR (STT) ---
def sesi_yaziya_cevir(audio_bytes):
    try:
        # MODEL GÜNCELLENDİ: gemini-flash-latest
        model = genai.GenerativeModel("gemini-flash-latest")
        response = model.generate_content([
            "Bu ses kaydında söylenenleri kelimesi kelimesine aynen yaz. Ekstra yorum yapma.",
            {"mime_type": "audio/wav", "data": audio_bytes}
        ])
        return response.text.strip()
    except Exception as e:
        return None

# --- YAZIYI SESE ÇEVİR (TTS) ---
def metni_oku(metin):
    try:
        tts = gTTS(text=metin, lang='tr')
        ses_dosyasi = io.BytesIO()
        tts.write_to_fp(ses_dosyasi)
        ses_dosyasi.seek(0)
        return ses_dosyasi
    except:
        return None

# ==========================================
# 3. ARAYÜZ - ÜST KISIM
# ==========================================
st.title("🤖 Kafadar")
st.markdown("<h3 style='text-align: center; color: #566573; margin-bottom: 20px;'>Senin Zeki Çalışma Arkadaşın</h3>", unsafe_allow_html=True)

st.info("👇 Önce kendini tanıt, sonra sorunu yükle:")

col_isim, col_sinif = st.columns(2)
with col_isim:
    isim = st.text_input("Adın ne?", placeholder="Örn: Ali")
with col_sinif:
    sinif = st.selectbox("Sınıfın kaç?", ["4. Sınıf", "5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf", "Lise"])

# Ses açma kapama ayarı
st.session_state.ses_aktif = st.toggle("🔊 Kafadar Sesli Yanıt Versin", value=True)

st.markdown("---")

# ==========================================
# 4. FOTOĞRAF YÜKLEME VE BAŞLATMA
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
        st.success("✅ Resim alındı! Şimdi başlatabilirsin.")
        st.image(uploaded_image, width=200, caption="Seçilen Soru")
        
        if st.button("🚀 KAFADAR İNCELE VE SOHBETİ BAŞLAT", type="primary"):
            if not isim:
                st.warning("⚠️ Lütfen yukarıya adını yazar mısın?")
            else:
                with st.spinner("Kafadar hazırlanıyor..."):
                    # MODEL GÜNCELLENDİ: gemini-flash-latest
                    model = genai.GenerativeModel("gemini-flash-latest")
                    
                    system_prompt = f"""
                    Senin adın 'Kafadar'. Sen {sinif} öğrencisi {isim}'in çalışma arkadaşısın.
                    
                    GÖREVLERİN:
                    1. Görüntüdeki dersi/konuyu anla.
                    2. Soru boşsa: Çözüm yolunu anlat ama CEVABI DİREKT VERME.
                    3. Soru çözülmüşse: Kontrol et, yanlışsa ipucu ver.
                    
                    ODAK KURALI:
                    - Ders dışı sohbete (oyun, maç vb.) girme, nazikçe derse döndür.
                    
                    TONU:
                    - Samimi, emojili, motive edici.
                    - {isim} diye hitap et.
                    """
                    
                    st.session_state.chat_session = model.start_chat(
                        history=[{"role": "user", "parts": [system_prompt, uploaded_image]}]
                    )
                    
                    response = st.session_state.chat_session.send_message("Hadi incele.")
                    
                    # Mesajı kaydet
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    
                    # SESLENDİRME (Eğer aktifse)
                    if st.session_state.ses_aktif:
                        ses = metni_oku(response.text.replace("*", "")) # Yıldızları temizle ki okurken takılmasın
                        if ses:
                            st.session_state.messages.append({"role": "audio", "content": ses})
                    
                    st.rerun()

# ==========================================
# 5. SOHBET EKRANI (SES & METİN)
# ==========================================
else:
    col_reset, col_dummy = st.columns([1, 2])
    with col_reset:
        if st.button("🔄 Yeni Soru Sor", on_click=sifirla, type="secondary"):
            pass

    # Eski mesajları göster
    for message in st.session_state.messages:
        if message["role"] == "audio":
            # Ses dosyalarını oynatıcı olarak göster
            st.audio(message["content"], format="audio/mp3")
        else:
            # Metin mesajlarını balon olarak göster
            with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])

    # KULLANICI GİRİŞİ (Yazı veya Ses)
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

    # CEVAP ÜRETME
    if user_input:
        # Kullanıcı mesajını ekle
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        with st.spinner("Kafadar düşünüyor..."):
            try:
                response = st.session_state.chat_session.send_message(user_input)
                
                # Metin cevabını ekle
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(response.text)
                
                # Sesli cevabı ekle (Otomatik Oynat)
                if st.session_state.ses_aktif:
                    # Okurken markdown işaretlerini (yıldızları vs) temizlemesi için basit temizlik
                    temiz_metin = response.text.replace("*", "").replace("#", "")
                    ses_verisi = metni_oku(temiz_metin)
                    if ses_verisi:
                        st.audio(ses_verisi, format="audio/mp3", autoplay=True)
                        st.session_state.messages.append({"role": "audio", "content": ses_verisi})
                        
            except Exception as e:
                st.error("Bağlantı hatası. Lütfen sayfayı yenile.")
