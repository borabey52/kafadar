import streamlit as st
import google.generativeai as genai
from PIL import Image

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
    
    /* Buton Tasarımı - Daha büyük ve dikkat çekici */
    .stButton>button {
        background-color: #F4D03F; color: #17202A; border-radius: 15px;
        font-weight: bold; border: none; padding: 12px 24px; transition: all 0.3s;
        width: 100%; /* Butonu genişlet */
    }
    .stButton>button:hover {
        background-color: #F1C40F; transform: scale(1.02); box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Input alanlarını belirginleştir */
    [data-testid="stTextInput"], [data-testid="stSelectbox"] {
        border: 2px solid #EAECEE; border-radius: 10px;
    }
    </style>
""", unsafe_allow_html=True)

if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("🔑 API Anahtarı Eksik!")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 2. HAFIZA (SESSION STATE)
# ==========================================
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_session" not in st.session_state: st.session_state.chat_session = None
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False

def sifirla():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False

# ==========================================
# 3. ARAYÜZ - ÜST BİLGİ ALANI (GİZLEME YOK!)
# ==========================================
st.title("🤖 Kafadar")
st.markdown("<h3 style='text-align: center; color: #566573; margin-bottom: 20px;'>Senin Zeki Çalışma Arkadaşın</h3>", unsafe_allow_html=True)

# Artık expander yok, direkt ekranda:
st.info("👇 Önce kendini tanıt, sonra sorunu yükle:")

col_isim, col_sinif = st.columns(2)
with col_isim:
    isim = st.text_input("Adın ne?", placeholder="Örn: Ali")
with col_sinif:
    sinif = st.selectbox("Sınıfın kaç?", ["4. Sınıf", "5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf", "Lise"])

st.markdown("---")

# ==========================================
# 4. FOTOĞRAF YÜKLEME VE BAŞLATMA
# ==========================================
# Eğer sohbet başlamadıysa yükleme ekranını göster
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

    # --- KRİTİK DÜZELTME: BUTON MANTIĞI ---
    # Resim varsa butonu GÖSTER (İsim olmasa bile buton görünsün)
    if uploaded_image:
        st.success("✅ Resim alındı! Şimdi başlatabilirsin.")
        st.image(uploaded_image, width=200, caption="Seçilen Soru")
        
        # Analiz Butonu
        if st.button("🚀 KAFADAR İNCELE VE SOHBETİ BAŞLAT", type="primary"):
            if not isim:
                st.warning("⚠️ Lütfen yukarıya adını yazar mısın? Sana isminle hitap etmek istiyorum.")
            else:
                with st.spinner("Kafadar hazırlanıyor..."):
                    # Model Ayarları
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
                    
                    # Sohbeti Başlat
                    st.session_state.chat_session = model.start_chat(
                        history=[{"role": "user", "parts": [system_prompt, uploaded_image]}]
                    )
                    
                    # İlk Mesajı Al
                    response = st.session_state.chat_session.send_message("Hadi incele.")
                    st.session_state.messages.append({"role": "assistant", "content": response.text})
                    st.rerun()

# ==========================================
# 5. SOHBET EKRANI (CHAT)
# ==========================================
else:
    # Üstte "Yeni Soru" butonu
    col_reset, col_dummy = st.columns([1, 2])
    with col_reset:
        if st.button("🔄 Yeni Soru Sor", on_click=sifirla, type="secondary"):
            pass

    # Mesajlaşma Döngüsü
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])

    # Yeni Mesaj Girişi
    if prompt := st.chat_input("Anlamadığın yeri sor..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        with st.spinner("Kafadar yazıyor..."):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(response.text)
            except:
                st.error("Bağlantı hatası. Lütfen sayfayı yenile.")
