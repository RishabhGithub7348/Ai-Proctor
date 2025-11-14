import cv2
import numpy as np
from ultralytics import YOLO
from typing import List, Dict, Tuple
import logging
import os

logger = logging.getLogger(__name__)


class ObjectDetector:
    """
    Detects phones and other prohibited objects using YOLO
    """

    def __init__(self, model_path: str = None, confidence_threshold: float = 0.5):
        """
        Initialize YOLO object detector

        Args:
            model_path: Path to YOLO model weights (uses YOLOv8 by default)
            confidence_threshold: Minimum confidence for detection
        """
        self.confidence_threshold = confidence_threshold

        # Use YOLOv8n (nano) for faster inference
        if model_path and os.path.exists(model_path):
            self.model = YOLO(model_path)
        else:
            # Download and use pretrained YOLOv8n model
            self.model = YOLO('yolov8n.pt')

        # Objects to detect (COCO dataset class IDs for YOLOv8/YOLOv3)
        # Following Proctoring-AI's focused approach: ONLY critical violations
        # COCO dataset IDs: https://tech.amikelive.com/node-718/what-object-categories-labels-are-in-coco-dataset/
        self.prohibited_objects = {
            67: 'cell phone',    # Mobile phone - CRITICAL (Proctoring-AI class 67)
            # Note: Person (class 0) is handled separately in face_detector
        }

        # Optional: Additional objects you may want to monitor (not in Proctoring-AI)
        self.optional_objects = {
            63: 'laptop',        # Laptop computer
            73: 'book',          # Books/notes
            66: 'keyboard',      # External keyboard
            64: 'mouse',         # Computer mouse
            62: 'tv',            # TV/monitor (second screen)
        }

        # All objects to monitor (combine both lists)
        self.all_monitored_objects = {**self.prohibited_objects, **self.optional_objects}

        # High priority objects (critical violations - immediate alert)
        self.high_priority = [67]  # Only cell phone (like Proctoring-AI)

        # Medium priority (optional monitoring)
        self.medium_priority = [63, 73, 66, 64, 62]

        logger.info(f"ObjectDetector initialized with confidence threshold: {confidence_threshold}")

    def detect_objects(self, image: np.ndarray) -> List[Dict]:
        """
        Detect objects in the image

        Args:
            image: BGR image from OpenCV

        Returns:
            List of detected objects with details
        """
        # Run inference
        results = self.model(image, conf=self.confidence_threshold, verbose=False)

        detected_objects = []

        # Process results
        for result in results:
            boxes = result.boxes

            for box in boxes:
                class_id = int(box.cls[0])
                confidence = float(box.conf[0])

                # Only track monitored objects (both prohibited and optional)
                if class_id in self.all_monitored_objects:
                    # Get bounding box coordinates
                    x1, y1, x2, y2 = box.xyxy[0].tolist()

                    # Determine priority level
                    if class_id in self.high_priority:
                        priority = 'critical'
                    elif class_id in self.medium_priority:
                        priority = 'high'
                    else:
                        priority = 'medium'

                    detected_objects.append({
                        'class_id': class_id,
                        'class_name': self.all_monitored_objects[class_id],
                        'confidence': confidence,
                        'bbox': {
                            'x1': int(x1),
                            'y1': int(y1),
                            'x2': int(x2),
                            'y2': int(y2),
                            'width': int(x2 - x1),
                            'height': int(y2 - y1)
                        },
                        'is_high_priority': class_id in self.high_priority,
                        'priority': priority
                    })

        return detected_objects

    def check_prohibited_objects(self, image: np.ndarray) -> Dict:
        """
        Check for prohibited objects and return violation status

        Args:
            image: BGR image from OpenCV

        Returns:
            Dictionary with violation status and details
        """
        detected_objects = self.detect_objects(image)

        # Check for violations
        has_phone = any(obj['class_id'] == 67 for obj in detected_objects)
        has_prohibited = len(detected_objects) > 0

        # Get high priority violations
        high_priority_violations = [
            obj for obj in detected_objects if obj['is_high_priority']
        ]

        alert_type = None
        if has_phone:
            alert_type = 'phone_detected'
        elif has_prohibited:
            alert_type = 'prohibited_object_detected'

        return {
            'violation': has_prohibited,
            'has_phone': has_phone,
            'num_objects': len(detected_objects),
            'objects': detected_objects,
            'high_priority_violations': high_priority_violations,
            'alert_type': alert_type
        }

    def draw_detections(self, image: np.ndarray, objects: List[Dict]) -> np.ndarray:
        """
        Draw bounding boxes around detected objects

        Args:
            image: BGR image from OpenCV
            objects: List of detected objects

        Returns:
            Image with drawn detections
        """
        output = image.copy()

        for obj in objects:
            bbox = obj['bbox']
            class_name = obj['class_name']
            confidence = obj['confidence']
            is_high_priority = obj['is_high_priority']

            # Color: Red for high priority, Orange for others
            color = (0, 0, 255) if is_high_priority else (0, 165, 255)

            # Draw rectangle
            cv2.rectangle(
                output,
                (bbox['x1'], bbox['y1']),
                (bbox['x2'], bbox['y2']),
                color,
                2
            )

            # Draw label
            label = f"{class_name}: {confidence:.2f}"
            cv2.putText(
                output,
                label,
                (bbox['x1'], bbox['y1'] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                color,
                2
            )

            # Draw warning for high priority
            if is_high_priority:
                cv2.putText(
                    output,
                    "VIOLATION!",
                    (bbox['x1'], bbox['y2'] + 20),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (0, 0, 255),
                    2
                )

        return output
