from ultralytics import YOLO
import cv2
import numpy as np
import torch
import io
from PIL import Image
from transformers import AutoImageProcessor, AutoModel
import asyncio
from datetime import datetime


device = None
processor = None
dino_model = None
yolo_model = None

def init_models():
    global device, processor, dino_model, yolo_model
    
    print("⏳ Загрузка ML-моделей в память...")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Используемый вычислитель: {device}")

    # Загружаем DINOv2
    processor = AutoImageProcessor.from_pretrained('facebook/dinov2-small')
    dino_model = AutoModel.from_pretrained('facebook/dinov2-small').to(device)
    dino_model.eval() # Режим инференса

    # Загружаем YOLOv8 (путь относительно корня проекта)
    yolo_model = YOLO('models/yolov8n-seg.pt')
    
    print("✅ ML-модели успешно загружены!")


async def get_embedding_from_image(image_content: bytes, save_debug=False) -> list[float]:
    return await asyncio.to_thread(_generate_embedding_sync, image_content, save_debug)

# async def get_pet_seg_image_and_type(image_content: bytes) -> tuple[bytes, str]:
    
#     # 1. Конвертируем сырые байты в numpy-массив (изображение OpenCV)
#     nparr = np.frombuffer(image_content, np.uint8)
#     img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
#     if img is None:
#         return None, None
        
#     # 2. Получаем маски (retina_masks=True для точного контура)
#     result = yolo_model(img, retina_masks=True)
    
#     if not result or not result[0].masks:
#         return None, None  # Животное не найдено
        
#     # 3. Извлекаем тензор маски первого найденного объекта
#     mask = result[0].masks.data[0].cpu().numpy()
    
#     # Подгоняем размер строго под оригинальное изображение (Ширина, Высота)
#     mask = cv2.resize(mask, (img.shape[1], img.shape[0]), interpolation=cv2.INTER_NEAREST)
    
#     # 4. Делаем маску строго бинарной (0 и 1) и типа uint8
#     mask_binary = (mask > 0.5).astype(np.uint8)
    
#     # Защита от ошибки OpenCV (-215:Assertion failed): убеждаемся, что маска строго 2D
#     if len(mask_binary.shape) > 2:
#         mask_binary = mask_binary.squeeze()
        
#     # 5. Вырезаем питомца, фон становится черным
#     masked_img = cv2.bitwise_and(img, img, mask=mask_binary)
    
#     # 6. НАХОДИМ ГРАНИЦЫ ПИТОМЦА И ОБРЕЗАЕМ ЛИШНИЙ ЧЕРНЫЙ ФОН
#     # Находим все координаты (y, x), где маска равна 1 (то есть где находится питомец)
#     y_indices, x_indices = np.where(mask_binary == 1)
    
#     if len(y_indices) == 0 or len(x_indices) == 0:
#         return None, None # На случай, если маска оказалась пустой
        
#     # Вычисляем минимальные и максимальные координаты (Bounding Box)
#     y_min, y_max = np.min(y_indices), np.max(y_indices)
#     x_min, x_max = np.min(x_indices), np.max(x_indices)
    
#     # Обрезаем изображение строго по этим координатам
#     cropped_img = masked_img[y_min:y_max+1, x_min:x_max+1]
    
#     # Сохраняем итоговое вырезанное и обрезанное изображение (для отладки)
#     # cv2.imwrite("cropped_pet.png", cropped_img)
    
#     # 7. Кодируем результат в PNG байты
#     _, buffer = cv2.imencode('.png', cropped_img)
#     seg_image_bytes = buffer.tobytes()
    
#     # Определяем тип животного
#     pet_type = result[0].names[result[0].boxes.cls[0].item()]
    
#     return seg_image_bytes, pet_type

def _generate_embedding_sync(image_content: bytes, save_debug_image=False) -> tuple[list[float] | None, str | None]:
    if dino_model is None or yolo_model is None:
        raise RuntimeError("Модели не инициализированы!")

    # 1. Загружаем картинку
    image_pil = Image.open(io.BytesIO(image_content)).convert("RGB")
    # Переводим в формат OpenCV (BGR) для YOLO
    image_cv = cv2.cvtColor(np.array(image_pil), cv2.COLOR_RGB2BGR)
    
    # 2. Прогоняем через YOLO
    results = yolo_model(image_cv, verbose=False)
    result = results[0]
    
    # Классы COCO: 15 - кошка, 16 - собака
    valid_classes = [15, 16] 
    class_dict = {15: "cat", 16: "dog"}
    pet_found = False
    pet_type = None
    
    if result.boxes is not None and result.masks is not None:
        for i, box in enumerate(result.boxes):
            cls = int(box.cls[0].item())
            if cls in valid_classes:
                pet_type = class_dict[cls]
                # Извлекаем маску
                mask = result.masks.data[i].cpu().numpy()
                # Ресайзим маску под размер оригинальной картинки
                mask = cv2.resize(mask, (image_cv.shape[1], image_cv.shape[0]))
                
                # Заливаем всё черным, кроме питомца (где маска > 0.5)
                black_bg = np.zeros_like(image_cv)
                black_bg[mask > 0.5] = image_cv[mask > 0.5]
                
                # Обрезаем картинку по bounding box, чтобы убрать лишний черный фон
                x1, y1, x2, y2 = map(int, box.xyxy[0].tolist())
                cropped_cv = black_bg[y1:y2, x1:x2]
                
                # Возвращаем в PIL Image
                image_pil = Image.fromarray(cv2.cvtColor(cropped_cv, cv2.COLOR_BGR2RGB))
                pet_found = True
                
                # ДЛЯ ТЕСТОВ: Сохраняем то, что увидит DINO
                if save_debug_image:
                    image_pil.save(f"debug/debug_cropped_{pet_type}_{datetime.now().strftime('%Y%m%d_%H%M%S_%')}.jpg")
                
                break # Берем первого найденного питомца
                
    if not pet_found:
        return None, None # Питомец не найден!

    # 3. Прогоняем очищенную картинку через DINOv2
    inputs = processor(images=image_pil, return_tensors="pt").to(device)
    
    with torch.no_grad():
        outputs = dino_model(**inputs)
        
    embedding = outputs.last_hidden_state[:, 0, :]
    embedding = torch.nn.functional.normalize(embedding, p=2, dim=1)
    
    return embedding.squeeze().cpu().tolist(), pet_type