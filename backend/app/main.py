import hashlib
import io
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import cv2
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from PIL import Image, UnidentifiedImageError

from .detector import detector

APP_VERSION = "0.2.0"
MAX_IMAGE_BYTES = int(os.getenv("MAX_IMAGE_MB", "15")) * 1024 * 1024
MAX_VIDEO_BYTES = int(os.getenv("MAX_VIDEO_MB", "100")) * 1024 * 1024
ALLOWED_IMAGE = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
ALLOWED_VIDEO = {".mp4", ".mov", ".avi", ".mkv", ".webm"}

app = FastAPI(
    title="DeepShield API",
    version=APP_VERSION,
    description="Local AI-generated image screening and experimental video frame analysis.",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.getenv(
        "CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

def response_base(filename: str, data: bytes, kind: str):
    return {
        "filename": Path(filename).name,
        "media_type": kind,
        "sha256": hashlib.sha256(data).hexdigest(),
        "analyzed_at_utc": datetime.now(timezone.utc).isoformat(),
    }

async def read_upload(upload: UploadFile, max_bytes: int, extensions: set[str]) -> bytes:
    suffix = Path(upload.filename or "").suffix.lower()
    if suffix not in extensions:
        raise HTTPException(415, f"Unsupported file extension: {suffix or '(none)'}")
    data = await upload.read(max_bytes + 1)
    if not data:
        raise HTTPException(400, "The uploaded file is empty.")
    if len(data) > max_bytes:
        raise HTTPException(413, f"File exceeds the {max_bytes // (1024*1024)} MB limit.")
    return data

@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "version": APP_VERSION,
        "model_id": os.getenv(
            "DEEPSHIELD_MODEL",
            "buildborderless/CommunityForensics-DeepfakeDet-ViT",
        ),
        "model_loaded": detector.model is not None,
        "device": str(detector.device),
        "load_error": detector.load_error,
    }

@app.post("/api/analyze/image")
async def analyze_image(file: UploadFile = File(...)):
    data = await read_upload(file, MAX_IMAGE_BYTES, ALLOWED_IMAGE)
    try:
        image = Image.open(io.BytesIO(data))
        image.load()
        image = image.convert("RGB")
    except (UnidentifiedImageError, OSError, ValueError):
        raise HTTPException(400, "The uploaded file is not a valid image.")
    try:
        prediction = detector.predict(image)
    except Exception as exc:
        raise HTTPException(503, f"Model could not load/run: {exc}") from exc
    result = response_base(file.filename or "image", data, "image")
    result.update({
        "width": image.width,
        "height": image.height,
        "prediction": prediction.__dict__,
    })
    return result

@app.post("/api/analyze/video")
async def analyze_video(file: UploadFile = File(...), max_frames: int = 8):
    if not 1 <= max_frames <= 16:
        raise HTTPException(400, "max_frames must be between 1 and 16.")
    data = await read_upload(file, MAX_VIDEO_BYTES, ALLOWED_VIDEO)
    suffix = Path(file.filename or "video.mp4").suffix.lower()
    temp_path = None
    capture = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(data)
            temp_path = tmp.name
        capture = cv2.VideoCapture(temp_path)
        if not capture.isOpened():
            raise HTTPException(400, "Could not decode video. Try a standard MP4 (H.264).")
        frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0)
        if frame_count <= 0:
            raise HTTPException(400, "Video has no readable frames.")
        # Sample across the full clip rather than only taking the opening frames.
        indexes = sorted(set(
            round(i * (frame_count - 1) / max(1, max_frames - 1))
            for i in range(min(max_frames, frame_count))
        ))
        frames = []
        for index in indexes:
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame_bgr = capture.read()
            if not ok:
                continue
            frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
            image = Image.fromarray(frame_rgb)
            pred = detector.predict(image)
            frames.append({
                "frame_index": index,
                "timestamp_seconds": round(index / fps, 3) if fps > 0 else None,
                "prediction": pred.__dict__,
            })
        if not frames:
            raise HTTPException(400, "Could not extract readable video frames.")
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(503, f"Video analysis failed: {exc}") from exc
    finally:
        if capture is not None:
            capture.release()
        if temp_path and os.path.exists(temp_path):
            os.remove(temp_path)

    fake_scores = [x["prediction"]["fake_score"] for x in frames]
    avg_fake = sum(fake_scores) / len(fake_scores)
    fake_count = sum(x >= 0.65 for x in fake_scores)
    real_count = sum(x <= 0.35 for x in fake_scores)
    if avg_fake >= 0.65 and fake_count >= max(1, len(frames) // 2):
        verdict = "Potential manipulation indicators"
    elif avg_fake <= 0.35 and real_count >= max(1, len(frames) // 2):
        verdict = "No strong indicators from sampled frames"
    else:
        verdict = "Inconclusive — review frames"

    result = response_base(file.filename or "video", data, "video")
    result.update({
        "duration_seconds": round(frame_count / fps, 3) if fps > 0 else None,
        "sampled_frames": len(frames),
        "average_fake_score": round(avg_fake, 6),
        "verdict": verdict,
        "frames": frames,
        "note": (
            "Experimental screening only. The underlying model is trained for AI-generated image "
            "detection, not validated specifically for face swaps or temporal video artifacts. "
            "Do not treat this result as proof."
        ),
    })
    return result
