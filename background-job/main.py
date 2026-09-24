from fastapi import FastAPI

app = FastAPI(title="Background Job API")


@app.get("/health")
def health():
    return {"status": "ok"}
