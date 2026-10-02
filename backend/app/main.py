from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

try:
    # preferred when running as a package from the backend folder
    from .routers import chatbot, transport, booking, admin, auth
except Exception:
    # fallback when running with module path like backend.app.main
    from app.routers import chatbot, transport, booking, admin

app = FastAPI(title="TravelMate AI - Backend")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chatbot.router, prefix="/chat", tags=["chatbot"])
app.include_router(transport.router, prefix="/transport", tags=["transport"])
app.include_router(booking.router, prefix="/booking", tags=["booking"])
app.include_router(admin.router, prefix="/admin", tags=["admin"])
app.include_router(auth.router, prefix="/auth", tags=["auth"])

@app.get("/")
def root():
    return {"status": "ok", "service": "TravelMate AI Backend"}
