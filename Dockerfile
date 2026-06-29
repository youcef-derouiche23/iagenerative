# Image de production pour AISCA-Cinema (Streamlit)
# Build : docker build -t aisca-cinema .
# Run   : docker run -p 8501:8501 --env-file .env aisca-cinema
FROM python:3.11-slim

# Dépendances système minimales (compilation de certaines wheels)
RUN apt-get update && apt-get install -y --no-install-recommends \
        build-essential \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Installer torch en version CPU (image plus légère, pas de CUDA)
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Dépendances applicatives (couche cache séparée du code)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Code applicatif
COPY . .

# Pré-télécharger le modèle SBERT dans l'image (démarrage plus rapide)
RUN python -c "from sentence_transformers import SentenceTransformer; \
    SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')"

EXPOSE 8501

# Healthcheck Streamlit
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8501/_stcore/health')" || exit 1

ENTRYPOINT ["streamlit", "run", "app.py", \
            "--server.port=8501", "--server.address=0.0.0.0", \
            "--server.headless=true"]
