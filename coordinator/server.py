from contextlib import asynccontextmanager
from fastapi import FastAPI
from .core import network
from .routes import koi_net_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    
    network.save_queues()

app = FastAPI(lifespan=lifespan)
app.include_router(koi_net_router)