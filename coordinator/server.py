from contextlib import asynccontextmanager
from fastapi import FastAPI
from .core import node
from .routes import koi_net_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    
    node.network.save_queues()

app = FastAPI(lifespan=lifespan)
app.include_router(koi_net_router)