from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI
import inngest.fast_api

from inngest_client import client
from functions import say_hello

app = FastAPI(title="Background Job API")
inngest.fast_api.serve(app, client, [say_hello], serve_path="/api/inngest")


@app.get("/health")
def health():
    return {"status": "ok"}
