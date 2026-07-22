from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title="Telegram Mini App API",
    description="API для записи к парикмахеру",
    version="1.0.0"
)

# CORS для React (Mini App)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {
        "message": "Telegram Mini App API работает!",
        "status": "ok",
        "version": "1.0.0"
    }

@app.get("/health")
async def health():
    return {"status": "ok"}