"""Vercel sample analytics and visitor-owned CSVs. Private PostgreSQL uses app.main."""
import os
import sys
import secrets
from pathlib import Path
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'backend'))
# This entrypoint offers request-bounded, no-model sample and visitor-data workflows.
os.environ.update(APP_ENVIRONMENT='development',DATABASE_URL='sqlite:////tmp/querypilot-demo-v2.db',
                  WAREHOUSE_DATABASE_URL='',PUBLIC_DEMO='true',SEED_DEMO='true',DEMO_ACCOUNTS='true',
                  EMBEDDED_WORKER='false',AUTO_CREATE_SCHEMA='true',ALLOW_LIVE_AI='false',OPENAI_API_KEY='')
os.environ.setdefault('JWT_SECRET',secrets.token_urlsafe(64))
from app.main import app
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from app.persistence.models import Base
from app.persistence import db
from app.warehouse.service import seed_all
from sqlalchemy.orm import Session
# Some serverless adapters omit ASGI lifespan; initialize this isolated demo explicitly.
Base.metadata.create_all(db.engine)
with Session(db.engine) as session:seed_all(session)
static=root/'frontend'/'dist'
if static.exists():
    app.mount('/assets',StaticFiles(directory=static/'assets'),name='assets')
    if (static/'recordings').is_dir():
        app.mount('/recordings',StaticFiles(directory=static/'recordings',html=True),name='recordings')
    @app.get('/{path:path}',include_in_schema=False)
    def frontend(path:str):
        if path.startswith(('api/','health/','ready/')):
            from fastapi import HTTPException
            raise HTTPException(404,'Not found')
        return FileResponse(static/'index.html')
