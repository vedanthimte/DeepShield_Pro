
from pathlib import Path
import sys

import torch
from PIL import Image, UnidentifiedImageError
from transformers import AutoImageProcessor, AutoModelForImageClassification

MODEL_NAME = "hamzenium/ViT-Deepfake-Classifier"

print("Loading DeepShield detector...")

processor = AutoImageProcessor.from_pretrained(MODEL_NAME)
model = AutoModelForImageClassification.from_pretrained(MODEL_NAME)
model.eval()


def predict_image(image_path):
    path = Path(image_path)

    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {path}")

    try:
        with Image.open(path) as img:
            image = img.convert("RGB")
    except (UnidentifiedImageError, OSError) as exc:
        raise ValueError("Invalid or unsupported image file.") from exc

    inputs = processor(images=image, return_tensors="pt")

    with torch.inference_mode():
        logits = model(**inputs).logits
        probabilities = torch.softmax(logits, dim=-1)[0]

    print("\n--- DeepShield Analysis ---")

    for index, score in enumerate(probabilities.tolist()):
        label = model.config.id2label.get(
            index, str(index)
        )
        print(f"{label}: {score:.2%}")

    predicted_index = probabilities.argmax().item()
    label = model.config.id2label[predicted_index]
    print(f"\nTop prediction: {label}")
    print(f"Model score: {probabilities[predicted_index]:.2%}")
    print("Note: This prediction is not proof of authenticity.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print('Usage: python test_detector.py "path/to/image.jpg"')
        raise SystemExit(1)

    predict_image(sys.argv[1])
