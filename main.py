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
    
    /* Buton Tasarımı */
    .stButton>button {
        background-color: #F4D03F; color: #17202A; border-radius: 20px;
        font-weight: bold; border: none; padding: 10px 24px; transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #F1C40F; transform: scale(1.05); box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Sekme Başlıkları */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem; font-weight: bold; color: #2E86C1;
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
# 2. HAFIZA YÖNETİMİ
# ==========================================
if 'karsilama_yapildi' not in st.session_state: st.session_state.karsilama_yapildi = False
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False
if 'analiz_cevap' not in st.session_state: st.session_state.analiz_cevap = None

def kamerayi_kapat_sil():
    st.session_state.kamera_acik = False
    st.session_state.analiz_cevap = None

def yeni_soru():
    st.session_state.analiz_cevap = None

# ==========================================
# 3. ARAYÜZ
# ==========================================
st.title("🤖 Kafadar")
st.markdown("<h3 style='text-align: center; color: #566573; margin-bottom: 20px;'>Senin Zeki Çalışma Arkadaşın</h3>", unsafe_allow_html=True)

c1, c2 = st.columns(2)
with c1:
    isim = st.text_input("Adın ne?", placeholder="Örn: Ali")
with c2:
    sinif = st.selectbox("Sınıfın kaç?", ["4. Sınıf", "5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf", "Lise"])

if isim and not st.session_state.karsilama_yapildi:
    st.info(f"👋 Merhaba {isim}! Hadi başlayalım.")
elif not isim:
    st.info("📸 Adını yazarsan başlayalım!")

st.markdown("---")

# ==========================================
# 4. FOTOĞRAF YÜKLEME
# ==========================================
tab1, tab2 = st.tabs(["📂 Dosyadan Yükle", "📸 Kamerayı Kullan"])
uploaded_image = None
image_source = None # Kaynağı takip et (kamera mı dosya mı)

with tab1:
    dosya = st.file_uploader("Galeriden Seç", type=["jpg", "png", "jpeg"])
    if dosya: 
        uploaded_image = Image.open(dosya)
        image_source = "dosya"
        st.caption("✅ Resim yüklendi.")

with tab2:
    # Kamerayı Aç/Kapat Butonu
    if st.button("📸 Kamerayı Aç" if not st.session_state.kamera_acik else "Kamerayı Kapat", use_container_width=True):
        st.session_state.kamera_acik = not st.session_state.kamera_acik
        st.rerun()

    if st.session_state.kamera_acik:
        kamera_img = st.camera_input("Fotoğraf Çek", label_visibility="hidden")
        if kamera_img:
            uploaded_image = Image.open(kamera_img)
            image_source = "kamera"
            # İngilizce "Clear photo" yerine Türkçe buton
            st.button("🗑️ Fotoğrafı Sil / Yeni Çek", on_click=yeni_soru, use_container_width=True, type="secondary")

# ==========================================
# 5. GÖRÜNTÜLEME VE ANALİZ
# ==========================================
if uploaded_image:
    # Eğer dosya yüklendiyse göster, kameraysa zaten widget gösteriyor (tekrar gösterme)
    if image_source == "dosya":
        st.image(uploaded_image, width=300)
    
    # Analiz Butonu
    btn_text = f"🚀 Kafadar İncele ({isim})" if isim else "🚀 İncele"
    
    if st.button(btn_text, type="primary", use_container_width=True):
        if not isim:
            st.warning("⚠️ Lütfen adını yazar mısın?")
        else:
            with st.spinner("Kafadar düşünüyor... 🧠"):
                try:
                    model = genai.GenerativeModel("gemini-flash-latest")
                    
                    giris = f"Merhaba {isim}!" if not st.session_state.karsilama_yapildi else f"{isim},"
                    st.session_state.karsilama_yapildi = True

                    prompt = f"""
                    Sen 'Kafadar'sın. {sinif} öğrencisi {isim}'in çalışma arkadaşısın.
                    GİRİŞ: {giris}
                    GÖREV:
                    1. Dersi tahmin et.
                    2. Soru çözülmüşse kontrol et, yanlışsa ipucu ver.
                    3. Soru boşsa cevabı söyleme, nasıl çözeceğini anlat.
                    KURALLAR:
                    - Kısa ve öz konuş.
                    - Markdown kullan.
                    - Arkadaşça tonla konuş.
                    """
                    
                    response = model.generate_content([prompt, uploaded_image])
                    st.session_state.analiz_cevap = response.text
                    
                except Exception as e:
                    st.error(f"Hata: {e}")

# Cevabı Ekranda Tutma (Butona tekrar basılmasa bile)
if st.session_state.analiz_cevap:
    st.markdown("---")
    st.success("Kafadar'ın Notu:")
    with st.container(border=True):
        st.markdown(st.session_state.analiz_cevap)
