FROM python:3.13-slim AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements.txt && useradd --create-home --uid 10001 querypilot
COPY --chown=querypilot:querypilot app ./app
USER querypilot
EXPOSE 8007
HEALTHCHECK --interval=15s --timeout=5s --start-period=20s CMD python -c "import httpx; httpx.get('http://127.0.0.1:8007/ready').raise_for_status()"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8007", "--no-access-log"]
FROM runtime AS test
USER root
COPY requirements-dev.txt .
RUN pip install --no-cache-dir --require-hashes -r requirements-dev.txt
COPY tests ./tests
COPY pytest.ini .
USER querypilot
CMD ["python", "-m", "pytest", "-q"]
