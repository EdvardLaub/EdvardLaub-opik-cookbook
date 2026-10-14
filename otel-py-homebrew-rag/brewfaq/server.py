"""FastAPI service: POST /ask {"question": "..."} -> {"answer": "...", "sources": [...]}."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI
from pydantic import BaseModel, Field

load_dotenv()  # walks up the tree, so a repo-root .env is found too

from .corpus import load_chunks  # noqa: E402  (after load_dotenv so model env vars apply)
from .rag import BrewRag  # noqa: E402


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)


class AskResponse(BaseModel):
    answer: str
    sources: list[str]


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.rag = BrewRag(load_chunks())
    app.state.rag.build_index()
    yield


app = FastAPI(title="Hollowbrook brewing FAQ", lifespan=lifespan)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    answer, hits = app.state.rag.ask(req.question)
    return AskResponse(answer=answer, sources=list(dict.fromkeys(h.chunk.source for h in hits)))


def main() -> None:
    uvicorn.run(app, host="127.0.0.1", port=int(os.getenv("PORT", "4430")), log_level="warning")


if __name__ == "__main__":
    main()
