from dotenv import load_dotenv

load_dotenv()

import uuid

import inngest
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel
import inngest.fast_api

from inngest_client import client
from functions import say_hello, make_report
from store import reports

app = FastAPI(title="Background Job API")
inngest.fast_api.serve(app, client, [say_hello, make_report], serve_path="/api/inngest")


@app.get("/health")
def health():
    return {"status": "ok"}


class CreateReportIn(BaseModel):
    topic: str | None = None


@app.post("/reports")
def create_report(payload: CreateReportIn):
    if not payload.topic:
        raise HTTPException(status_code=400, detail="topic is required")

    report_id = str(uuid.uuid4())
    reports[report_id] = {"id": report_id, "topic": payload.topic, "status": "pending"}

    client.send_sync(
        inngest.Event(
            name="report/requested",
            data={"id": report_id, "topic": payload.topic},
        )
    )

    return JSONResponse(status_code=202, content={"id": report_id, "status": "pending"})


@app.get("/reports/{report_id}")
def get_report(report_id: str):
    report = reports.get(report_id)
    if report is None:
        raise HTTPException(status_code=404, detail="report not found")
    return report
