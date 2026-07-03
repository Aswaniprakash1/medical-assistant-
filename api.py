from __future__ import annotations

import re
import tempfile
from pathlib import Path

from fastapi import FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.prompts import LAB_REPORT_PROMPT
from database.db import init_db
from models.schemas import HistoryRecord
from repositories.history_repository import HistoryRepository
from services.groq_service import GroqService
from services.ocr_service import OCRService
from services.reminder_service import ReminderService


GENERAL_RANGES = {
    "HbA1c": "Below 5.7%",
    "Creatinine": "0.6-1.3 mg/dL",
    "Vitamin D": "20-50 ng/mL",
    "Hemoglobin": "12-17.5 g/dL",
    "Cholesterol": "Below 200 mg/dL",
    "Uric Acid": "3.5-7.2 mg/dL",
    "TSH": "0.4-4.0 mIU/L",
    "Blood Sugar": "70-140 mg/dL depending on fasting/post-meal context",
}


class ChatRequest(BaseModel):
    messages: list[dict[str, str]]


class MedicineRequest(BaseModel):
    name: str
    context: str = ""


class ReminderRequest(BaseModel):
    medicine_name: str
    dosage: str
    days: list[str]
    reminder_time: str


app = FastAPI(title="MediExplain AI API")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict[str, bool]:
    return {"ok": True}


@app.get("/api/dashboard")
def dashboard() -> dict:
    history = HistoryRepository().list()
    reminders = ReminderService().upcoming()[:5]
    return {
        "stats": {
            "uploads": len(history),
            "medicines": sum(len(item.payload.get("medicines", [])) for item in history),
            "reports": sum(1 for item in history if item.record_type == "Lab Report"),
            "ai_reviews": sum(1 for item in history if item.ai_summary),
        },
        "history": [record.model_dump(mode="json") for record in history[:8]],
        "reminders": [reminder.model_dump(mode="json") for reminder in reminders],
    }


@app.get("/api/history")
def history(query: str = "", record_type: str = "All") -> list[dict]:
    records = HistoryRepository().list(query=query, record_type=record_type)
    return [record.model_dump(mode="json") for record in records]


@app.delete("/api/history/{record_id}")
def delete_history(record_id: int) -> dict[str, bool]:
    HistoryRepository().delete(record_id)
    return {"ok": True}


@app.post("/api/reminders")
def create_reminder(payload: ReminderRequest) -> dict[str, int]:
    reminder_id = ReminderService().add(
        payload.medicine_name,
        payload.dosage,
        payload.days,
        payload.reminder_time,
    )
    return {"id": reminder_id}


@app.post("/api/chat")
def chat(payload: ChatRequest) -> dict[str, str]:
    context = "\n".join(f"{message.get('role', 'user')}: {message.get('content', '')}" for message in payload.messages[-8:])
    response = GroqService().chat(f"Conversation so far:\n{context}\n\nAnswer the latest user question safely.")
    return {"response": response}


@app.post("/api/medicine")
def medicine(payload: MedicineRequest) -> dict[str, str]:
    return {"explanation": GroqService().medicine_explanation(payload.name, payload.context)}


@app.post("/api/prescriptions/analyze")
async def analyze_prescription(file: UploadFile = File(...), language: str = Form("English")) -> dict:
    ocr = OCRService()
    saved_path = await _save_upload_for_service(file, ocr)
    text = ocr.extract_text(saved_path)
    correction = ocr.correct_ocr(text)
    corrected_text = correction.get("corrected_text") or text
    structured = ocr.extract_prescription_json(corrected_text)
    medicines = structured.get("medicines", []) if isinstance(structured, dict) else []

    summaries = []
    groq = GroqService()
    for item in medicines or [{"name": "Detected medicine"}]:
        name = item.get("name") if isinstance(item, dict) else str(item)
        summaries.append({"name": name or "Medicine", "explanation": groq.medicine_explanation(name or "unknown medicine", corrected_text)})

    record_id = HistoryRepository().create(
        HistoryRecord(
            record_type="Prescription",
            title=file.filename or "Prescription",
            file_path=str(saved_path),
            ocr_text=text,
            corrected_text=corrected_text,
            ai_summary="\n\n".join(item["explanation"] for item in summaries),
            payload=structured if isinstance(structured, dict) else {"raw": structured},
        )
    )
    return {
        "id": record_id,
        "ocr_text": text,
        "correction": correction,
        "corrected_text": corrected_text,
        "structured": structured,
        "medicine_explanations": summaries,
        "language": language,
    }


@app.post("/api/labs/analyze")
async def analyze_lab(file: UploadFile = File(...)) -> dict:
    ocr = OCRService()
    saved_path = await _save_upload_for_service(file, ocr)
    text = ocr.extract_text(saved_path)
    values = _rough_extract_values(text)
    summary = GroqService().chat(f"Lab OCR text:\n{text}\n\nGeneral ranges:\n{GENERAL_RANGES}", LAB_REPORT_PROMPT)
    record_id = HistoryRepository().create(
        HistoryRecord(
            record_type="Lab Report",
            title=file.filename or "Lab Report",
            file_path=str(saved_path),
            ocr_text=text,
            ai_summary=summary,
            payload={"values": values},
        )
    )
    return {"id": record_id, "ocr_text": text, "values": values, "summary": summary}


async def _save_upload_for_service(file: UploadFile, ocr: OCRService) -> Path:
    suffix = Path(file.filename or "").suffix
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    class UploadedFileAdapter:
        name = file.filename or tmp_path.name

        def getvalue(self) -> bytes:
            return tmp_path.read_bytes()

    try:
        return ocr.save_upload(UploadedFileAdapter())
    finally:
        tmp_path.unlink(missing_ok=True)


def _rough_extract_values(text: str) -> list[dict[str, str]]:
    rows = []
    for test, ref in GENERAL_RANGES.items():
        match = re.search(rf"({re.escape(test)}).*?([\d.]+)\s*([A-Za-z/%]+)?", text, re.IGNORECASE)
        if match:
            rows.append({"test": test, "value": match.group(2), "unit": match.group(3) or "", "general_range": ref})
    return rows
