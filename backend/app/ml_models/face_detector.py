import cv2
import mediapipe as mp
import numpy as np
from typing import List, Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class FaceDetector:
    """
    Detects faces and facial landmarks using MediaPipe
    """

    def __init__(self):
        self.mp_face_detection = mp.solutions.face_detection
        self.mp_face_mesh = mp.solutions.face_mesh
        self.mp_drawing = mp.solutions.drawing_utils

        # Initialize face detection
        self.face_detection = self.mp_face_detection.FaceDetection(
            model_selection=1,  # 0 for short-range, 1 for full-range
            min_detection_confidence=0.5
        )

        # Initialize face mesh for detailed landmarks
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=3,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

        logger.info("FaceDetector initialized")

    def detect_faces(self, image: np.ndarray) -> Tuple[int, List[Dict]]:
        """
        Detect faces in the image

        Args:
            image: BGR image from OpenCV

        Returns:
            Tuple of (number_of_faces, list of face data)
        """
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process the image
        results = self.face_detection.process(image_rgb)

        faces = []
        num_faces = 0

        if results.detections:
            num_faces = len(results.detections)

            for detection in results.detections:
                # Get bounding box
                bboxC = detection.location_data.relative_bounding_box
                ih, iw, _ = image.shape

                bbox = {
                    'x': int(bboxC.xmin * iw),
                    'y': int(bboxC.ymin * ih),
                    'width': int(bboxC.width * iw),
                    'height': int(bboxC.height * ih)
                }

                faces.append({
                    'bbox': bbox,
                    'confidence': detection.score[0]
                })

        return num_faces, faces

    def get_face_landmarks(self, image: np.ndarray) -> Optional[List]:
        """
        Get detailed face landmarks for eye tracking and head pose

        Args:
            image: BGR image from OpenCV

        Returns:
            List of landmark data or None
        """
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process the image
        results = self.face_mesh.process(image_rgb)

        if results.multi_face_landmarks:
            return results.multi_face_landmarks

        return None

    def check_multiple_faces(self, image: np.ndarray, max_allowed: int = 1) -> Dict:
        """
        Check if there are multiple faces in the frame

        Args:
            image: BGR image from OpenCV
            max_allowed: Maximum number of faces allowed

        Returns:
            Dictionary with violation status and details
        """
        num_faces, faces = self.detect_faces(image)

        violation = num_faces > max_allowed

        return {
            'violation': violation,
            'num_faces': num_faces,
            'max_allowed': max_allowed,
            'faces': faces,
            'alert_type': 'multiple_persons' if violation else None
        }

    def draw_faces(self, image: np.ndarray, faces: List[Dict]) -> np.ndarray:
        """
        Draw bounding boxes around detected faces

        Args:
            image: BGR image from OpenCV
            faces: List of face data

        Returns:
            Image with drawn faces
        """
        output = image.copy()

        for face in faces:
            bbox = face['bbox']
            confidence = face['confidence']

            # Draw rectangle
            cv2.rectangle(
                output,
                (bbox['x'], bbox['y']),
                (bbox['x'] + bbox['width'], bbox['y'] + bbox['height']),
                (0, 255, 0),
                2
            )

            # Draw confidence
            cv2.putText(
                output,
                f"{confidence:.2f}",
                (bbox['x'], bbox['y'] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 255, 0),
                2
            )

        return output

    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'face_detection'):
            self.face_detection.close()
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()
