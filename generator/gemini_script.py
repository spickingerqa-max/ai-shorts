import os
import random
from google import genai
from db import get_recent_titles
from agent_pipeline import run_pipeline

_gemini_client = genai.Client(api_key=os.getenv('GEMINI_API_KEY', ''))

GENRES = ['horror', 'history', 'success', 'trend']

_lang_toggle = ['ko']

GENRE_STYLE = {
    'horror':  ('dark horror atmosphere, eerie lighting, shadows',  '#공포',   'horror',  '#Horror'),
    'history': ('historical epic scene, dramatic lighting',          '#역사',   'history', '#History'),
    'success': ('motivational bright scene, successful character',   '#성공',   'success', '#Success'),
    'trend':   ('vibrant trendy scene, modern setting',              '#트렌드', 'trend',   '#Trending'),
}


def generate_script(genre=None, language=None):
    if genre is None:
        genre = random.choice(GENRES)

    if language is None:
        language = _lang_toggle[0]
        _lang_toggle[0] = 'en' if _lang_toggle[0] == 'ko' else 'ko'

    style_hint, ko_tag, en_tag_genre, en_tag = GENRE_STYLE[genre]
    hashtag1 = ko_tag if language == 'ko' else f'#{en_tag_genre.capitalize()}'
    hashtag2 = '#쇼츠' if language == 'ko' else en_tag

    recent_titles = get_recent_titles(20)

    print(f"[Pipeline] 장르={genre} lang={language} - 5-Agent 파이프라인 시작")
    script = run_pipeline(
        genre=genre,
        language=language,
        gemini_client=_gemini_client,
        style_hint=style_hint,
        hashtag1=hashtag1,
        hashtag2=hashtag2,
        recent_titles=recent_titles,
    )

    assert 'title'  in script
    assert 'genre'  in script
    assert 'hook'   in script
    assert 'scenes' in script and len(script['scenes']) == 5
    assert 'hashtags' in script

    script['language'] = language
    print(f"[Pipeline] 완료: {script['title']} (lang={language})")
    return script
