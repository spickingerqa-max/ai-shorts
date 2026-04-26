# shorts-factory

## 개요
RTX 4090 + Docker Compose 기반 유튜브 쇼츠 자동 생성 시스템.
공포 / 역사 / 성공 3개 장르를 2시간마다 자동으로 생성한다.

## 기술 스택
- 스크립트: Gemini 1.5 Flash (무료 API)
- 이미지: animagine-xl-3.1 (로컬 SDXL, RTX 4090 CUDA)
- TTS: Edge-TTS (ko-KR 한국어)
- 영상: MoviePy + FFmpeg (Ken Burns 효과 + 자막)
- DB: MySQL 8.0
- 대시보드: PHP 8.2 + Apache
- 모니터링: Grafana
- 스케줄: Python schedule (2시간마다)
- 인프라: Docker Compose

## 폴더 구조 (전부 새로 만들어야 함)
```
shorts-factory/
├── docker-compose.yml
├── .env
├── generator/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py
│   ├── gemini_script.py
│   ├── image_gen.py
│   ├── tts_gen.py
│   ├── video_assembly.py
│   └── db.py
├── mysql/
│   └── init.sql
├── web/
│   ├── Dockerfile
│   └── html/
│       ├── index.php
│       └── api.php
└── grafana/
    └── provisioning/
        ├── datasources/
        │   └── mysql.yml
        └── dashboards/
            ├── dashboards.yml
            └── shorts.json
```

## Docker 서비스

### mysql
- image: mysql:8.0
- port: 3307:3306
- DB: shortsdb / user: shorts / password: ${MYSQL_PASSWORD}
- volume: mysql_data

### generator
- base: pytorch/pytorch:2.3.0-cuda12.1-cudnn8-runtime
- GPU: RTX 4090 (deploy.resources.reservations.devices nvidia)
- shm_size: 4gb
- volume: videos (영상 저장), hf_cache (모델 캐시)
- 2시간마다 쇼츠 자동 생성

### web
- base: php:8.2-apache
- port: 8080:80
- volume: videos (generator와 공유)

### grafana
- image: grafana/grafana:latest
- port: 3000:3000
- MySQL 자동 프로비저닝

## MySQL 스키마
```sql
CREATE DATABASE IF NOT EXISTS shortsdb CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
USE shortsdb;
CREATE TABLE IF NOT EXISTS shorts (
  id           INT AUTO_INCREMENT PRIMARY KEY,
  title        VARCHAR(100) NOT NULL,
  genre        ENUM('horror','history','success') NOT NULL,
  hook         TEXT,
  hashtags     JSON,
  filename     VARCHAR(200) NOT NULL,
  file_size_mb FLOAT DEFAULT 0,
  status       ENUM('done','error') DEFAULT 'done',
  created_at   TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## .env 내용
```
GEMINI_API_KEY=AIzaSyAlBOhP0-E17lWhOQFMBRTALmwR_P4xgJw
MYSQL_ROOT_PASSWORD=rootpass1234
MYSQL_PASSWORD=shortspass1234
GRAFANA_PASSWORD=admin123
GENERATE_INTERVAL_HOURS=2
```

## generator/requirements.txt
```
google-generativeai==0.7.2
diffusers==0.29.2
transformers==4.41.2
accelerate==0.31.0
safetensors==0.4.3
xformers==0.0.27
edge-tts==6.1.10
moviepy==1.0.3
Pillow==10.3.0
pymysql==1.1.1
schedule==1.2.2
numpy==1.26.4
requests==2.31.0
python-dotenv==1.0.1
```

## PHP 대시보드 (index.php) 요구사항
- MySQL 연결 (환경변수 사용)
- 생성된 영상 목록 (제목/장르/날짜/크기)
- 장르별 필터 (전체/공포/역사/성공)
- video 태그로 브라우저 내 재생
- 상단에 총 생성 수 + 장르별 통계
- 5초마다 자동 새로고침
- 다크 테마, 모바일 반응형

## Grafana 대시보드 패널
1. 총 생성 쇼츠 수 (Stat)
2. 장르별 분포 (Pie chart)
3. 시간별 생성 추이 (Time series)
4. 최근 20개 목록 (Table)

## 핵심 Python 로직 (CLI가 구현할 때 참고)

### gemini_script.py
- 장르별 프롬프트로 Gemini 1.5 Flash 호출
- JSON 반환: {title, genre, hook, scenes:[{id, narration, image_prompt, duration}], hashtags}
- 3개 장르: horror / history / success
- API 실패시 재시도 3번

### image_gen.py
- animagine-xl-3.1 모델 (cagliostrolab/animagine-xl-3.1)
- torch.float16, xformers 메모리 최적화
- 해상도: 832x1472 (9:16) → resize 1080x1920
- DPMSolverMultistepScheduler (sde-dpmsolver++, karras)
- steps=25, guidance=7.0
- 장르별 스타일 prefix + 네거티브 프롬프트

### tts_gen.py
- horror: ko-KR-InJoonNeural, rate=-10%, pitch=-5Hz
- history: ko-KR-SunHiNeural, rate=+5%
- success: ko-KR-SunHiNeural, rate=+20%, pitch=+10Hz

### video_assembly.py
- Ken Burns 효과: zoom 1.0→1.08 (방향 교차)
- PIL로 자막 렌더링: 흰글씨 + 검정 테두리, NotoSansCJK 폰트
- 씬별 duration은 오디오 전체 길이에 맞게 스케일
- 출력: 1080x1920, 30fps, libx264, crf=23

### db.py
- MySQL 연결 재시도 10회 (5초 간격)
- save_short(): title, genre, hook, hashtags, filename, file_size_mb 저장

### main.py
- 시작 즉시 1회 생성, 이후 2시간마다 반복
- 임시파일 자동 정리 (/outputs/temp)
- 최대 100개 영상 보관 (오래된 것부터 삭제)
