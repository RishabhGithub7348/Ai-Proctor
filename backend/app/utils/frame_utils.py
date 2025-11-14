import cv2
import numpy as np
from typing import Optional, Tuple
from skimage.metrics import structural_similarity as ssim
import logging

logger = logging.getLogger(__name__)


class FrameAnalyzer:
    """
    Utility class for frame analysis including SSIM comparison,
    black screen detection, and other optimizations
    """

    def __init__(self, ssim_threshold: float = 0.95, black_threshold: float = 30):
        """
        Initialize frame analyzer

        Args:
            ssim_threshold: SSIM similarity threshold (0-1). Frames above this are considered duplicates
            black_threshold: Average pixel intensity threshold for black screen detection
        """
        self.ssim_threshold = ssim_threshold
        self.black_threshold = black_threshold
        self.previous_frame = None
        self.frame_count = 0

        logger.info(f"FrameAnalyzer initialized - SSIM threshold: {ssim_threshold}, "
                   f"Black threshold: {black_threshold}")

    def calculate_ssim(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """
        Calculate SSIM (Structural Similarity Index) between two frames

        Args:
            frame1: First BGR image
            frame2: Second BGR image

        Returns:
            SSIM value between 0 and 1 (1 = identical)
        """
        try:
            # Convert to grayscale for faster comparison
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

            # Resize if images are too large (for performance)
            if gray1.shape[0] > 480:
                scale = 480 / gray1.shape[0]
                gray1 = cv2.resize(gray1, None, fx=scale, fy=scale)
                gray2 = cv2.resize(gray2, None, fx=scale, fy=scale)

            # Calculate SSIM
            similarity_index = ssim(gray1, gray2)

            return float(similarity_index)

        except Exception as e:
            logger.error(f"SSIM calculation failed: {e}")
            return 0.0

    def is_duplicate_frame(self, current_frame: np.ndarray) -> bool:
        """
        Check if current frame is a duplicate of the previous frame using SSIM

        Args:
            current_frame: Current BGR image

        Returns:
            True if frame is a duplicate and should be skipped
        """
        self.frame_count += 1

        # First frame is never a duplicate
        if self.previous_frame is None:
            self.previous_frame = current_frame.copy()
            return False

        # Calculate similarity
        similarity = self.calculate_ssim(self.previous_frame, current_frame)

        # Check if frames are too similar (duplicate)
        is_duplicate = similarity > self.ssim_threshold

        if is_duplicate:
            logger.debug(f"Frame {self.frame_count} is duplicate (SSIM: {similarity:.3f})")
        else:
            # Update previous frame only if not duplicate
            self.previous_frame = current_frame.copy()

        return is_duplicate

    def is_black_screen(self, frame: np.ndarray) -> bool:
        """
        Detect if the frame is mostly black (camera covered or off)

        Args:
            frame: BGR image

        Returns:
            True if frame is mostly black
        """
        try:
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

            # Calculate average pixel intensity
            avg_intensity = np.mean(gray)

            is_black = avg_intensity < self.black_threshold

            if is_black:
                logger.debug(f"Black screen detected (avg intensity: {avg_intensity:.1f})")

            return is_black

        except Exception as e:
            logger.error(f"Black screen detection failed: {e}")
            return False

    def calculate_histogram_similarity(self, frame1: np.ndarray, frame2: np.ndarray) -> float:
        """
        Calculate histogram similarity between two frames
        Used for additional validation of face visibility

        Args:
            frame1: First BGR image
            frame2: Second BGR image

        Returns:
            Similarity value between 0 and 1 (1 = identical)
        """
        try:
            # Convert to grayscale
            gray1 = cv2.cvtColor(frame1, cv2.COLOR_BGR2GRAY)
            gray2 = cv2.cvtColor(frame2, cv2.COLOR_BGR2GRAY)

            # Calculate histograms
            hist1 = cv2.calcHist([gray1], [0], None, [256], [0, 256])
            hist2 = cv2.calcHist([gray2], [0], None, [256], [0, 256])

            # Normalize histograms
            hist1 = cv2.normalize(hist1, hist1).flatten()
            hist2 = cv2.normalize(hist2, hist2).flatten()

            # Compare using correlation method
            similarity = cv2.compareHist(hist1, hist2, cv2.HISTCMP_CORREL)

            return float(similarity)

        except Exception as e:
            logger.error(f"Histogram similarity calculation failed: {e}")
            return 0.0

    def should_process_frame(self, frame: np.ndarray, skip_mod: int = 1) -> Tuple[bool, str]:
        """
        Determine if a frame should be processed based on multiple criteria

        Args:
            frame: BGR image
            skip_mod: Process every Nth frame (1 = process all, 3 = process every 3rd)

        Returns:
            Tuple of (should_process, reason)
        """
        # Check black screen
        if self.is_black_screen(frame):
            return False, "black_screen"

        # Check frame skipping
        if skip_mod > 1 and self.frame_count % skip_mod != 0:
            return False, "frame_skipped"

        # Check duplicate
        if self.is_duplicate_frame(frame):
            return False, "duplicate_frame"

        return True, "ok"

    def reset(self):
        """Reset the frame analyzer state"""
        self.previous_frame = None
        self.frame_count = 0
        logger.debug("FrameAnalyzer state reset")
