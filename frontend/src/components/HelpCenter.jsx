import React, { useState, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { Search, HelpCircle, MessageCircle, BarChart3, Heart, Moon, Settings, ChevronRight, ThumbsUp, ThumbsDown, X } from 'lucide-react'
import api from '../utils/api'
import './HelpCenter.css'

function HelpCenter() {
  const { t } = useTranslation()
  const [searchQuery, setSearchQuery] = useState('')
  const [selectedCategory, setSelectedCategory] = useState(null)
  const [articles, setArticles] = useState([])
  const [faqs, setFaqs] = useState([])
  const [categories, setCategories] = useState([])
  const [searchResults, setSearchResults] = useState(null)
  const [selectedArticle, setSelectedArticle] = useState(null)
  const [selectedFaq, setSelectedFaq] = useState(null)
  const [loading, setLoading] = useState(false)
  const [language, setLanguage] = useState('en')

  useEffect(() => {
    loadCategories()
    loadArticles()
    loadFAQs()
  }, [language])

  useEffect(() => {
    if (selectedCategory) {
      loadArticles(selectedCategory)
      loadFAQs(selectedCategory)
    }
  }, [selectedCategory, language])

  const loadCategories = async () => {
    try {
      const data = await api.getHelpCategories(language)
      setCategories(data.categories || [])
    } catch (error) {
      console.error('Failed to load categories:', error)
    }
  }

  const loadArticles = async (category = null) => {
    setLoading(true)
    try {
      const data = await api.getHelpArticles(category, language, null)
      setArticles(data.articles || [])
    } catch (error) {
      console.error('Failed to load articles:', error)
    } finally {
      setLoading(false)
    }
  }

  const loadFAQs = async (category = null) => {
    try {
      const data = await api.getFAQs(category, language, null)
      setFaqs(data.faqs || [])
    } catch (error) {
      console.error('Failed to load FAQs:', error)
    }
  }

  const handleSearch = async (e) => {
    e.preventDefault()
    if (!searchQuery.trim()) {
      setSearchResults(null)
      return
    }

    setLoading(true)
    try {
      const data = await api.searchHelp(searchQuery, language)
      setSearchResults(data)
      setSelectedCategory(null)
    } catch (error) {
      console.error('Search failed:', error)
      // Show error message to user
      setSearchResults({
        query: searchQuery,
        articles: [],
        faqs: [],
        total_results: 0,
        error: 'Search failed. Please try again.'
      })
    } finally {
      setLoading(false)
    }
  }

  // Real-time search as user types (debounced)
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults(null)
      return
    }

    const timeoutId = setTimeout(() => {
      handleSearch({ preventDefault: () => {} })
    }, 500) // Debounce for 500ms

    return () => clearTimeout(timeoutId)
  }, [searchQuery, language])

  const handleArticleClick = async (articleId) => {
    try {
      const article = await api.getHelpArticle(articleId)
      setSelectedArticle(article)
      setSelectedFaq(null)
    } catch (error) {
      console.error('Failed to load article:', error)
    }
  }

  const handleFaqClick = (faq) => {
    setSelectedFaq(faq)
    setSelectedArticle(null)
  }

  const handleFeedback = async (articleId, faqId, isHelpful) => {
    try {
      await api.submitHelpFeedback(articleId, faqId, isHelpful)
      // Update local state
      if (articleId && selectedArticle) {
        if (isHelpful) {
          selectedArticle.helpful_count++
        } else {
          selectedArticle.not_helpful_count++
        }
        setSelectedArticle({ ...selectedArticle })
      }
      if (faqId && selectedFaq) {
        if (isHelpful) {
          selectedFaq.helpful_count++
        } else {
          selectedFaq.not_helpful_count++
        }
        setSelectedFaq({ ...selectedFaq })
      }
    } catch (error) {
      console.error('Failed to submit feedback:', error)
    }
  }

  const categoryIcons = {
    getting_started: <HelpCircle size={20} />,
    chat: <MessageCircle size={20} />,
    tracking: <BarChart3 size={20} />,
    night_mode: <Moon size={20} />,
    checkin: <Heart size={20} />,
    settings: <Settings size={20} />
  }

  const displayItems = searchResults
    ? [...(searchResults.articles || []), ...(searchResults.faqs || [])]
    : selectedCategory
    ? [...articles, ...faqs]
    : [...articles, ...faqs]

  return (
    <div className="help-center">
      <div className="help-center-header">
        <h2>📚 Help Center</h2>
        <p>Find answers to your questions</p>
      </div>

      <form onSubmit={handleSearch} className="help-search">
        <div className="search-input-wrapper">
          <Search size={20} className="search-icon" />
          <input
            type="text"
            placeholder="Search for help..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            className="search-input"
          />
          {searchQuery && (
            <button
              type="button"
              onClick={() => {
                setSearchQuery('')
                setSearchResults(null)
              }}
              className="clear-search"
            >
              <X size={18} />
            </button>
          )}
        </div>
        <button type="submit" className="search-button" disabled={loading}>
          {loading ? 'Searching...' : 'Search'}
        </button>
      </form>

      {searchResults && (
        <div className="search-results">
          <h3>Search Results ({searchResults.total_results})</h3>
          {searchResults.total_results === 0 ? (
            <p className="no-results">No results found. Try different keywords.</p>
          ) : (
            <div className="results-list">
              {searchResults.articles.map(article => (
                <div
                  key={article.article_id}
                  className="result-item"
                  onClick={() => handleArticleClick(article.article_id)}
                >
                  <div className="result-icon">{categoryIcons[article.category] || <HelpCircle size={20} />}</div>
                  <div className="result-content">
                    <h4>{article.title}</h4>
                    <p className="result-meta">Article • {article.category}</p>
                  </div>
                  <ChevronRight size={20} />
                </div>
              ))}
              {searchResults.faqs.map(faq => (
                <div
                  key={faq.faq_id}
                  className="result-item"
                  onClick={() => handleFaqClick(faq)}
                >
                  <div className="result-icon">❓</div>
                  <div className="result-content">
                    <h4>{faq.question}</h4>
                    <p className="result-meta">FAQ</p>
                  </div>
                  <ChevronRight size={20} />
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      {!searchResults && (
        <>
          <div className="help-categories">
            <h3>Browse by Category</h3>
            <div className="category-grid">
              <button
                className={`category-card ${selectedCategory === null ? 'active' : ''}`}
                onClick={() => setSelectedCategory(null)}
              >
                <HelpCircle size={24} />
                <span>All</span>
              </button>
              {categories.map(category => (
                <button
                  key={category}
                  className={`category-card ${selectedCategory === category ? 'active' : ''}`}
                  onClick={() => setSelectedCategory(category)}
                >
                  {categoryIcons[category] || <HelpCircle size={24} />}
                  <span>{category.replace('_', ' ').replace(/\b\w/g, l => l.toUpperCase())}</span>
                </button>
              ))}
            </div>
          </div>

          <div className="help-content">
            {selectedArticle ? (
              <div className="article-view">
                <button className="back-button" onClick={() => setSelectedArticle(null)}>
                  ← Back
                </button>
                <h2>{selectedArticle.title}</h2>
                <div className="article-meta">
                  <span>{selectedArticle.category}</span>
                  <span>{selectedArticle.view_count} views</span>
                </div>
                <div className="article-content" dangerouslySetInnerHTML={{ __html: selectedArticle.content.replace(/\n/g, '<br>') }} />
                <div className="article-feedback">
                  <p>Was this helpful?</p>
                  <div className="feedback-buttons">
                    <button
                      onClick={() => handleFeedback(selectedArticle.article_id, null, true)}
                      className="feedback-btn helpful"
                    >
                      <ThumbsUp size={18} />
                      Yes ({selectedArticle.helpful_count})
                    </button>
                    <button
                      onClick={() => handleFeedback(selectedArticle.article_id, null, false)}
                      className="feedback-btn not-helpful"
                    >
                      <ThumbsDown size={18} />
                      No ({selectedArticle.not_helpful_count})
                    </button>
                  </div>
                </div>
              </div>
            ) : selectedFaq ? (
              <div className="faq-view">
                <button className="back-button" onClick={() => setSelectedFaq(null)}>
                  ← Back
                </button>
                <h2>{selectedFaq.question}</h2>
                <div className="faq-content">{selectedFaq.answer}</div>
                <div className="article-feedback">
                  <p>Was this helpful?</p>
                  <div className="feedback-buttons">
                    <button
                      onClick={() => handleFeedback(null, selectedFaq.faq_id, true)}
                      className="feedback-btn helpful"
                    >
                      <ThumbsUp size={18} />
                      Yes ({selectedFaq.helpful_count})
                    </button>
                    <button
                      onClick={() => handleFeedback(null, selectedFaq.faq_id, false)}
                      className="feedback-btn not-helpful"
                    >
                      <ThumbsDown size={18} />
                      No ({selectedFaq.not_helpful_count})
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              <>
                {articles.length > 0 && (
                  <div className="help-section">
                    <h3>Articles</h3>
                    <div className="items-list">
                      {articles.map(article => (
                        <div
                          key={article.article_id}
                          className="help-item"
                          onClick={() => handleArticleClick(article.article_id)}
                        >
                          <div className="item-icon">{categoryIcons[article.category] || <HelpCircle size={20} />}</div>
                          <div className="item-content">
                            <h4>{article.title}</h4>
                            <p className="item-meta">{article.category} • {article.view_count} views</p>
                          </div>
                          <ChevronRight size={20} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {faqs.length > 0 && (
                  <div className="help-section">
                    <h3>Frequently Asked Questions</h3>
                    <div className="items-list">
                      {faqs.map(faq => (
                        <div
                          key={faq.faq_id}
                          className="help-item"
                          onClick={() => handleFaqClick(faq)}
                        >
                          <div className="item-icon">❓</div>
                          <div className="item-content">
                            <h4>{faq.question}</h4>
                            <p className="item-meta">FAQ</p>
                          </div>
                          <ChevronRight size={20} />
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                {articles.length === 0 && faqs.length === 0 && (
                  <div className="empty-state">
                    <HelpCircle size={48} />
                    <p>No help content available yet.</p>
                  </div>
                )}
              </>
            )}
          </div>

          <div className="help-disclaimer" id="product-disclaimer">
            <h3>{t('disclaimer.title')}</h3>
            <p>{t('disclaimer.short')}</p>
          </div>
        </>
      )}
    </div>
  )
}

export default HelpCenter
