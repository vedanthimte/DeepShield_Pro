
import sys
import torch
from PIL import Image
from transformers import AutoImageProcessor, AutoModelForImageClassification

MODEL_ID = "buildborderless/CommunityForensics-DeepfakeDet-ViT"

if len(sys.argv) < 2:
    print('Usage: python testor.py "path\\to\\image.jpg"')
    raise SystemExit(1)

image_path = sys.argv[1]

print("Loading current image processor...")
processor = AutoImageProcessor.from_pretrained(
    MODEL_ID,
    force_download=True
)

print("Processor:", type(processor).__name__)

print("Loading model...")
model = AutoModelForImageClassification.from_pretrained(MODEL_ID)
model.eval()

print("Model labels:", model.config.num_labels)
print("Attention heads:", model.config.num_attention_heads)
print("Intermediate size:", model.config.intermediate_size)

assert model.config.num_labels == 1, "Incorrect model configuration"
assert model.config.num_attention_heads == 6, "Incorrect model configuration"
assert model.config.intermediate_size == 1536, "Incorrect model configuration"

image = Image.open(image_path).convert("RGB")
inputs = processor(images=image, return_tensors="pt")

print("Input tensor:", tuple(inputs["pixel_values"].shape))

with torch.inference_mode():
    logits = model(**inputs).logits
    fake_probability = torch.sigmoid(logits.reshape(-1)[0]).item()

print(f"\nRaw logit:        {logits.reshape(-1)[0].item():.6f}")
print(f"Fake probability: {fake_probability * 100:.2f}%")
print(f"Real probability: {(1 - fake_probability) * 100:.2f}%")

if fake_probability >= 0.5:
    print("Prediction: LIKELY AI-GENERATED")
else:
    print("Prediction: LIKELY REAL")