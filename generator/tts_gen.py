import asyncio
import os
import edge_tts
from google import genai

client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))

AVAILABLE_VOICES = {
    'ko': [
        'ko-KR-SunHiNeural',
        'ko-KR-InJoonNeural',
        'ko-KR-HyunsuNeural',
        'ko-KR-YuJinNeural',
        'ko-KR-BongJinNeural',
        'ko-KR-SeoHyeonNeural',
    ],
    'en': [
        'en-US-GuyNeural',
        'en-US-AriaNeural',
        'en-US-ChristopherNeural',
        'en-US-JennyNeural',
        'en-US-EricNeural',
        'en-US-MichelleNeural',
        'en-US-SteffanNeural',
        'en-US-EmmaNeural',
        'en-GB-SoniaNeural',
        'en-GB-RyanNeural',
        'en-GB-ThomasNeural',
        'en-AU-NatashaNeural',
    ],
}

GENRE_DEFAULTS = {
    'ko': {
        'horror':  'ko-KR-InJoonNeural',
        'history': 'ko-KR-BongJinNeural',
        'success': 'ko-KR-HyunsuNeural',
        'trend':   'ko-KR-YuJinNeural',
    },
    'en': {
        'horror':  'en-US-ChristopherNeural',
        'history': 'en-GB-RyanNeural',
        'success': 'en-US-SteffanNeural',
        'trend':   'en-US-AriaNeural',
    },
}

GENRE_RATE_PITCH = {
    'horror':  {'rate': '-10%', 'pitch': '-5Hz'},
    'history': {'rate': '+5%',  'pitch': '+0Hz'},
    'success': {'rate': '+20%', 'pitch': '+10Hz'},
    'trend':   {'rate': '+15%', 'pitch': '+0Hz'},
}

VOICE_SELECT_PROMPT = {
    'ko': """아래 유튜브 쇼츠 영상에 가장 어울리는 한국어 Edge-TTS 목소리를 골라줘.

영상 정보:
- 제목: {title}
- 장르: {genre}
- 훅(첫 문장): {hook}

사용 가능한 목소리 목록:
- ko-KR-SunHiNeural (여성, 밝고 또렷)
- ko-KR-InJoonNeural (남성, 차분하고 묵직)
- ko-KR-HyunsuNeural (남성, 젊고 에너지)
- ko-KR-YuJinNeural (여성, 트렌디하고 자연스러움)
- ko-KR-BongJinNeural (남성, 중후함)
- ko-KR-SeoHyeonNeural (여성, 부드럽고 감성적)

반드시 아래 형식으로만 답해줘 (다른 텍스트 없이):
목소리: ko-KR-XXXXXX
이유: 한 줄 설명
""",
    'en': """Choose the best English Edge-TTS voice for the YouTube Shorts video below.

Video info:
- Title: {title}
- Genre: {genre}
- Hook (opening line): {hook}

Available voices:
- en-US-GuyNeural (male, calm and steady)
- en-US-AriaNeural (female, bright and engaging)
- en-US-ChristopherNeural (male, deep and authoritative)
- en-US-JennyNeural (female, trendy and conversational)
- en-US-EricNeural (male, trustworthy)
- en-US-MichelleNeural (female, soft and warm)
- en-US-SteffanNeural (male, dynamic and energetic)
- en-US-EmmaNeural (female, natural and relatable)
- en-GB-SoniaNeural (British female, elegant)
- en-GB-RyanNeural (British male, trustworthy)
- en-GB-ThomasNeural (British male, formal)
- en-AU-NatashaNeural (Australian female, distinctive)

Reply ONLY in this format (no other text):
Voice: en-XX-XXXXXNeural
Reason: one-line explanation
""",
}


def _select_voice(title, genre, hook, language):
    prompt = VOICE_SELECT_PROMPT[language].format(title=title, genre=genre, hook=hook)
    voices = AVAILABLE_VOICES[language]
    prefix = 'Voice:' if language == 'en' else '목소리:'

    try:
        response = client.models.generate_content(
            model='gemini-flash-latest',
            contents=prompt,
        )
        text = response.text.strip()
        print(f"[TTS] Gemini 목소리 선택 응답:\n{text}")

        for line in text.splitlines():
            if line.startswith(prefix):
                voice = line.split(':', 1)[1].strip()
                if voice in voices:
                    return voice
                print(f"[TTS] 알 수 없는 목소리 '{voice}' - 기본값 사용")
                break

    except Exception as e:
        print(f"[TTS] Gemini 목소리 선택 실패: {e} - 기본값 사용")

    return GENRE_DEFAULTS[language].get(genre, voices[0])


async def _synthesize(text, voice, rate, pitch, output_path):
    communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
    await communicate.save(output_path)


def generate_tts(text, genre, output_path, title='', hook='', language='ko'):
    voice = _select_voice(title=title, genre=genre, hook=hook, language=language)

    rp = GENRE_RATE_PITCH.get(genre, GENRE_RATE_PITCH['history'])
    rate = rp['rate']
    pitch = rp['pitch']

    print(f"[TTS] 생성 중... lang={language} 장르={genre} 목소리={voice} rate={rate} pitch={pitch}")

    asyncio.run(_synthesize(
        text=text,
        voice=voice,
        rate=rate,
        pitch=pitch,
        output_path=output_path,
    ))

    if not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
        raise RuntimeError(f"[TTS] 파일 생성 실패: {output_path}")

    print(f"[TTS] 완료: {output_path}")
