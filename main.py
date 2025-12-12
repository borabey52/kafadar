import streamlit as st
import google.generativeai as genai
from PIL import Image
import edge_tts
import asyncio
import io
import re
import random
import time

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
    [data-testid="stTextInput"], [data-testid="stSelectbox"] { border: 2px solid #EAECEE; border-radius: 10px; }
    [data-testid="stAudioInput"] { margin-top: 10px; }
    
    /* Footer Sabitleme */
    .footer {
        position: fixed; left: 0; bottom: 0; width: 100%;
        background-color: #fcfdfd; color: #888; text-align: center;
        font-size: 14px; padding: 15px; border-top: 1px solid #eee; z-index: 1000;
    }
    .block-container { padding-bottom: 100px; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. API ANAHTARI VE OPTİMİZASYON
# ==========================================
def get_api_keys():
    keys = [v for k, v in st.secrets.items() if "GOOGLE_API_KEY" in k]
    if not keys and "GOOGLE_API_KEY" in st.secrets:
        keys.append(st.secrets["GOOGLE_API_KEY"])
    return keys

API_KEYS = get_api_keys()
if not API_KEYS:
    st.error("🚨 API Anahtarı bulunamadı!")
    st.stop()

# --- HIZLANDIRICI: RESİM SIKIŞTIRMA ---
def compress_image(image):
    """
    Büyük resimleri 800px genişliğe küçültür.
    Bu işlem API'ye gönderim süresini ve işleme süresini ciddi oranda düşürür.
    """
    img = image.copy()
    img.thumbnail((800, 800))  # En-boy oranını koruyarak max 800px yapar
    return img

# ==========================================
# 3. HAFIZA VE FONKSİYONLAR
# ==========================================
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_session" not in st.session_state: st.session_state.chat_session = None
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False
if 'ses_aktif' not in st.session_state: st.session_state.ses_aktif = True

def sifirla():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False

def metni_temizle_tts_icin(text):
    text = re.sub(r'(?i)cevap', 'yanıt', text)
    text = re.sub(r'(?i)cevab', 'yanıt', text)
    text = text.replace("#", "").replace("*", "")
    temiz_text = re.sub(r"[^a-zA-Z0-9çğıöşüÇĞIÖŞÜ\s\.,!\?\-':;]", "", text)
    return temiz_text.strip()

def sesi_yaziya_cevir(audio_bytes):
    random.shuffle(API_KEYS)
    for key in API_KEYS:
        try:
            genai.configure(api_key=key)
             # En hızlı model ismini sabitledik
            response = model.generate_content([
                "Söylenenleri aynen yaz.",
                {"mime_type": "audio/wav", "data": audio_bytes}
            ])
            return response.text.strip()
        except:
            continue
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
# 5. BAŞLATMA VE OPTİMİZE ANALİZ
# ==========================================
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

    if uploaded_image:
        st.success("✅ Resim alındı!")
        # Önizleme için küçük halini göster
        st.image(uploaded_image, width=200, caption="Seçilen Soru")
        
        if st.button("🚀 KAFADAR İNCELE (HIZLI MOD)", type="primary"):
            if not isim:
                st.warning("⚠️ Lütfen adını yaz.")
            else:
                # --- HIZLANDIRMA 1: RESMİ KÜÇÜLT ---
                compressed_img = compress_image(uploaded_image)
                
                # Placeholder: Cevap geldikçe buraya yazılacak
                cevap_kutusu = st.empty()
                full_text = ""

                # Prompt
                system_prompt = f"""
                Senin adın 'Kafadar'. {sinif} öğrencisi {isim}'in çalışma arkadaşısın.
                GÖREV: Dersi anla. Boşsa çözüm yolunu anlat (cevabı verme). Çözülmüşse kontrol et.
                ODAK: Kısa ve öz cevap ver. Uzatma.
                TON: Samimi, emojili. {isim} diye hitap et.
                """
                
                basarili = False
                random.shuffle(API_KEYS)
                
                for key in API_KEYS:
                    try:
                        genai.configure(api_key=key)
                        model = genai.GenerativeModel("gemini-flash-latest")
                        
                        st.session_state.chat_session = model.start_chat(
                            history=[{"role": "user", "parts": [system_prompt, compressed_img]}]
                        )
                        
                        # --- HIZLANDIRMA 2: STREAMING (AKIŞ) ---
                        response_stream = st.session_state.chat_session.send_message("Hadi incele.", stream=True)
                        
                        # Kelime kelime ekrana basma döngüsü
                        for chunk in response_stream:
                            full_text += chunk.text
                            # Canlı daktilo efekti
                            cevap_kutusu.markdown(f"**Kafadar:** \n\n{full_text} ▌")
                        
                        # İmleci kaldır, son hali bas
                        cevap_kutusu.markdown(f"**Kafadar:** \n\n{full_text}")
                        
                        # Hafızaya kaydet
                        st.session_state.messages.append({"role": "assistant", "content": full_text})
                        
                        # Seslendirme (Metin bittikten sonra başlar)
                        if st.session_state.ses_aktif:
                            ses = metni_oku(full_text)
                            if ses: st.session_state.messages.append({"role": "audio", "content": ses})
                        
                        basarili = True
                        break 
                    except Exception as e:
                        continue
                
                if not basarili:
                    st.error("⚠️ Bağlantı kurulamadı, tekrar dene.")
                else:
                    st.rerun()

# ==========================================
# 6. SOHBET DÖNGÜSÜ (STREAMING DESTEKLİ)
# ==========================================
else:
    col_reset, col_dummy = st.columns([1, 2])
    with col_reset:
        if st.button("🔄 Yeni Soru Sor", on_click=sifirla, type="secondary"):
            pass

    # Eski mesajları göster
    for message in st.session_state.messages:
        if message["role"] == "audio":
            st.audio(message["content"], format="audio/mp3")
        else:
            with st.chat_message(message["role"], avatar="🤖" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])

    user_input = None
    text_input = st.chat_input("Anlamadığın yeri yaz...")
    if text_input: user_input = text_input

    audio_input = st.audio_input("🎤 Sesli Sor", label_visibility="collapsed")
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

        # --- STREAMING SOHBET ---
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            full_response = ""
            
            try:
                response_stream = st.session_state.chat_session.send_message(user_input, stream=True)
                
                for chunk in response_stream:
                    full_response += chunk.text
                    message_placeholder.markdown(full_response + "▌")
                
                message_placeholder.markdown(full_response)
                st.session_state.messages.append({"role": "assistant", "content": full_response})
                
                if st.session_state.ses_aktif:
                    ses_verisi = metni_oku(full_response)
                    if ses_verisi:
                        st.audio(ses_verisi, format="audio/mp3", autoplay=True)
                        st.session_state.messages.append({"role": "audio", "content": ses_verisi})
            except:
                st.error("Bağlantı hatası.")

# ==========================================
# 7. FOOTER
# ==========================================
st.markdown("""
<div class="footer">
    © Kafadar uygulaması <b>Sinan Sayılır</b> tarafından geliştirilmiştir.
</div>
""", unsafe_allow_html=True)
