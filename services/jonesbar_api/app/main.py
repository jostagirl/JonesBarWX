from fastapi import FastAPI

app = FastAPI(title="Jones Bar API")

@app.get("/health")
def health():
    return {"status": "ok"}
