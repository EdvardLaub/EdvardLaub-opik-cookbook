"""Retriever: an in-memory vector store over the handbook chunks."""

from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore
from langchain_openai import OpenAIEmbeddings

from boating_rag.corpus import load_chunks


def build_retriever(embeddings: Embeddings | None = None, k: int = 3):
    """Embed every chunk once and return a top-k similarity retriever."""
    embeddings = embeddings or OpenAIEmbeddings(model="text-embedding-3-small")
    store = InMemoryVectorStore.from_texts(load_chunks(), embeddings)
    return store.as_retriever(search_kwargs={"k": k})


def search(retriever, question: str) -> list[str]:
    """Return the text of the top-k chunks for a question."""
    return [doc.page_content for doc in retriever.invoke(question)]
