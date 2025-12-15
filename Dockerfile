# 1. Python'un hafif bir sürümünü temel al
FROM python:3.9-slim

# 2. Çalışma klasörünü ayarla
WORKDIR /app

# 3. Gerekli sistem araçlarını yükle (Opencv gibi kütüphaneler için gerekebilir)
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

# 4. Dosyaları kopyala
COPY . .

# 5. Kütüphaneleri yükle (requirements.txt dosyasını oluşturacağız)
RUN pip install -r requirements.txt

# 6. Uygulamanın çalışacağı portu aç
EXPOSE 8501

# 7. Sağlık kontrolü (Uygulama çöküp çökmediğini kontrol eder)
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

# 8. Uygulamayı başlat
ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
