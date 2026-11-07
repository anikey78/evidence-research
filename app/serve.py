"""Production container entry point."""
import importlib
import os

if __name__ == "__main__":
    uvicorn = importlib.import_module("uvicorn")
    server_host = os.environ.get("HOST", "127.0.0.1")
    uvicorn.run(
        "app.main:app",
        host=server_host,
        port=int(os.environ.get("PORT", "8000")),
        access_log=False,
    )
