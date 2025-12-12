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
    
    /* Buton Tasarımı */
    .stButton>button {
        background-color: #F4D03F; color: #17202A; border-radius: 20px;
        font-weight: bold; border: none; padding: 10px 24px; transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #F1C40F; transform: scale(1.05); box-shadow: 0 4px 8px rgba(0,0,0,0.2);
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
# 2. HAFIZA YÖNETİMİ (SESSION STATE)
# ==========================================
# Sohbet geçmişini tutacak liste
if "messages" not in st.session_state:
    st.session_state.messages = []

# Chat oturum nesnesini tutacak (Gemini ile bağlantı)
if "chat_session" not in st.session_state:
    st.session_state.chat_session = None

if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False

def sifirla():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False

# ==========================================
# 3. ARAYÜZ - BAŞLIK
# ==========================================
st.title("🤖 Kafadar")
st.markdown("<h3 style='text-align: center; color: #566573; margin-bottom: 20px;'>Senin Zeki Çalışma Arkadaşın</h3>", unsafe_allow_html=True)

with st.expander("👤 Öğrenci Ayarları (Değiştirmek için tıkla)"):
    c1, c2 = st.columns(2)
    with c1:
        isim = st.text_input("Adın ne?", placeholder="Örn: Ali")
    with c2:
        sinif = st.selectbox("Sınıfın kaç?", ["4. Sınıf", "5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf", "Lise"])

# ==========================================
# 4. FOTOĞRAF YÜKLEME (Sadece Sohbet Başlamadıysa Göster)
# ==========================================
uploaded_image = None

# Eğer henüz bir sohbet başlamamışsa fotoğraf yükleme alanını göster
if not st.session_state.chat_session:
    if isim:
        st.info(f"👋 Hadi {isim}, çözemediğin sorunun fotoğrafını yükle, sohbet edelim!")
    else:
        st.info("👋 Önce yukarıya adını yaz, sonra soru yükle!")

    tab1, tab2 = st.tabs(["📂 Dosyadan Yükle", "📸 Kamerayı Kullan"])
    
    with tab1:
        dosya = st.file_uploader("Galeriden Seç", type=["jpg", "png", "jpeg"])
        if dosya: uploaded_image = Image.open(dosya)

    with tab2:
        if st.button("📸 Kamerayı Aç" if not st.session_state.kamera_acik else "Kamerayı Kapat", use_container_width=True):
            st.session_state.kamera_acik = not st.session_state.kamera_acik
            st.rerun()

        if st.session_state.kamera_acik:
            kamera_img = st.camera_input("Fotoğraf Çek", label_visibility="hidden")
            if kamera_img: uploaded_image = Image.open(kamera_img)

    # Başlat Butonu
    if uploaded_image and isim:
        st.image(uploaded_image, width=200, caption="Seçilen Soru")
        if st.button("🚀 Sohbeti Başlat", type="primary", use_container_width=True):
            with st.spinner("Kafadar hazırlanıyor..."):
                # --- İLK KURULUM (PROMPT) ---
                model = genai.GenerativeModel("gemini-flash-latest")
                
                system_prompt = f"""
                Senin adın 'Kafadar'. Sen {sinif} öğrencisi {isim}'in en sevdiği çalışma arkadaşısın.
                
                GÖREVLERİN:
                1. Görüntüdeki dersi ve konuyu anla.
                2. Soru boşsa: Çözüm yolunu anlat ama cevabı direkt verme.
                3. Soru çözülmüşse: Kontrol et, yanlışsa ipucu ver.
                
                ÖZEL KURAL (ODAK KONTROLÜ):
                - Eğer öğrenci dersle ilgili bir şey sorarsa (Neden 3?, Yüklem neresi? vb.) sabırla açıkla.
                - Eğer öğrenci KONU DIŞI bir şey sorarsa (Maç kaç kaç?, En sevdiğin renk ne?, Nasılsın? vb.):
                  Esprili bir şekilde reddet ve nazikçe derse döndür.
                  Örnek: "Canım şu an sadece bu soruyu düşünüyorum, hadi bitirelim sonra konuşuruz! 😉"
                  Örnek: "Oyun kaçmıyor ama bu soru sınavda çıkabilir! Odaklanalım. 🚀"

                TONU:
                - Samimi, emojili ve kısa cümleler kur.
                - {isim} diye hitap et.
                """
                
                # Sohbeti başlatıyoruz ve geçmişe ekliyoruz
                st.session_state.chat_session = model.start_chat(
                    history=[
                        {"role": "user", "parts": [system_prompt, uploaded_image]},
                    ]
                )
                
                # İlk cevabı al (Hoşgeldin mesajı ve analiz)
                response = st.session_state.chat_session.send_message("Hadi incele ve yorumla.")
                st.session_state.messages.append({"role": "assistant", "content": response.text})
                st.rerun()

# ==========================================
# 5. SOHBET EKRANI
# ==========================================
else:
    # "Yeni Soru" butonu (Sohbeti sıfırlamak için)
    if st.button("🔄 Yeni Soru Sor / Bitir", on_click=sifirla, use_container_width=True):
        pass

    # Eski mesajları ekrana yazdır
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])

    # Kullanıcıdan yeni mesaj al
    if prompt := st.chat_input("Kafadar'a bir şey sor (Örn: Neden 5 bulduk?)"):
        # 1. Kullanıcı mesajını ekrana bas
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user", avatar="👤"):
            st.markdown(prompt)

        # 2. Yapay zekaya gönder ve cevap al
        with st.spinner("Kafadar yazıyor..."):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                ai_text = response.text
                
                # 3. AI mesajını ekrana bas ve kaydet
                st.session_state.messages.append({"role": "assistant", "content": ai_text})
                with st.chat_message("assistant", avatar="🤖"):
                    st.markdown(ai_text)
            except Exception as e:
                st.error("Bağlantı koptu, yeni soru butonuna basıp tekrar deneyebilirsin.")
