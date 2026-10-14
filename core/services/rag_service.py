"""
RAG Service - Retrieval Augmented Generation for general information from reputable sources.

Used for content safety only (e.g. grounding AI responses in general-info sources);
not medical validation or certification. The product is a companion/support tool, not a medical device.
"""

import os
from typing import List, Optional
from config.settings import get_settings
from services.logging_service import logger
from utils.runtime_paths import resolve_runtime_path

# Try to import langchain components with fallback
try:
    from langchain_openai import OpenAIEmbeddings
    from langchain.vectorstores import Chroma
    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain.schema import Document
    LANGCHAIN_AVAILABLE = True
except ImportError:
    # Fallback for different langchain versions
    try:
        from langchain.embeddings import OpenAIEmbeddings
        from langchain.vectorstores import Chroma
        from langchain.text_splitter import RecursiveCharacterTextSplitter
        from langchain.schema import Document
        LANGCHAIN_AVAILABLE = True
    except ImportError:
        LANGCHAIN_AVAILABLE = False
        OpenAIEmbeddings = None
        Chroma = None
        RecursiveCharacterTextSplitter = None
        Document = None


class RAGService:
    """RAG service for retrieving trusted medical information"""
    
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.openai_api_key
        self.embedding_model = settings.openai_embedding_model
        self.vector_db_path = str(resolve_runtime_path(settings.vector_db_path, "vector_db"))
        self.embeddings = None
        self.vectorstore = None
        self.initialized = False
    
    async def initialize(self):
        """Initialize RAG service with embeddings and vector store"""
        try:
            if not OpenAIEmbeddings or not Chroma:
                logger.log_warning("RAG dependencies not available. RAG features will be disabled.")
                self.initialized = False
                return
            
            # Initialize embeddings
            self.embeddings = OpenAIEmbeddings(
                openai_api_key=self.api_key,
                model=self.embedding_model
            )
            
            # The configured storage path is resolved and restricted during initialization.
            if os.path.exists(self.vector_db_path):
                # Load existing vector store
                self.vectorstore = Chroma(
                    persist_directory=self.vector_db_path,
                    embedding_function=self.embeddings
                )
            else:
                # Create new vector store with sample medical information
                await self._initialize_with_sample_data()
            
            self.initialized = True
        except Exception as e:
            logger.log_error(e, context={"action": "rag_initialization"})
            self.initialized = False
    
    async def _initialize_with_sample_data(self):
        """Initialize vector store with sample trusted medical information"""
        if not LANGCHAIN_AVAILABLE or not RecursiveCharacterTextSplitter or not Document:
            logger.log_warning("Cannot initialize RAG: missing dependencies")
            return
        
        # Sample trusted medical information about postpartum and newborn care
        sample_docs = [
            """Newborn Feeding Guidelines:
- Newborns typically feed 8-12 times per day in the first weeks
- Breastfed babies may feed more frequently (every 1-3 hours)
- Formula-fed babies typically feed every 3-4 hours
- Watch for hunger cues: rooting, sucking motions, bringing hands to mouth
- Signs of adequate feeding: 6+ wet diapers per day, steady weight gain, alertness when awake""",
            
            """Postpartum Recovery:
- Vaginal birth recovery: typically 6-8 weeks
- C-section recovery: typically 6-8 weeks, avoid heavy lifting
- Normal bleeding (lochia): can last 4-6 weeks, should gradually decrease
- Pain management: consult healthcare provider for appropriate medications
- Red flags: heavy bleeding (soaking pad in 1 hour), fever, severe pain, foul-smelling discharge""",
            
            """Newborn Sleep Patterns:
- Newborns sleep 14-17 hours per day in first weeks
- Sleep is fragmented into 2-4 hour periods
- It's normal for newborns to wake frequently for feeding
- Safe sleep: place baby on back, firm mattress, no loose bedding
- Room-sharing recommended for first 6 months""",
            
            """Postpartum Mental Health:
- Baby blues: common in first 2 weeks, usually resolves
- Postpartum depression: persistent sadness, loss of interest, difficulty bonding
- Risk factors: history of depression, lack of support, complications
- Seek help if: symptoms persist >2 weeks, interfere with daily life, thoughts of harm
- Resources: Postpartum Support International, healthcare provider, mental health professional""",
            
            """Diaper Changes:
- Newborns typically have 6+ wet diapers per day
- Breastfed babies may have frequent, loose stools
- Formula-fed babies may have fewer, firmer stools
- Red flags: no wet diapers for 6+ hours, blood in stool, severe diaper rash""",
            
            """Postpartum Recovery - Body Changes:
- Weight loss: gradual over 6-12 months is normal
- Breast changes: engorgement, blocked ducts, mastitis possible
- Bleeding (lochia): starts heavy, gradually decreases over 4-6 weeks
- Pain: normal after delivery, consult provider if severe
- Exercise: start gradually, consult provider before intense exercise
- Sources: ACOG (American College of Obstetricians and Gynecologists), WHO""",
            
            """Breastfeeding Guidelines:
- Frequency: 8-12 times per day in first weeks
- Duration: 10-45 minutes per feeding
- Signs of good latch: baby's mouth covers areola, no pain
- Engorgement: normal in first days, frequent feeding helps
- Blocked ducts: warm compress, massage, frequent feeding
- Mastitis: fever, breast pain, redness - seek medical care
- Sources: La Leche League, WHO, AAP (American Academy of Pediatrics)""",
            
            """Newborn Care - Health Monitoring:
- Temperature: normal 97.7-99.5°F (36.5-37.5°C)
- Breathing: 30-60 breaths per minute is normal
- Jaundice: common in first week, monitor for yellowing
- Umbilical cord: keep dry, falls off in 1-3 weeks
- Red flags: fever >100.4°F, difficulty breathing, won't wake up, severe jaundice
- Sources: AAP, WHO, pediatric associations""",
            
            """Postpartum Recovery - Emergency Signs:
- Heavy bleeding: soaking pad in less than 1 hour
- Fever: >100.4°F (38°C) may indicate infection
- Severe pain: not relieved by medication
- Foul-smelling discharge: may indicate infection
- Red, warm, painful area: may indicate infection
- Thoughts of harming self or baby: seek immediate help
- Sources: ACOG, WHO, Postpartum Support International""",
            
            """Newborn Crying and Soothing:
- Normal: newborns cry 1-4 hours per day
- Common causes: hunger, wet/dirty diaper, tired, overstimulated
- Soothing techniques: swaddling, gentle rocking, white noise, pacifier
- Colic: excessive crying >3 hours/day, >3 days/week, >3 weeks
- When to worry: inconsolable crying, high-pitched cry, won't feed
- Sources: AAP, pediatric associations""",
            
            """Postpartum Mental Health - Support:
- Baby blues: 50-80% of new mothers, resolves in 2 weeks
- Postpartum depression: 10-15% of mothers, requires treatment
- Risk factors: previous depression, lack of support, complications
- Support resources: family, friends, support groups, healthcare providers
- Treatment: therapy, medication, support groups
- Emergency: thoughts of harm - call 911 or crisis hotline
- Sources: Postpartum Support International, ACOG, mental health organizations""",
            
            """When to Contact Healthcare Provider:
- Baby: fever (rectal temp >100.4°F), difficulty breathing, dehydration signs, jaundice
- Mother: heavy bleeding, fever, severe pain, signs of infection, mental health concerns
- Always trust your instincts - if something feels wrong, contact provider"""
        ]
        
        # Split documents
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=50
        )
        
        documents = []
        for doc_text in sample_docs:
            splits = text_splitter.split_text(doc_text)
            documents.extend([Document(page_content=text) for text in splits])
        
        # Create vector store
        self.vectorstore = Chroma.from_documents(
            documents=documents,
            embedding=self.embeddings,
            persist_directory=self.vector_db_path
        )
    
    async def search(self, query: str, k: int = 3) -> str:
        return (await self.search_with_sources(query, k))["context"]

    async def search_with_sources(self, query: str, k: int = 3) -> dict:
        """
        Search for relevant medical information with safety enhancements
        
        Prioritizes authoritative sources and adds safety disclaimers
        """
        if not self.initialized or not self.vectorstore:
            return {"context": "", "sources": []}
        
        try:
            # Search for similar documents
            results = self.vectorstore.similarity_search(query, k=k)
            
            if not results:
                return {"context": "", "sources": []}
            
            # Combine results with citations and prioritize authoritative sources
            context_parts = []
            sources = []
            authoritative_keywords = ["ACOG", "WHO", "AAP", "pediatric", "medical", "healthcare provider"]
            
            # Sort results to prioritize authoritative sources
            sorted_results = sorted(
                results,
                key=lambda doc: sum(1 for keyword in authoritative_keywords if keyword.lower() in doc.page_content.lower()),
                reverse=True
            )
            
            for i, doc in enumerate(sorted_results, 1):
                source_text = doc.page_content
                source_text = f"[Retrieved item {i}] {source_text}"
                context_parts.append(source_text)
                metadata = doc.metadata or {}
                # Only document metadata can supply a link. Textual source names
                # in sample material do not establish a URL or source verification.
                url = metadata.get("source_url") or metadata.get("url") or metadata.get("source")
                if isinstance(url, str) and url.startswith("https://"):
                    sources.append({"url": url, "title": metadata.get("title") or ""})
            
            combined_context = "\n\n".join(context_parts)
            
            # Add safety disclaimer
            safety_note = "\n\n[Safety Note] This information is for general guidance only and does not replace professional medical advice. Always consult your healthcare provider for medical concerns. If this is an emergency, call emergency services immediately."
            
            return {"context": combined_context + safety_note, "sources": sources}
        except Exception as e:
            logger.log_error(e, context={"action": "rag_search"})
            return {"context": "", "sources": []}
    
    async def add_documents(self, documents: List[str], metadata: Optional[List[dict]] = None):
        """Add new documents to the vector store"""
        if not self.initialized:
            await self.initialize()
        
        if not self.vectorstore:
            return
        
        try:
            text_splitter = RecursiveCharacterTextSplitter(
                chunk_size=500,
                chunk_overlap=50
            )
            
            if metadata:
                splits = text_splitter.create_documents(documents, metadatas=metadata)
            else:
                splits = text_splitter.create_documents(documents)
            self.vectorstore.add_documents(splits)
            self.vectorstore.persist()
        except Exception as e:
            logger.log_error(e, context={"action": "rag_add_documents", "document_count": len(documents)})
