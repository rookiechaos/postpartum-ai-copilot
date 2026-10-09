#!/usr/bin/env python3
"""
Usage: python test_ai_providers.py
"""

import sys
from pathlib import Path
_BACKEND = Path(__file__).resolve().parents[2] / "backend"
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))

import os
import sys
import asyncio
from dotenv import load_dotenv

load_dotenv('backend/.env')

# Add backend to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from services.ai_providers import get_ai_provider

async def test_provider(provider_name: str):
    print(f"\n{'='*50}")
    print(f"Testing {provider_name.upper()} provider")
    print(f"{'='*50}\n")
    
    original_provider = os.getenv("AI_PROVIDER")
    os.environ["AI_PROVIDER"] = provider_name
    
    try:
        provider = get_ai_provider()
        
        messages = [
            {
                "role": "system",
                "content": "You are a helpful assistant for new mothers."
            },
            {
                "role": "user",
                "content": "My baby is 2 weeks old and won't sleep. Is this normal? Please answer in one sentence."
            }
        ]
        
        print("Sending test message...")
        response = await provider.chat(messages, temperature=0.7, max_tokens=100)
        
        print(f"✓ {provider_name} response succeeded")
        print(f"  provider: {response.get('provider', 'unknown')}")
        print(f"  Model: {response.get('model', 'unknown')}")
        print(f"  Response: {response.get('text', '')[:100]}...")
        print()
        
        return True
        
    except ValueError as e:
        print(f"✗ Configuration error: {str(e)}")
        print("  Check API key configuration in .env\n")
        return False
    except Exception as e:
        print(f"✗ Test failed: {str(e)}\n")
        return False
    finally:
        if original_provider:
            os.environ["AI_PROVIDER"] = original_provider

async def main():
    print("\n" + "="*50)
    print("AI Provider Connection Tests")
    print("="*50)
    
    providers = ["openai", "claude", "gemini"]
    results = {}
    
    for provider in providers:
        if provider == "openai" and not os.getenv("OPENAI_API_KEY"):
            print(f"\n⚠ Skipping {provider.upper()}: not configured OPENAI_API_KEY")
            continue
        elif provider == "claude" and not os.getenv("ANTHROPIC_API_KEY"):
            print(f"\n⚠ Skipping {provider.upper()}: not configured ANTHROPIC_API_KEY")
            continue
        elif provider == "gemini" and not os.getenv("GOOGLE_API_KEY"):
            print(f"\n⚠ Skipping {provider.upper()}: not configured GOOGLE_API_KEY")
            continue
        
        results[provider] = await test_provider(provider)
    
    print("\n" + "="*50)
    print("Test Results Summary")
    print("="*50)
    
    for provider, success in results.items():
        status = "✓ PASSED" if success else "✗ FAILED"
        print(f"{provider.upper():10} {status}")
    
    passed = sum(1 for s in results.values() if s)
    total = len(results)
    
    print(f"\nTotal: {passed}/{total} provider tests passed")
    
    if passed == 0:
        print("\n⚠ Warning: no AI providers available")
        print("Configure at least one provider API key")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(asyncio.run(main()))


