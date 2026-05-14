# LegalMind Agent

Assistant juridique intelligent base sur les lois tunisiennes.

## Structure
- backend/ : API FastAPI, RAG, agent IA
- frontend/ : interface Gradio
- sources/ : PDF juridiques tunisiens (arabe)
- data/ : index vectoriel ChromaDB
- uploads/ : documents utilisateur
- scripts/ : scripts utilitaires (ingestion)

## Prerequis
- Python 3.10+
- Cle API Groq

## Configuration
Copiez `.env.example` vers `.env` et remplissez les valeurs.

## Lancer
1) Installer les dependances
```
pip install -r backend/requirements.txt
```
2) Ingestion des lois tunisiennes
```
python scripts/ingest.py
```
3) API backend
```
uvicorn backend.app.main:app --reload
```
4) UI Gradio
```
python frontend/app.py
```

## Notes
- Cette version inclut RAG + agent avec deux tools: recherche juridique et analyse de contrat.
- Les reponses incluent des citations (source + page).
