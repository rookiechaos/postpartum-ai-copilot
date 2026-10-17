"""Retrieve explicitly approved public material; no automatic demo or medical corpus."""

from datetime import date, datetime, timedelta, timezone
from ipaddress import ip_address
from typing import List, Optional
from urllib.parse import urlsplit

from config.settings import get_settings
from services.logging_service import logger
from utils.runtime_paths import resolve_runtime_path

try:
    from langchain_openai import OpenAIEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
except ImportError:
    try:
        from langchain.embeddings import OpenAIEmbeddings
        from langchain.vectorstores import Chroma
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.schema import Document
    except ImportError:
        OpenAIEmbeddings = Chroma = RecursiveCharacterTextSplitter = Document = None


# Existing collections, including the previous unlabelled sample corpus, stay on
# disk but are never queried. Operators must explicitly approve/re-ingest sources.
PUBLIC_SOURCE_COLLECTION = "postpartum_public_sources_v2"


def approved_source_metadata(value):
    """An operator's publication attestation, not automatic verification of a source."""
    if not isinstance(value, dict) or value.get("approved") is not True:
        return None
    url = value.get("source_url") or value.get("url") or value.get("source")
    title = value.get("title")
    reviewed = value.get("reviewed_on")
    if not isinstance(url, str) or len(url) > 2000 or not isinstance(title, str) or not title.strip():
        return None
    try:
        parts = urlsplit(url.strip())
        _ = parts.port
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password:
            return None
        host = parts.hostname.lower().rstrip(".")
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return None
        try:
            if not ip_address(host).is_global:
                return None
        except ValueError:
            if "." not in host:
                return None
        checked = date.fromisoformat(reviewed)
        if checked > datetime.now(timezone(timedelta(hours=9))).date():
            return None
    except (TypeError, ValueError):
        return None
    return {"approved": True, "source_url": parts.geturl(), "title": title.strip()[:150],
            "reviewed_on": checked.isoformat()}


class RAGService:
    """Retrieve curated public documents without claiming medical validation."""

    def __init__(self):
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.embedding_model = settings.openai_embedding_model
        self.vector_db_path = str(resolve_runtime_path(settings.vector_db_path, "vector_db"))
        self.embeddings = None
        self.vectorstore = None
        self.initialized = False

    async def initialize(self):
        """Open a separate, initially empty collection; never import demo content."""
        if self.initialized:
            return
        try:
            if not OpenAIEmbeddings or not Chroma or not self.api_key:
                return
            self.embeddings = OpenAIEmbeddings(openai_api_key=self.api_key, model=self.embedding_model)
            self.vectorstore = Chroma(collection_name=PUBLIC_SOURCE_COLLECTION,
                persist_directory=self.vector_db_path, embedding_function=self.embeddings)
            self.initialized = True
        except Exception as error:
            logger.log_error(error, context={"action": "rag_initialization"})
            self.initialized = False

    async def search(self, query: str, k: int = 3) -> str:
        return (await self.search_with_sources(query, k))["context"]

    async def search_with_sources(self, query: str, k: int = 3) -> dict:
        """Only approved, attributed chunks may enter the prompt or source list."""
        if not self.initialized or self.vectorstore is None or not query:
            return {"context": "", "sources": []}
        try:
            results = self.vectorstore.similarity_search(query, k=k, filter={"approved": True})
            context_parts, sources = [], []
            for document in results:
                metadata = approved_source_metadata(document.metadata)
                if metadata is None or not document.page_content.strip():
                    continue
                context_parts.append(f"[Retrieved item {len(context_parts) + 1}] {document.page_content}")
                sources.append({"url": metadata["source_url"], "title": metadata["title"]})
            if not context_parts:
                return {"context": "", "sources": []}
            notice = "\n\n[Source note] These are operator-approved public materials, not a clinical assessment. Apply the Japan-specific instructions and do not invent service details."
            return {"context": "\n\n".join(context_parts) + notice, "sources": sources}
        except Exception as error:
            logger.log_error(error, context={"action": "rag_search"})
            return {"context": "", "sources": []}

    async def add_documents(self, documents: List[str], metadata: Optional[List[dict]] = None):
        """Explicit operator ingestion into the new collection; no legacy auto-migration."""
        if not documents or metadata is None or len(documents) != len(metadata):
            raise ValueError("Every public document requires approval, a title, an HTTPS source URL and a review date")
        selected = [approved_source_metadata(item) for item in metadata]
        if any(item is None for item in selected) or any(not isinstance(text, str) or not text.strip() for text in documents):
            raise ValueError("Only explicitly approved public documents with valid source metadata may be indexed")
        if not self.initialized:
            await self.initialize()
        if self.vectorstore is None or not RecursiveCharacterTextSplitter:
            return False
        try:
            splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
            chunks = splitter.create_documents(documents, metadatas=selected)
            self.vectorstore.add_documents(chunks)
            self.vectorstore.persist()
            return True
        except Exception as error:
            logger.log_error(error, context={"action": "rag_add_documents"})
            return False
