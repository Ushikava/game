from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from routers import auth, game

app = FastAPI(title="Godot/FastAPI game API")


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(router=game, prefix="/api")
app.include_router(router=auth, prefix="/api")