import streamlit as st
import google.generativeai as genai
from PIL import Image
import edge_tts
import asyncio
import io
import re
import base64
import json  # JSON kütüphanesini ekledik

# ==========================================
# 1. AYARLAR & CSS TASARIMI 🎨
# ==========================================
st.set_page_config(page_title="Zekai", page_icon="🧠", layout="centered")

st.markdown("""
    <style>
    .stApp { background-color: #fcfdfd; }
    
    .block-container {
        padding-top: 2rem !important;
        padding-bottom: 250px;
    }
    
    .stChatMessage { border-radius: 10px; }
    
    .stButton>button {
        background-color: #F4D03F; color: #17202A; border-radius: 15px;
        font-weight: bold; border: none; padding: 12px 24px; transition: all 0.3s;
        width: 100%;
        border: 2px solid transparent;
    }
    .stButton>button:hover {
        background-color: #F1C40F; transform: scale(1.02); box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Test Alanı Tasarımı */
    .soru-karti {
        background-color: #ffffff;
        border: 1px solid #e0e0e0;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.05);
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

# State Tanımları
if "messages" not in st.session_state: st.session_state.messages = []
if "chat_session" not in st.session_state: st.session_state.chat_session = None
if 'kamera_acik' not in st.session_state: st.session_state.kamera_acik = False
if 'ses_aktif' not in st.session_state: st.session_state.ses_aktif = True
if 'ilk_karsilama_yapildi' not in st.session_state: st.session_state.ilk_karsilama_yapildi = False
# YENİ: İnteraktif test verisi için hafıza
if 'aktif_test_verisi' not in st.session_state: st.session_state.aktif_test_verisi = None

def yeni_soru_yukle():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False
    st.session_state.aktif_test_verisi = None # Testi sıfırla

def metni_temizle_tts_icin(text):
    text = re.sub(r'(?i)cevap', 'yanıt', text)
    text = re.sub(r'(?i)cevab', 'yanıt', text)
    text = text.replace("#", "").replace("*", "")
    temiz_text = re.sub(r"[^a-zA-Z0-9çğıöşüÇĞIÖŞÜ\s\.,!\?\-':;]", "", text)
    return temiz_text.strip()

def sesi_yaziya_cevir(audio_bytes):
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-latest")
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
# 4. ARAYÜZ (GİRİŞ)
# ==========================================
img_base64 = get_base64_image("zekai_logo.png")
if img_base64:
    st.markdown(
        f"""<div style="text-align: center; margin-bottom: 20px;">
            <img src="data:image/png;base64,{img_base64}" width="400" style="max-width: 100%; height: auto;">
            <h3 style="color: #566573; margin-top: 10px; font-family: 'Comic Sans MS', sans-serif;">Yeni Nesil Zeki Öğrenci Koçu</h3>
        </div>""", unsafe_allow_html=True
    )
else:
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
# 5. İÇERİK OLUŞTURMA ALANI
# ==========================================
if not st.session_state.chat_session:
    
    # --- A) DOSYA YÜKLEME ALANI ---
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

    # Resim varsa "İncele" butonu çıkar
    if uploaded_images:
        st.success(f"✅ {len(uploaded_images)} sayfa alındı!")
        cols = st.columns(min(len(uploaded_images), 4))
        for i, img in enumerate(uploaded_images[:4]):
            cols[i].image(img, width=100, caption=f"Sayfa {i+1}")

        if st.button("🚀 ZEKAİ İNCELE", type="primary"):
            if not isim:
                st.warning("⚠️ Lütfen adını yaz.")
            else:
                with st.spinner("Zekai inceliyor... 🚀"):
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
                        2. (PUANLAMA) 5+ soru veya yazılı kağıdıysa: Doğru/Yanlış analizi yap ve 100 üzerinden not ver.
                        3. Boşsa: Çözüm yolunu anlat (CEVABI DİREKT VERME).
                        4. Çözülmüşse: Kontrol et, yanlışsa ipucu ver.
                        TONU: Samimi, emojili, motive edici.
                        """
                        prompt_content.append(system_prompt)
                        for img in uploaded_images: prompt_content.append(compress_image(img))
                        
                        model = genai.GenerativeModel("gemini-1.5-flash-latest")
                        st.session_state.chat_session = model.start_chat(
                            history=[{"role": "user", "parts": prompt_content}]
                        )
                        
                        response_stream = st.session_state.chat_session.send_message("Hadi incele.", stream=True)
                        full_text = ""
                        message_placeholder = st.empty()
                        for chunk in response_stream:
                            full_text += chunk.text
                            message_placeholder.markdown(full_text + "▌")
                        message_placeholder.markdown(full_text)
                        
                        st.session_state.messages.append({"role": "assistant", "content": full_text})
                        st.session_state.ilk_karsilama_yapildi = True
                        
                        if st.session_state.ses_aktif:
                            ses = metni_oku(full_text)
                            if ses: st.session_state.messages.append({"role": "audio", "content": ses})
                            st.rerun()
                        
                    except Exception as e:
                        st.error(f"Hata: {e}")

    # --- B) KONUMATİK: İNTERAKTİF ÇALIŞMA ALANI ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🎯 Konumatik: Özel Çalışma Alanı")
    st.info("Resim yüklemek zorunda değilsin! İstediğin konuyu yaz, Zekai sana özel içerik hazırlasın.")

    with st.container(border=True):
        konu_basligi = st.text_input("Hangi konuya çalışmak istersin?", placeholder="Örn: Hücre Bölünmesi, Kesirler, Fiilimsiler...")
        
        c1, c2, c3 = st.columns(3)
        
        buton_tiklandi = False
        secilen_mod = None
        
        # BUTONLAR
        if c1.button("📝 5 Soru İnteraktif Test"):
            secilen_mod = "5_soru_interaktif"
            buton_tiklandi = True
            
        if c2.button("✍️ Yazılı Provası (5 Açık Uçlu)"):
            secilen_mod = "yazili"
            buton_tiklandi = True
            
        if c3.button("📚 Konu Anlatımı"):
            secilen_mod = "konu_anlatimi"
            buton_tiklandi = True

        # --- İŞLEMLER ---
        if buton_tiklandi and isim and konu_basligi:
            # Eski test verisini temizle
            st.session_state.aktif_test_verisi = None
            
            with st.spinner("Zekai içerik hazırlıyor..."):
                try:
                    # Session kontrol
                    if not st.session_state.chat_session:
                        system_prompt = f"Sen 'Zekai'. {sinif} öğrencisi {isim}'in koçusun. Konumuz: {konu_basligi}."
                        model = genai.GenerativeModel("gemini-1.5-flash-latest")
                        st.session_state.chat_session = model.start_chat(history=[{"role": "user", "parts": [system_prompt]}])
                        st.session_state.ilk_karsilama_yapildi = True

                    # ----------------------------------------
                    # MOD 1: İNTERAKTİF TEST (JSON FORMATI)
                    # ----------------------------------------
                    if secilen_mod == "5_soru_interaktif":
                        # JSON Modunu açıyoruz
                        prompt = f"""
                        '{konu_basligi}' konusuyla ilgili {sinif} seviyesinde 5 adet çoktan seçmeli soru hazırla.
                        
                        ÖNEMLİ: Çıktıyı SADECE aşağıdaki JSON formatında ver. Başka hiçbir metin yazma.
                        
                        [
                          {{
                            "soru": "Soru metni buraya",
                            "secenekler": ["A) ...", "B) ...", "C) ...", "D) ..."],
                            "dogru_cevap": "Doğru olan seçenek (örn: A) ...)",
                            "aciklama": "Neden yanlış olduğuna veya doğru olduğuna dair kısa açıklama."
                          }},
                          ...
                        ]
                        """
                        # JSON verisi alırken 'stream=False' daha güvenli (bütünlüğü bozulmasın)
                        response = st.session_state.chat_session.send_message(prompt)
                        
                        # JSON Temizleme (Bazen markdown ```json ekliyor)
                        text_data = response.text.replace("```json", "").replace("```", "").strip()
                        test_data = json.loads(text_data)
                        
                        # Veriyi state'e kaydet
                        st.session_state.aktif_test_verisi = test_data
                        st.session_state.messages.append({"role": "user", "content": f"⚡ **Mod:** {konu_basligi} hakkında İnteraktif Test başlattım."})
                    
                    # ----------------------------------------
                    # MOD 2 & 3: NORMAL METİN (STREAMING)
                    # ----------------------------------------
                    else:
                        final_prompt = ""
                        if secilen_mod == "yazili":
                            final_prompt = f"'{konu_basligi}' konusuyla ilgili 5 adet klasik (açık uçlu) yazılı sınav sorusu hazırla. Sorular düşündürücü olsun. En sona örnek cevapları ekle."
                        elif secilen_mod == "konu_anlatimi":
                            final_prompt = f"'{konu_basligi}' konusunu bana {sinif} seviyesinde, eğlenceli, emojili ve maddeler halinde harika bir şekilde anlat. Unutmayacağım ipuçları ver."

                        response_stream = st.session_state.chat_session.send_message(final_prompt, stream=True)
                        
                        full_text = ""
                        st.markdown("---")
                        stream_area = st.empty()
                        for chunk in response_stream:
                            full_text += chunk.text
                            stream_area.markdown(full_text + "▌")
                        stream_area.markdown(full_text)
                        
                        st.session_state.messages.append({"role": "assistant", "content": full_text})

                except Exception as e:
                    st.error(f"Hata: {e}")
        
        elif buton_tiklandi and not isim:
            st.warning("⚠️ Lütfen önce yukarıdan adını gir.")
        elif buton_tiklandi and not konu_basligi:
            st.warning("⚠️ Lütfen bir konu başlığı yaz.")

    # --- İNTERAKTİF TEST GÖSTERİM ALANI ---
    if st.session_state.aktif_test_verisi:
        st.markdown("---")
        st.subheader(f"📝 {konu_basligi} - Mini Test")
        
        # Her soruyu döngüyle bas
        for i, soru_data in enumerate(st.session_state.aktif_test_verisi):
            with st.container():
                st.markdown(f"**{i+1}. {soru_data['soru']}**")
                
                # Radio button (seçenekler)
                # Key benzersiz olmalı (soru indexi)
                secim = st.radio(
                    label="Cevabınız:",
                    options=soru_data['secenekler'],
                    key=f"soru_{i}",
                    index=None  # Başlangıçta hiçbiri seçili olmasın
                )
                
                # Kontrol Butonu
                if st.button(f"Soru {i+1} Kontrol Et", key=f"btn_{i}"):
                    if secim:
                        if secim == soru_data['dogru_cevap']:
                            st.success("✅ Tebrikler! Doğru cevap.")
                            st.caption(f"💡 {soru_data['aciklama']}") # Doğruysa da açıklama görsün pekişsin
                        else:
                            st.error("❌ Maalesef yanlış.")
                            st.warning(f"👉 Doğru Cevap: {soru_data['dogru_cevap']}")
                            st.info(f"ℹ️ **Açıklama:** {soru_data['aciklama']}")
                    else:
                        st.warning("Lütfen bir şık işaretle.")
                
                st.markdown("---") # Sorular arası çizgi


# ==========================================
# 6. SOHBET VE İÇERİK GÖSTERİMİ
# ==========================================
else:
    col_reset, col_dummy = st.columns([1, 2])
    with col_reset:
        if st.button("🔄 Başka Soruya/Konuya Geç", on_click=yeni_soru_yukle, type="secondary"):
            pass

    for message in st.session_state.messages:
        if message["role"] == "audio":
            st.audio(message["content"], format="audio/mp3")
        else:
            with st.chat_message(message["role"], avatar="🧠" if message["role"] == "assistant" else "👤"):
                st.markdown(message["content"])

    # --- FOOTER ---
    st.markdown("""<div class="footer">© Zekai uygulaması <b>Sinan Sayılır</b> tarafından geliştirilmiştir.</div>""", unsafe_allow_html=True)

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
            
            if st.session_state.ses_aktif:
                ses_verisi = metni_oku(full_response)
                if ses_verisi:
                    st.audio(ses_verisi, format="audio/mp3", autoplay=True)
                    st.session_state.messages.append({"role": "audio", "content": ses_verisi})
        except Exception as e:
            st.error(f"Hata: {e}")
