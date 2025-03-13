import uvicorn

uvicorn.run("consumer.routes:server", port=8001)