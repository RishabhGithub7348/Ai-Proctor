import google.generativeai as genai
import cv2
import numpy as np
from typing import Dict, Optional, List
import logging
import base64
from PIL import Image
import io

from app.core.config import settings

logger = logging.getLogger(__name__)


class GeminiViolationVerifier:
    """
    Uses Google Gemini (multimodal AI) to verify if detected violations are genuine

    How it works:
    1. Takes a screenshot (image) when a violation is about to trigger an alert
    2. Sends image + violation context to Gemini for visual analysis
    3. Gemini analyzes the actual scene and returns verdict + confidence
    4. Only genuine violations (70%+ confidence) are reported

    This dramatically reduces false positives by having AI verify what it "sees"
    """

    def __init__(self):
        """Initialize Gemini API"""
        if settings.GEMINI_API_KEY:
            genai.configure(api_key=settings.GEMINI_API_KEY)
            self.model = genai.GenerativeModel(settings.GEMINI_MODEL)
            self.enabled = settings.ENABLE_AI_VERIFICATION
            logger.info(f"GeminiViolationVerifier initialized with model: {settings.GEMINI_MODEL}")
        else:
            self.enabled = False
            logger.warning("Gemini API key not set. AI verification disabled.")

    def verify_eye_tracking_violation(self, image: np.ndarray, violation_data: Dict) -> Dict:
        """
        Verify if eye tracking violation is genuine

        Args:
            image: Screenshot from webcam (BGR format)
            violation_data: Data from eye tracker (direction, duration, etc.)

        Returns:
            Dict with verification results
        """
        if not self.enabled:
            return {
                'verified': True,  # Pass through if disabled
                'confidence': 1.0,
                'reasoning': 'AI verification disabled',
                'ai_analysis': None
            }

        try:
            # Convert to PIL Image
            pil_image = self._convert_to_pil(image)

            # Create prompt
            direction = violation_data.get('gaze_direction', 'unknown')
            duration = violation_data.get('duration', 0)

            prompt = f"""Analyze this interview screenshot carefully for eye tracking behavior.

**CONTEXT:**
- Detection Type: EYES LOOKING AWAY
- Direction Detected: {direction}
- Duration: {duration:.1f} seconds

**YOUR TASK:**
Verify if this is a genuine violation that should trigger an alert.

**ANALYSIS CHECKLIST:**
1. **Face Visibility**: Is there a clear, well-lit face visible?
2. **Eye Direction**: Are the person's eyes actually looking {direction} (not at screen)?
3. **False Positive Check**: Could this be:
   - Natural thinking/concentration (brief glance away)
   - Reading a question on screen (eyes moving naturally)
   - Blinking or adjusting posture
   - Poor lighting causing detection error
   - Glare or reflection on glasses
4. **Head Position**: Is their head also turned {direction}, or just eyes?
5. **Duration Context**: {duration:.1f} seconds is {"very brief (likely normal)" if duration < 3 else "moderate (could be suspicious)" if duration < 5 else "prolonged (suspicious)"}
6. **Body Language**: Do they appear to be reading from notes or another screen?

**IMPORTANT CONSIDERATIONS:**
- Brief glances away (< 2-3 seconds) during thinking are NORMAL interview behavior
- Only flag if it appears they're reading from notes/another screen/getting help
- Confidence should be HIGH (>0.8) only if you're very certain it's cheating

**RESPOND IN VALID JSON:**
{{
    "violation_confirmed": true/false,
    "confidence": 0.0-1.0,
    "actual_behavior": "what they're actually doing",
    "explanation": "detailed reasoning for your decision",
    "severity": "low/medium/high",
    "recommended_action": "monitor/warn/flag"
}}"""

            # Get Gemini response
            response = self.model.generate_content([prompt, pil_image])

            # Parse response
            analysis = self._parse_gemini_response(response.text)

            return {
                'verified': analysis.get('violation_confirmed', analysis.get('is_genuine_violation', True)),
                'confidence': analysis.get('confidence', 0.5),
                'reasoning': analysis.get('explanation', analysis.get('reasoning', 'AI analysis completed')),
                'actual_behavior': analysis.get('actual_behavior', 'unknown'),
                'severity': analysis.get('severity', 'medium'),
                'recommended_action': analysis.get('recommended_action', 'monitor'),
                'ai_analysis': analysis
            }

        except Exception as e:
            logger.error(f"Gemini verification failed: {e}")
            return {
                'verified': True,  # Pass through on error
                'confidence': 1.0,
                'reasoning': f'Verification error: {str(e)}',
                'ai_analysis': None
            }

    def verify_multiple_persons_violation(self, image: np.ndarray, violation_data: Dict) -> Dict:
        """
        Verify if multiple persons detection is genuine

        Args:
            image: Screenshot from webcam
            violation_data: Data from face detector

        Returns:
            Dict with verification results
        """
        if not self.enabled:
            return {'verified': True, 'confidence': 1.0, 'reasoning': 'AI verification disabled'}

        try:
            pil_image = self._convert_to_pil(image)
            num_faces = violation_data.get('num_faces', 0)

            prompt = f"""Analyze this interview screenshot carefully for multiple person detection.

**CONTEXT:**
- Detection Type: MULTIPLE PERSONS DETECTED
- Number of Faces Detected: {num_faces} faces

**YOUR TASK:**
Verify if there are genuinely multiple real people present (which is a violation).

**ANALYSIS CHECKLIST:**
1. **Count Real People**: How many distinct, real human beings are actually visible?
2. **False Positive Detection**: Check for common false positives:
   - Posters, artwork, or photos on walls
   - Pictures/photos on desk or shelves
   - Face on computer screen or monitor
   - Mirror reflections
   - Pet faces (dogs/cats sometimes detected as faces)
   - Action figures, dolls, or mannequins
   - Magazine covers or book covers with faces
3. **Face Authenticity**: Are all detected faces:
   - Real 3D human faces (not flat/printed)?
   - Actually present in the room (not on screens)?
   - Belonging to different people (not reflections)?
4. **Violation Severity**: If multiple real people:
   - Are they actively helping the candidate?
   - Just passing by in background?
   - Sitting together (high severity)?
5. **Camera Position**: Could the detection be from:
   - Window reflection?
   - Camera angle capturing someone in another room?

**IMPORTANT CONSIDERATIONS:**
- Only flag as violation if there are genuinely 2+ real people in the interview space
- Posters/photos/screens are NOT violations (very common false positives)
- Be very certain before confirming - false positives here are damaging

**RESPOND IN VALID JSON:**
{{
    "violation_confirmed": true/false,
    "confidence": 0.0-1.0,
    "actual_person_count": number,
    "explanation": "detailed reasoning with what you see",
    "false_positive_causes": ["list", "of", "items"],
    "severity": "low/medium/high",
    "recommended_action": "monitor/warn/flag"
}}"""

            response = self.model.generate_content([prompt, pil_image])
            analysis = self._parse_gemini_response(response.text)

            return {
                'verified': analysis.get('violation_confirmed', analysis.get('is_genuine_violation', True)),
                'confidence': analysis.get('confidence', 0.5),
                'reasoning': analysis.get('explanation', analysis.get('reasoning', 'AI analysis completed')),
                'actual_person_count': analysis.get('actual_person_count', num_faces),
                'false_positive_causes': analysis.get('false_positive_causes', []),
                'severity': analysis.get('severity', 'high'),
                'recommended_action': analysis.get('recommended_action', 'flag'),
                'ai_analysis': analysis
            }

        except Exception as e:
            logger.error(f"Gemini verification failed: {e}")
            return {'verified': True, 'confidence': 1.0, 'reasoning': f'Error: {str(e)}', 'severity': 'high'}

    def verify_object_detection_violation(self, image: np.ndarray, violation_data: Dict) -> Dict:
        """
        Verify if prohibited object detection is genuine

        Args:
            image: Screenshot from webcam
            violation_data: Data from object detector

        Returns:
            Dict with verification results
        """
        if not self.enabled:
            return {'verified': True, 'confidence': 1.0, 'reasoning': 'AI verification disabled'}

        try:
            pil_image = self._convert_to_pil(image)
            objects = violation_data.get('objects', [])
            object_names = [obj.get('class_name', 'unknown') for obj in objects]
            object_list = ', '.join(object_names)

            prompt = f"""Analyze this interview screenshot carefully for prohibited objects.

**CONTEXT:**
- Detection Type: PROHIBITED OBJECTS
- Objects Detected by System: {object_list}

**YOUR TASK:**
Verify if the detected objects are genuine violations that warrant an alert.

**ANALYSIS CHECKLIST:**
1. **Object Identification**: For each detected object:
   - Is it actually visible in the image?
   - Can you clearly identify what it is?
   - Where is it located (hands, desk, background)?

2. **Common False Positives - CHECK THESE FIRST:**
   - **Phone** vs: TV remote, calculator, small rectangular items, glasses case, wallet
   - **Laptop** vs: Monitor, tablet stand, closed laptop (not being used), picture frame
   - **Book** vs: Notebook, folder, closed planner, mousepad, tablet in case
   - **Background items**: Objects on shelves, wall decorations, items far from candidate

3. **Usage Context**:
   - Is the candidate actively holding/using the object?
   - Or is it just sitting on desk/background (not being used)?
   - Could it be part of normal desk setup (keyboard, mouse, monitor)?

4. **Severity Assessment**:
   - **CRITICAL**: Cell phone in hands, open book/notes being read, second laptop/screen in use
   - **HIGH**: Prohibited items on desk within reach, visible but not currently used
   - **LOW**: Items in far background, clearly not accessible, ambiguous objects

5. **Confidence Level**:
   - HIGH (>0.8): Clearly see prohibited item being actively used
   - MEDIUM (0.5-0.8): See prohibited item present but usage unclear
   - LOW (<0.5): Ambiguous object, likely false positive

**IMPORTANT CONSIDERATIONS:**
- Only flag if you're confident it's a REAL prohibited item
- Background objects that aren't being used are generally OK
- Closed books/laptops far from reach are low priority
- Active use (holding phone, reading notes) is critical violation

**RESPOND IN VALID JSON:**
{{
    "violation_confirmed": true/false,
    "confidence": 0.0-1.0,
    "actual_objects_seen": [{{"name": "what_you_see", "is_prohibited": true/false, "being_used": true/false}}],
    "explanation": "detailed reasoning for your decision",
    "false_positive_likelihood": 0.0-1.0,
    "severity": "low/medium/high/critical",
    "recommended_action": "ignore/monitor/warn/flag"
}}"""

            response = self.model.generate_content([prompt, pil_image])
            analysis = self._parse_gemini_response(response.text)

            return {
                'verified': analysis.get('violation_confirmed', analysis.get('is_genuine_violation', True)),
                'confidence': analysis.get('confidence', 0.5),
                'reasoning': analysis.get('explanation', analysis.get('reasoning', 'AI analysis completed')),
                'actual_objects_seen': analysis.get('actual_objects_seen', analysis.get('verified_objects', [])),
                'false_positive_likelihood': analysis.get('false_positive_likelihood', 0.0),
                'severity': analysis.get('severity', 'high'),
                'recommended_action': analysis.get('recommended_action', 'flag'),
                'ai_analysis': analysis
            }

        except Exception as e:
            logger.error(f"Gemini verification failed: {e}")
            return {'verified': True, 'confidence': 1.0, 'reasoning': f'Error: {str(e)}', 'severity': 'high'}

    def _convert_to_pil(self, image: np.ndarray) -> Image.Image:
        """Convert OpenCV BGR image to PIL RGB Image"""
        # Convert BGR to RGB
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        return Image.fromarray(rgb_image)

    def _parse_gemini_response(self, response_text: str) -> Dict:
        """
        Parse Gemini's JSON response

        Args:
            response_text: Raw response from Gemini

        Returns:
            Parsed dictionary
        """
        try:
            # Remove markdown code blocks if present
            cleaned_text = response_text.strip()
            if cleaned_text.startswith('```json'):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.startswith('```'):
                cleaned_text = cleaned_text[3:]
            if cleaned_text.endswith('```'):
                cleaned_text = cleaned_text[:-3]

            cleaned_text = cleaned_text.strip()

            # Parse JSON
            import json
            return json.loads(cleaned_text)

        except Exception as e:
            logger.error(f"Failed to parse Gemini response: {e}")
            logger.debug(f"Raw response: {response_text}")

            # Return safe default
            return {
                'is_genuine_violation': True,  # When in doubt, flag it
                'confidence': 0.5,
                'reasoning': 'Failed to parse AI response',
                'raw_response': response_text
            }
