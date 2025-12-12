import streamlit as st
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. AYARLAR & TASARIM (KAFADAR TEMASI)
# ==========================================
st.set_page_config(page_title="Kafadar - Çalışma Arkadaşım", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    /* GENEL ARKA PLAN VE FONT */
    .stApp {
        background-color: #fcfdfd;
    }
    
    /* BAŞLIK TASARIMI */
    h1 {
        color: #2E86C1;
        font-family: 'Comic Sans MS', sans-serif;
        text-align: center;
    }
    
    /* BUTONLAR */
    .stButton>button {
        background-color: #F4D03F;
        color: #17202A;
        border-radius: 20px;
        font-weight: bold;
        border: none;
        padding: 10px 24px;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #F1C40F;
        transform: scale(1.05);
        box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* MESAJ KUTULARI */
    .stAlert {
        border-radius: 15px;
    }
    </style>
""", unsafe_allow_html=True)

# API Anahtarı Kontrolü (Secrets'tan alır)
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("🔑 API Anahtarı Bulunamadı! Lütfen ayarlardan ekle.")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 2. HAFIZA VE OTURUM
# ==========================================
if 'chat_history' not in st.session_state:
    st.session_state.chat_history = []

def temizle():
    st.session_state.chat_history = []
    st.rerun()

# ==========================================
# 3. ARAYÜZ - KAFADAR KARŞILAMA
# ==========================================
st.title("🤖 Kafadar")
st.markdown("<h3 style='text-align: center; color: #566573;'>Senin Zeki Çalışma Arkadaşın</h3>", unsafe_allow_html=True)
st.markdown("---")

# Kullanıcıdan Bilgi Alma
col1, col2 = st.columns([1, 1])
with col1:
    ders = st.selectbox("Hangi dersi çalışıyoruz?", ["Matematik", "Türkçe", "Fen Bilimleri", "Sosyal Bilgiler", "İngilizce", "Din Kültürü"])
with col2:
    sinif = st.selectbox("Kaçıncı sınıftasın?", ["4. Sınıf", "5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf"])

st.info("📸 Sorunun veya etkinliğin fotoğrafını aşağıya yükle, beraber bakalım!")

# Fotoğraf Yükleme Alanı (Hem Kamera Hem Dosya)
tab1, tab2 = st.tabs(["📂 Dosya Yükle", "📸 Fotoğraf Çek"])
uploaded_image = None

with tab1:
    dosya = st.file_uploader("Resim Seç", type=["jpg", "png", "jpeg"])
    if dosya: uploaded_image = Image.open(dosya)

with tab2:
    kamera = st.camera_input("Kamerayı Aç")
    if kamera: uploaded_image = Image.open(kamera)

# ==========================================
# 4. YAPAY ZEKA İŞLEMİ (BEYİN)
# ==========================================
if uploaded_image:
    st.image(uploaded_image, caption="Senin Gönderdiğin", width=300)
    
    if st.button("🚀 Hadi Bakalım Kafadar!", use_container_width=True):
        with st.spinner("Kafadar düşünüyor... 🧠"):
            try:
                # --- MODEL SEÇİMİ ---
                model = genai.GenerativeModel("gemini-1.5-flash") # Hızlı ve vizyon yeteneği yüksek
                
                # --- KAFADAR'IN KİŞİLİĞİ (PROMPT) ---
                system_prompt = f"""
                Senin adın 'Kafadar'. Sen {sinif} öğrencisinin en sevdiği, neşeli, sabırlı ve zeki çalışma arkadaşısın.
                Şu an {ders} dersine bakıyoruz.
                
                GÖREVİN:
                Öğrencinin yüklediği fotoğrafı analiz et. İki durum olabilir:
                
                DURUM 1: ÖĞRENCİ SORUYU ÇÖZMÜŞ VEYA ETKİNLİĞİ YAPMIŞ
                - Cevapları kontrol et.
                - Doğruysa: Harika bir dille tebrik et (Emoji kullan! 🎉).
                - Yanlışsa: Direkt cevabı söyleme. Nerede hata yaptığını ipucu vererek buldurmaya çalış. "Sanırım şurada küçük bir işlem hatası var" gibi.
                
                DURUM 2: SORU BOŞ / ÇÖZÜLMEMİŞ
                - ASLA cevabı direkt söyleme! Bu kopya olur.
                - Konuyu kısaca hatırlat.
                - İlk adımı sen at, gerisini ona bırak. "Önce parantez içini yapalım, sence sonuç ne olur?" gibi yönlendir.
                
                GENEL KURALLAR:
                - Tonun: Arkadaş canlısı, cesaretlendirici ve eğitici.
                - Asla sıkıcı olma.
                - Çıktıyı Markdown formatında düzenli ver. Başlıklar kullan.
                - Matematik işlemi varsa adım adım göster.
                """
                
                response = model.generate_content([system_prompt, uploaded_image])
                
                st.balloons()
                st.success("İşte Kafadar'ın Yorumu:")
                
                # Çıktıyı güzel bir kutuda göster
                with st.container(border=True):
                    st.markdown(response.text)
                    
            except Exception as e:
                st.error(f"Bir hata oldu: {e}")