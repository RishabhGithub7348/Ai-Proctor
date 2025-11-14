import cv2
import numpy as np
import mediapipe as mp
from typing import Dict, Optional, Tuple
import logging
import time

logger = logging.getLogger(__name__)


class EyeGazeTracker:
    """
    Tracks eye gaze direction using MediaPipe Face Mesh
    Detects when user is looking away from the screen
    """

    def __init__(self, threshold_seconds: float = 3.0):
        self.mp_face_mesh = mp.solutions.face_mesh
        self.face_mesh = self.mp_face_mesh.FaceMesh(
            max_num_faces=3,  # Allow tracking up to 3 faces
            refine_landmarks=True,
            min_detection_confidence=0.3,  # Lower threshold for better detection
            min_tracking_confidence=0.3
        )

        # Key facial landmarks for head pose estimation
        # MediaPipe Face Mesh indices (468 landmarks total)
        # Ref: https://github.com/google/mediapipe/blob/master/mediapipe/modules/face_geometry/data/canonical_face_model_uv_visualization.png
        self.POSE_LANDMARKS = [
            1,    # Nose tip
            152,  # Chin
            33,   # Left eye left corner
            263,  # Right eye right corner
            61,   # Left mouth corner
            291   # Right mouth corner
        ]

        # Eye landmarks for iris tracking
        self.LEFT_EYE_LANDMARKS = [362, 385, 387, 263, 373, 380]  # Left eye
        self.RIGHT_EYE_LANDMARKS = [33, 160, 158, 133, 153, 144]  # Right eye

        # 3D model points for head pose estimation
        self.model_points = np.array([
            (0.0, 0.0, 0.0),             # Nose tip
            (0.0, -330.0, -65.0),        # Chin
            (-225.0, 170.0, -135.0),     # Left eye left corner
            (225.0, 170.0, -135.0),      # Right eye right corner
            (-150.0, -150.0, -125.0),    # Left mouth corner
            (150.0, -150.0, -125.0)      # Right mouth corner
        ])

        # Thresholds
        self.threshold_seconds = threshold_seconds
        self.looking_away_start = None
        self.total_looking_away_time = 0

        # Head rotation threshold (based on Proctoring-AI's 48 degree threshold)
        self.HEAD_ROTATION_THRESHOLD = 25.0  # degrees

        # Calibration - store neutral head position
        self.neutral_pitch = 0.0
        self.neutral_yaw = 0.0
        self.neutral_roll = 0.0
        self.is_calibrated = False
        self.calibration_frames = []
        self.calibration_frame_count = 10  # Calibrate using first 10 frames

        logger.info(f"EyeGazeTracker initialized with threshold: {threshold_seconds}s")

    def detect_iris_position(self, landmarks, image, image_shape) -> Optional[Dict]:
        """
        Detect iris position to determine gaze direction (Proctoring-AI method)
        Uses contour detection on eye region to find pupil/iris position

        Args:
            landmarks: MediaPipe face landmarks
            image: Original BGR image
            image_shape: Shape of the image

        Returns:
            Dictionary with gaze information or None
        """
        try:
            h, w = image_shape[:2]
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

            # Get left eye region
            left_eye_points = []
            for idx in self.LEFT_EYE_LANDMARKS:
                if idx < len(landmarks):
                    x = int(landmarks[idx].x * w)
                    y = int(landmarks[idx].y * h)
                    left_eye_points.append((x, y))

            # Get right eye region
            right_eye_points = []
            for idx in self.RIGHT_EYE_LANDMARKS:
                if idx < len(landmarks):
                    x = int(landmarks[idx].x * w)
                    y = int(landmarks[idx].y * h)
                    right_eye_points.append((x, y))

            if len(left_eye_points) < 4 or len(right_eye_points) < 4:
                return None

            # Analyze each eye
            left_gaze = self._analyze_eye_region(gray, np.array(left_eye_points))
            right_gaze = self._analyze_eye_region(gray, np.array(right_eye_points))

            # Combine results from both eyes - they should agree
            if left_gaze is not None and right_gaze is not None:
                # Calculate average ratios for both methods
                avg_x_ratio = (left_gaze['x_ratio'] + right_gaze['x_ratio']) / 2
                avg_y_ratio = (left_gaze['y_ratio'] + right_gaze['y_ratio']) / 2

                # Get direction from each eye
                left_direction = self._determine_gaze_direction(left_gaze)
                right_direction = self._determine_gaze_direction(right_gaze)

                # Both eyes should agree (Proctoring-AI method)
                if left_direction == right_direction and left_direction != 'center':
                    direction = left_direction
                else:
                    # Use averaged ratios if eyes don't agree
                    direction = self._determine_gaze_direction({'x_ratio': avg_x_ratio, 'y_ratio': avg_y_ratio})

                return {
                    'x_ratio': avg_x_ratio,
                    'y_ratio': avg_y_ratio,
                    'horizontal_ratio': (left_gaze['horizontal_ratio'] + right_gaze['horizontal_ratio']) / 2,
                    'vertical_ratio': (left_gaze['vertical_ratio'] + right_gaze['vertical_ratio']) / 2,
                    'direction': direction,
                    'looking_away': direction != 'center'
                }

            return None

        except Exception as e:
            logger.error(f"Iris position detection failed: {e}")
            return None

    def _analyze_eye_region(self, gray_image, eye_points) -> Optional[Dict]:
        """
        Analyze eye region to find iris/pupil position using Proctoring-AI method

        Args:
            gray_image: Grayscale image
            eye_points: Eye landmark points

        Returns:
            Dict with horizontal and vertical ratios
        """
        try:
            # Create mask for eye region
            mask = np.zeros(gray_image.shape, dtype=np.uint8)
            cv2.fillConvexPoly(mask, eye_points, 255)

            # Extract eye region
            eye_region = cv2.bitwise_and(gray_image, gray_image, mask=mask)

            # Get bounding box
            x, y, w, h = cv2.boundingRect(eye_points)
            if w == 0 or h == 0:
                return None

            # Find extreme points for ratio calculation (Proctoring-AI method)
            # eye_points is already a 2D array of (x, y) coordinates
            left_point = tuple(eye_points[eye_points[:, 0].argmin()])
            right_point = tuple(eye_points[eye_points[:, 0].argmax()])
            top_point = tuple(eye_points[eye_points[:, 1].argmin()])
            bottom_point = tuple(eye_points[eye_points[:, 1].argmax()])

            eye_crop = eye_region[y:y+h, x:x+w]

            # Threshold to find dark pupil (adjustable, default 70)
            _, thresh = cv2.threshold(eye_crop, 70, 255, cv2.THRESH_BINARY_INV)

            # AGGRESSIVE PREPROCESSING (Proctoring-AI method)
            # Kernel for morphological operations
            kernel = np.ones((9, 9), np.uint8)

            # Erosion (2 iterations)
            thresh = cv2.erode(thresh, kernel, iterations=2)

            # Dilation (4 iterations)
            thresh = cv2.dilate(thresh, kernel, iterations=4)

            # Median blur for noise reduction
            thresh = cv2.medianBlur(thresh, 3)

            # Bitwise NOT
            thresh = cv2.bitwise_not(thresh)

            # Find contours
            contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            if not contours:
                return None

            # Get largest contour (iris/pupil)
            largest_contour = max(contours, key=cv2.contourArea)

            # Calculate moments to get centroid
            M = cv2.moments(largest_contour)
            if M['m00'] == 0:
                return None

            # Centroid in cropped coordinates
            cx_crop = int(M['m10'] / M['m00'])
            cy_crop = int(M['m01'] / M['m00'])

            # Convert to full image coordinates
            cx = cx_crop + x
            cy = cy_crop + y

            # Calculate ratios using Proctoring-AI formula
            # x_ratio = (left - cx) / (cx - right)
            # y_ratio = (cy - top) / (bottom - cy)

            left_x, left_y = left_point
            right_x, right_y = right_point
            top_x, top_y = top_point
            bottom_x, bottom_y = bottom_point

            # Avoid division by zero
            denominator_x = (cx - right_x)
            denominator_y = (bottom_y - cy)

            if abs(denominator_x) < 1 or abs(denominator_y) < 1:
                return None

            x_ratio = (left_x - cx) / denominator_x
            y_ratio = (cy - top_y) / denominator_y

            return {
                'x_ratio': x_ratio,
                'y_ratio': y_ratio,
                'horizontal_ratio': cx / w if w > 0 else 0.5,  # Keep for backward compatibility
                'vertical_ratio': cy / h if h > 0 else 0.5
            }

        except Exception as e:
            logger.debug(f"Eye region analysis failed: {e}")
            return None

    def _determine_gaze_direction(self, result_dict: Dict) -> str:
        """
        Determine gaze direction using Proctoring-AI exact thresholds

        Args:
            result_dict: Dictionary containing x_ratio and y_ratio from eye analysis

        Returns:
            Direction string: 'left', 'right', 'up', 'center'
        """
        if result_dict is None:
            return 'center'

        x_ratio = result_dict.get('x_ratio', 0)
        y_ratio = result_dict.get('y_ratio', 0)

        # Proctoring-AI exact thresholds
        # x_ratio > 3: Looking left
        # x_ratio < 0.33: Looking right
        # y_ratio < 0.33: Looking up

        if x_ratio > 3:
            return 'left'
        elif x_ratio < 0.33:
            return 'right'
        elif y_ratio < 0.33:
            return 'up'

        return 'center'

    def estimate_head_pose(self, landmarks, image_shape) -> Optional[Tuple[float, float, float]]:
        """
        Estimate head pose using solvePnP (production-proven method)

        Args:
            landmarks: MediaPipe face landmarks
            image_shape: Shape of the image (height, width)

        Returns:
            Tuple of (pitch, yaw, roll) rotation angles in degrees, or None if failed
        """
        h, w = image_shape[:2]

        # Extract 2D image points from landmarks
        image_points = np.array([
            (landmarks[self.POSE_LANDMARKS[0]].x * w, landmarks[self.POSE_LANDMARKS[0]].y * h),  # Nose tip
            (landmarks[self.POSE_LANDMARKS[1]].x * w, landmarks[self.POSE_LANDMARKS[1]].y * h),  # Chin
            (landmarks[self.POSE_LANDMARKS[2]].x * w, landmarks[self.POSE_LANDMARKS[2]].y * h),  # Left eye
            (landmarks[self.POSE_LANDMARKS[3]].x * w, landmarks[self.POSE_LANDMARKS[3]].y * h),  # Right eye
            (landmarks[self.POSE_LANDMARKS[4]].x * w, landmarks[self.POSE_LANDMARKS[4]].y * h),  # Left mouth
            (landmarks[self.POSE_LANDMARKS[5]].x * w, landmarks[self.POSE_LANDMARKS[5]].y * h)   # Right mouth
        ], dtype="double")

        # Camera internals (approximation)
        focal_length = w
        center = (w / 2, h / 2)
        camera_matrix = np.array([
            [focal_length, 0, center[0]],
            [0, focal_length, center[1]],
            [0, 0, 1]
        ], dtype="double")

        # Assume no lens distortion
        dist_coeffs = np.zeros((4, 1))

        try:
            # Solve for pose
            success, rotation_vec, translation_vec = cv2.solvePnP(
                self.model_points,
                image_points,
                camera_matrix,
                dist_coeffs,
                flags=cv2.SOLVEPNP_ITERATIVE
            )

            if not success:
                return None

            # Convert rotation vector to rotation matrix
            rotation_mat, _ = cv2.Rodrigues(rotation_vec)

            # Extract Euler angles
            pose_mat = cv2.hconcat((rotation_mat, translation_vec))
            _, _, _, _, _, _, euler_angles = cv2.decomposeProjectionMatrix(pose_mat)

            pitch = euler_angles[0][0]
            yaw = euler_angles[1][0]
            roll = euler_angles[2][0]

            return pitch, yaw, roll

        except Exception as e:
            logger.error(f"Head pose estimation failed: {e}")
            return None

    def calibrate(self, pitch: float, yaw: float, roll: float):
        """
        Calibrate the neutral head position using initial frames

        Args:
            pitch: Current pitch angle
            yaw: Current yaw angle
            roll: Current roll angle
        """
        if len(self.calibration_frames) < self.calibration_frame_count:
            self.calibration_frames.append((pitch, yaw, roll))
            logger.debug(f"Calibration frame {len(self.calibration_frames)}/{self.calibration_frame_count}")

            if len(self.calibration_frames) == self.calibration_frame_count:
                # Calculate average neutral position
                pitches = [p for p, y, r in self.calibration_frames]
                yaws = [y for p, y, r in self.calibration_frames]
                rolls = [r for p, y, r in self.calibration_frames]

                self.neutral_pitch = np.median(pitches)
                self.neutral_yaw = np.median(yaws)
                self.neutral_roll = np.median(rolls)
                self.is_calibrated = True

                logger.info(f"Calibration complete - Neutral position: "
                          f"Pitch={self.neutral_pitch:.1f}, "
                          f"Yaw={self.neutral_yaw:.1f}, "
                          f"Roll={self.neutral_roll:.1f}")

    def is_looking_away(self, pitch: float, yaw: float, roll: float) -> Tuple[bool, str]:
        """
        Determine if the user is looking away based on head rotation angles
        Uses calibrated neutral position as baseline

        Args:
            pitch: Up/down rotation (degrees)
            yaw: Left/right rotation (degrees)
            roll: Tilt rotation (degrees)

        Returns:
            Tuple of (is_looking_away, direction)
        """
        # Calculate deviation from neutral position
        if self.is_calibrated:
            pitch_diff = pitch - self.neutral_pitch
            yaw_diff = yaw - self.neutral_yaw
        else:
            # If not calibrated yet, use absolute values
            pitch_diff = pitch
            yaw_diff = yaw

        # Check if head is turned significantly
        if abs(yaw_diff) > self.HEAD_ROTATION_THRESHOLD:
            direction = "left" if yaw_diff < 0 else "right"
            return True, direction

        if abs(pitch_diff) > self.HEAD_ROTATION_THRESHOLD:
            direction = "down" if pitch_diff > 0 else "up"
            return True, direction

        return False, "center"

    def track_gaze(self, image: np.ndarray) -> Dict:
        """
        Track eye gaze using head pose estimation (production-proven method)

        Args:
            image: BGR image from OpenCV

        Returns:
            Dictionary with gaze tracking results
        """
        # Convert BGR to RGB
        image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

        # Process the image
        results = self.face_mesh.process(image_rgb)

        if not results.multi_face_landmarks:
            # No face detected
            logger.debug("Eye tracker: No face landmarks detected")
            return {
                'face_detected': False,
                'looking_away': False,
                'gaze_direction': 'unknown',
                'violation': False,
                'duration': 0,
                'pitch': 0,
                'yaw': 0,
                'roll': 0
            }

        # Get the first face
        face_landmarks = results.multi_face_landmarks[0].landmark

        # Method 1: Iris-based eye tracking (Proctoring-AI method - more accurate for eye movement)
        iris_result = self.detect_iris_position(face_landmarks, image, image.shape)

        # Method 2: Head pose estimation (for head turns)
        pose_result = self.estimate_head_pose(face_landmarks, image.shape)

        # Default values
        looking_away = False
        gaze_direction = 'center'
        pitch = yaw = roll = 0

        # Prioritize iris tracking if available (more accurate for subtle eye movements)
        if iris_result is not None:
            looking_away = iris_result['looking_away']
            gaze_direction = iris_result['direction']
            logger.debug(f"Iris tracking - x_ratio: {iris_result['x_ratio']:.2f}, "
                        f"y_ratio: {iris_result['y_ratio']:.2f}, Direction: {gaze_direction}")

        # Fall back to or combine with head pose
        if pose_result is not None:
            pitch, yaw, roll = pose_result

            # Calibrate neutral position using first few frames
            if not self.is_calibrated:
                self.calibrate(pitch, yaw, roll)

            # Check head rotation (for larger head movements)
            head_looking_away, head_direction = self.is_looking_away(pitch, yaw, roll)

            # If iris detection failed or head is significantly turned, use head pose
            if iris_result is None or head_looking_away:
                looking_away = head_looking_away
                gaze_direction = head_direction

        # Track duration of looking away
        current_time = time.time()
        if looking_away:
            if self.looking_away_start is None:
                self.looking_away_start = current_time
            duration = current_time - self.looking_away_start
        else:
            if self.looking_away_start is not None:
                self.total_looking_away_time += current_time - self.looking_away_start
            self.looking_away_start = None
            duration = 0

        # Check if violation threshold is exceeded
        violation = duration > self.threshold_seconds

        # Log for debugging
        logger.debug(f"Head pose - Pitch: {pitch:.1f}, Yaw: {yaw:.1f}, Roll: {roll:.1f} | "
                    f"Looking away: {looking_away} ({gaze_direction}) | Duration: {duration:.1f}s")

        return {
            'face_detected': True,
            'looking_away': looking_away,
            'gaze_direction': gaze_direction,
            'pitch': float(pitch),
            'yaw': float(yaw),
            'roll': float(roll),
            'duration': duration,
            'violation': violation,
            'alert_type': 'eyes_looking_away' if violation else None,
            'total_away_time': self.total_looking_away_time
        }

    def draw_gaze_info(self, image: np.ndarray, gaze_data: Dict) -> np.ndarray:
        """
        Draw gaze tracking information on the image with head pose data
        """
        output = image.copy()

        if not gaze_data['face_detected']:
            cv2.putText(output, "No face detected", (10, 30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
            return output

        # Draw gaze direction
        direction = gaze_data['gaze_direction']
        color = (0, 0, 255) if gaze_data['looking_away'] else (0, 255, 0)

        cv2.putText(output, f"Gaze: {direction}", (10, 30),
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, color, 2)

        # Draw head pose angles
        pitch = gaze_data.get('pitch', 0)
        yaw = gaze_data.get('yaw', 0)
        roll = gaze_data.get('roll', 0)
        cv2.putText(output, f"Pitch: {pitch:.1f} Yaw: {yaw:.1f} Roll: {roll:.1f}",
                   (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        # Draw duration if looking away
        if gaze_data['looking_away']:
            duration = gaze_data['duration']
            cv2.putText(output, f"Looking away: {duration:.1f}s", (10, 90),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # Draw violation warning
        if gaze_data['violation']:
            cv2.putText(output, "ALERT: Eyes off screen!", (10, 120),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        return output

    def reset(self):
        """Reset tracking state and calibration"""
        self.looking_away_start = None
        self.total_looking_away_time = 0
        self.is_calibrated = False
        self.calibration_frames = []
        logger.info("Eye tracker reset - will recalibrate on next session")

    def __del__(self):
        """Cleanup resources"""
        if hasattr(self, 'face_mesh'):
            self.face_mesh.close()
