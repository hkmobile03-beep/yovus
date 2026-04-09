"""
Gemini API Connection Test
Tests both SDK and HTTP methods to verify API key works.

Usage:
  pip install google-genai
  python scripts/test_gemini.py
"""
import sys
import os
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(level=logging.INFO, format="  [%(name)s] %(message)s")


def load_key():
    key = os.environ.get("GEMINI_API_KEY", "") or os.environ.get("GOOGLE_API_KEY", "")
    env_file = PROJECT_ROOT / ".env"
    if not key and env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            if line.startswith("GEMINI_API_KEY=") or line.startswith("GOOGLE_API_KEY="):
                key = line.split("=", 1)[1].strip().strip('"').strip("'")
    return key


def test_list_models(api_key):
    """List available models to find valid model names."""
    print("\n--- Test 0: List Available Models ---")
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        models = []
        for m in client.models.list():
            name = m.name if isinstance(m.name, str) else str(m.name)
            model_id = name.replace("models/", "")
            if "gemini" in model_id and "embedding" not in model_id:
                models.append(model_id)
        print(f"  Found {len(models)} Gemini models:")
        for m in models[:15]:
            print(f"    - {m}")
        if len(models) > 15:
            print(f"    ... and {len(models) - 15} more")
        return models
    except ImportError:
        print("  SKIP: google-genai not installed")
        print("  Install: pip install google-genai")
        return []
    except Exception as e:
        print(f"  ERROR: {e}")
        return []


def test_sdk(api_key, available_models=None):
    """Test with official google-genai SDK"""
    print("\n--- Test 1: google-genai SDK (text) ---")
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print("  SKIP: google-genai not installed")
        print("  Install: pip install google-genai")
        return False, None

    client = genai.Client(api_key=api_key)

    # Preferred models first, then discovered ones
    models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]
    if available_models:
        for m in available_models:
            if m not in models:
                models.append(m)

    for model_name in models:
        try:
            print(f"  Trying model: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents="Say 'hello' in one word.",
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=64,
                ),
            )
            print(f"  SUCCESS! Model: {model_name}")
            print(f"  Response: {response.text[:100]}")
            return True, model_name
        except Exception as e:
            print(f"  FAILED: {model_name} -> {str(e)[:150]}")

    return False, None


def test_sdk_vision(api_key, working_model=None):
    """Test SDK with an actual image (vision capability)"""
    print("\n--- Test 2: SDK Vision (image input) ---")
    try:
        from google import genai
        from google.genai import types
        from PIL import Image
    except ImportError:
        print("  SKIP: missing packages")
        return False

    client = genai.Client(api_key=api_key)

    # Create a simple test image
    img = Image.new("RGB", (64, 64), color=(200, 150, 100))

    models = []
    if working_model:
        models.append(working_model)
    models.extend(["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"])
    # Deduplicate while preserving order
    seen = set()
    unique_models = []
    for m in models:
        if m not in seen:
            seen.add(m)
            unique_models.append(m)

    for model_name in unique_models:
        try:
            print(f"  Trying vision: {model_name}...")
            response = client.models.generate_content(
                model=model_name,
                contents=[img, "What color is this image? One word."],
                config=types.GenerateContentConfig(
                    temperature=0.1,
                    max_output_tokens=64,
                ),
            )
            print(f"  SUCCESS! Vision works with: {model_name}")
            print(f"  Response: {response.text[:100]}")
            return True
        except Exception as e:
            print(f"  FAILED: {model_name} -> {str(e)[:150]}")

    return False


def test_http(api_key):
    """Test with raw HTTP requests"""
    print("\n--- Test 3: Raw HTTP API ---")
    try:
        import httpx
    except ImportError:
        print("  SKIP: httpx not installed")
        return False

    models = ["gemini-2.5-flash", "gemini-2.5-pro", "gemini-2.0-flash"]
    api_versions = ["v1beta", "v1"]

    for api_ver in api_versions:
        for model_name in models:
            url = (
                f"https://generativelanguage.googleapis.com/{api_ver}/models/"
                f"{model_name}:generateContent?key={api_key}"
            )
            payload = {
                "contents": [{"parts": [{"text": "Say 'hello' in one word."}]}],
                "generationConfig": {"temperature": 0.1, "maxOutputTokens": 64},
            }
            try:
                print(f"  Trying {api_ver}/{model_name}...")
                resp = httpx.post(url, json=payload, timeout=30.0)
                if resp.status_code == 200:
                    data = resp.json()
                    text = data["candidates"][0]["content"]["parts"][0]["text"]
                    print(f"  SUCCESS! {api_ver}/{model_name}")
                    print(f"  Response: {text[:100]}")
                    return True
                else:
                    err = ""
                    try:
                        err = resp.json().get("error", {}).get("message", "")[:150]
                    except Exception:
                        err = resp.text[:150]
                    print(f"  HTTP {resp.status_code}: {err}")
            except Exception as e:
                print(f"  ERROR: {e}")

    return False


def main():
    api_key = load_key()
    if not api_key:
        print("ERROR: No Gemini API key found.")
        print("Set GEMINI_API_KEY in .env file or environment variable.")
        sys.exit(1)

    print(f"API Key: {api_key[:10]}...{api_key[-4:]}")

    available = test_list_models(api_key)
    sdk_ok, working_model = test_sdk(api_key, available)
    vision_ok = test_sdk_vision(api_key, working_model) if sdk_ok else False
    http_ok = test_http(api_key)

    print("\n" + "=" * 50)
    print("  RESULTS")
    print("=" * 50)
    print(f"  Model discovery: {'OK (' + str(len(available)) + ' models)' if available else 'FAILED'}")
    print(f"  SDK text:        {'OK (' + working_model + ')' if sdk_ok else 'FAILED'}")
    print(f"  SDK vision:      {'OK' if vision_ok else 'FAILED'}")
    print(f"  HTTP:            {'OK' if http_ok else 'FAILED'}")

    if sdk_ok and vision_ok:
        print("\n  Gemini is fully working! Identity analysis will use SDK.")
    elif sdk_ok or http_ok:
        print("\n  Gemini partially working.")
    else:
        print("\n  All methods failed. Possible causes:")
        print("  1. API key invalid or expired")
        print("  2. Generative Language API not enabled in Google Cloud Console")
        print("  3. Network blocked (use VPN if in restricted region)")
        print("  4. Quota exceeded")
        print("\n  Try: pip install --upgrade google-genai")

    print("=" * 50)


if __name__ == "__main__":
    main()
