# DeepShield Pro (native Windows, no Docker)

python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 

React + Vite frontend and FastAPI + PyTorch backend. Uses the corrected CommunityForensics model for AI-generated image screening. Includes experimental video frame sampling, JSON report download, SHA-256 hashing, upload limits, a health endpoint, and conservative `Likely real / Inconclusive / Likely AI-generated` output.

## Model choice
`buildborderless/CommunityForensics-DeepfakeDet-ViT`, a ViT-Small detector trained on 2.7 million samples across 4,803 generators. The model card was updated in July 2026 to correct its weights/config. This project requires `transformers>=5.4.0` and checks that the model has the expected single-logit configuration. See https://huggingface.co/buildborderless/CommunityForensics-DeepfakeDet-ViT

## Prerequisites
- Windows 10/11
- Python 3.11 (recommended)
- Node.js 20+ with npm
- 8 GB RAM recommended; first model download needs internet and several hundred MB of disk space
- Optional NVIDIA GPU; PyTorch uses CUDA if available

## Run
1. Extract this folder.
2. Install Python 3.11 and Node.js 20+ if missing.
3. Double-click `run_windows.bat`.
4. The script installs backend requirements, starts FastAPI, installs frontend packages and starts Vite.
5. Open the URL printed by Vite, usually `http://localhost:5173`.
6. API docs: `http://127.0.0.1:8000/docs`.

The first analysis may take several minutes while model weights download. Keep the backend terminal open.

## Manual start
Backend terminal:
```powershell
py -3.11 -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r backend\requirements.txt
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
Frontend terminal:
```powershell
cd frontend
npm install
npm run dev
```

## Environment options
- `DEEPSHIELD_MODEL`: defaults to the CommunityForensics model ID.
- `REAL_THRESHOLD`: defaults to `0.35`.
- `FAKE_THRESHOLD`: defaults to `0.65`.
- `MAX_IMAGE_MB`: defaults to `15`.
- `MAX_VIDEO_MB`: defaults to `100`.
- `CORS_ORIGINS`: comma-separated frontend origins.

Thresholds are conservative triage defaults, not statistically calibrated confidence levels. Calibrate them on a held-out dataset before production use.

## API
- `GET /api/health`
- `POST /api/analyze/image` multipart field `file`
- `POST /api/analyze/video` multipart field `file`, optional `max_frames` 1–16

## Important limitations
- AI-generated image detector, not a validated dedicated face-swap detector.
- Video endpoint samples up to 8 frames across a clip and applies the image model independently to each. It does not analyze temporal inconsistencies and must be treated as experimental screening only.
- The score is a sigmoid model output, not a calibrated probability or proof of authenticity.
- Do not use results alone for consequential decisions. Test false positives and false negatives on your own representative dataset.
- Local backend does not persist uploads. In-memory model cache is used.
- Before production deployment, add authentication, request rate limiting, malware scanning, audit controls, a job queue for long videos, and a privacy/retention policy.
