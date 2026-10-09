"""
Help Service - Help articles and FAQ management
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func, desc, String
import uuid
import re

from models.help_models import HelpArticleDB, FAQDB, HelpFeedbackDB
from services.logging_service import logger
from exceptions import NotFoundError, DatabaseError


class HelpService:
    """Service for managing help articles and FAQs"""
    
    def create_article(
        self,
        title: str,
        content: str,
        category: str,
        language: str = "en",
        tags: Optional[List[str]] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Create a new help article"""
        try:
            article_id = f"article_{uuid.uuid4().hex[:12]}"
            
            article = HelpArticleDB(
                article_id=article_id,
                title=title,
                content=content,
                category=category,
                language=language,
                tags=tags or [],
                is_published=True
            )
            
            db.add(article)
            db.commit()
            db.refresh(article)
            
            logger.log_info(f"Help article created: {article_id}")
            return self._article_to_dict(article)
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "create_article"})
            raise DatabaseError(f"Failed to create article: {str(e)}")
    
    def get_articles(
        self,
        category: Optional[str] = None,
        language: str = "en",
        search: Optional[str] = None,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Get help articles with optional filtering"""
        try:
            query = db.query(HelpArticleDB).filter(
                and_(
                    HelpArticleDB.is_published == True,
                    HelpArticleDB.language == language
                )
            )
            
            if category:
                query = query.filter(HelpArticleDB.category == category)
            
            if search:
                search_term = f"%{search.lower()}%"
                query = query.filter(
                    or_(
                        func.lower(HelpArticleDB.title).like(search_term),
                        func.lower(HelpArticleDB.content).like(search_term)
                    )
                )
            
            articles = query.order_by(HelpArticleDB.order, HelpArticleDB.created_at.desc()).all()
            return [self._article_to_dict(a) for a in articles]
        except Exception as e:
            logger.log_error(e, context={"action": "get_articles"})
            return []
    
    def get_article(
        self,
        article_id: str,
        db: Session
    ) -> Optional[Dict[str, Any]]:
        """Get a single help article"""
        try:
            article = db.query(HelpArticleDB).filter(
                HelpArticleDB.article_id == article_id,
                HelpArticleDB.is_published == True
            ).first()
            
            if article:
                # Increment view count
                article.view_count += 1
                db.commit()
                return self._article_to_dict(article)
            return None
        except Exception as e:
            logger.log_error(e, context={"action": "get_article"})
            return None
    
    def create_faq(
        self,
        question: str,
        answer: str,
        category: Optional[str] = None,
        language: str = "en",
        db: Session = None
    ) -> Dict[str, Any]:
        """Create a new FAQ"""
        try:
            faq_id = f"faq_{uuid.uuid4().hex[:12]}"
            
            faq = FAQDB(
                faq_id=faq_id,
                question=question,
                answer=answer,
                category=category,
                language=language,
                is_published=True
            )
            
            db.add(faq)
            db.commit()
            db.refresh(faq)
            
            logger.log_info(f"FAQ created: {faq_id}")
            return self._faq_to_dict(faq)
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "create_faq"})
            raise DatabaseError(f"Failed to create FAQ: {str(e)}")
    
    def get_faqs(
        self,
        category: Optional[str] = None,
        language: str = "en",
        search: Optional[str] = None,
        db: Session = None
    ) -> List[Dict[str, Any]]:
        """Get FAQs with optional filtering"""
        try:
            query = db.query(FAQDB).filter(
                and_(
                    FAQDB.is_published == True,
                    FAQDB.language == language
                )
            )
            
            if category:
                query = query.filter(FAQDB.category == category)
            
            if search:
                search_term = f"%{search.lower()}%"
                query = query.filter(
                    or_(
                        func.lower(FAQDB.question).like(search_term),
                        func.lower(FAQDB.answer).like(search_term)
                    )
                )
            
            faqs = query.order_by(FAQDB.order, FAQDB.created_at.desc()).all()
            return [self._faq_to_dict(f) for f in faqs]
        except Exception as e:
            logger.log_error(e, context={"action": "get_faqs"})
            return []
    
    def search_help(
        self,
        query: str,
        language: str = "en",
        db: Session = None
    ) -> Dict[str, Any]:
        """
        Enhanced full-text search for both articles and FAQs
        Supports multiple search terms and relevance scoring
        """
        try:
            # Split query into individual terms for better matching
            search_terms = [term.strip().lower() for term in query.split() if term.strip()]
            if not search_terms:
                return {"query": query, "articles": [], "faqs": [], "total_results": 0}
            
            # Build search conditions for articles
            article_conditions = [
                HelpArticleDB.is_published == True,
                HelpArticleDB.language == language
            ]
            
            article_search_conditions = []
            for term in search_terms:
                search_term = f"%{term}%"
                article_search_conditions.append(
                    or_(
                        func.lower(HelpArticleDB.title).like(search_term),
                        func.lower(HelpArticleDB.content).like(search_term),
                        func.lower(HelpArticleDB.tags.cast(String)).like(search_term)
                    )
                )
            
            if article_search_conditions:
                article_conditions.append(or_(*article_search_conditions))
            
            articles = db.query(HelpArticleDB).filter(
                and_(*article_conditions)
            ).limit(20).all()
            
            # Build search conditions for FAQs
            faq_conditions = [
                FAQDB.is_published == True,
                FAQDB.language == language
            ]
            
            faq_search_conditions = []
            for term in search_terms:
                search_term = f"%{term}%"
                faq_search_conditions.append(
                    or_(
                        func.lower(FAQDB.question).like(search_term),
                        func.lower(FAQDB.answer).like(search_term)
                    )
                )
            
            if faq_search_conditions:
                faq_conditions.append(or_(*faq_search_conditions))
            
            faqs = db.query(FAQDB).filter(
                and_(*faq_conditions)
            ).limit(20).all()
            
            # Score and sort results by relevance
            def score_article(article, terms):
                score = 0
                title_lower = article.title.lower()
                content_lower = article.content.lower()
                for term in terms:
                    if term in title_lower:
                        score += 10  # Title matches are more relevant
                    if term in content_lower:
                        score += 1
                return score
            
            def score_faq(faq, terms):
                score = 0
                question_lower = faq.question.lower()
                answer_lower = faq.answer.lower()
                for term in terms:
                    if term in question_lower:
                        score += 10
                    if term in answer_lower:
                        score += 1
                return score
            
            # Sort by relevance
            articles_with_scores = [(a, score_article(a, search_terms)) for a in articles]
            articles_with_scores.sort(key=lambda x: x[1], reverse=True)
            articles = [a for a, _ in articles_with_scores]
            
            faqs_with_scores = [(f, score_faq(f, search_terms)) for f in faqs]
            faqs_with_scores.sort(key=lambda x: x[1], reverse=True)
            faqs = [f for f, _ in faqs_with_scores]
            
            return {
                "query": query,
                "articles": [self._article_to_dict(a) for a in articles[:10]],
                "faqs": [self._faq_to_dict(f) for f in faqs[:10]],
                "total_results": len(articles) + len(faqs)
            }
        except Exception as e:
            logger.log_error(e, context={"action": "search_help"})
            return {"query": query, "articles": [], "faqs": [], "total_results": 0}
    
    def submit_feedback(
        self,
        article_id: Optional[str] = None,
        faq_id: Optional[str] = None,
        user_id: Optional[str] = None,
        is_helpful: bool = True,
        comment: Optional[str] = None,
        db: Session = None
    ) -> Dict[str, Any]:
        """Submit feedback for an article or FAQ"""
        try:
            if not article_id and not faq_id:
                raise ValueError("Either article_id or faq_id must be provided")
            
            feedback = HelpFeedbackDB(
                article_id=article_id,
                faq_id=faq_id,
                user_id=user_id,
                is_helpful=is_helpful,
                comment=comment
            )
            
            db.add(feedback)
            
            # Update helpful count
            if article_id:
                article = db.query(HelpArticleDB).filter(
                    HelpArticleDB.article_id == article_id
                ).first()
                if article:
                    if is_helpful:
                        article.helpful_count += 1
                    else:
                        article.not_helpful_count += 1
            
            if faq_id:
                faq = db.query(FAQDB).filter(FAQDB.faq_id == faq_id).first()
                if faq:
                    if is_helpful:
                        faq.helpful_count += 1
                    else:
                        faq.not_helpful_count += 1
            
            db.commit()
            
            return {"status": "success", "message": "Feedback submitted"}
        except Exception as e:
            db.rollback()
            logger.log_error(e, context={"action": "submit_feedback"})
            raise DatabaseError(f"Failed to submit feedback: {str(e)}")
    
    def get_categories(self, language: str = "en", db: Session = None) -> List[str]:
        """Get all available categories"""
        try:
            categories = db.query(HelpArticleDB.category).filter(
                and_(
                    HelpArticleDB.is_published == True,
                    HelpArticleDB.language == language
                )
            ).distinct().all()
            
            return [c[0] for c in categories]
        except Exception as e:
            logger.log_error(e, context={"action": "get_categories"})
            return []
    
    def _article_to_dict(self, article: HelpArticleDB) -> Dict[str, Any]:
        """Convert article to dictionary"""
        return {
            "id": article.id,
            "article_id": article.article_id,
            "title": article.title,
            "content": article.content,
            "category": article.category,
            "language": article.language,
            "tags": article.tags or [],
            "view_count": article.view_count,
            "helpful_count": article.helpful_count,
            "not_helpful_count": article.not_helpful_count,
            "created_at": article.created_at.isoformat() if article.created_at else None,
            "updated_at": article.updated_at.isoformat() if article.updated_at else None
        }
    
    def _faq_to_dict(self, faq: FAQDB) -> Dict[str, Any]:
        """Convert FAQ to dictionary"""
        return {
            "id": faq.id,
            "faq_id": faq.faq_id,
            "question": faq.question,
            "answer": faq.answer,
            "category": faq.category,
            "language": faq.language,
            "view_count": faq.view_count,
            "helpful_count": faq.helpful_count,
            "not_helpful_count": faq.not_helpful_count,
            "created_at": faq.created_at.isoformat() if faq.created_at else None,
            "updated_at": faq.updated_at.isoformat() if faq.updated_at else None
        }

