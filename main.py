import streamlit as st
import google.generativeai as genai
from PIL import Image
import json
import time
import pandas as pd
import io
import base64
import re
import streamlit.components.v1 as components # <--- YENİ EKLENDİ (Kaydırma için)

# ==========================================
# 1. AYARLAR & TASARIM
# ==========================================
st.set_page_config(page_title="OkutAİ - Akıllı Sınav Okuma", layout="wide", page_icon="📑")

st.markdown("""
    <style>
    /* --- GÖRSEL EŞİTLEME --- */
    .stTextArea label, .stRadio label, .stFileUploader label p {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #31333F !important;
    }
    .stTabs button {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #31333F !important;
    }
    [data-testid="stFileUploaderDropzone"] button {
        font-size: 16px !important;
        font-weight: 600 !important;
        color: #31333F !important;
    }
    
    /* BUTON RENKLERİ */
    button[kind="primary"] { color: white !important; }
    button[kind="secondary"] { color: #333 !important; border-color: #dcdcdc !important; }
    
    /* DÜZEN */
    .block-container { padding-top: 2rem !important; padding-bottom: 2rem !important; }
    header[data-testid="stHeader"] { background-color: transparent; }
    [data-testid="stSidebarUserContent"] { padding-top: 2rem !important; }
    
    /* SOL MENÜ */
    [data-testid="stSidebarNav"] a {
        background-color: #f0f2f6; padding: 15px; border-radius: 10px;
        margin-bottom: 10px; text-decoration: none !important;
        color: #002D62 !important; font-weight: 700; display: block;
        text-align: center; border: 1px solid #dcdcdc; transition: all 0.3s;
    }
    [data-testid="stSidebarNav"] a:hover {
        background-color: #e6e9ef; transform: scale(1.02);
        box-shadow: 0 4px 6px rgba(0,0,0,0.1); border-color: #b0b0b0;
    }
    
    /* KAMERA */
    div[data-testid="stCameraInput"] button { color: transparent !important; }
    div[data-testid="stCameraInput"] button::after {
        content: "📸 TARAT"; color: #333; font-weight: bold; position: absolute; left:0; right:0; top:0; bottom:0; display: flex; align-items: center; justify-content: center;
    }
    
    /* DETAYLAR */
    .streamlit-expanderHeader {
        font-weight: bold; background-color: #ffffff; border: 1px solid #e0e0e0; border-radius: 8px; margin-bottom: 5px;
    }
    </style>
""", unsafe_allow_html=True)

# API Anahtarı
if "GOOGLE_API_KEY" in st.secrets:
    SABIT_API_KEY = st.secrets["GOOGLE_API_KEY"]
else:
    SABIT_API_KEY = ""

# --- HAFIZA ---
if 'sinif_verileri' not in st.session_state: st.session_state.sinif_verileri = []
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False

def tam_hafiza_temizligi():
    st.session_state.sinif_verileri = []
    st.toast("🧹 Liste temizlendi!", icon="🗑️")
    st.rerun()

def kamera_durumunu_degistir():
    st.session_state.kamera_acik = not st.session_state.kamera_acik

def extract_json(text):
    text = text.strip()
    if "```" in text:
        try:
            text = re.split(r"```(?:json)?", text)[1].split("```")[0]
        except:
            pass
    
    start = text.find('{')
    end = text.rfind('}') + 1
    if start != -1 and end != 0:
        return text[start:end]
    return text

def get_img_as_base64(file):
    with open(file, "rb") as f:
        data = f.read()
    return base64.b64encode(data).decode()

# ==========================================
# 2. ARAYÜZ (HEADER)
# ==========================================

with st.sidebar:
    st.header("⚙️ Durum")
    st.info(f"📂 Okunan: **{len(st.session_state.sinif_verileri)}**")
    if len(st.session_state.sinif_verileri) > 0:
        if st.button("🚨 Listeyi Sıfırla", type="primary", use_container_width=True):
            tam_hafiza_temizligi()
    st.divider()
    st.caption("OkutAİ v1.21 - AutoScroll")

try:
    img_base64 = get_img_as_base64("okutai_logo.png") 
    st.markdown(
        f"""
        <div style="display: flex; flex-direction: column; align-items: center; justify-content: center;">
            <img src="data:image/png;base64,{img_base64}" width="350" style="margin-bottom: 5px;">
            <h3 style='color: #002D62; margin: 0; font-size: 1.5rem; font-weight: 800;'>Sen Okut, O Puanlasın.</h3>
        </div>
        """,
        unsafe_allow_html=True
    )
except:
    st.markdown("""
        <h1 style='text-align: center; color: #002D62;'>Okut<span style='color: #00aaff;'>Aİ</span></h1>
        <h3 style='text-align: center;'>Sen Okut, O Puanlasın.</h3>
        """, unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 3. İŞLEM ALANI
# ==========================================
col_sol, col_sag = st.columns([1, 1], gap="large")

with col_sol:
    st.header("1. Sınav Ayarları")
    ogretmen_promptu = st.text_area("Öğretmen Notu / Puanlama Kriteri:", height=100, placeholder="Ör: Yazım hataları -1 puan, anlam bütünlüğü önemli...")
    sayfa_tipi = st.radio("Her Öğrenci Kaç Sayfa?", ["Tek Sayfa (Sadece Ön)", "Çift Sayfa (Ön + Arka)"], horizontal=True)
    
    with st.expander("Cevap Anahtarı (Opsiyonel)"):
        rubrik_dosyasi = st.file_uploader("Cevap Anahtarı Yükle", type=["jpg", "png", "jpeg"], key="rubrik")
        rubrik_img = Image.open(rubrik_dosyasi) if rubrik_dosyasi else None

with col_sag:
    st.header("2. Kağıt Yükleme")
    
    tab_dosya, tab_kamera = st.tabs(["📂 Dosya Yükle", "📸 Kamera"])
    
    uploaded_files = []
    camera_file = None
    
    with tab_dosya:
        st.info("Galeriden çoklu seçim yapabilirsiniz.")
        uploaded_files_list = st.file_uploader("Okutulacak Kağıtları Seç", type=["jpg", "png", "jpeg"], accept_multiple_files=True)
        if uploaded_files_list: uploaded_files = uploaded_files_list
            
    with tab_kamera:
        if st.session_state.kamera_acik:
            if st.button("❌ Kamerayı Kapat", type="secondary", use_container_width=True):
                kamera_durumunu_degistir()
                st.rerun()
            camera_input = st.camera_input("Fotoğrafı Çek")
            if camera_input: camera_file = camera_input
        else:
            if st.button("📸 Kamerayı Başlat", type="primary", use_container_width=True):
                kamera_durumunu_degistir()
                st.rerun()

# ==========================================
# 4. İŞLEM BUTONU VE MOTORU
# ==========================================
st.markdown("---")

if st.button("🚀 KAĞITLARI OKUT VE PUANLA", type="primary", use_container_width=True):
    
    tum_gorseller = []
    if uploaded_files: tum_gorseller.extend(uploaded_files)
    if camera_file: tum_gorseller.append(camera_file)
    
    if not SABIT_API_KEY:
        st.error("API Anahtarı Eksik!")
    elif not tum_gorseller:
        st.warning("Lütfen dosya yükleyin veya fotoğraf çekin.")
    else:
        # Model Ayarları
        genai.configure(api_key=SABIT_API_KEY)
        model = genai.GenerativeModel("gemini-flash-latest")

        is_paketleri = []
        adim = 2 if "Çift" in sayfa_tipi and len(tum_gorseller) > 1 else 1
        sorted_files = sorted(tum_gorseller, key=lambda x: x.name if hasattr(x, 'name') else "camera")

        for i in range(0, len(sorted_files), adim):
            paket = sorted_files[i : i + adim]
            if len(paket) > 0:
                img_paket = [Image.open(f) for f in paket]
                is_paketleri.append(img_paket)

        progress_bar = st.progress(0)
        durum_text = st.empty()
        toplam_paket = len(is_paketleri)
        basarili = 0

        for index, images in enumerate(is_paketleri):
            durum_text.write(f"⏳ Taranıyor: {index + 1}. Öğrenci / {toplam_paket}...")
            
            try:
                # Prompt
                prompt = ["""
                Sen uzman bir öğretmensin. Sınav kağıdını değerlendir.
                
                GÖREVLER:
                1. KAĞIDI TANI: İsim, Numara ve Soruları bul.
                2. SORULARI EŞLEŞTİR: Kağıt çok sayfalıysa soruları sıraya koy.
                
                3. PUANLAMA:
                   - Kağıtta puan yazıyorsa onu kullan.
                   - Yazmıyorsa soru sayısına göre eşit dağıt (Örn: 10 soru = her biri 10 puan).
                   - Yanlışlara 0 ver.
                
                4. ÇIKTI FORMATI:
                SADECE şu JSON formatını kullan:
                { 
                  "kimlik": {"ad_soyad": "Öğrenci Adı", "numara": "123"}, 
                  "degerlendirme": [
                    {"no":"1", "soru":"...", "cevap":"...", "puan":10, "tam_puan":10, "yorum":"..."}
                  ] 
                }
                """]
                
                if ogretmen_promptu: prompt.append(f"ÖĞRETMEN NOTU: {ogretmen_promptu}")
                if rubrik_img: prompt.extend(["CEVAP ANAHTARI:", rubrik_img])
                prompt.append("KAĞITLAR:")
                prompt.extend(images)

                response = model.generate_content(prompt)
                
                # Temizlik
                json_text = extract_json(response.text)
                if not json_text: raise ValueError("Boş cevap.")
                data = json.loads(json_text)
                
                kimlik = data.get("kimlik", {})
                sorular = data.get("degerlendirme", [])
                
                # Puan Hesapla
                toplam_puan = 0
                for s in sorular:
                    try:
                        p = float(str(s.get('puan', 0)).replace(',', '.'))
                        toplam_puan += p
                    except: pass
                
                kayit = {
                    "Ad Soyad": kimlik.get("ad_soyad", f"Öğrenci {index+1}"), 
                    "Numara": kimlik.get("numara", "-"), 
                    "Toplam Puan": toplam_puan,
                    "Detaylar": sorular
                }
                
                for s in sorular: 
                    kayit[f"Soru {s.get('no')}"] = s.get('puan', 0)

                st.session_state.sinif_verileri.append(kayit)
                basarili += 1

            except Exception as e:
                st.error(f"⚠️ Hata: {e}")
            
            progress_bar.progress((index + 1) / toplam_paket)
            time.sleep(1)

        durum_text.success(f"✅ İşlem tamam! {basarili} kağıt okundu.")
        st.balloons()
        time.sleep(1)
        st.rerun()

# ==========================================
# 5. SONUÇ LİSTESİ
# ==========================================
if len(st.session_state.sinif_verileri) > 0:
    
    # --- YUKARI KAYDIRMA (AUTO SCROLL) KODU ---
    # Bu kod çalıştığında tarayıcı otomatik olarak en üste kayar
    components.html(
        """
        <script>
            window.parent.document.querySelector('section.main').scrollTo(0, 0);
        </script>
        """,
        height=0
    )
    # ------------------------------------------

    st.markdown("### 📝 Sınıf Sonuçları")
    
    for i, ogrenci in enumerate(st.session_state.sinif_verileri):
        baslik = f"📄 {ogrenci['Ad Soyad']} (No: {ogrenci['Numara']}) | Puan: {int(ogrenci['Toplam Puan'])}"
        
        with st.expander(baslik, expanded=False):
            if "Detaylar" in ogrenci:
                for soru in ogrenci["Detaylar"]:
                    try:
                        puan = float(str(soru.get('puan', 0)).replace(',', '.'))
                        tam_puan = float(str(soru.get('tam_puan', 0)).replace(',', '.'))
                    except:
                        puan = 0; tam_puan = 0
                    
                    if puan == tam_puan and tam_puan > 0:
                        renk = "green"; ikon = "✅"
                    elif puan == 0:
                        renk = "red"; ikon = "❌"
                    else:
                        renk = "orange"; ikon = "⚠️"
                    
                    p_goster = int(puan) if puan.is_integer() else puan
                    tp_goster = int(tam_puan) if tam_puan.is_integer() else tam_puan

                    st.markdown(f"**Soru {soru.get('no')}** - {ikon} :{renk}[**{p_goster}** / {tp_goster}]")
                    st.info(f"**Öğrenci Cevabı:** {soru.get('cevap')}")
                    
                    st.markdown(f"""
                    <div style="background-color: #f0f8ff; padding: 10px; border-radius: 5px; border-left: 5px solid #002D62; margin-bottom: 5px;">
                        <span style="font-weight:bold; color:#002D62;">🤖 OkutAİ Yorumu:</span><br>
                        <span style="font-size: 16px; color: #222;">{soru.get('yorum')}</span>
                    </div>
                    """, unsafe_allow_html=True)
                    st.divider() 

    # Excel İndirme
    st.markdown("---")
    df_excel = pd.DataFrame(st.session_state.sinif_verileri)
    if "Detaylar" in df_excel.columns: df_excel = df_excel.drop(columns=["Detaylar"])
    
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df_excel.to_excel(writer, index=False, sheet_name='Sonuclar')
        
    st.download_button("📥 Excel Olarak İndir", data=output.getvalue(), file_name='OkutAI_Sonuclari.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', type="primary", use_container_width=True)

# Footer
st.markdown("---")
st.markdown("""
    <div style='text-align: center; margin-top: 50px; margin-bottom: 20px; color: #666;'>
        <p style='font-size: 18px; font-weight: 600;'>
            © 2024 OkutAİ - Sinan Sayılır tarafından geliştirilmiştir.
        </p>
        <p style='font-size: 14px;'>Sen Okut, O Puanlasın.</p>
    </div>
""", unsafe_allow_html=True)
