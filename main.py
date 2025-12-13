import streamlit as st
import google.generativeai as genai
from PIL import Image
import edge_tts
import asyncio
import io
import re
import base64

# ==========================================
# 1. AYARLAR & TASARIM (CSS)
# ==========================================
st.set_page_config(page_title="Zekai", page_icon="🧠", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fcfdfd; }
    
    /* --- ÜST BOŞLUĞU KALDIRMA --- */
    /* Sayfanın en tepesindeki varsayılan boşluğu 6rem'den 2rem'e indirdik */
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 200px; /* Alt kısım mikrofon için açık kalsın */
    }
    
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
    
    /* Input Alanları Temizliği */
    [data-testid="stTextInput"] > div > div { border: none !important; background-color: #f0f2f6; border-radius: 10px; }
    [data-testid="stSelectbox"] > div > div { border: none !important; background-color: #f0f2f6; border-radius: 10px; }
    
    /* Mikrofon Sabitleme */
    [data-testid="stAudioInput"] {
        position: fixed; bottom: 80px; left: 50%; transform: translateX(-50%);
        width: 100%; max-width: 700px; z-index: 999;
        background-color: rgba(252, 253, 253, 0.9);
        padding: 5px 20px; border-radius: 20px 20px 0 0; backdrop-filter: blur(5px);
    }
    
    .footer {
        text-align: center; color: #888; font-size: 12px; margin-top: 50px; padding-bottom: 20px;
    }
    
    /* Pekiştirme & Test Kutuları */
    .pekistirme-box {
        background-color: #e8f6f3; border: 2px dashed #1abc9c; border-radius: 15px; padding: 20px; margin-top: 20px; margin-bottom: 20px;
    }
    .test-box {
        background-color: #fef9e7; border: 2px solid #f1c40f; border-radius: 15px; padding: 20px; margin-top: 20px;
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

def get_base64_image(image_path):
    """Resmi HTML içinde kullanmak için Base64 formatına çevirir."""
    with open(image_path, "rb") as img_file:
        return base64.b64encode(img_file.read()).decode()

# State Tanımları
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_session" not in st.session_state: st.session_state.chat_session = None
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False
if 'ses_aktif' not in st.session_state: st.session_state.ses_aktif = True
if 'ilk_karsilama_yapildi' not in st.session_state: st.session_state.ilk_karsilama_yapildi = False
if 'yeni_pratik_soru' not in st.session_state: st.session_state.yeni_pratik_soru = None
if 'hazirlanan_test' not in st.session_state: st.session_state.hazirlanan_test = None

def yeni_soru_yukle():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False
    st.session_state.yeni_pratik_soru = None
    st.session_state.hazirlanan_test = None

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
# 4. ARAYÜZ (GİRİŞ) - LOGO & SLOGAN
# ==========================================

# Logoyu HTML/CSS ile tam ortaya koyuyoruz (Base64)
try:
    img_base64 = get_base64_image("zekai_logo.png")
    st.markdown(
        f"""
        <div style="text-align: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{img_base64}" width="400" style="max-width: 100%;">
            <h3 style="color: #566573; margin-top: 10px; font-family: 'Comic Sans MS', sans-serif;">      Yeni Nesil Öğrenci Koçu</h3>
        </div>
        """,
        unsafe_allow_html=True
    )
except:
    # Eğer resim dosyası yoksa metin olarak göster (Fallback)
    st.title("🧠 Zekai")
    st.markdown("<h3 style='text-align: center; color: #566573;'>Yeni Nesil Zeki Öğrenci Koçu</h3>", unsafe_allow_html=True)

st.info("👇 Önce kendini tanıt, sonra sorunu yükle:")

col1, col2 = st.columns(2)
with col1:
    isim = st.text_input("Adın ne?", placeholder="Örn: Ali")
with col2:
    sinif = st.selectbox("Sınıfın kaç?", ["4. Sınıf", "5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf", "Lise"])

with st.expander("⚙️ Ses Ayarı", expanded=False):
    st.session_state.ses_aktif = st.toggle("🔊 Zekai Sesli Konuşsun", value=True)

st.markdown("---")

# ==========================================
# 5. DOSYA YÜKLEME VE BAŞLATMA
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

        if st.button("🚀 ZEKAİ İNCELE", type="primary"):
            if not isim:
                st.warning("⚠️ Lütfen adını yaz.")
            else:
                with st.spinner("Zekai inceliyor..."):
                    try:
                        hitap_kurali = ""
                        if st.session_state.ilk_karsilama_yapildi == False:
                            hitap_kurali = f"GİRİŞ: '{isim}, merhaba! Ben Zekai. Hadi şu kağıtlara birlikte bakalım.' şeklinde sıcak bir giriş yap."
                        else:
                            hitap_kurali = f"GİRİŞ: Tekrar merhaba demene gerek yok. Sanki az önce konuşuyormuşuz gibi devam et."

                        prompt_content = []
                        system_prompt = f"""
                        Senin adın 'Zekai'. {sinif} öğrencisi {isim}'in çalışma arkadaşısın.
                        {hitap_kurali}
                        GÖREVLERİN:
                        1. Dersi/konuyu anla.
                        2. (PUANLAMA) 5+ soru veya yazılı kağıdıysa: Doğru/Yanlış analizi yap ve 100 üzerinden motive edici bir not ver.
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
# 6. SOHBET VE PRATİK ALANI
# ==========================================
else:
    col_reset, col_dummy = st.columns([1, 2])
    with col_reset:
        if st.button("🔄 Başka Soruya Geç", on_click=yeni_soru_yukle, type="secondary"):
            pass

    for message in st.session_state.messages:
        if message["role"] == "audio":
            st.audio(message["content"], format="audio/mp3")
        else:
            with st.chat_message(message["role"], avatar="🧠" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])

    # --- EKSTRA ÇALIŞMA ALANI ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] in ["assistant", "audio"]:
        st.markdown("<br>", unsafe_allow_html=True)
        
        if not st.session_state.yeni_pratik_soru and not st.session_state.hazirlanan_test:
            
            st.caption("🚀 Kendini Denemek İster misin?")
            soru_sayisi = st.radio("Test Uzunluğu:", [5, 10], horizontal=True, index=0)
            col_meydan, col_test = st.columns(2)
            
            # 1. BUTON: MEYDAN OKU
            with col_meydan:
                if st.button("🥊 Meydan Oku (Tek Soru)", use_container_width=True):
                    with st.spinner("Zekai zorlu bir soru hazırlıyor..."):
                        try:
                            pratik_prompt = """
                            Öğretmen sensin! Konuya benzer, rakamları farklı YENİ BİR SORU yaz.
                            Format:
                            **SORU:** [Soru]
                            A) ...
                            B) ...
                            C) ...
                            D) ...
                            **CEVAP_GIZLI:** [Cevap ve Çözüm]
                            """
                            response = st.session_state.chat_session.send_message(pratik_prompt)
                            st.session_state.yeni_pratik_soru = response.text
                            st.rerun()
                        except:
                            st.error("Hata oluştu.")

            # 2. BUTON: TEST HAZIRLA
            with col_test:
                if st.button(f"📝 {soru_sayisi} Soruluk Test", use_container_width=True):
                    with st.spinner(f"Zekai {soru_sayisi} soruluk testi hazırlıyor..."):
                        try:
                            test_prompt = f"""
                            Konuyla ilgili {soru_sayisi} adet çoktan seçmeli sorudan oluşan bir tarama testi hazırla.
                            KURALLAR:
                            1. Soruları art arda numaralandır (1., 2. gibi).
                            2. Cevap anahtarını testin EN SONUNDA ver.
                            3. Format:
                               **1. Soru:** ...
                               A)... B)...
                               ---
                               **CEVAP ANAHTARI:**
                               1-A, 2-C ...
                            """
                            response = st.session_state.chat_session.send_message(test_prompt)
                            st.session_state.hazirlanan_test = response.text
                            st.rerun()
                        except:
                            st.error("Test hazırlanamadı.")

        # --- GÖRÜNÜM: TEK SORU ---
        if st.session_state.yeni_pratik_soru:
            try:
                parts = st.session_state.yeni_pratik_soru.split("**CEVAP_GIZLI:**")
                soru = parts[0].replace("**SORU:**", "").strip()
                cevap = parts[1].strip() if len(parts) > 1 else "Cevap yok."
                
                st.markdown(f'<div class="pekistirme-box"><h4>🥊 Meydan Okuma Sorusu</h4>{soru}</div>', unsafe_allow_html=True)
                with st.expander("👀 Cevabı Gör"):
                    st.info(cevap)
                    if st.button("Kapat"):
                        st.session_state.yeni_pratik_soru = None
                        st.rerun()
            except:
                st.write(st.session_state.yeni_pratik_soru)

        # --- GÖRÜNÜM: ÇOKLU TEST ---
        if st.session_state.hazirlanan_test:
            st.markdown(f'<div class="test-box"><h4>📝 Konu Tarama Testi</h4>', unsafe_allow_html=True)
            try:
                if "CEVAP ANAHTARI" in st.session_state.hazirlanan_test:
                    bolumler = st.session_state.hazirlanan_test.split("CEVAP ANAHTARI")
                    sorular = bolumler[0]
                    anahtar = bolumler[1]
                else:
                    sorular = st.session_state.hazirlanan_test
                    anahtar = "Metnin içinde ara."
                
                st.markdown(sorular)
                st.markdown('</div>', unsafe_allow_html=True)
                
                with st.expander("🔑 Cevap Anahtarını Göster"):
                    st.success(f"**CEVAP ANAHTARI:** {anahtar}")
                    if st.button("Testi Bitir"):
                        st.session_state.hazirlanan_test = None
                        st.rerun()
            except:
                st.write(st.session_state.hazirlanan_test)

    # --- FOOTER & INPUT ---
    st.markdown("""<div class="footer">© Zekai uygulaması <b>Sinan Sayılır</b> tarafından geliştirilmiştir.</div>""", unsafe_allow_html=True)

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

        with st.spinner("Zekai düşünüyor..."):
            try:
                response = st.session_state.chat_session.send_message(user_input)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                with st.chat_message("assistant", avatar="🧠"):
                    st.markdown(response.text)
                
                if st.session_state.ses_aktif:
                    ses_verisi = metni_oku(response.text)
                    if ses_verisi:
                        st.audio(ses_verisi, format="audio/mp3", autoplay=True)
                        st.session_state.messages.append({"role": "audio", "content": ses_verisi})
            except Exception as e:
                st.error(f"Hata: {e}")
