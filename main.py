import streamlit as st
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. AYARLAR & TASARIM
# ==========================================
st.set_page_config(page_title="Kafadar - Çalışma Arkadaşım", page_icon="🤖", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fcfdfd; }
    h1 { color: #2E86C1; font-family: 'Comic Sans MS', sans-serif; text-align: center; }
    .stButton>button {
        background-color: #F4D03F; color: #17202A; border-radius: 20px;
        font-weight: bold; border: none; padding: 10px 24px; transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #F1C40F; transform: scale(1.05); box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    </style>
""", unsafe_allow_html=True)

# API Anahtarı
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    st.error("🔑 API Anahtarı Eksik!")
    st.stop()

genai.configure(api_key=api_key)

# ==========================================
# 2. ARAYÜZ - KAFADAR KARŞILAMA
# ==========================================
st.title("🤖 Kafadar")
st.markdown("<h3 style='text-align: center; color: #566573;'>Senin Zeki Çalışma Arkadaşın</h3>", unsafe_allow_html=True)
st.markdown("---")

# KİŞİSELLEŞTİRME ALANI
c1, c2 = st.columns(2)
with c1:
    isim = st.text_input("Adın ne?", placeholder="Örn: Ali, Ayşe...")
with c2:
    sinif = st.selectbox("Sınıfın kaç?", ["4. Sınıf", "5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf", "Lise"])

st.info(f"📸 {isim if isim else 'Arkadaşım'}, takıldığın sorunun veya yaptığın etkinliğin fotoğrafını yükle bakalım!")

# FOTOĞRAF ALANI (Otomatik Açılmayı Engellemek İçin)
tab1, tab2 = st.tabs(["📂 Dosyadan Yükle", "📸 Kamerayı Kullan"])
uploaded_image = None

with tab1:
    dosya = st.file_uploader("Resim Seç", type=["jpg", "png", "jpeg"], label_visibility="collapsed")
    if dosya: uploaded_image = Image.open(dosya)

with tab2:
    # Kamera sadece bu anahtar açılırsa aktif olur
    kamera_acik = st.toggle("Kamerayı Başlat")
    if kamera_acik:
        kamera = st.camera_input("Fotoğraf Çek")
        if kamera: uploaded_image = Image.open(kamera)

# ==========================================
# 3. YAPAY ZEKA (BEYİN)
# ==========================================
if uploaded_image:
    st.image(uploaded_image, caption="Senin Gönderdiğin", width=300)
    
    # Buton metnini kişiselleştir
    btn_text = f"🚀 Hadi Bakalım Kafadar, {isim} için incele!" if isim else "🚀 Hadi Bakalım Kafadar!"
    
    if st.button(btn_text, use_container_width=True):
        if not isim:
            st.warning("⚠️ Lütfen adını yazar mısın? Sana isminle hitap etmek istiyorum.")
        else:
            with st.spinner("Kafadar inceliyor... 🧠"):
                try:
                    model = genai.GenerativeModel("gemini-1.5-flash")
                    
                    system_prompt = f"""
                    Senin adın 'Kafadar'. Sen öğrencilerin en sevdiği, esprili, sabırlı ve zeki çalışma arkadaşısın.
                    Karşındaki öğrencinin adı: {isim}
                    Sınıf Seviyesi: {sinif}
                    
                    GÖREVLERİN:
                    1. ÖNCE DERSİ TESPİT ET: Görüntüdeki dersin ne olduğunu (Matematik, Türkçe, Fen vb.) kendin anla.
                    2. DURUMU ANALİZ ET:
                       - Eğer soru çözülmüşse: Kontrol et. Doğruysa {isim}'i coşkuyla tebrik et. Yanlışsa hatayı nazikçe göster (cevabı direkt verme).
                       - Eğer soru boşsa: Asla cevabı söyleme. Konuyu kısaca özetle ve {isim}'e çözmesi için ilk ipucunu ver.
                    
                    KURALLAR:
                    - Hitap: Sürekli "{isim}" diyerek samimi konuş.
                    - Ton: Eğlenceli, motive edici, emojili (🌟, 🔥, 🚀).
                    - Format: Markdown kullan. Başlıkları belirgin yap.
                    - Asla sıkıcı olma, öğretmen gibi not verme, arkadaş gibi yol göster.
                    """
                    
                    response = model.generate_content([system_prompt, uploaded_image])
                    
                    st.balloons()
                    with st.container(border=True):
                        st.markdown(response.text)
                        
                except Exception as e:
                    st.error(f"Bir hata oldu: {e}")
