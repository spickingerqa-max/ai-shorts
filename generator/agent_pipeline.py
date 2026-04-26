"""
6-Agent Multi-Agent Pipeline
Agent1 Trend Scout       : Gemini Flash + Google Search
Agent2 Creative Director : Groq llama-3.3-70b-versatile
Agent3 Devil's Advocate  : Groq llama-3.1-8b-instant
Agent4 Analyst           : Ollama gemma2:27b
Agent5 Script Master     : Cerebras qwen-3-235b-a22b-instruct-2507
Agent6 Final Writer      : Groq llama-3.3-70b-versatile
"""

import os
import json
import time
import requests
from google.genai import types

GROQ_API_KEY     = os.getenv('GROQ_API_KEY', '')
CEREBRAS_API_KEY = os.getenv('CEREBRAS_API_KEY', '')
OLLAMA_HOST      = os.getenv('OLLAMA_HOST', 'http://ollama:11434')

# ── 상수 ────────────────────────────────────────────────────────────
GENRE_SEARCH_PROMPTS = {
    'ko': {
        'horror':  "지금 한국 유튜브와 SNS에서 가장 바이럴되고 있는 공포/괴담 주제 1개를 Google Search로 찾아서, 주제 이름과 왜 핫한지 한 문장으로만 답해줘.",
        'history': "지금 한국 유튜브와 SNS에서 가장 화제가 되고 있는 역사 관련 주제 1개를 Google Search로 찾아서, 주제 이름과 왜 핫한지 한 문장으로만 답해줘.",
        'success': "지금 한국 유튜브와 SNS에서 가장 많이 공유되는 성공/동기부여 스토리 주제 1개를 Google Search로 찾아서, 주제 이름과 왜 핫한지 한 문장으로만 답해줘.",
        'trend':   "지금 한국 유튜브 쇼츠와 SNS에서 가장 핫한 트렌드 주제 1개를 Google Search로 찾아서, 주제 이름과 왜 핫한지 한 문장으로만 답해줘.",
    },
    'en': {
        'horror':  "Find the most viral horror or ghost story topic on YouTube Shorts and social media right now using Google Search. Reply in one sentence: topic name and why it's trending.",
        'history': "Find the most trending historical topic on YouTube Shorts and social media right now using Google Search. Reply in one sentence: topic name and why it's trending.",
        'success': "Find the most shared success or motivation story on YouTube Shorts and social media right now using Google Search. Reply in one sentence: topic name and why it's trending.",
        'trend':   "Find the hottest trending topic on YouTube Shorts and social media right now using Google Search. Reply in one sentence: topic name and why it's trending.",
    },
}

GENRE_DEFAULTS = {
    'ko': {
        'horror':  '최근 화제의 한국 도시전설',
        'history': '조선시대 숨겨진 역사적 사건',
        'success': '무일푼에서 성공한 창업가 이야기',
        'trend':   '요즘 MZ세대가 열광하는 트렌드',
    },
    'en': {
        'horror':  'A chilling ghost story that went viral online',
        'history': 'A shocking historical event most people never learned',
        'success': 'A rags-to-riches entrepreneur story',
        'trend':   'The hottest viral trend taking over social media',
    },
}

# Final Writer 스크립트 템플릿 (JSON 리터럴 중괄호는 {{ }} 로 이스케이프)
_FINAL_WRITER_TEMPLATE = {
    'ko': (
        "[역할] 당신은 유튜브 쇼츠 전문 스크립트 작가입니다. Script Master의 초안을 검토하고 최종 JSON으로 완성합니다.\n\n"
        "[지금까지의 모든 에이전트 논의]\n"
        "{conversation_log}\n\n"
        "[작성 규칙]\n"
        "1. 훅: 첫 1~2초 안에 시청자가 엄지를 멈추게 만드는 한 문장. 구체적인 숫자/상황/감정으로 시작.\n"
        "   좋은 예: '26살, 통장 잔고 3만원. 그날 나는 결정을 내렸다.'\n"
        "   나쁜 예: '여러분, 오늘은 놀라운 이야기를 해드리겠습니다.'\n"
        "2. 씬 구조: 씬1(충격적 시작) -> 씬2(갈등/전개) -> 씬3(반전/핵심) -> 씬4(감정 클라이맥스) -> 씬5(강렬한 마무리+댓글유도)\n"
        "3. 나레이션: 말하듯이 자연스럽게, 짧고 강한 문장들, 각 씬 10~15초 분량.\n"
        "4. image_prompt: 반드시 영어로. {style_hint} 스타일. 구체적 장면/표정/배경 묘사.\n\n"
        "아래 JSON 형식으로만 반환하세요 (코드블록, 설명 없이):\n"
        '{{\n'
        '  "title": "클릭하지 않을 수 없는 제목 (30자 이내, 숫자나 반전 포함)",\n'
        '  "genre": "{genre}",\n'
        '  "language": "ko",\n'
        '  "hook": "엄지를 멈추게 만드는 첫 한 문장 (구체적 숫자/상황 포함)",\n'
        '  "scenes": [\n'
        '    {{"id": 1, "narration": "씬1 나레이션 (말하듯이, 10~15초)", "image_prompt": "{style_hint}, scene 1 detailed description in English", "duration": 12}},\n'
        '    {{"id": 2, "narration": "씬2 나레이션 (말하듯이, 10~15초)", "image_prompt": "{style_hint}, scene 2 detailed description in English", "duration": 12}},\n'
        '    {{"id": 3, "narration": "씬3 나레이션 (반전/핵심 공개, 10~15초)", "image_prompt": "{style_hint}, scene 3 detailed description in English", "duration": 12}},\n'
        '    {{"id": 4, "narration": "씬4 나레이션 (감정 클라이맥스, 10~15초)", "image_prompt": "{style_hint}, scene 4 detailed description in English", "duration": 12}},\n'
        '    {{"id": 5, "narration": "씬5 나레이션 (강렬한 마무리 + 댓글 유도, 10~15초)", "image_prompt": "{style_hint}, scene 5 detailed description in English", "duration": 12}}\n'
        '  ],\n'
        '  "hashtags": ["{hashtag1}", "{hashtag2}", "#쇼츠", "#유튜브쇼츠"]\n'
        '}}'
    ),
    'en': (
        "[ROLE] You are an expert YouTube Shorts scriptwriter. Review the Script Master's draft and produce the final JSON.\n\n"
        "[FULL AGENT DISCUSSION]\n"
        "{conversation_log}\n\n"
        "[RULES]\n"
        "1. Hook: Stop-the-scroll in first 1-2 seconds. Use specific numbers/situations/emotions.\n"
        "   Good: 'At 19, he had $0. Three years later, he sold his company for $50M.'\n"
        "   Bad: 'Today I'm going to tell you an amazing story.'\n"
        "2. Scene structure: Scene1(shocking hook) -> Scene2(conflict) -> Scene3(twist/reveal) -> Scene4(emotional climax) -> Scene5(powerful ending+engagement)\n"
        "3. Narration: Conversational, short punchy sentences, 10-15 sec per scene.\n"
        "4. image_prompt: Must be English. {style_hint} style. Specific scene/expression/background.\n\n"
        "Return ONLY the JSON below (no code blocks, no explanation):\n"
        '{{\n'
        '  "title": "Irresistible title under 60 chars (number or twist)",\n'
        '  "genre": "{genre}",\n'
        '  "language": "en",\n'
        '  "hook": "Stop-the-scroll first sentence with specific number/situation",\n'
        '  "scenes": [\n'
        '    {{"id": 1, "narration": "Scene 1 narration (conversational, 10-15 sec)", "image_prompt": "{style_hint}, scene 1 detailed description", "duration": 12}},\n'
        '    {{"id": 2, "narration": "Scene 2 narration (conversational, 10-15 sec)", "image_prompt": "{style_hint}, scene 2 detailed description", "duration": 12}},\n'
        '    {{"id": 3, "narration": "Scene 3 narration (twist/reveal, 10-15 sec)", "image_prompt": "{style_hint}, scene 3 detailed description", "duration": 12}},\n'
        '    {{"id": 4, "narration": "Scene 4 narration (emotional climax, 10-15 sec)", "image_prompt": "{style_hint}, scene 4 detailed description", "duration": 12}},\n'
        '    {{"id": 5, "narration": "Scene 5 narration (powerful ending+engagement, 10-15 sec)", "image_prompt": "{style_hint}, scene 5 detailed description", "duration": 12}}\n'
        '  ],\n'
        '  "hashtags": ["{hashtag1}", "{hashtag2}", "#Shorts", "#YouTubeShorts"]\n'
        '}}'
    ),
}


# ── 유틸 ────────────────────────────────────────────────────────────
def _format_log(conversation: list) -> str:
    return "\n\n".join(f"=== {e['agent']} ===\n{e['content']}" for e in conversation)


def _parse_json(text: str) -> dict:
    text = text.strip()
    if text.startswith('```'):
        text = text.split('```')[1]
        if text.startswith('json'):
            text = text[4:]
        text = text.strip()
    return json.loads(text)


# ── LLM 호출 래퍼 ───────────────────────────────────────────────────
def _call_groq(model: str, system: str, user: str, temperature=0.85, max_tokens=1024, retries=2) -> str:
    from groq import Groq
    client = Groq(api_key=GROQ_API_KEY)
    last_err = None
    for attempt in range(1, retries + 2):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            last_err = e
            msg = str(e)
            print(f"[Groq/{model}] 실패 ({attempt}): {msg[:100]}")
            if any(k in msg.lower() for k in ['429', 'rate', 'quota', 'limit']):
                wait = 30 * attempt
                print(f"[Groq] {wait}초 대기 후 재시도...")
                time.sleep(wait)
            else:
                break
    raise RuntimeError(f"Groq {model} 실패: {last_err}")


def _call_cerebras(model: str, system: str, user: str, temperature=0.85, max_tokens=1500, retries=2) -> str:
    from cerebras.cloud.sdk import Cerebras
    client = Cerebras(api_key=CEREBRAS_API_KEY)
    last_err = None
    for attempt in range(1, retries + 2):
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                temperature=temperature,
                max_tokens=max_tokens,
            )
            return resp.choices[0].message.content.strip()
        except Exception as e:
            last_err = e
            msg = str(e)
            print(f"[Cerebras/{model}] 실패 ({attempt}): {msg[:100]}")
            if any(k in msg.lower() for k in ['429', 'rate', 'quota', 'limit']):
                wait = 30 * attempt
                print(f"[Cerebras] {wait}초 대기 후 재시도...")
                time.sleep(wait)
            else:
                break
    raise RuntimeError(f"Cerebras {model} 실패: {last_err}")


def _call_ollama(model: str, prompt: str, temperature=0.8, num_predict=2048, timeout=600) -> str:
    resp = requests.post(
        f"{OLLAMA_HOST}/api/generate",
        json={
            "model":   model,
            "prompt":  prompt,
            "stream":  False,
            "options": {"temperature": temperature, "num_predict": num_predict},
        },
        timeout=timeout,
    )
    resp.raise_for_status()
    return resp.json()["response"].strip()


# ── Agent 1: Trend Scout (Gemini + Google Search) ──────────────────
def _agent1_trend_scout(gemini_client, genre: str, language: str) -> str:
    prompt = GENRE_SEARCH_PROMPTS[language][genre]
    try:
        resp = gemini_client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
            config=types.GenerateContentConfig(
                tools=[types.Tool(google_search=types.GoogleSearch())],
            ),
        )
        topic = resp.text.strip()
        print(f"[Agent1/TrendScout] 트렌드 발견: {topic[:80]}")
        return topic
    except Exception as e:
        print(f"[Agent1/TrendScout] Google Search 실패: {e} - 기본 주제 사용")
        return GENRE_DEFAULTS[language][genre]


# ── Agent 2: Creative Director (Groq llama-3.3-70b-versatile) ───────
_CD_SYSTEM = {
    'ko': "당신은 유튜브 쇼츠 전문 크리에이티브 디렉터입니다. 수백만 조회수를 달성한 바이럴 콘텐츠 전략가로, 주어진 주제에서 완전히 다른 3가지 스토리 각도를 제안하는 것이 전문입니다.",
    'en': "You are a YouTube Shorts creative director who has achieved millions of views. You specialize in proposing 3 completely different story angles for any given topic.",
}

def _agent2_creative_director(conversation: list, genre: str, language: str) -> str:
    log = _format_log(conversation)
    if language == 'ko':
        user = (
            f"위 Trend Scout가 발견한 트렌딩 주제를 바탕으로, '{genre}' 장르 유튜브 쇼츠의 완전히 다른 3가지 스토리 각도를 제안해줘.\n\n"
            f"[논의 내용]\n{log}\n\n"
            "각 각도마다 다음을 포함해:\n"
            "- 각도 번호와 제목\n"
            "- 핵심 훅 (첫 2초 안에 시청자를 잡을 한 문장)\n"
            "- 스토리 방향 (2~3문장)\n"
            "- 예상 감정 반응 (공감/충격/동기부여 등)\n\n"
            "3가지 각도를 제안해. 각각 완전히 다른 방향이어야 해."
        )
    else:
        user = (
            f"Based on the trending topic found by the Trend Scout, propose 3 completely different story angles for a '{genre}' YouTube Shorts.\n\n"
            f"[DISCUSSION]\n{log}\n\n"
            "For each angle include:\n"
            "- Angle number and title\n"
            "- Core hook (one sentence to stop scroll in 2 seconds)\n"
            "- Story direction (2-3 sentences)\n"
            "- Expected emotional response (empathy/shock/motivation etc.)\n\n"
            "Propose 3 angles. Each must be a completely different direction."
        )
    result = _call_groq('llama-3.3-70b-versatile', _CD_SYSTEM[language], user, temperature=0.9, max_tokens=900)
    print(f"[Agent2/CreativeDirector] 완료 ({len(result)}자)")
    return result


# ── Agent 3: Devil's Advocate (Groq mixtral-8x7b-32768) ────────────
_DA_SYSTEM = {
    'ko': "당신은 콘텐츠 품질 비평가입니다. 모든 아이디어의 약점을 날카롭게 파헤치고, 가장 바이럴 가능성이 높은 단 하나의 각도만 살아남게 합니다.",
    'en': "You are a ruthless content quality critic. You find weaknesses in every idea and ensure only the angle with the highest viral potential survives.",
}

def _agent3_devils_advocate(conversation: list, genre: str, language: str) -> str:
    log = _format_log(conversation)
    if language == 'ko':
        user = (
            f"Creative Director가 제안한 3가지 각도를 날카롭게 비판하고 최강의 각도 1개를 선택해.\n\n"
            f"[전체 논의]\n{log}\n\n"
            "각 각도에 대해:\n"
            "- 약점 / 식상한 부분 / 실패 위험 요소\n"
            "- 핵심 개선점\n\n"
            "마지막에 반드시 '최종 선택: 각도 N - [이유 2문장]' 형식으로 최강 각도를 선택해."
        )
    else:
        user = (
            f"Critically evaluate the 3 angles from the Creative Director and select the single strongest one.\n\n"
            f"[FULL DISCUSSION]\n{log}\n\n"
            "For each angle:\n"
            "- Weaknesses / clichés / failure risks\n"
            "- Key improvements needed\n\n"
            "End with: 'FINAL SELECTION: Angle N - [2 sentences of reasoning]'"
        )
    result = _call_groq('llama-3.1-8b-instant', _DA_SYSTEM[language], user, temperature=0.8, max_tokens=800)
    print(f"[Agent3/DevilsAdvocate] 완료 ({len(result)}자)")
    return result


# ── Agent 4: Analyst (Ollama gemma2:27b) ───────────────────────────
def _agent4_analyst(conversation: list, genre: str, language: str) -> str:
    log = _format_log(conversation)
    if language == 'ko':
        prompt = (
            "[역할] 당신은 유튜브 쇼츠 타겟 시청자 분석가입니다.\n\n"
            f"[지금까지의 논의]\n{log}\n\n"
            "[임무] Devil's Advocate가 선택한 최종 각도를 타겟 시청자 관점에서 분석하고 최종 방향을 확정해:\n"
            "1. 핵심 타겟은 누구인가? (나이대/성별/관심사)\n"
            "2. 어떤 감정을 자극할 것인가?\n"
            "3. 댓글/공유를 유도할 핵심 감정 포인트\n"
            "4. 최종 확정 스토리 방향 (명확하게 1~2문장)\n\n"
            "분석 결과와 최종 확정 방향을 제시해줘."
        )
    else:
        prompt = (
            "[ROLE] You are a YouTube Shorts target audience analyst.\n\n"
            f"[DISCUSSION SO FAR]\n{log}\n\n"
            "[TASK] Analyze the selected angle from the target audience perspective and confirm the final direction:\n"
            "1. Who is the core target? (age/gender/interests)\n"
            "2. What emotions will it trigger?\n"
            "3. Key emotional hook for comments/shares\n"
            "4. Final confirmed story direction (clearly in 1-2 sentences)\n\n"
            "Provide your analysis and state the final confirmed direction."
        )
    result = _call_ollama('gemma2:27b', prompt, temperature=0.75, num_predict=600)
    print(f"[Agent4/Analyst] 완료 ({len(result)}자)")
    return result


# ── Agent 5: Script Master (Cerebras llama-3.3-70b) ────────────────
_SM_SYSTEM = {
    'ko': "당신은 유튜브 쇼츠 전문 스크립트 마스터입니다. 지금까지의 모든 논의를 종합하여 완성도 높은 쇼츠 스크립트 초안을 작성합니다. 말하듯이 자연스럽고, 감정적으로 강렬한 나레이션을 작성하는 전문가입니다.",
    'en': "You are a YouTube Shorts script master. You synthesize all prior discussion into a compelling draft script with natural, emotionally powerful narration.",
}

def _agent5_script_master(conversation: list, genre: str, language: str, style_hint: str) -> str:
    log = _format_log(conversation)
    if language == 'ko':
        user = (
            f"지금까지 모든 에이전트의 논의를 종합해서, '{genre}' 장르 유튜브 쇼츠 스크립트 초안을 작성해줘.\n\n"
            f"[전체 에이전트 논의]\n{log}\n\n"
            "초안 작성 요건:\n"
            "- 훅: 첫 1~2초 안에 엄지를 멈추게 만드는 구체적인 한 문장 (숫자/상황/감정 포함)\n"
            "- 씬1~5 나레이션: 말하듯이 자연스럽게, 각 씬 10~15초 분량\n"
            "- 씬 구조: 충격 -> 전개 -> 반전 -> 클라이맥스 -> 마무리+댓글유도\n"
            f"- 이미지 방향: {style_hint} 스타일로 각 씬 분위기 묘사 (영어로)\n\n"
            "JSON이 아닌 자연스러운 텍스트로 초안을 작성해줘. Final Writer가 이를 JSON으로 변환할 거야."
        )
    else:
        user = (
            f"Synthesize all agent discussions into a compelling draft script for a '{genre}' YouTube Shorts.\n\n"
            f"[FULL AGENT DISCUSSION]\n{log}\n\n"
            "Draft requirements:\n"
            "- Hook: One specific sentence to stop the scroll in 1-2 seconds (include number/situation/emotion)\n"
            "- Scene 1-5 narration: Conversational tone, 10-15 sec each\n"
            "- Scene structure: Hook -> Conflict -> Twist -> Climax -> Ending+engagement prompt\n"
            f"- Image direction: {style_hint} style, describe each scene's atmosphere (in English)\n\n"
            "Write the draft in natural text, NOT JSON. The Final Writer will convert it to JSON."
        )
    result = _call_cerebras('qwen-3-235b-a22b-instruct-2507', _SM_SYSTEM[language], user, temperature=0.88, max_tokens=1500)
    print(f"[Agent5/ScriptMaster] 완료 ({len(result)}자)")
    return result


# ── Agent 6: Final Writer (Groq llama-3.3-70b-versatile) ───────────
_FW_SYSTEM = {
    'ko': "당신은 유튜브 쇼츠 전문 스크립트 작가입니다. Script Master의 초안을 검토하고 최종 JSON으로 완성합니다. 반드시 순수 JSON만 반환하고, 코드블록이나 설명은 절대 포함하지 마세요.",
    'en': "You are an expert YouTube Shorts scriptwriter. Review the Script Master's draft and produce the final JSON. Return ONLY raw JSON — no code blocks, no explanation.",
}

def _agent6_final_writer(conversation: list, genre: str, language: str,
                          style_hint: str, hashtag1: str, hashtag2: str,
                          recent_titles=None) -> dict:
    log = _format_log(conversation)

    avoid_section = ""
    if recent_titles:
        titles_str = "\n".join(f"- {t}" for t in recent_titles)
        if language == 'ko':
            avoid_section = f"\n[절대 중복 금지] 아래 제목들과 비슷한 주제나 내용은 절대 만들지 마세요:\n{titles_str}\n"
        else:
            avoid_section = f"\n[NO DUPLICATES] Never create content similar to these titles:\n{titles_str}\n"

    user = _FINAL_WRITER_TEMPLATE[language].format(
        conversation_log=log,
        genre=genre,
        style_hint=style_hint,
        hashtag1=hashtag1,
        hashtag2=hashtag2,
    ) + avoid_section

    result = _call_groq('llama-3.3-70b-versatile', _FW_SYSTEM[language], user,
                        temperature=0.8, max_tokens=2048)
    print(f"[Agent6/FinalWriter] 완료 ({len(result)}자)")
    return _parse_json(result)


# ── 메인 파이프라인 ─────────────────────────────────────────────────
def run_pipeline(genre: str, language: str, gemini_client,
                 style_hint: str, hashtag1: str, hashtag2: str,
                 recent_titles=None) -> dict:
    """
    6-Agent 파이프라인 실행. 최종 스크립트 dict 반환.
    각 에이전트는 이전 에이전트들의 전체 대화를 context로 받아 반응.
    """
    conversation = []

    def _log_agent(name, content):
        sep = "─" * 60
        print(f"\n{sep}")
        print(f"💬 {name}")
        print(sep)
        print(content[:600] + ("..." if len(content) > 600 else ""))
        print(sep)

    print("[Pipeline] Agent 1/6 - Trend Scout (Gemini Flash + Google Search)")
    topic = _agent1_trend_scout(gemini_client, genre, language)
    label = "트렌딩 주제" if language == 'ko' else "Trending topic"
    conversation.append({"agent": "Trend Scout", "content": f"{label}: {topic}"})
    _log_agent("Trend Scout", f"{label}: {topic}")

    print("[Pipeline] Agent 2/6 - Creative Director (Groq llama-3.3-70b-versatile)")
    creative = _agent2_creative_director(conversation, genre, language)
    conversation.append({"agent": "Creative Director", "content": creative})
    _log_agent("Creative Director", creative)

    print("[Pipeline] Agent 3/6 - Devil's Advocate (Groq llama-3.1-8b-instant)")
    devils = _agent3_devils_advocate(conversation, genre, language)
    conversation.append({"agent": "Devil's Advocate", "content": devils})
    _log_agent("Devil's Advocate", devils)

    print("[Pipeline] Agent 4/6 - Analyst (Ollama gemma2:27b)")
    analyst = _agent4_analyst(conversation, genre, language)
    conversation.append({"agent": "Analyst", "content": analyst})
    _log_agent("Analyst", analyst)

    print("[Pipeline] Agent 5/6 - Script Master (Cerebras qwen-3-235b)")
    draft = _agent5_script_master(conversation, genre, language, style_hint)
    conversation.append({"agent": "Script Master", "content": draft})
    _log_agent("Script Master", draft)

    print("[Pipeline] Agent 6/6 - Final Writer (Groq llama-3.3-70b-versatile)")
    script = _agent6_final_writer(
        conversation, genre, language,
        style_hint, hashtag1, hashtag2,
        recent_titles,
    )

    return script
