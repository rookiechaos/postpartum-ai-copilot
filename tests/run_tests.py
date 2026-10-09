#!/usr/bin/env python3
"""
Comprehensive test suite for Postpartum AI Copilot
Runs all unit tests and integration tests
"""

import sys
import os
import subprocess
import time
from pathlib import Path

# Colors for output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
NC = '\033[0m'  # No Color

def print_header(text):
    """Print a formatted header"""
    print(f"\n{BLUE}{'='*60}{NC}")
    print(f"{BLUE}{text}{NC}")
    print(f"{BLUE}{'='*60}{NC}\n")

def print_test(name, passed, message=""):
    """Print test result"""
    status = f"{GREEN}✓{NC}" if passed else f"{RED}✗{NC}"
    print(f"{status} {name}")
    if message:
        print(f"    {message}")

def run_unit_tests():
    """Run unit tests that don't require backend"""
    print_header("Unit Tests (No Backend Required)")
    
    results = []
    base_dir = Path(__file__).resolve().parent.parent
    
    # Test 1: Validation system
    print(f"{YELLOW}Testing Validation System...{NC}")
    try:
        sys.path.insert(0, str(base_dir / "backend"))
        from services.suggestion_validator import SuggestionValidator
        from services.medical_safety_rules import MedicalSafetyRules
        
        validator = SuggestionValidator()
        
        # Test safe suggestion
        safe_result = validator.validate_suggestion(
            "Newborns typically feed 8-12 times per day. This is normal.",
            {}, "general"
        )
        safe_passed = safe_result["is_valid"] and safe_result["safety_score"] > 0.8
        
        # Test dangerous suggestion
        danger_result = validator.validate_suggestion(
            "Give your baby medication without consulting a doctor.",
            {}, "general"
        )
        danger_passed = not danger_result["is_valid"] or danger_result["safety_score"] < 0.5
        
        # Test forbidden patterns
        violations = MedicalSafetyRules.check_forbidden_patterns(
            "Give medication without doctor"
        )
        forbidden_passed = len(violations) > 0
        
        all_passed = safe_passed and danger_passed and forbidden_passed
        results.append(("Validation System", all_passed))
        print_test("Validation System", all_passed, 
                  f"Safe: {safe_passed}, Dangerous: {danger_passed}, Forbidden: {forbidden_passed}")
        
    except Exception as e:
        results.append(("Validation System", False))
        print_test("Validation System", False, f"Error: {str(e)}")
    
    # Test 2: Companion Layer
    print(f"\n{YELLOW}Testing Companion Layer...{NC}")
    try:
        from services.companion_layer import CompanionLayer
        
        companion = CompanionLayer()
        
        # Test English wrapping
        raw = "Your baby should feed 8-12 times per day."
        wrapped = companion.wrap_response(raw, {}, "en")
        # Check if response was wrapped (should be longer and contain companion phrases)
        companion_phrases = ["I understand", "You're doing", "Take care", "Here's what", "Hi there", "Hello", "Hey", "You're stronger", "It's okay", "Remember"]
        en_passed = len(wrapped) > len(raw) and any(phrase in wrapped for phrase in companion_phrases)
        
        # Test Japanese wrapping
        raw_ja = "赤ちゃんは1日8-12回授乳する必要があります。"
        wrapped_ja = companion.wrap_response(raw_ja, {}, "ja")
        ja_passed = len(wrapped_ja) > len(raw_ja)
        
        all_passed = en_passed and ja_passed
        results.append(("Companion Layer", all_passed))
        print_test("Companion Layer", all_passed,
                  f"English: {en_passed}, Japanese: {ja_passed}")
        
    except Exception as e:
        results.append(("Companion Layer", False))
        print_test("Companion Layer", False, f"Error: {str(e)}")
    
    # Test 3: Information Buffer
    print(f"\n{YELLOW}Testing Information Buffer...{NC}")
    try:
        from services.information_buffer import InformationBuffer
        
        buffer = InformationBuffer()
        
        # Test safe response processing
        safe_response = {
            "text": "Newborns typically feed 8-12 times per day.",
            "suggestions": ["Track feeding times"],
            "red_flags": []
        }
        processed = buffer.process_chat_response(safe_response, {}, "en")
        buffer_passed = "response" in processed and len(processed["response"]) > 0
        
        # Test dangerous response filtering
        danger_response = {
            "text": "Give your baby medication without consulting a doctor.",
            "suggestions": [],
            "red_flags": []
        }
        processed_danger = buffer.process_chat_response(danger_response, {}, "en")
        filter_passed = not processed_danger["safety_metadata"]["response_validation"]["is_safe"]
        
        all_passed = buffer_passed and filter_passed
        results.append(("Information Buffer", all_passed))
        print_test("Information Buffer", all_passed,
                  f"Processing: {buffer_passed}, Filtering: {filter_passed}")
        
    except Exception as e:
        results.append(("Information Buffer", False))
        print_test("Information Buffer", False, f"Error: {str(e)}")
    
    return results

def check_backend():
    """Check if backend is running"""
    try:
        import requests
        response = requests.get("http:localhost:8000/health", timeout=2)
        return response.status_code == 200
    except:
        return False

def run_api_tests():
    """Run API integration tests"""
    print_header("API Integration Tests (Backend Required)")
    
    if not check_backend():
        print(f"{YELLOW}⚠ Backend not running. Skipping API tests.{NC}")
        print(f"{YELLOW}   To run API tests, start backend: cd backend && uvicorn main:app --reload{NC}\n")
        return []
    
    print(f"{GREEN}✓ Backend is running{NC}\n")
    
    # Run the API test script
    test_script = Path(__file__).parent / "test_api.py"
    if test_script.exists():
        try:
            result = subprocess.run(
                [sys.executable, str(test_script)],
                capture_output=True,
                text=True,
                timeout=120
            )
            print(result.stdout)
            if result.stderr:
                print(result.stderr)
            return [("API Tests", result.returncode == 0)]
        except subprocess.TimeoutExpired:
            print(f"{RED}✗ API tests timed out{NC}")
            return [("API Tests", False)]
        except Exception as e:
            print(f"{RED}✗ Error running API tests: {str(e)}{NC}")
            return [("API Tests", False)]
    else:
        print(f"{YELLOW}⚠ API test script not found{NC}")
        return []

def main():
    """Run all tests"""
    print(f"\n{GREEN}{'='*60}{NC}")
    print(f"{GREEN}Postpartum AI Copilot - Comprehensive Test Suite{NC}")
    print(f"{GREEN}{'='*60}{NC}")
    
    all_results = []
    
    # Run unit tests
    unit_results = run_unit_tests()
    all_results.extend(unit_results)
    
    # Run API tests if backend is available
    api_results = run_api_tests()
    all_results.extend(api_results)
    
    # Summary
    print_header("Test Summary")
    
    passed = sum(1 for _, result in all_results if result)
    total = len(all_results)
    
    for name, result in all_results:
        status = f"{GREEN}✓ PASSED{NC}" if result else f"{RED}✗ FAILED{NC}"
        print(f"{status} {name}")
    
    print(f"\n{BLUE}Results: {passed}/{total} tests passed{NC}")
    
    if passed == total:
        print(f"\n{GREEN}🎉 All tests passed!{NC}\n")
        return 0
    else:
        print(f"\n{RED}⚠ Some tests failed. Please review the output above.{NC}\n")
        return 1

if __name__ == "__main__":
    exit(main())

