import os
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse

from db import get_connection, init_db
from render import generate_report_pdf

REPORTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports")

app = FastAPI(title="PDF Report Generator")
init_db()
os.makedirs(REPORTS_DIR, exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/reports", status_code=201)
def create_report():
    conn = get_connection()
    report_id = conn.execute(
        "INSERT INTO reports (path, created_at) VALUES ('', ?)", (datetime.utcnow().isoformat(),)
    ).lastrowid
    conn.commit()

    pdf_path = os.path.join(REPORTS_DIR, f"{report_id}.pdf")
    generate_report_pdf(pdf_path)

    conn.execute("UPDATE reports SET path = ? WHERE id = ?", (pdf_path, report_id))
    conn.commit()
    conn.close()

    return {"id": report_id, "file": f"/reports/{report_id}/file"}


@app.get("/reports/{report_id}")
def get_report(report_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    if row is None:
        raise HTTPException(status_code=404, detail="Report not found")
    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "file": f"/reports/{row['id']}/file",
    }


@app.get("/reports/{report_id}/file")
def get_report_file(report_id: int):
    conn = get_connection()
    row = conn.execute("SELECT * FROM reports WHERE id = ?", (report_id,)).fetchone()
    conn.close()
    if row is None or not os.path.exists(row["path"]):
        raise HTTPException(status_code=404, detail="Report not found")
    return FileResponse(row["path"], media_type="application/pdf", filename=f"report-{report_id}.pdf")
