import os
import glob
import shutil
import schedule
import time

from dotenv import load_dotenv
load_dotenv()

from gemini_script import generate_script
from image_gen import generate_image
from tts_gen import generate_tts
from video_assembly import assemble_video
from db import save_short

VIDEO_DIR = '/outputs/videos'
TEMP_DIR  = '/outputs/temp'
MAX_VIDEOS = 100


def _cleanup_temp(temp_session_dir):
    try:
        shutil.rmtree(temp_session_dir, ignore_errors=True)
        print(f"[Main] 임시파일 정리 완료: {temp_session_dir}")
    except Exception as e:
        print(f"[Main] 임시파일 정리 실패: {e}")


def _enforce_video_limit():
    videos = sorted(
        glob.glob(os.path.join(VIDEO_DIR, '*.mp4')),
        key=os.path.getmtime,
    )
    if len(videos) > MAX_VIDEOS:
        to_delete = videos[:len(videos) - MAX_VIDEOS]
        for path in to_delete:
            try:
                os.remove(path)
                print(f"[Main] 오래된 영상 삭제: {os.path.basename(path)}")
            except Exception as e:
                print(f"[Main] 삭제 실패: {path} - {e}")


def generate_one():
    session_id = int(time.time())
    temp_dir = os.path.join(TEMP_DIR, str(session_id))
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(VIDEO_DIR, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"[Main] 쇼츠 생성 시작 (session={session_id})")
    print(f"{'='*50}")

    try:
        # Step 1: 스크립트 생성 (language 자동 교대)
        script = generate_script()
        title    = script['title']
        genre    = script['genre']
        language = script.get('language', 'ko')
        hook     = script['hook']
        hashtags = script['hashtags']
        scenes   = script['scenes']
        print(f"[Main] 스크립트 완료: [{language}] {title}")

        # Step 2: 씬별 이미지 + TTS 생성
        image_paths = []
        audio_paths = []

        for i, scene in enumerate(scenes):
            print(f"[Main] 씬 {i+1}/5 처리 중...")

            # 이미지 생성
            img_path = os.path.join(temp_dir, f"scene_{i+1}.png")
            generate_image(scene['image_prompt'], genre, img_path)
            image_paths.append(img_path)

            # TTS 생성
            audio_path = os.path.join(temp_dir, f"scene_{i+1}.mp3")
            generate_tts(
                text=scene['narration'],
                genre=genre,
                output_path=audio_path,
                title=title,
                hook=hook,
                language=language,
            )
            audio_paths.append(audio_path)

        # Step 3: 영상 조립
        video_path, filename, file_size_mb = assemble_video(
            script=script,
            image_paths=image_paths,
            audio_paths=audio_paths,
            output_dir=VIDEO_DIR,
        )

        # Step 4: DB 저장
        save_short(
            title=title,
            genre=genre,
            hook=hook,
            hashtags=hashtags,
            filename=filename,
            file_size_mb=file_size_mb,
        )

        # Step 5: 임시파일 정리
        _cleanup_temp(temp_dir)

        # Step 6: 영상 100개 초과 시 오래된 것 삭제
        _enforce_video_limit()

        print(f"[Main] 완료: {filename} ({file_size_mb:.1f} MB)")

    except Exception as e:
        print(f"[Main] 생성 실패: {e}")
        _cleanup_temp(temp_dir)


def main():
    interval_hours = float(os.getenv('GENERATE_INTERVAL_HOURS', '2'))
    interval_minutes = int(interval_hours * 60)

    print("=" * 50)
    print("Shorts Factory 시작!")
    print(f"생성 주기: {interval_hours}시간마다")
    print("=" * 50)

    # 시작 즉시 1회 실행
    generate_one()

    # 이후 주기적으로 반복
    schedule.every(interval_minutes).minutes.do(generate_one)

    while True:
        schedule.run_pending()
        time.sleep(30)


if __name__ == '__main__':
    main()
