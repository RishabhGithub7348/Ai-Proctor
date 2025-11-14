import cv2
import numpy as np
from typing import Dict, List, Optional, Any
import logging
from datetime import datetime
import time
import json

from app.ml_models.face_detector import FaceDetector
from app.ml_models.eye_tracker import EyeGazeTracker
from app.ml_models.object_detector import ObjectDetector
from app.ml_models.audio_analyzer import AudioAnalyzer
from app.utils.frame_utils import FrameAnalyzer
from app.services.gemini_verifier import GeminiViolationVerifier
from app.core.config import settings

logger = logging.getLogger(__name__)


def convert_to_json_serializable(obj: Any) -> Any:
    """Convert numpy types to Python native types for JSON serialization"""
    if isinstance(obj, np.bool_):
        return bool(obj)
    elif isinstance(obj, np.integer):
        return int(obj)
    elif isinstance(obj, np.floating):
        return float(obj)
    elif isinstance(obj, np.ndarray):
        return obj.tolist()
    elif isinstance(obj, dict):
        return {key: convert_to_json_serializable(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_to_json_serializable(item) for item in obj]
    else:
        return obj


class ProctoringService:
    """
    Main proctoring service that integrates all ML models
    """

    def __init__(self):
        # Initialize all detectors
        self.face_detector = FaceDetector()
        self.eye_tracker = EyeGazeTracker(
            threshold_seconds=settings.EYE_GAZE_THRESHOLD
        )
        self.object_detector = ObjectDetector(
            confidence_threshold=settings.MODEL_CONFIDENCE_THRESHOLD
        )
        self.audio_analyzer = AudioAnalyzer()

        # Frame analyzer for optimization
        self.frame_analyzer = FrameAnalyzer(
            ssim_threshold=0.95,  # Skip frames with >95% similarity
            black_threshold=30    # Detect black screens
        )

        # Gemini AI verifier for reducing false positives
        self.gemini_verifier = GeminiViolationVerifier()

        # Alert cooldown to prevent spam
        self.alert_cooldown = settings.ALERT_COOLDOWN_SECONDS
        self.last_alert_times = {}

        # Session tracking
        self.session_data = {}

        # Frame processing optimization
        self.frame_skip_mod = 1  # Process all frames (1 = no skipping)

        logger.info("ProctoringService initialized with all detectors, frame optimization, and AI verification")

    def process_frame(self, image: np.ndarray, session_id: str) -> Dict:
        """
        Process a single video frame with all detectors
        Uses frame optimization to skip duplicate/black frames

        Args:
            image: BGR image from OpenCV
            session_id: Unique session identifier

        Returns:
            Dictionary with all detection results and alerts
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'violations': [],
            'alerts': [],
            'face_detection': {},
            'eye_tracking': {},
            'object_detection': {},
            'status': 'ok',
            'frame_processed': True
        }

        try:
            # Check if frame should be processed (optimization)
            should_process, skip_reason = self.frame_analyzer.should_process_frame(
                image,
                skip_mod=self.frame_skip_mod
            )

            if not should_process:
                logger.debug(f"Frame skipped: {skip_reason}")
                results['status'] = 'skipped'
                results['skip_reason'] = skip_reason
                results['frame_processed'] = False
                return convert_to_json_serializable(results)

            # Add black screen violation if detected
            if self.frame_analyzer.is_black_screen(image):
                violation = {
                    'type': 'black_screen',
                    'severity': 'high',
                    'description': 'Camera appears to be covered or off',
                    'timestamp': datetime.now().isoformat(),
                    'data': {'avg_intensity': float(np.mean(cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)))}
                }
                results['violations'].append(violation)
                if self._should_create_alert(session_id, 'black_screen'):
                    results['alerts'].append(self._create_alert(violation))
            # 1. Face Detection - Check for multiple people
            face_result = self.face_detector.check_multiple_faces(
                image,
                max_allowed=settings.MAX_FACES_ALLOWED
            )
            results['face_detection'] = face_result

            if face_result['violation']:
                # Only verify with AI if we're about to create an alert
                should_alert = self._should_create_alert(session_id, 'multiple_persons')

                violation = {
                    'type': 'multiple_persons',
                    'severity': 'high',
                    'description': f"Detected {face_result['num_faces']} persons",
                    'timestamp': datetime.now().isoformat(),
                    'data': face_result
                }

                # AI Verification - ONLY when creating alert
                if should_alert and settings.ENABLE_AI_VERIFICATION:
                    logger.debug(f"Verifying multiple_persons violation with Gemini AI...")
                    ai_verification = self.gemini_verifier.verify_multiple_persons_violation(image, face_result)
                    violation['ai_verified'] = ai_verification['verified']
                    violation['ai_confidence'] = ai_verification['confidence']
                    violation['ai_reasoning'] = ai_verification['reasoning']

                    if ai_verification['verified'] and ai_verification['confidence'] >= settings.AI_VERIFICATION_CONFIDENCE_THRESHOLD:
                        results['violations'].append(violation)
                        results['alerts'].append(self._create_alert(violation))
                        logger.info(f"✅ AI APPROVED multiple_persons violation - confidence: {ai_verification['confidence']:.2f}, reason: {ai_verification['reasoning']} - ALERT CREATED")
                    else:
                        logger.info(f"❌ AI REJECTED multiple_persons violation - confidence: {ai_verification['confidence']:.2f}, reason: {ai_verification['reasoning']}")
                elif should_alert:
                    results['violations'].append(violation)
                    results['alerts'].append(self._create_alert(violation))
                else:
                    results['violations'].append(violation)

            # 2. Eye Gaze Tracking - Track even with multiple faces
            if face_result['num_faces'] >= 1:
                gaze_result = self.eye_tracker.track_gaze(image)
                results['eye_tracking'] = gaze_result

                # Log gaze status for debugging
                logger.debug(f"Gaze: {gaze_result.get('gaze_direction')} | Looking away: {gaze_result.get('looking_away')} | Duration: {gaze_result.get('duration', 0):.1f}s")

                if gaze_result['violation']:
                    # Only verify with AI if we're about to create an alert (not in cooldown)
                    should_alert = self._should_create_alert(session_id, 'eyes_looking_away')

                    violation = {
                        'type': 'eyes_looking_away',
                        'severity': 'medium',
                        'description': f"Eyes looking {gaze_result['gaze_direction']} for {gaze_result['duration']:.1f}s",
                        'timestamp': datetime.now().isoformat(),
                        'data': gaze_result
                    }

                    # AI Verification - ONLY when creating alert (saves API calls & latency)
                    if should_alert and settings.ENABLE_AI_VERIFICATION:
                        logger.debug(f"Verifying eye_tracking violation with Gemini AI...")
                        ai_verification = self.gemini_verifier.verify_eye_tracking_violation(image, gaze_result)
                        violation['ai_verified'] = ai_verification['verified']
                        violation['ai_confidence'] = ai_verification['confidence']
                        violation['ai_reasoning'] = ai_verification['reasoning']

                        # Only create alert if AI confirms it's genuine
                        if ai_verification['verified'] and ai_verification['confidence'] >= settings.AI_VERIFICATION_CONFIDENCE_THRESHOLD:
                            results['violations'].append(violation)
                            results['alerts'].append(self._create_alert(violation))
                            logger.info(f"✅ AI APPROVED eye_tracking violation - confidence: {ai_verification['confidence']:.2f}, reason: {ai_verification['reasoning']} - ALERT CREATED")
                        else:
                            logger.info(f"❌ AI REJECTED eye_tracking violation - confidence: {ai_verification['confidence']:.2f}, reason: {ai_verification['reasoning']}")
                    elif should_alert:
                        # No AI verification, create alert immediately
                        results['violations'].append(violation)
                        results['alerts'].append(self._create_alert(violation))
                    else:
                        # In cooldown, add violation but no alert
                        results['violations'].append(violation)

            # 3. Object Detection - Check for phones and prohibited items
            object_result = self.object_detector.check_prohibited_objects(image)
            results['object_detection'] = object_result

            if object_result['violation']:
                # Only verify with AI if we're about to create an alert
                should_alert = self._should_create_alert(session_id, 'prohibited_object')

                severity = 'critical' if object_result['has_phone'] else 'high'
                objects_list = [obj['class_name'] for obj in object_result['objects']]

                violation = {
                    'type': 'prohibited_object',
                    'severity': severity,
                    'description': f"Detected: {', '.join(objects_list)}",
                    'timestamp': datetime.now().isoformat(),
                    'data': object_result
                }

                # AI Verification - ONLY when creating alert
                if should_alert and settings.ENABLE_AI_VERIFICATION:
                    logger.debug(f"Verifying object_detection violation with Gemini AI...")
                    ai_verification = self.gemini_verifier.verify_object_detection_violation(image, object_result)
                    violation['ai_verified'] = ai_verification['verified']
                    violation['ai_confidence'] = ai_verification['confidence']
                    violation['ai_reasoning'] = ai_verification['reasoning']

                    if ai_verification['verified'] and ai_verification['confidence'] >= settings.AI_VERIFICATION_CONFIDENCE_THRESHOLD:
                        results['violations'].append(violation)
                        results['alerts'].append(self._create_alert(violation))
                        logger.info(f"✅ AI APPROVED object_detection violation - confidence: {ai_verification['confidence']:.2f}, reason: {ai_verification['reasoning']} - ALERT CREATED")
                    else:
                        logger.info(f"❌ AI REJECTED object_detection violation - confidence: {ai_verification['confidence']:.2f}, reason: {ai_verification['reasoning']}")
                elif should_alert:
                    results['violations'].append(violation)
                    results['alerts'].append(self._create_alert(violation))
                else:
                    results['violations'].append(violation)

            # Update status
            if results['violations']:
                results['status'] = 'violations_detected'

        except Exception as e:
            logger.error(f"Error processing frame: {str(e)}")
            results['status'] = 'error'
            results['error'] = str(e)

        # Convert all numpy types to JSON serializable types
        return convert_to_json_serializable(results)

    def process_audio(self, audio_data: np.ndarray, session_id: str) -> Dict:
        """
        Process audio chunk

        Args:
            audio_data: Audio data as numpy array
            session_id: Unique session identifier

        Returns:
            Dictionary with audio analysis results
        """
        results = {
            'timestamp': datetime.now().isoformat(),
            'session_id': session_id,
            'violations': [],
            'alerts': [],
            'audio_analysis': {},
            'status': 'ok'
        }

        try:
            # Analyze audio
            audio_result = self.audio_analyzer.analyze_audio(audio_data)
            results['audio_analysis'] = audio_result

            if audio_result['violation']:
                violation = {
                    'type': 'audio_anomaly',
                    'severity': 'medium',
                    'description': f"Audio anomaly: {audio_result['anomaly_type']}",
                    'timestamp': datetime.now().isoformat(),
                    'data': audio_result
                }
                results['violations'].append(violation)

                if self._should_create_alert(session_id, 'audio_anomaly'):
                    results['alerts'].append(self._create_alert(violation))

            if results['violations']:
                results['status'] = 'violations_detected'

        except Exception as e:
            logger.error(f"Error processing audio: {str(e)}")
            results['status'] = 'error'
            results['error'] = str(e)

        return results

    def _should_create_alert(self, session_id: str, alert_type: str) -> bool:
        """
        Check if an alert should be created based on cooldown

        Args:
            session_id: Session identifier
            alert_type: Type of alert

        Returns:
            True if alert should be created
        """
        key = f"{session_id}_{alert_type}"
        current_time = time.time()

        if key not in self.last_alert_times:
            self.last_alert_times[key] = current_time
            return True

        time_since_last = current_time - self.last_alert_times[key]

        if time_since_last >= self.alert_cooldown:
            self.last_alert_times[key] = current_time
            return True

        return False

    def _create_alert(self, violation: Dict) -> Dict:
        """
        Create an alert from a violation

        Args:
            violation: Violation data

        Returns:
            Alert dictionary
        """
        return {
            'alert_id': f"{violation['type']}_{int(time.time() * 1000)}",
            'type': violation['type'],
            'severity': violation['severity'],
            'message': violation['description'],
            'timestamp': violation['timestamp'],
            'requires_attention': violation['severity'] in ['high', 'critical']
        }

    def start_session(self, session_id: str) -> Dict:
        """
        Start a new proctoring session

        Args:
            session_id: Unique session identifier

        Returns:
            Session info
        """
        self.session_data[session_id] = {
            'start_time': datetime.now().isoformat(),
            'status': 'active',
            'total_violations': 0,
            'total_alerts': 0,
            'frames_processed': 0,
            'frames_skipped': 0
        }

        # Reset trackers
        self.eye_tracker.reset()
        self.audio_analyzer.reset()
        self.frame_analyzer.reset()

        logger.info(f"Started proctoring session: {session_id}")

        return self.session_data[session_id]

    def end_session(self, session_id: str) -> Dict:
        """
        End a proctoring session

        Args:
            session_id: Unique session identifier

        Returns:
            Session summary
        """
        if session_id in self.session_data:
            self.session_data[session_id]['end_time'] = datetime.now().isoformat()
            self.session_data[session_id]['status'] = 'ended'

            logger.info(f"Ended proctoring session: {session_id}")

            return self.session_data[session_id]

        return {'error': 'Session not found'}

    def get_session_summary(self, session_id: str) -> Dict:
        """
        Get session summary

        Args:
            session_id: Unique session identifier

        Returns:
            Session summary with statistics
        """
        if session_id in self.session_data:
            return self.session_data[session_id]

        return {'error': 'Session not found'}
