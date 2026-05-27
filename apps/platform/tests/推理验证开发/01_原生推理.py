from pathlib import Path
from ultralytics import YOLO

model_path = Path(__file__).parent / "train3-20250704-165500-yolo11n-best.pt"
model = YOLO(str(model_path))
model.predict(source="0", show=True)