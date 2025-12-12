import streamlit as st
import google.generativeai as genai
from PIL import Image

# ==========================================
# 1. AYARLAR & TASARIM
# ==========================================
# Sayfa başlığı, ikonu ve düzeni ayarlanır.
st.set_page_config(page_title="Kafadar - Çalışma Arkadaşım", page_icon="🤖", layout="centered")

# CSS ile özel tasarım ayarları yapılır.
st.markdown("""
    <style>
    /* Arka plan rengi */
    .stApp { background-color: #fcfdfd; }
    /* Ana başlık stili */
    h1 { color: #2E86C1; font-family: 'Comic Sans MS', sans-serif; text-align: center; }
    /* Buton stilleri (renk, yuvarlaklık, gölge efekti) */
    .stButton>button {
        background-color: #F4D03F; color: #17202A; border-radius: 20px;
        font-weight: bold; border: none; padding: 10px 24px; transition: all 0.3s;
    }
    .stButton>button:hover {
        background-color: #F1C40F; transform: scale(1.05); box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    /* Streamlit'in varsayılan kamera butonunu gizleme (Türkçeleştirme için) */
    [data-testid="stCameraInputButton"] { display: none; }
    /* Kamera ve dosya yükleme sekmelerinin başlık stili */
    .stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
        font-size: 1.1rem; font-weight: bold; color: #2E86C1;
    }
    </style>
""", unsafe_allow_html=True)

# Google Gemini API anahtarı Streamlit secrets'tan alınır.
if "GOOGLE_API_KEY" in st.secrets:
    api_key = st.secrets["GOOGLE_API_KEY"]
else:
    # Anahtar yoksa hata mesajı gösterilir ve uygulama durdurulur.
    st.error("🔑 API Anahtarı Eksik! Lütfen secrets ayarlarını kontrol et.")
    st.stop()

# Gemini API yapılandırılır.
genai.configure(api_key=api_key)

# ==========================================
# 2. HAFIZA (SESSION STATE) YÖNETİMİ
# ==========================================
# 'karsilama_yapildi': Öğrenciye bir kez "Merhaba" denildikten sonra tekrar denmemesi için bayrak.
if 'karsilama_yapildi' not in st.session_state:
    st.session_state.karsilama_yapildi = False
    
# 'kamera_acik': Kameranın o an açık olup olmadığını kontrol eden bayrak.
if 'kamera_acik' not in st.session_state:
    st.session_state.kamera_acik = False

# Çekilen fotoğrafı silen ve kamera modunu kapatan fonksiyon.
def fotoyu_sil():
    st.session_state.kamera_acik = False # Kamerayı kapatır.
    # st.rerun() çağrısı gerekmez, çünkü buton tıklaması zaten sayfayı yeniler.

# ==========================================
# 3. ARAYÜZ - BAŞLIK VE KİŞİSELLEŞTİRME
# ==========================================
# Uygulama başlığı ve alt başlığı.
st.title("🤖 Kafadar")
st.markdown("<h3 style='text-align: center; color: #566573; margin-bottom: 30px;'>Senin Zeki Çalışma Arkadaşın</h3>", unsafe_allow_html=True)

# Öğrenci bilgileri için iki sütunlu yapı.
c1, c2 = st.columns(2)
with c1:
    # Öğrencinin adını girdiği alan.
    isim = st.text_input("Adın ne?", placeholder="Örn: Ali, Ayşe...")
with c2:
    # Öğrencinin sınıfını seçtiği açılır menü.
    sinif = st.selectbox("Sınıfın kaç?", ["4. Sınıf", "5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf", "Lise"])

# Duruma göre değişen bilgilendirme mesajı.
# Eğer isim girilmişse ve henüz karşılama yapılmamışsa ilk mesajı göster.
if isim and not st.session_state.karsilama_yapildi:
    st.info(f"👋 Merhaba {isim}! Hadi başlayalım, takıldığın yeri gönder, beraber bakalım.")
# İsim girilmiş ve daha önce karşılama yapılmışsa genel mesajı göster.
elif isim:
    st.info(f"📸 {isim}, sıradaki soruyu veya etkinliği gönder bakalım.")
# İsim girilmemişse isim girmesini isteyen mesajı göster.
else:
    st.info("📸 Adını yazarsan başlayalım!")

st.markdown("---")

# ==========================================
# 4. FOTOĞRAF YÜKLEME ALANI
# ==========================================
# Dosya yükleme ve kamera kullanımı için sekmeler oluşturulur.
tab1, tab2 = st.tabs(["📂 Dosyadan Yükle", "📸 Kamerayı Kullan"])
uploaded_image = None # Yüklenen görseli tutacak değişken.

# 1. Sekme: Dosyadan Yükle
with tab1:
    dosya = st.file_uploader("Galeriden bir resim seç", type=["jpg", "png", "jpeg"], label_visibility="visible")
    if dosya: uploaded_image = Image.open(dosya)

# 2. Sekme: Kamerayı Kullan
with tab2:
    # Kamerayı açıp kapatan, durumu 'kamera_acik' bayrağına bağlı olan buton.
    if st.button("📸 Görüntü Yakala" if not st.session_state.kamera_acik else "Kamerayı Kapat", use_container_width=True, key="cam_toggle_btn"):
        st.session_state.kamera_acik = not st.session_state.kamera_acik
        st.rerun() # Durum değişince arayüzü yenile.

    # Kamera açıksa görüntü giriş alanını göster.
    if st.session_state.kamera_acik:
        kamera_img = st.camera_input("Çekim Alanı", label_visibility="hidden")
        if kamera_img:
            uploaded_image = Image.open(kamera_img)
            # Fotoğraf çekildiyse, altına silme butonu ekle.
            st.button("🗑️ Fotoğrafı Sil", on_click=fotoyu_sil, use_container_width=True, type="secondary", key="del_photo_btn")

# ==========================================
# 5. YAPAY ZEKA (BEYİN) ANALİZİ
# ==========================================
# Eğer bir görsel yüklenmişse (dosyadan veya kameradan) analiz butonunu göster.
if uploaded_image:
    st.markdown("### 🧐 İnceliyorum...")
    # Buton metni, isim girilmişse kişiselleştirilir.
    btn_text = f"🚀 Hadi Bakalım Kafadar, {isim} için incele!" if isim else "🚀 Hadi Bakalım Kafadar!"
    
    # Analiz butonu.
    if st.button(btn_text, use_container_width=True, type="primary"):
        # İsim girilmemişse uyarı ver.
        if not isim:
            st.warning("⚠️ Lütfen yukarıya adını yazar mısın? Sana isminle hitap etmek istiyorum.")
        else:
            # Analiz başlasın.
            with st.spinner("Kafadar düşünüyor... 🧠"):
                try:
                    # Hızlı ve görsel yeteneği olan model seçilir.
                    model = genai.GenerativeModel("gemini-flash-latest")
                    
                    # --- PROMPT MÜHENDİSLİĞİ ---
                    # Karşılama durumuna göre giriş cümlesi belirlenir.
                    giris_cumlesi = ""
                    if not st.session_state.karsilama_yapildi:
                        # İlk kez analiz yapılıyorsa "Merhaba" de ve bayrağı True yap.
                        giris_cumlesi = f"Merhaba {isim}! Ben Kafadar. Hadi şu gönderdiğine birlikte bakalım."
                        st.session_state.karsilama_yapildi = True
                    else:
                        # Daha önce konuşulmuşsa direkt konuya gir.
                        giris_cumlesi = f"{isim}, bu yeni soruya bakalım."

                    # Yapay zekaya verilecek talimatlar (System Prompt).
                    system_prompt = f"""
                    Senin adın 'Kafadar'. Sen {sinif} öğrencisi {isim}'in en sevdiği, esprili ve zeki çalışma arkadaşısın.
                    Bir öğretmen gibi değil, bir "kanka" gibi konuşmalısın.

                    GİRİŞ: {giris_cumlesi}
                    
                    GÖREVLERİN:
                    1. ÖNCE DERSİ TESPİT ET: Görüntüdeki dersin ne olduğunu (Matematik, Türkçe, Fen vb.) kendin anla.
                    2. DURUMU ANALİZ ET:
                       - Çözülmüşse: Kontrol et. Doğruysa kısa ve coşkulu tebrik et (🎉). Yanlışsa hatayı nazikçe, ipucu vererek göster (cevabı direkt verme).
                       - Boşsa: ASLA cevabı direkt söyleme. Konuyu KISACA (2-3 cümle) özetle ve çözmesi için ilk adımı/ipucunu ver.
                    
                    KURALLAR:
                    - HİTAP: Sürekli "Merhaba" deme. Sadece ilk mesajda de (yukarıdaki GİRİŞ kısmını kullan). Sonrakilerde direkt konuya gir.
                    - TON: Arkadaş canlısı, kısa, öz ve anlaşılır. Bir ansiklopedi gibi değil, bir arkadaş gibi konuş.
                    - ÇOK DETAYA GİRME: Konuyu anlatırken en önemli noktayı söyle, sayfalarca anlatma. Öğrenci sıkılır.
                    - FORMAT: Markdown kullan. Emojileri (🌟, 🤔, 👍, 🚀) abartmadan, yerinde kullan. Başlıklar ve maddelerle metni okunur kıl.
                    """
                    
                    # Modelden yanıtı al.
                    response = model.generate_content([system_prompt, uploaded_image])
                    
                    # Yanıtı şık bir kutu içinde göster.
                    with st.container(border=True):
                        st.markdown(response.text)
                        
                except Exception as e:
                    # Bir hata oluşursa kullanıcıya bildir.
                    st.error(f"Bir hata oldu, üzgünüm: {e}")
