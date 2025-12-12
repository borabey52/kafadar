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
    
    [data-testid="stTextInput"] > div > div { border: none !important; background-color: #f0f2f6; border-radius: 10px; }
    [data-testid="stSelectbox"] > div > div { border: none !important; background-color: #f0f2f6; border-radius: 10px; }
    
    [data-testid="stAudioInput"] { margin-top: 20px; margin-bottom: -20px; }
    .block-container { padding-bottom: 140px; }
    
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #fcfdfd; color: #888; text-align: center;
        font-size: 14px; padding: 10px; border-top: 1px solid #eee; z-index: 900;
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API BAĞLANTISI
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

# --- SESSION STATE BAŞLATMA ---
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_session" not in st.session_state: st.session_state.chat_session = None
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False
if 'ses_aktif' not in st.session_state: st.session_state.ses_aktif = True
# YENİ: İlk karşılaşma kontrolü
if 'ilk_karsilama_yapildi' not in st.session_state: st.session_state.ilk_karsilama_yapildi = False

def yeni_soru_yukle():
    # Sadece mesaj geçmişini temizle, session'ı (tanışıklığı) koru.
    st.session_state.messages = []
    # Chat session'ı sıfırlıyoruz ki yeni resim için temiz sayfa açılsın,
    # ama 'ilk_karsilama_yapildi' değişkenine dokunmuyoruz.
    st.session_state.chat_session = None 
    st.session_state.kamera_acik = False

def tam_sifirlama():
    # Sayfayı yenile ve her şeyi unut (Ad değişirse vb.)
    st.session_state.clear()
    st.rerun()

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
st.markdown("<h3 style='text-align: center; color: #566573; margin-bottom: 20px;'>Yeni Nesil Öğrenci Koçu</h3>", unsafe_allow_html=True)

st.info("👇 Önce kendini tanıt, sonra sorunu yükle:")

col1, col2 = st.columns(2)
with col1:
    isim = st.text_input("Adın ne?", placeholder="Örn: Ali")
with col2:
    sinif = st.selectbox("Sınıfın kaç?", ["4. Sınıf", "5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf", "Lise"])

with st.expander("⚙️ Ses Ayarı", expanded=False):
    st.session_state.ses_aktif = st.toggle("🔊 Kafadar Sesli Konuşsun", value=True)
    if st.button("Tüm Hafızayı Sil (Sıfırla)", type="secondary"):
        tam_sifirlama()

st.markdown("---")

# ==========================================
# 5. BAŞLATMA (AKILLI SELAMLAMA)
# ==========================================
if not st.session_state.chat_session:
    tab1, tab2 = st.tabs(["📂 Dosyadan Yükle (Çoklu)", "📸 Kamerayı Kullan"])
    uploaded_images = []
    
    with tab1:
        dosyalar = st.file_uploader("Kağıtları Seç", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if dosyalar:
            for d in dosyalar: uploaded_images.append(Image.open(d))

    with tab2:
        if st.button("📸 Kamerayı Aç / Kapat", key="cam_toggle"):
            st.session_state.kamera_acik = not st.session_state.kamera_acik
            st.rerun()
        if st.session_state.kamera_acik:
            kamera_img = st.camera_input("Fotoğraf Çek", label_visibility="hidden")
            if kamera_img: uploaded_images.append(Image.open(kamera_img))

    if uploaded_images:
        st.success(f"✅ {len(uploaded_images)} sayfa alındı!")
        cols = st.columns(min(len(uploaded_images), 4))
        for i, img in enumerate(uploaded_images[:4]):
            cols[i].image(img, width=100, caption=f"Sayfa {i+1}")

        if st.button("🚀 KAFADAR İNCELE", type="primary"):
            if not isim:
                st.warning("⚠️ Lütfen adını yaz.")
            else:
                with st.spinner("Kafadar inceliyor..."):
                    try:
                        # --- PROMPT MANTIĞI ---
                        # Eğer ilk kez konuşuyorsa "Merhaba Ali", değilse "Hadi bakalım"
                        hitap_kurali = ""
                        if st.session_state.ilk_karsilama_yapildi == False:
                            hitap_kurali = f"GİRİŞ: '{isim}, merhaba! Ben Kafadar. Hadi şu kağıtlara birlikte bakalım.' şeklinde sıcak bir giriş yap."
                        else:
                            hitap_kurali = f"GİRİŞ: Tekrar merhaba demene gerek yok. Sanki az önce konuşuyormuşuz gibi 'Hemen bu yeni soruya da bakalım {isim}' gibi akıcı bir bağlaçla gir."

                        prompt_content = []
                        system_prompt = f"""
                        Senin adın 'Kafadar'. {sinif} öğrencisi {isim}'in çalışma arkadaşısın.
                        
                        {hitap_kurali}

                        GÖREVLERİN:
                        1. Dersi/konuyu anla.
                        2. (PUANLAMA) 5+ soru veya yazılı kağıdıysa: Doğru/Yanlış analizi yap ve 100 üzerinden not ver.
                        3. Boşsa: Çözüm yolunu anlat (CEVABI DİREKT VERME).
                        4. Çözülmüşse: Kontrol et, yanlışsa ipucu ver.
                        
                        TONU: Samimi, emojili, motive edici.
                        """
                        prompt_content.append(system_prompt)
                        for img in uploaded_images: prompt_content.append(compress_image(img))
                        
                        model = genai.GenerativeModel("gemini-flash-latest")
                        st.session_state.chat_session = model.start_chat(
                            history=[{"role": "user", "parts": prompt_content}]
                        )
                        
                        response = st.session_state.chat_session.send_message("Hadi incele.")
                        st.session_state.messages.append({"role": "assistant", "content": response.text})
                        
                        # Bayrağı işaretle: Artık tanıştık!
                        st.session_state.ilk_karsilama_yapildi = True
                        
                        if st.session_state.ses_aktif:
                            ses = metni_oku(response.text)
                            if ses: st.session_state.messages.append({"role": "audio", "content": ses})
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")

# ==========================================
# 6. SOHBET DÖNGÜSÜ
# ==========================================
else:
    col_reset, col_dummy = st.columns([1, 2])
    with col_reset:
        # Burada "tam_sifirlama" değil "yeni_soru_yukle" çağırıyoruz ki isim hafızada kalsın.
        if st.button("🔄 Başka Soruya Geç", on_click=yeni_soru_yukle, type="secondary"):
            pass

    for message in st.session_state.messages:
        if message["role"] == "audio":
            st.audio(message["content"], format="audio/mp3")
        else:
            with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])

    user_input = None
    audio_input = st.audio_input("🎤 Sesli Sor", label_visibility="collapsed")
    text_input = st.chat_input("Anlamadığın yeri yaz...")

    if text_input: user_input = text_input
    if audio_input:
        with st.spinner("Ses algılanıyor..."):
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
                st.error(f"Hata: {e}")

# ==========================================
# 7. FOOTER
# ==========================================
st.markdown("""
<div class="footer">
    © Kafadar uygulaması <b>Sinan Sayılır</b> tarafından geliştirilmiştir.
</div>
""", unsafe_allow_html=True)
