"""Retriever: an in-memory vector store over the handbook chunks."""

import os

import opik
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

from boating_rag.corpus import load_chunks


def build_retriever(embeddings: Embeddings | None = None, k: int | None = None):
    """Embed every chunk once and return a top-k similarity retriever."""
    k = k or int(os.getenv("RAG_TOP_K", "3"))  # try RAG_TOP_K=1 to watch precision drop
    embeddings = embeddings or OpenAIEmbeddings(model="text-embedding-3-small")
    store = InMemoryVectorStore.from_texts(load_chunks(), embeddings)
    return store.as_retriever(search_kwargs={"k": k})


# OpikTracer does not log the LangChain retriever run here (the retrieve node
# has no child span), so we wrap the lookup ourselves: this adds a "tool" span
# named vector_search under retrieve, with the question as input and the chunks as output.
@opik.track(name="vector_search", type="tool")
def search(retriever, question: str) -> list[str]:
    """Return the text of the top-k chunks for a question."""
    return [doc.page_content for doc in retriever.invoke(question)]
