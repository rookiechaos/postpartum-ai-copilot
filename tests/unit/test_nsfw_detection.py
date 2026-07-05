"""
Tests for NSFW Detection Service
NSFW detection service tests
"""

import pytest
from services.nsfw_detector import get_nsfw_detector, NSFWLevel


@pytest.mark.asyncio
async def test_nsfw_detection_safe_content():
    """Test that safe content passes NSFW detection"""
    detector = get_nsfw_detector()
    
    safe_texts = [
        "How often should I feed my baby?",
        "What are the signs of postpartum depression?",
        "My baby is 2 weeks old and sleeps a lot. Is this normal?",
        "I'm feeling tired. Can you help me understand what's normal?",
        "When should I call the doctor about my baby's fever?"
    ]
    
    for text in safe_texts:
        result = await detector.check(text, language="en", check_type="input")
        assert result["safe"] is True, f"Safe text was flagged: {text}"
        assert result["level"] == NSFWLevel.SAFE.value
        assert not detector.should_block(result)


@pytest.mark.asyncio
async def test_nsfw_detection_empty_text():
    """Test that empty text is considered safe"""
    detector = get_nsfw_detector()
    
    result = await detector.check("", language="en")
    assert result["safe"] is True
    assert result["level"] == NSFWLevel.SAFE.value
    assert not detector.should_block(result)


@pytest.mark.asyncio
async def test_nsfw_detection_disabled():
    """Test that detection can be disabled"""
    import os
    original_value = os.getenv("NSFW_DETECTION_ENABLED")
    
    try:
        os.environ["NSFW_DETECTION_ENABLED"] = "false"
        # Recreate detector to pick up new setting
        from services.nsfw_detector import NSFWDetector
        detector = NSFWDetector()
        
        result = await detector.check("test", language="en")
        assert result["safe"] is True
        assert result["reason"] == "NSFW detection disabled"
    finally:
        if original_value:
            os.environ["NSFW_DETECTION_ENABLED"] = original_value
        else:
            os.environ.pop("NSFW_DETECTION_ENABLED", None)


@pytest.mark.asyncio
async def test_nsfw_detection_block_message():
    """Test that block messages are returned in correct language"""
    detector = get_nsfw_detector()
    
    en_message = detector.get_block_message("en")
    assert "inappropriate" in en_message.lower() or "cannot" in en_message.lower()
    
    ja_message = detector.get_block_message("ja")
    assert len(ja_message) > 0
    
    zh_message = detector.get_block_message("zh")
    assert len(zh_message) > 0


@pytest.mark.asyncio
async def test_nsfw_detection_input_vs_output():
    """Test that input and output checks work correctly"""
    detector = get_nsfw_detector()
    
    text = "How can I help my baby sleep better?"
    
    input_result = await detector.check(text, language="en", check_type="input")
    output_result = await detector.check(text, language="en", check_type="output")
    
    # Both should be safe
    assert input_result["safe"] is True
    assert output_result["safe"] is True


def test_nsfw_level_enum():
    """Test NSFW level enum values"""
    assert NSFWLevel.SAFE.value == "safe"
    assert NSFWLevel.SUSPICIOUS.value == "suspicious"
    assert NSFWLevel.UNSAFE.value == "unsafe"

