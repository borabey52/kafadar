import streamlit as st
import google.generativeai as genai
from PIL import Image
import base64
import json

# ==========================================
# 1. AYARLAR & CSS TASARIMI 🎨
# ==========================================
st.set_page_config(page_title="Dehai", page_icon="🧠", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fcfdfd; }
    
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 250px;
    }
    
    .stChatMessage { border-radius: 10px; }
    
    /* Buton Stili */
    .stButton>button {
        background-color: #F4D03F; color: #17202A; border-radius: 15px;
        font-weight: bold; border: none; padding: 12px 24px; transition: all 0.3s;
        width: 100%;
        border: 2px solid transparent;
    }
    .stButton>button:hover {
        background-color: #F1C40F; transform: scale(1.02); box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Soru Kartı */
    .soru-karti {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    [data-testid="stAudioInput"] {
        position: fixed; bottom: 110px; left: 0; right: 0; margin: 0 auto;
        width: 100%; max-width: 700px; z-index: 999;
        background-color: rgba(252, 253, 253, 0.95);
        padding: 10px 20px; border-radius: 20px 20px 0 0; border-top: 1px solid #eee;
        backdrop-filter: blur(5px);
    }
    
    .footer { text-align: center; color: #888; font-size: 12px; margin-top: 50px; padding-bottom: 20px; }
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
    try:
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    except:
        return None

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

# State Tanımları
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_session" not in st.session_state: st.session_state.chat_session = None
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False
if 'ilk_karsilama_yapildi' not in st.session_state: st.session_state.ilk_karsilama_yapildi = False
if 'aktif_test_verisi' not in st.session_state: st.session_state.aktif_test_verisi = None

def yeni_soru_yukle():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False
    st.session_state.aktif_test_verisi = None

# ==========================================
# 4. ARAYÜZ (GİRİŞ)
# ==========================================
# DİKKAT: Logo dosya adını projenizde de "dehai_logo.png" yapmalısınız.
img_base64 = get_base64_image("dehai_logo.png") 
if img_base64:
    st.markdown(
        f"""<div style="text-align: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{img_base64}" width="400" style="max-width: 100%; height: auto;">
            <h3 style="color: #566573; margin-top: 10px; font-family: 'Comic Sans MS', sans-serif;">Yeni Nesil Zeki Öğrenci Koçu</h3>
        </div>""", unsafe_allow_html=True
    )
else:
    st.title("🧠 Dehai")
    st.markdown("<h3 style='text-align: center; color: #566573;'>Yeni Nesil Zeki Öğrenci Koçu</h3>", unsafe_allow_html=True)

st.info("👇 Önce kendini tanıt, sonra sorunu yükle:")

col1, col2 = st.columns(2)
with col1:
    isim = st.text_input("Adın ne?", placeholder="Örn: Ali")
with col2:
    sinif = st.selectbox("Sınıfın kaç?", ["4. Sınıf", "5. Sınıf", "6. Sınıf", "7. Sınıf", "8. Sınıf", "Lise"])

st.markdown("---")

# ==========================================
# 5. BAŞLANGIÇ EKRANI (DOSYA YÜKLEME & KONUMATİK)
# ==========================================
if not st.session_state.chat_session:
    
    # --- A) DOSYA YÜKLEME ---
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

    # Resim İnceleme Butonu
    if uploaded_images:
        st.success(f"✅ {len(uploaded_images)} sayfa alındı!")
        cols = st.columns(min(len(uploaded_images), 4))
        for i, img in enumerate(uploaded_images[:4]):
            cols[i].image(img, width=100, caption=f"Sayfa {i+1}")

        if st.button("🚀 DEHAİ İNCELE", type="primary"):
            if not isim:
                st.warning("⚠️ Lütfen adını yaz.")
            else:
                with st.spinner("Dehai inceliyor... 🚀"):
                    try:
                        prompt_content = []
                        system_prompt = f"""
                        Senin adın 'Dehai'. {sinif} öğrencisi {isim}'in çalışma arkadaşısın.
                        GÖREVLERİN:
                        1. Dersi/konuyu anla.
                        2. (PUANLAMA) 5+ soru veya yazılı kağıdıysa not ver.
                        3. Boşsa: Çözüm yolunu anlat.
                        4. Çözülmüşse: Kontrol et.
                        """
                        prompt_content.append(system_prompt)
                        for img in uploaded_images: prompt_content.append(compress_image(img))
                        
                        model = genai.GenerativeModel("gemini-flash-latest")
                        st.session_state.chat_session = model.start_chat(history=[{"role": "user", "parts": prompt_content}])
                        
                        response_stream = st.session_state.chat_session.send_message("Hadi incele.", stream=True)
                        full_text = ""
                        message_placeholder = st.empty()
                        for chunk in response_stream:
                            full_text += chunk.text
                            message_placeholder.markdown(full_text + "▌")
                        message_placeholder.markdown(full_text)
                        
                        st.session_state.messages.append({"role": "assistant", "content": full_text})
                        st.session_state.ilk_karsilama_yapildi = True
                        st.session_state.aktif_test_verisi = None
                        
                    except Exception as e:
                        st.error(f"Hata: {e}")

    # --- B) KONUMATİK ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🎯 Konumatik: Özel Çalışma Alanı")
    st.info("Resim yüklemek zorunda değilsin! İstediğin konuyu yaz, Dehai sana özel içerik hazırlasın.")

    with st.container(border=True):
        konu_basligi = st.text_input("Hangi konuya çalışmak istersin?", placeholder="Örn: Hücre Bölünmesi, Kesirler, Fiilimsiler...")
        
        c1, c2, c3 = st.columns(3)
        btn_interaktif = c1.button("📝 5 Soru İnteraktif Test")
        btn_yazili = c2.button("✍️ Yazılı Provası (5 Açık Uçlu)")
        btn_konu = c3.button("📚 Konu Anlatımı")

        # İşlemler
        if (btn_interaktif or btn_yazili or btn_konu) and isim and konu_basligi:
            with st.spinner("Dehai içerik hazırlıyor..."):
                try:
                    if not st.session_state.chat_session:
                        system_prompt = f"Sen 'Dehai'. {sinif} öğrencisi {isim}'in koçusun. Konumuz: {konu_basligi}."
                        model = genai.GenerativeModel("gemini-flash-latest")
                        st.session_state.chat_session = model.start_chat(history=[{"role": "user", "parts": [system_prompt]}])
                        st.session_state.ilk_karsilama_yapildi = True

                    # 1. TEST MODU (JSON)
                    if btn_interaktif:
                        st.session_state.aktif_test_verisi = None
                        prompt = f"""
                        '{konu_basligi}' konusuyla ilgili {sinif} seviyesinde 5 adet çoktan seçmeli soru hazırla.
                        ÖNEMLİ: Çıktıyı SADECE aşağıdaki JSON formatında ver:
                        [
                          {{
                            "soru": "Soru metni...",
                            "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
                            "dogru_cevap": "Doğru seçenek (örn: A) ...)",
                            "aciklama": "Açıklama."
                          }}, ...
                        ]
                        """
                        response = st.session_state.chat_session.send_message(prompt)
                        text_data = response.text.replace("```json", "").replace("```", "").strip()
                        test_data = json.loads(text_data)
                        
                        st.session_state.aktif_test_verisi = test_data
                        st.session_state.messages.append({"role": "user", "content": f"⚡ **Mod:** {konu_basligi} - İnteraktif Test"})
                        st.rerun()
                    
                    # 2. DİĞER MODLAR (STREAMING)
                    else:
                        st.session_state.aktif_test_verisi = None
                        final_prompt = ""
                        if btn_yazili: final_prompt = f"'{konu_basligi}' için 5 adet klasik açık uçlu soru ve cevaplarını hazırla."
                        elif btn_konu: final_prompt = f"'{konu_basligi}' konusunu eğlenceli şekilde anlat."

                        response_stream = st.session_state.chat_session.send_message(final_prompt, stream=True)
                        full_text = ""
                        stream_area = st.empty()
                        for chunk in response_stream:
                            full_text += chunk.text
                            stream_area.markdown(full_text + "▌")
                        stream_area.empty()
                        
                        st.session_state.messages.append({"role": "assistant", "content": full_text})
                        st.rerun()

                except Exception as e:
                    st.error(f"Hata: {e}")
        elif (btn_interaktif or btn_yazili or btn_konu) and (not isim or not konu_basligi):
            st.warning("⚠️ Lütfen bilgileri doldur.")

# ==========================================
# 6. SOHBET VE TEST EKRANI (ELSE BLOĞU)
# ==========================================
else:
    col_reset, col_dummy = st.columns([1, 2])
    with col_reset:
        if st.button("🔄 Başka Soruya/Konuya Geç", on_click=yeni_soru_yukle, type="secondary"):
            pass

    # --- SOHBET GEÇMİŞİ ---
    for message in st.session_state.messages:
        with st.chat_message(message["role"], avatar="🧠" if message["role"] == "assistant" else "👤"):
            st.markdown(message["content"])

    # ----------------------------------------------------------------------
    # İNTERAKTİF TEST GÖSTERİMİ
    # ----------------------------------------------------------------------
    if st.session_state.aktif_test_verisi:
        st.markdown("---")
        st.subheader(f"📝 İnteraktif Test")
        
        for i, soru_data in enumerate(st.session_state.aktif_test_verisi):
            with st.container():
                st.markdown(f"""
                <div class="soru-karti">
                    <b>{i+1}. {soru_data['soru']}</b>
                </div>
                """, unsafe_allow_html=True)
                
                # Seçenekler
                secim = st.radio(
                    "Cevabınız:",
                    soru_data['secenekler'],
                    key=f"test_soru_{i}",
                    index=None,
                    label_visibility="collapsed"
                )
                
                # ANINDA DÖNÜT
                if secim:
                    dogru_mu = (secim == soru_data['dogru_cevap']) or (secim.split(")")[0] == soru_data['dogru_cevap'].split(")")[0])
                    
                    if dogru_mu:
                        st.success("🎉 Tebrikler! Doğru.")
                        with st.expander("💡 Açıklamayı Oku", expanded=True):
                            st.write(soru_data['aciklama'])
                    else:
                        st.error("❌ Yanlış.")
                        with st.expander("👀 Doğru Cevap ve Açıklama", expanded=True):
                            st.info(f"👉 **Doğru Cevap:** {soru_data['dogru_cevap']}")
                            st.write(f"**Açıklama:** {soru_data['aciklama']}")
                
                st.markdown("<br>", unsafe_allow_html=True)

    # --- FOOTER ---
    st.markdown("""<div class="footer">© Dehai uygulaması <b>Sinan Sayılır</b> tarafından geliştirilmiştir.</div>""", unsafe_allow_html=True)

    # --- INPUT ALANLARI ---
    user_input = None
    audio_input = st.audio_input("🎤 Sesli Sor", label_visibility="collapsed")
    text_input = st.chat_input("Anlamadığın yeri yaz...")

    if text_input: user_input = text_input
    if audio_input:
        with st.spinner("Ses işleniyor..."):
            audio_bytes = audio_input.read()
            transcribed_text = sesi_yaziya_cevir(audio_bytes)
            if transcribed_text: user_input = transcribed_text
            else: st.error("Ses anlaşılamadı.")

    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        try:
            full_response = ""
            message_placeholder = st.empty()
            response_stream = st.session_state.chat_session.send_message(user_input, stream=True)
            for chunk in response_stream:
                full_response += chunk.text
                message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"Hata: {e}")
