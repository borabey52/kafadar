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
    .block-container { padding-bottom: 150px; }
    
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #fcfdfd; color: #888; text-align: center;
        font-size: 14px; padding: 10px; border-top: 1px solid #eee; z-index: 900;
    }
    
    /* Pekiştirme Alanı Stili */
    .pekistirme-box {
        background-color: #e8f6f3;
        border: 2px dashed #1abc9c;
        border-radius: 15px;
        padding: 20px;
        margin-top: 20px;
        margin-bottom: 20px;
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

if "messages" not in st.session_state: st.session_state.messages = []
if "chat_session" not in st.session_state: st.session_state.chat_session = None
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False
if 'ses_aktif' not in st.session_state: st.session_state.ses_aktif = True
if 'ilk_karsilama_yapildi' not in st.session_state: st.session_state.ilk_karsilama_yapildi = False
# YENİ: Pratik sorusu hafızası
if 'yeni_pratik_soru' not in st.session_state: st.session_state.yeni_pratik_soru = None

def yeni_soru_yukle():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False
    st.session_state.yeni_pratik_soru = None # Yeni soru yüklenince pratik sorusunu sıfırla

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
                        hitap_kurali = ""
                        if st.session_state.ilk_karsilama_yapildi == False:
                            hitap_kurali = f"GİRİŞ: '{isim}, merhaba! Ben Kafadar. Hadi şu kağıtlara birlikte bakalım.' şeklinde sıcak bir giriş yap."
                        else:
                            hitap_kurali = f"GİRİŞ: Tekrar merhaba demene gerek yok. Sanki az önce konuşuyormuşuz gibi devam et."

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
                        st.session_state.ilk_karsilama_yapildi = True
                        
                        if st.session_state.ses_aktif:
                            ses = metni_oku(response.text)
                            if ses: st.session_state.messages.append({"role": "audio", "content": ses})
                        
                        st.rerun()
                    except Exception as e:
                        st.error(f"Hata: {e}")

# ==========================================
# 6. SOHBET VE PEKİŞTİRME ALANI
# ==========================================
else:
    col_reset, col_dummy = st.columns([1, 2])
    with col_reset:
        if st.button("🔄 Başka Soruya Geç", on_click=yeni_soru_yukle, type="secondary"):
            pass

    # SOHBET GEÇMİŞİNİ GÖSTER
    for message in st.session_state.messages:
        if message["role"] == "audio":
            st.audio(message["content"], format="audio/mp3")
        else:
            with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])

    # ---------------------------------------------------------
    # YENİ ÖZELLİK: BENZER SORU ÜRETME (PEKİŞTİRME)
    # ---------------------------------------------------------
    # Sadece sohbet varsa ve en son mesaj asistandansa göster
    if st.session_state.messages and st.session_state.messages[-1]["role"] in ["assistant", "audio"]:
        
        st.markdown("<br>", unsafe_allow_html=True) # Biraz boşluk

        # Eğer henüz soru üretilmediyse butonu göster
        if not st.session_state.yeni_pratik_soru:
            if st.button("💪 Meydan Okuyorum! Benzer Soru Sor", type="primary", use_container_width=True):
                with st.spinner("Kafadar senin için özel bir soru hazırlıyor..."):
                    try:
                        pratik_prompt = """
                        Şimdi öğretmen sensin! Az önce konuştuğumuz/çözdüğümüz soruya 
                        MATEMATİKSEL ve MANTIKSAL olarak benzer, rakamları farklı YENİ BİR SORU yaz.
                        
                        KURALLAR:
                        1. Cevabı hemen verme.
                        2. Formatı kesinlikle şöyle yap:
                           **SORU:** [Soru Metni]
                           A) ... B) ... C) ... D) ...
                           **CEVAP_GIZLI:** [Doğru Cevap ve Çözümü]
                        """
                        response_pratik = st.session_state.chat_session.send_message(pratik_prompt)
                        st.session_state.yeni_pratik_soru = response_pratik.text
                        st.rerun()
                    except:
                        st.error("Soru hazırlanamadı.")
        
        # Soru üretildiyse göster
        if st.session_state.yeni_pratik_soru:
            try:
                # Soruyu ve cevabı ayır
                parts = st.session_state.yeni_pratik_soru.split("**CEVAP_GIZLI:**")
                soru_kismi = parts[0].replace("**SORU:**", "").strip()
                cevap_kismi = parts[1].strip() if len(parts) > 1 else "Cevap yüklenemedi."
                
                st.markdown(f"""
                <div class="pekistirme-box">
                    <h4 style="color: #16a085;">🎯 Sıra Sende {isim}!</h4>
                    <p style="font-size: 1.1em;">{soru_kismi}</p>
                </div>
                """, unsafe_allow_html=True)
                
                with st.expander("👀 Cevabı ve Çözümü Gör"):
                    st.info(cevap_kismi)
                    if st.button("Tamamdır, bu konuyu kaptım! 😎", on_click=lambda: st.session_state.update(yeni_pratik_soru=None)):
                        pass

            except:
                st.warning("Format hatası oluştu ama işte soru:")
                st.write(st.session_state.yeni_pratik_soru)

    # ---------------------------------------------------------
    # INPUT ALANLARI
    # ---------------------------------------------------------
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
