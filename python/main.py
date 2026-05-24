import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from route.app import router

app = FastAPI(title="Blog Agent", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


@app.get("/health")
def health():
    return {"ok": True}


if __name__ == "__main__":
    # 仅监听本机，由 Spring Boot 内网转发，勿暴露公网
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
