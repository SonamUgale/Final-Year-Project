import os
import uvicorn

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = os.environ.get("HOST", "0.0.0.0")
    print(f"Starting DarkShield AI Backend on {host}:{port}...")
    uvicorn.run("backend.app:app", host=host, port=port, reload=False)
