# MediExplain AI

MediExplain AI is a production-shaped Streamlit web application for explaining prescriptions, medicines, lab reports, and medical terminology using OCR plus Groq-powered LLM responses.

It is an educational assistant only. It does not diagnose, prescribe, or replace qualified medical care.

## Features

- Healthcare SaaS-style Streamlit dashboard
- Prescription image/PDF upload
- OCR enhancement and extraction
- LLM-assisted OCR correction with original text preserved
- Structured prescription extraction
- Medicine explanations with safety warnings
- Lab report OCR and general reference range comparison
- Medical dictionary
- AI health chat with memory
- Multilingual explanation support: English, Malayalam, Hindi, Tamil
- Text-to-speech playback
- SQLite offline history
- Local medicine reminders
- PDF and JSON export
- Modular service, repository, model, database, and page architecture

## Architecture

```text
app.py
pages/
core/
services/
repositories/
models/
utils/
database/
config/
static/css/
sample_data/
```

The app uses a feature-oriented Streamlit UI with shared services for Groq, OCR, PDF export, translation, speech, reminders, and persistence.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
streamlit run app.py
```

Add your Groq key to `.env`:

```env
GROQ_API_KEY=your_key
```

For image OCR, install the Tesseract engine. The app can still run without it, but OCR will be limited.

## Deployment

### Streamlit Community Cloud

1. Push the repository to GitHub.
2. Set `GROQ_API_KEY` in Streamlit secrets.
3. Use `app.py` as the entrypoint.

### Render

1. Create a Web Service from the repository.
2. Build command: `pip install -r requirements.txt`
3. Start command: `streamlit run app.py --server.address=0.0.0.0 --server.port=$PORT`
4. Add `GROQ_API_KEY` as an environment variable.

### Docker

```bash
docker build -t mediexplain-ai .
docker run -p 8501:8501 --env-file .env mediexplain-ai
```

### Hugging Face Spaces

1. Create a Streamlit Space.
2. Upload the repository files.
3. Add `GROQ_API_KEY` as a Space secret.
4. Ensure `requirements.txt` is present.

## Security And Privacy Notes

- Store secrets in environment variables.
- Avoid logging sensitive medical information.
- Uploaded files and history are stored locally under `data/`.
- Validate all uploaded files before production use.
- Add authentication and encrypted storage before multi-user deployment.

## Future Enhancements

- Medicine interaction checker
- Allergy detection
- Gemini Vision or PaddleOCR support
- User accounts and encrypted cloud sync
- Doctor portal
- Emergency workflow integrations
