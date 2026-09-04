from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import os

from app.config import settings
from app.database import engine, Base
from app.seed import seed_database
from app.routers import auth, collaborator, supervisor, admin, campaigns, feedback, trainings

# Initialize DB tables & seed data on startup
Base.metadata.create_all(bind=engine)
seed_database()

app = FastAPI(title=settings.PROJECT_NAME)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(auth.router)
app.include_router(collaborator.router)
app.include_router(supervisor.router)
app.include_router(admin.router)
app.include_router(campaigns.router)
app.include_router(feedback.router)
app.include_router(trainings.router)

# Dynamic Route for Uploaded Training Files (supports Vercel /tmp)
@app.get("/static/uploads/trainings/{filename}")
def serve_training_upload_file(filename: str):
    import tempfile
    tmp_path = os.path.join(tempfile.gettempdir(), "uploads", "trainings", filename)
    if os.path.exists(tmp_path):
        return FileResponse(tmp_path)
    static_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "uploads", "trainings", filename)
    if os.path.exists(static_path):
        return FileResponse(static_path)
    return FileResponse(os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "index.html"))

# Mount Static Files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/manifest.json")
def get_manifest():
    return FileResponse(os.path.join(static_dir, "manifest.json"), media_type="application/json")

@app.get("/sw.js")
def get_sw():
    return FileResponse(os.path.join(static_dir, "sw.js"), media_type="application/javascript")

@app.get("/{full_path:path}")
def serve_spa(full_path: str):
    if full_path.startswith("api/"):
        return {"error": "Endpoint not found"}
    file_path = os.path.join(static_dir, full_path)
    if os.path.exists(file_path) and os.path.isfile(file_path):
        return FileResponse(file_path)
    return FileResponse(os.path.join(static_dir, "index.html"))
