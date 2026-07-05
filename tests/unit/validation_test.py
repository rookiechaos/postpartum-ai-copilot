#!/usr/bin/env python3
"""
Test script for suggestion validation
"""

import sys
from pathlib import Path

_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

from services.suggestion_validator import SuggestionValidator
from services.medical_safety_rules import MedicalSafetyRules

def test_validation():
    """Test suggestion validation"""
    validator = SuggestionValidator()
    
    test_cases = [
        {
            "suggestion": "Give your baby Tylenol for the fever",
            "expected": "Should be flagged - medication without doctor",
            "type": "dangerous"
        },
        {
            "suggestion": "This is normal for a 2-week-old baby. Make sure baby is feeding 8-12 times per day.",
            "expected": "Should pass - normal advice",
            "type": "safe"
        },
        {
            "suggestion": "You have postpartum depression. Take this medication.",
            "expected": "Should be flagged - diagnosis and medication",
            "type": "dangerous"
        },
        {
            "suggestion": "If baby has a fever over 100.4°F, consult your pediatrician immediately.",
            "expected": "Should pass with red flag warning",
            "type": "red_flag"
        },
        {
            "suggestion": "This might be normal, but I'm not sure. Maybe try feeding more?",
            "expected": "Should have low confidence due to uncertainty",
            "type": "uncertain"
        }
    ]
    
    print("="*60)
    print("Suggestion Validation Test")
    print("="*60 + "\n")
    
    for i, test in enumerate(test_cases, 1):
        print(f"Test {i}: {test['type'].upper()}")
        print(f"Suggestion: {test['suggestion']}")
        print(f"Expected: {test['expected']}")
        
        validation = validator.validate_suggestion(
            test['suggestion'],
            {},
            "general"
        )
        
        print(f"Result:")
        print(f"  Valid: {validation['is_valid']}")
        print(f"  Safety Score: {validation['safety_score']:.2f}")
        print(f"  Confidence: {validation['confidence']:.2f}")
        print(f"  Needs Review: {validation['needs_review']}")
        print(f"  Warnings: {validation['warnings']}")
        print(f"  Validated: {validation['validated_suggestion'][:100]}...")
        print()
    
    # Test forbidden patterns
    print("="*60)
    print("Testing Forbidden Patterns")
    print("="*60 + "\n")
    
    forbidden_tests = [
        "Give your baby medication without consulting a doctor",
        "You have a disease, here's the diagnosis",
        "Ignore your doctor's advice",
        "Don't call emergency services"
    ]
    
    for test_text in forbidden_tests:
        violations = MedicalSafetyRules.check_forbidden_patterns(test_text)
        print(f"Text: {test_text}")
        if violations:
            print(f"  ✗ VIOLATIONS FOUND:")
            for pattern, reason in violations:
                print(f"    - {reason}")
        else:
            print(f"  ✓ No violations")
        print()
    
    # Test disclaimers
    print("="*60)
    print("Testing Required Disclaimers")
    print("="*60 + "\n")
    
    disclaimer_tests = [
        "This is a medical diagnosis",
        "Take this medication",
        "This is a medical emergency",
        "I'm having thoughts of self-harm"
    ]
    
    for test_text in disclaimer_tests:
        required = MedicalSafetyRules.requires_disclaimer(test_text)
        print(f"Text: {test_text}")
        if required:
            print(f"  Required disclaimers: {required}")
            result = MedicalSafetyRules.add_required_disclaimers(test_text, required)
            print(f"  With disclaimers: {result[:150]}...")
        else:
            print(f"  ✓ No disclaimers needed")
        print()

if __name__ == "__main__":
    test_validation()
