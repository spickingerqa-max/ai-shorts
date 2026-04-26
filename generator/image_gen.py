import torch
from diffusers import StableDiffusionXLPipeline, DPMSolverMultistepScheduler
from PIL import Image

MODEL_ID = "SG161222/RealVisXL_V4.0"

GENRE_PREFIX = {
    'horror':  (
        "RAW photo, photorealistic, ultra-detailed, cinematic, "
        "dark horror scene, eerie atmosphere, dramatic shadows, dim moonlight, "
        "abandoned place, terrifying, suspenseful, realistic human figure, "
        "film grain, 4k, shot on canon eos, "
    ),
    'history': (
        "RAW photo, photorealistic, ultra-detailed, cinematic, "
        "historical epic scene, ancient or medieval setting, "
        "period-accurate costume, dramatic lighting, realistic person, "
        "documentary style, detailed environment, 4k, "
    ),
    'success': (
        "RAW photo, photorealistic, ultra-detailed, cinematic, "
        "1 young professional person, modern city or office background, "
        "business casual, confident expression, warm golden hour light, "
        "inspiring atmosphere, sharp focus, 4k, shot on sony a7, "
    ),
    'trend':   (
        "RAW photo, photorealistic, ultra-detailed, cinematic, "
        "1 stylish young person, trendy urban setting, street or cafe, "
        "vibrant natural colors, candid shot, social media aesthetic, "
        "lifestyle photography, 4k, "
    ),
}

GENRE_NEGATIVE = {
    'horror':  "anime, cartoon, drawing, illustration, bright, cheerful, cute, ",
    'history': "anime, cartoon, drawing, modern clothing, futuristic, ",
    'success': "anime, cartoon, drawing, robot, fantasy, sci-fi, ",
    'trend':   "anime, cartoon, drawing, historical, old-fashioned, dark, ",
}

NEGATIVE_PROMPT = (
    "anime, cartoon, illustration, drawing, 3d render, cgi, "
    "lowres, bad anatomy, bad hands, missing fingers, extra fingers, "
    "blurry, low quality, ugly, deformed, mutated, watermark, text, "
    "signature, username, nsfw, nude, explicit"
)

_pipe = None


def _load_model():
    global _pipe
    if _pipe is not None:
        return _pipe

    print("[ImageGen] 모델 로딩 중... (최초 1회, 약 1~2분 소요)")

    scheduler = DPMSolverMultistepScheduler.from_pretrained(
        MODEL_ID,
        subfolder="scheduler",
        algorithm_type="sde-dpmsolver++",
        use_karras_sigmas=True,
    )

    pipe = StableDiffusionXLPipeline.from_pretrained(
        MODEL_ID,
        scheduler=scheduler,
        torch_dtype=torch.float16,
        use_safetensors=True,
    )
    pipe = pipe.to("cuda")
    pipe.enable_xformers_memory_efficient_attention()

    _pipe = pipe
    print("[ImageGen] 모델 로딩 완료")
    return _pipe


def generate_image(image_prompt, genre, output_path):
    pipe = _load_model()

    prefix = GENRE_PREFIX.get(genre, GENRE_PREFIX['history'])
    full_prompt = prefix + image_prompt
    genre_neg = GENRE_NEGATIVE.get(genre, "")
    full_negative = genre_neg + NEGATIVE_PROMPT

    print(f"[ImageGen] 이미지 생성 중... 장르={genre}")
    print(f"[ImageGen] 프롬프트: {full_prompt[:80]}...")

    result = pipe(
        prompt=full_prompt,
        negative_prompt=full_negative,
        width=832,
        height=1472,
        num_inference_steps=25,
        guidance_scale=7.0,
        num_images_per_prompt=1,
    )

    image = result.images[0]
    image = image.resize((1080, 1920), Image.LANCZOS)
    image.save(output_path)

    print(f"[ImageGen] 저장 완료: {output_path}")
    return output_path
