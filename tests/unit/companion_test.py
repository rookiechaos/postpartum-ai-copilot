#!/usr/bin/env python3
"""
Test script for Companion Layer and Information Buffer
"""

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from services.companion_layer import CompanionLayer
from services.information_buffer import InformationBuffer

def test_companion_layer():
    """Test companion layer"""
    print("="*60)
    print("Companion Layer Test")
    print("="*60 + "\n")
    
    companion = CompanionLayer()
    
    # Test English
    print("English Response:")
    raw_response = "Your baby should feed 8-12 times per day. This is normal."
    wrapped = companion.wrap_response(raw_response, {}, "en")
    print(f"Original: {raw_response}")
    print(f"Wrapped: {wrapped}\n")
    
    # Test Japanese
    print("Japanese Response:")
    raw_response_ja = "赤ちゃんは1日8-12回授乳する必要があります。これは正常です。"
    wrapped_ja = companion.wrap_response(raw_response_ja, {}, "ja")
    print(f"Original: {raw_response_ja}")
    print(f"Wrapped: {wrapped_ja}\n")
    
    # Test with emotional context
    print("Emotional Context Response:")
    emotional_context = {"mood_level": "low"}
    wrapped_emotional = companion.wrap_response(
        "It's okay to feel overwhelmed.", 
        emotional_context, 
        "en"
    )
    print(f"Wrapped: {wrapped_emotional}\n")

def test_information_buffer():
    """Test information buffer"""
    print("="*60)
    print("Information Buffer Test")
    print("="*60 + "\n")
    
    buffer = InformationBuffer()
    
    # Test safe response
    print("1. Safe Response:")
    safe_response = {
        "text": "Newborns typically feed 8-12 times per day. This is normal.",
        "suggestions": [
            "Track feeding times",
            "Watch for hunger cues"
        ],
        "red_flags": []
    }
    processed = buffer.process_chat_response(safe_response, {}, "en")
    print(f"Processed: {processed['response'][:100]}...")
    print(f"Suggestions: {processed['suggestions']}\n")
    
    # Test dangerous response
    print("2. Dangerous Response (should be filtered):")
    dangerous_response = {
        "text": "Give your baby medication without consulting a doctor.",
        "suggestions": ["Take this medicine"],
        "red_flags": []
    }
    processed_danger = buffer.process_chat_response(dangerous_response, {}, "en")
    print(f"Processed: {processed_danger['response']}")
    print(f"Safe: {processed_danger['safety_metadata']['response_validation']['is_safe']}\n")
    
    # Test crisis response
    print("3. Crisis Response:")
    crisis_response = {
        "text": "Baby won't stop crying. Try these steps.",
        "actions": [
            "Check diaper",
            "Try feeding",
            "Rock gently"
        ],
        "red_flags": ["If fever persists, call doctor"]
    }
    processed_crisis = buffer.process_crisis_response(crisis_response, {}, "en")
    print(f"Processed: {processed_crisis['response'][:100]}...")
    print(f"Actions: {processed_crisis['actions']}")
    print(f"Red Flags: {processed_crisis['red_flags']}\n")

if __name__ == "__main__":
    test_companion_layer()
    print("\n")
    test_information_buffer()
