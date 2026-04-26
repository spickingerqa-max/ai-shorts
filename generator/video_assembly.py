import os
import time
import textwrap
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from moviepy.editor import VideoClip, AudioFileClip, concatenate_videoclips

WIDTH, HEIGHT = 1080, 1920
FPS = 30
CRF = 23

FONT_PATHS = [
    '/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc',
    '/usr/share/fonts/opentype/noto/NotoSansCJKkr-Regular.otf',
    '/usr/share/fonts/noto-cjk/NotoSansCJKkr-Regular.otf',
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',
]


def _get_font(size):
    for path in FONT_PATHS:
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    print("[Video] 경고: NotoSansCJK 폰트 없음, 기본 폰트 사용")
    return ImageFont.load_default()


def _render_subtitle(text, language='ko'):
    """흰 글씨 + 검정 테두리 자막을 RGBA PIL 이미지로 렌더링"""
    img = Image.new('RGBA', (WIDTH, HEIGHT), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    font_size = 52
    font = _get_font(font_size)

    # 언어별 줄바꿈 기준
    max_chars = 18 if language == 'ko' else 38
    lines = textwrap.wrap(text, width=max_chars)
    if not lines:
        return np.array(img)

    line_height = font_size + 14
    total_h = len(lines) * line_height
    y_start = HEIGHT - total_h - 130

    outline_range = [-2, -1, 0, 1, 2]
    for i, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        text_w = bbox[2] - bbox[0]
        x = (WIDTH - text_w) // 2
        y = y_start + i * line_height

        # 검정 테두리 (8방향 + 대각선 포함)
        for dx in outline_range:
            for dy in outline_range:
                if dx != 0 or dy != 0:
                    draw.text((x + dx, y + dy), line, font=font, fill=(0, 0, 0, 255))
        # 흰 글씨
        draw.text((x, y), line, font=font, fill=(255, 255, 255, 255))

    return np.array(img)


def _make_scene_clip(image_path, duration, narration, language, zoom_in):
    """Ken Burns 효과 + 자막 합성 클립 생성"""
    base_img = Image.open(image_path).convert('RGB').resize((WIDTH, HEIGHT), Image.LANCZOS)
    base_arr = np.array(base_img)

    subtitle_arr = _render_subtitle(narration, language)
    subtitle_pil = Image.fromarray(subtitle_arr, 'RGBA')

    def make_frame(t):
        progress = t / max(duration, 0.001)
        # zoom in: 1.0 → 1.08 / zoom out: 1.08 → 1.0
        scale = (1.0 + 0.08 * progress) if zoom_in else (1.08 - 0.08 * progress)

        new_w = int(WIDTH * scale)
        new_h = int(HEIGHT * scale)
        scaled = Image.fromarray(base_arr).resize((new_w, new_h), Image.LANCZOS)

        # 중앙 크롭
        x = (new_w - WIDTH) // 2
        y = (new_h - HEIGHT) // 2
        frame = scaled.crop((x, y, x + WIDTH, y + HEIGHT)).convert('RGBA')

        # 자막 합성
        frame.paste(subtitle_pil, (0, 0), subtitle_pil)
        return np.array(frame.convert('RGB'))

    return VideoClip(make_frame, duration=duration).set_fps(FPS)


def assemble_video(script, image_paths, audio_paths, output_dir):
    """
    script      : generate_script() 반환 dict
    image_paths : 씬별 이미지 파일 경로 리스트 (5개)
    audio_paths : 씬별 오디오 파일 경로 리스트 (5개)
    output_dir  : 출력 디렉터리
    """
    genre = script['genre']
    language = script.get('language', 'ko')
    timestamp = int(time.time())
    filename = f"{genre}_{language}_{timestamp}.mp4"
    output_path = os.path.join(output_dir, filename)

    os.makedirs(output_dir, exist_ok=True)

    # 씬별 오디오 로드 및 실제 길이 측정
    audio_clips = []
    durations = []
    for path in audio_paths:
        clip = AudioFileClip(path)
        audio_clips.append(clip)
        durations.append(clip.duration)

    total_audio = sum(durations)
    print(f"[Video] 총 오디오 길이: {total_audio:.1f}초 | 씬별: {[f'{d:.1f}s' for d in durations]}")

    # 씬별 클립 생성
    scene_clips = []
    for i, (img_path, audio_clip, duration) in enumerate(zip(image_paths, audio_clips, durations)):
        zoom_in = (i % 2 == 0)  # 짝수 씬: zoom in, 홀수 씬: zoom out
        narration = script['scenes'][i]['narration']

        print(f"[Video] 씬 {i+1}/5 렌더링 중... (zoom_{'in' if zoom_in else 'out'}, {duration:.1f}s)")
        clip = _make_scene_clip(img_path, duration, narration, language, zoom_in)
        clip = clip.set_audio(audio_clip)
        scene_clips.append(clip)

    # 씬 연결
    print("[Video] 씬 연결 중...")
    final = concatenate_videoclips(scene_clips, method='compose')

    # 출력
    print(f"[Video] 렌더링 시작: {output_path}")
    final.write_videofile(
        output_path,
        fps=FPS,
        codec='libx264',
        audio_codec='aac',
        ffmpeg_params=['-crf', str(CRF), '-movflags', '+faststart'],
        verbose=False,
        logger=None,
    )

    # 리소스 정리
    for clip in audio_clips + scene_clips:
        try:
            clip.close()
        except Exception:
            pass
    final.close()

    file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
    print(f"[Video] 완료: {filename} ({file_size_mb:.1f} MB)")
    return output_path, filename, file_size_mb
