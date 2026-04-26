"""
Multi-provider LLM client
우선순위: Groq → Gemini → Ollama (로컬)
모두 실패하면 RuntimeError 발생
"""
import os
import time

# ── 설정 ──────────────────────────────────────────────
GROQ_API_KEY = os.getenv('GROQ_API_KEY', '')
OLLAMA_HOST  = os.getenv('OLLAMA_HOST', 'http://ollama:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'gemma2:27b')
GROQ_MODEL   = 'llama-3.3-70b-versatile'


def _call_groq(prompt: str) -> str:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.9,
        max_tokens=2048,
    )
    return response.choices[0].message.content


def _call_ollama(prompt: str) -> str:
    import requests
    response = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.9, "num_predict": 2048},
        },
        timeout=180,
    )
    response.raise_for_status()
    return response.json()["response"]


PROVIDERS = [
    ("Groq",   _call_groq,   lambda: bool(GROQ_API_KEY)),
    ("Ollama", _call_ollama, lambda: True),
]


def generate(prompt: str, retries: int = 2) -> str:
    """
    사용 가능한 LLM 순서대로 시도. 모두 실패하면 RuntimeError.
    """
    errors = []
    for name, fn, available in PROVIDERS:
        if not available():
            print(f"[LLM] {name} 스킵 (API 키 없음)")
            continue
        for attempt in range(1, retries + 2):
            try:
                print(f"[LLM] {name} 시도 ({attempt}/{retries + 1})...")
                result = fn(prompt)
                print(f"[LLM] {name} 성공 ✓")
                return result
            except Exception as e:
                err_msg = str(e)
                print(f"[LLM] {name} 실패: {err_msg[:120]}")
                errors.append(f"{name}: {err_msg[:80]}")
                # rate limit 계열이면 잠깐 대기 후 재시도
                if any(k in err_msg.lower() for k in ['429', 'rate', 'quota', 'limit']):
                    wait = 30 * attempt
                    print(f"[LLM] {wait}초 대기 후 재시도...")
                    time.sleep(wait)
                else:
                    break  # 다른 에러는 바로 다음 provider로

    raise RuntimeError(f"[LLM] 모든 provider 실패: {' | '.join(errors)}")
