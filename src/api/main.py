from fastapi import FastAPI

app = FastAPI(title="Agentic OS")

@app.get("/")
def read_root():
    return {"status": "ok", "message": "Agentic OS Orchestrator is running"}
