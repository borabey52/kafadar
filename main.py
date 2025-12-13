import streamlit as st
import google.generativeai as genai
from PIL import Image
import edge_tts
import asyncio
import io
import re
import base64
import time

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
    
    /* Genel Buton Stili */
    .stButton>button {
        background-color: #F4D03F; color: #17202A; border-radius: 15px;
        font-weight: bold; border: none; padding: 12px 24px; transition: all 0.3s;
        width: 100%;
        border: 2px solid transparent;
    }
    .stButton>button:hover {
        background-color: #F1C40F; transform: scale(1.02); box-shadow: 0 4px 8px rgba(0,0,0,0.2);
    }
    
    /* Konumatik Alanı Özel Tasarımı */
    .konu-box {
        background-color: #ebf5fb;
        border: 2px solid #3498db;
        border-radius: 15px;
        padding: 20px;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    
    [data-testid="stTextInput"] > div > div { border: none !important; background-color: #f0f2f6; border-radius: 10px; }
    [data-testid="stSelectbox"] > div > div { border: none !important; background-color: #f0f2f6; border-radius: 10px; }
    
    /* MİKROFON SABİTLEME */
    [data-testid="stAudioInput"] {
        position: fixed; bottom: 110px; left: 0; right: 0; margin: 0 auto;
        width: 100%; max-width: 700px; z-index: 999;
        background-color: rgba(252, 253, 253, 0.95);
        padding: 10px 20px; border-radius: 20px 20px 0 0; border-top: 1px solid #eee;
        backdrop-filter: blur(5px);
    }
    
    .footer { text-align: center; color: #888; font-size: 12px; margin-top: 50px; padding-bottom: 20px; }
    .pekistirme-box { background-color: #e8f6f3; border: 2px dashed #1abc9c; border-radius: 15px; padding: 20px; margin-top: 20px; margin-bottom: 20px; }
    .test-box { background-color: #fef9e7; border: 2px solid #f1c40f; border-radius: 15px; padding: 20px; margin-top: 20px; }
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
if 'yeni_pratik_soru' not in st.session_state: st.session_state.yeni_pratik_soru = None
if 'hazirlanan_test' not in st.session_state: st.session_state.hazirlanan_test = None

def yeni_soru_yukle():
    st.session_state.messages = []
    st.session_state.chat_session = None
    st.session_state.kamera_acik = False
    st.session_state.yeni_pratik_soru = None
    st.session_state.hazirlanan_test = None

def metni_temizle_tts_icin(text):
    text = re.sub(r'(?i)cevap', 'yanıt', text)
    text = re.sub(r'(?i)cevab', 'yanıt', text)
    text = text.replace("#", "").replace("*", "")
    temiz_text = re.sub(r"[^a-zA-Z0-9çğıöşüÇĞIÖŞÜ\s\.,!\?\-':;]", "", text)
    return temiz_text.strip()

def sesi_yaziya_cevir(audio_bytes):
    try:
        # MODEL GÜNCELLENDİ: gemini-1.5-flash-latest
        model = genai.GenerativeModel("gemini-flash-latest") 
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
# 5. İÇERİK OLUŞTURMA ALANI (RESİM YÜKLEME VE KONU ÇALIŞMA)
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
                with st.spinner("Zekai jet hızında inceliyor... 🚀"):
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
                        
                        # MODEL GÜNCELLENDİ: gemini-1.5-flash-latest
                        model = genai.GenerativeModel("gemini-flash-latest") 
                        st.session_state.chat_session = model.start_chat(
                            history=[{"role": "user", "parts": prompt_content}]
                        )
                        
                        # Streaming response
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

    # --- B) KONUMATİK: YENİ KONU ÇALIŞMA ALANI ---
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("### 🎯 Konumatik: Özel Çalışma Alanı")
    st.info("Resim yüklemek zorunda değilsin! İstediğin konuyu yaz, Zekai sana özel içerik hazırlasın.")

    with st.container(border=True):
        konu_basligi = st.text_input("Hangi konuya çalışmak istersin?", placeholder="Örn: Hücre Bölünmesi, Kesirler, Fiilimsiler...")
        
        c1, c2, c3, c4 = st.columns(4)
        
        buton_tiklandi = False
        secilen_mod = None
        
        if c1.button("📝 5 Soru Test"):
            secilen_mod = "5_soru"
            buton_tiklandi = True
        if c2.button("📝 10 Soru Test"):
            secilen_mod = "10_soru"
            buton_tiklandi = True
        if c3.button("✍️ Yazılı Provası"):
            secilen_mod = "yazili"
            buton_tiklandi = True
        if c4.button("📚 Konu Anlatımı"):
            secilen_mod = "konu_anlatimi"
            buton_tiklandi = True

        if buton_tiklandi and isim and konu_basligi:
            with st.spinner("Zekai içeriği hazırlıyor..."):
                try:
                    # Session yoksa başlat
                    if not st.session_state.chat_session:
                        system_prompt = f"Sen 'Zekai'. {sinif} öğrencisi {isim}'in koçusun. Konumuz: {konu_basligi}."
                        # MODEL GÜNCELLENDİ: gemini-1.5-flash-latest
                        model = genai.GenerativeModel("gemini-flash-latest") 
                        st.session_state.chat_session = model.start_chat(history=[{"role": "user", "parts": [system_prompt]}])
                        st.session_state.ilk_karsilama_yapildi = True

                    # Prompt Belirleme
                    final_prompt = ""
                    if secilen_mod == "5_soru":
                        final_prompt = f"'{konu_basligi}' konusuyla ilgili 5 soruluk harika bir test hazırla. Cevap anahtarı en sonda olsun."
                    elif secilen_mod == "10_soru":
                        final_prompt = f"'{konu_basligi}' konusuyla ilgili 10 soruluk kapsamlı bir test hazırla. Cevap anahtarı en sonda olsun."
                    elif secilen_mod == "yazili":
                        final_prompt = f"'{konu_basligi}' konusuyla ilgili klasik (açık uçlu) yazılı sınav soruları hazırla. Sorular düşündürücü olsun. En sona örnek cevapları ekle."
                    elif secilen_mod == "konu_anlatimi":
                        final_prompt = f"'{konu_basligi}' konusunu bana {sinif} seviyesinde, eğlenceli, emojili ve maddeler halinde harika bir şekilde anlat. Unutmayacağım ipuçları ver."

                    # Streaming ile cevap al
                    response_stream = st.session_state.chat_session.send_message(final_prompt, stream=True)
                    
                    full_text = ""
                    stream_area = st.empty()
                    for chunk in response_stream:
                        full_text += chunk.text
                        stream_area.markdown(full_text + "▌")
                    stream_area.empty() # İş bitince temizle
                    
                    # Mesajı geçmişe ekle
                    st.session_state.messages.append({"role": "user", "content": f"⚡ **Mod:** {konu_basligi} hakkında {secilen_mod} istedim."})
                    st.session_state.messages.append({"role": "assistant", "content": full_text})
                    
                    st.rerun()

                except Exception as e:
                    st.error(f"Hata: {e}")
        elif buton_tiklandi and not isim:
            st.warning("⚠️ Lütfen önce yukarıdan adını gir.")
        elif buton_tiklandi and not konu_basligi:
            st.warning("⚠️ Lütfen bir konu başlığı yaz.")


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

    # --- EKSTRA ÇALIŞMA ALANI ---
    if st.session_state.messages and st.session_state.messages[-1]["role"] in ["assistant", "audio"]:
        st.markdown("<br>", unsafe_allow_html=True)
        
        if not st.session_state.yeni_pratik_soru and not st.session_state.hazirlanan_test:
            
            son_mesaj = st.session_state.messages[-1]["content"]
            
            if "CEVAP ANAHTARI" not in son_mesaj:
                st.caption("🚀 Bu konuyu pekiştirelim mi?")
                soru_sayisi = st.radio("Test Uzunluğu:", [5, 10], horizontal=True, index=0)
                col_meydan, col_test = st.columns(2)
                
                with col_meydan:
                    if st.button("🥊 Meydan Oku (Tek Soru)", use_container_width=True):
                        with st.spinner("Hazırlanıyor..."):
                            try:
                                prompt = "Öğretmen sensin! Benzer YENİ BİR SORU yaz. Format:\n**SORU:** [Soru]\nA)...\nB)...\nC)...\nD)...\n**CEVAP_GIZLI:** [Cevap]"
                                resp = st.session_state.chat_session.send_message(prompt)
                                st.session_state.yeni_pratik_soru = resp.text
                                st.rerun()
                            except: st.error("Hata.")

                with col_test:
                    if st.button(f"📝 {soru_sayisi} Soruluk Test", use_container_width=True):
                        with st.spinner(f"Hazırlanıyor..."):
                            try:
                                prompt = f"Konuyla ilgili {soru_sayisi} adet test sorusu hazırla. Cevap anahtarı en sonda olsun."
                                resp_stream = st.session_state.chat_session.send_message(prompt, stream=True)
                                full_test_txt = ""
                                test_placeholder = st.empty()
                                for chunk in resp_stream:
                                    full_test_txt += chunk.text
                                    test_placeholder.markdown(full_test_txt + "▌")
                                st.session_state.hazirlanan_test = full_test_txt
                                st.rerun()
                            except: st.error("Hata.")

        # --- GÖRÜNÜM: TEK SORU ---
        if st.session_state.yeni_pratik_soru:
            try:
                parts = st.session_state.yeni_pratik_soru.split("**CEVAP_GIZLI:**")
                soru = parts[0].replace("**SORU:**", "").strip()
                cevap = parts[1].strip() if len(parts) > 1 else "Cevap yok."
                st.markdown(f'<div class="pekistirme-box"><h4>🥊 Meydan Okuma Sorusu</h4>{soru}</div>', unsafe_allow_html=True)
                with st.expander("👀 Cevabı Gör"):
                    st.info(cevap)
                    if st.button("Kapat"):
                        st.session_state.yeni_pratik_soru = None
                        st.rerun()
            except: st.write(st.session_state.yeni_pratik_soru)

        # --- GÖRÜNÜM: ÇOKLU TEST ---
        if st.session_state.hazirlanan_test:
            st.markdown(f'<div class="test-box"><h4>📝 Konu Tarama Testi</h4>', unsafe_allow_html=True)
            try:
                if "CEVAP ANAHTARI" in st.session_state.hazirlanan_test:
                    bolumler = st.session_state.hazirlanan_test.split("CEVAP ANAHTARI")
                    st.markdown(bolumler[0])
                    anahtar = bolumler[1]
                else:
                    st.markdown(st.session_state.hazirlanan_test)
                    anahtar = "Metnin içinde ara."
                st.markdown('</div>', unsafe_allow_html=True)
                with st.expander("🔑 Cevap Anahtarını Göster"):
                    st.success(f"**CEVAP ANAHTARI:** {anahtar}")
                    if st.button("Testi Bitir"):
                        st.session_state.hazirlanan_test = None
                        st.rerun()
            except: st.write(st.session_state.hazirlanan_test)

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
