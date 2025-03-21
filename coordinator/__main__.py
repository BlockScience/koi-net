import uvicorn
from .config import port

uvicorn.run("coordinator.server:app", port=port)