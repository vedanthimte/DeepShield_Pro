import os
import threading
from dataclasses import dataclass
from typing import Any

import torch
from PIL import Image, ImageOps
from transformers import ViTForImageClassification, ViTImageProcessor

MODEL_ID = os.getenv(
    "DEEPSHIELD_MODEL",
    "buildborderless/CommunityForensics-DeepfakeDet-ViT",
)
FAKE_THRESHOLD = float(os.getenv("FAKE_THRESHOLD", "0.65"))
REAL_THRESHOLD = float(os.getenv("REAL_THRESHOLD", "0.35"))

@dataclass
class Prediction:
    verdict: str
    fake_score: float
    real_score: float
    threshold: dict[str, float]
    model: str
    device: str
    note: str

class Detector:
    """Lazy-loaded CommunityForensics detector. The model emits one logit."""
    def __init__(self):
        self._lock = threading.Lock()
        self.processor = None
        self.model = None
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.load_error = None

    def load(self):
        if self.model is not None:
            return
        with self._lock:
            if self.model is not None:
                return
            try:
                # This model's corrected config requires Transformers >= 5.4.0.
                processor = ViTImageProcessor.from_pretrained(MODEL_ID)
                model = ViTForImageClassification.from_pretrained(
                    MODEL_ID, use_safetensors=True
                )
                model.to(self.device)
                model.eval()
                # Guard against old/bad cached configs silently producing wrong output.
                if getattr(model.config, "num_labels", None) != 1:
                    raise RuntimeError(
                        "Model config is not the corrected single-logit version. "
                        "Clear the Hugging Face cache for this model and retry."
                    )
                self.processor, self.model = processor, model
                self.load_error = None
            except Exception as exc:
                self.load_error = str(exc)
                raise

    @torch.inference_mode()
    def predict(self, image: Image.Image) -> Prediction:
        self.load()
        image = ImageOps.exif_transpose(image).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        inputs = {k: v.to(self.device) for k, v in inputs.items()}
        logits = self.model(**inputs).logits.reshape(-1)
        fake_score = float(torch.sigmoid(logits[0]).detach().cpu().item())
        print("\n========== DEEPSHIELD DEBUG ==========")
        print("Model:", MODEL_ID)
        print("Logits shape:", tuple(logits.shape))
        print("Raw logit:", logits.detach().cpu().tolist())
        print("Fake score:", fake_score)
        print("======================================\n")   
        real_score = 1.0 - fake_score

        # Conservative triage: middle scores are inconclusive, not forced into a class.
        if fake_score >= FAKE_THRESHOLD:
            verdict = "Likely AI-generated / manipulated"
        elif fake_score <= REAL_THRESHOLD:
            verdict = "Likely real"
        else:
            verdict = "Inconclusive"

        return Prediction(
            verdict=verdict,
            fake_score=round(fake_score, 6),
            real_score=round(real_score, 6),
            threshold={"real_max": REAL_THRESHOLD, "fake_min": FAKE_THRESHOLD},
            model=MODEL_ID,
            device=str(self.device),
            note=(
                "Scores are model outputs, not calibrated probabilities or proof of authenticity. "
                "This model targets AI-generated images; video-frame results are experimental and "
                "are not a validated face-swap detector."
            ),
        )

detector = Detector()
