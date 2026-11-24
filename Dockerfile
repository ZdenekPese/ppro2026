FROM python:3.12-slim

# Nastavení Python prostředí
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instalace curl pro healthcheck
RUN apt-get update && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Instalace Python závislostí před kopírováním zdrojového kódu (efektivní cache vrstev)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Vytvoření neprivilegovaného systémového uživatele (zákaz běhu pod rootem)
RUN groupadd --system appgroup && useradd --system --gid appgroup --create-home appuser

# Zkopírování zdrojového kódu a normalizace konců řádků entrypoint skriptu
COPY --chown=appuser:appgroup . .
RUN sed -i 's/\r$//' /app/docker/entrypoint.sh && chmod +x /app/docker/entrypoint.sh

USER appuser

EXPOSE 8000

ENTRYPOINT ["/app/docker/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
