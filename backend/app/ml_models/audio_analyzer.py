import numpy as np
import logging
from typing import Dict, Optional
from collections import deque
import time

logger = logging.getLogger(__name__)


class AudioAnalyzer:
    """
    Analyzes audio for multiple speakers and anomalies
    Note: This is a simplified version. For production, use pyannote.audio
    """

    def __init__(self, sample_rate: int = 16000, window_size: int = 1024):
        """
        Initialize audio analyzer

        Args:
            sample_rate: Audio sample rate in Hz
            window_size: Size of analysis window
        """
        self.sample_rate = sample_rate
        self.window_size = window_size

        # Energy thresholds
        self.speech_threshold = 0.02  # RMS threshold for speech detection
        self.noise_threshold = 0.05   # High energy threshold

        # Track audio patterns
        self.audio_history = deque(maxlen=50)  # Store last 50 frames
        self.baseline_energy = None
        self.anomaly_count = 0
        self.last_anomaly_time = None

        logger.info("AudioAnalyzer initialized")

    def calculate_rms_energy(self, audio_data: np.ndarray) -> float:
        """
        Calculate RMS (Root Mean Square) energy of audio signal
        """
        return np.sqrt(np.mean(audio_data ** 2))

    def calculate_zero_crossing_rate(self, audio_data: np.ndarray) -> float:
        """
        Calculate zero crossing rate (useful for voice activity detection)
        """
        zero_crossings = np.sum(np.abs(np.diff(np.sign(audio_data)))) / 2
        return zero_crossings / len(audio_data)

    def detect_speech(self, audio_data: np.ndarray) -> bool:
        """
        Simple speech detection based on energy
        """
        energy = self.calculate_rms_energy(audio_data)
        return energy > self.speech_threshold

    def analyze_audio(self, audio_data: np.ndarray) -> Dict:
        """
        Analyze audio chunk for anomalies

        Args:
            audio_data: Audio data as numpy array (normalized -1 to 1)

        Returns:
            Dictionary with analysis results
        """
        # Calculate audio features
        energy = self.calculate_rms_energy(audio_data)
        zcr = self.calculate_zero_crossing_rate(audio_data)
        has_speech = self.detect_speech(audio_data)

        # Initialize baseline if needed
        if self.baseline_energy is None and has_speech:
            self.baseline_energy = energy

        # Store in history
        self.audio_history.append({
            'energy': energy,
            'zcr': zcr,
            'has_speech': has_speech,
            'timestamp': time.time()
        })

        # Detect anomalies
        anomaly_detected = False
        anomaly_type = None

        # High energy spike (could indicate multiple speakers or background noise)
        if self.baseline_energy and energy > self.baseline_energy * 2.5:
            anomaly_detected = True
            anomaly_type = 'high_energy_spike'
            self.anomaly_count += 1

        # Sudden energy change
        if len(self.audio_history) > 1:
            prev_energy = self.audio_history[-2]['energy']
            energy_change = abs(energy - prev_energy)

            if energy_change > 0.1 and has_speech:
                anomaly_detected = True
                anomaly_type = 'sudden_change'

        # Track anomaly timing
        if anomaly_detected:
            current_time = time.time()
            if self.last_anomaly_time:
                time_since_last = current_time - self.last_anomaly_time
            else:
                time_since_last = 0
            self.last_anomaly_time = current_time
        else:
            time_since_last = 0

        # Determine if this is a violation (multiple anomalies in short time)
        violation = self.anomaly_count > 3 and anomaly_detected

        return {
            'energy': float(energy),
            'zero_crossing_rate': float(zcr),
            'has_speech': has_speech,
            'anomaly_detected': anomaly_detected,
            'anomaly_type': anomaly_type,
            'anomaly_count': self.anomaly_count,
            'violation': violation,
            'alert_type': 'multiple_voices_detected' if violation else None,
            'baseline_energy': self.baseline_energy
        }

    def detect_multiple_speakers_simple(self, audio_data: np.ndarray) -> Dict:
        """
        Simplified multiple speaker detection
        For production, use pyannote.audio speaker diarization
        """
        # Analyze audio
        analysis = self.analyze_audio(audio_data)

        # Very basic heuristic: rapid energy changes could indicate speaker changes
        if len(self.audio_history) >= 10:
            recent_energies = [frame['energy'] for frame in list(self.audio_history)[-10:]]
            energy_variance = np.var(recent_energies)

            # High variance could indicate multiple speakers
            if energy_variance > 0.01:
                analysis['possible_multiple_speakers'] = True
                analysis['speaker_confidence'] = min(energy_variance * 100, 1.0)
            else:
                analysis['possible_multiple_speakers'] = False
                analysis['speaker_confidence'] = 0.0

        return analysis

    def reset(self):
        """Reset analyzer state"""
        self.audio_history.clear()
        self.baseline_energy = None
        self.anomaly_count = 0
        self.last_anomaly_time = None


# Placeholder for advanced audio analysis
class AdvancedAudioAnalyzer:
    """
    Advanced audio analyzer using pyannote.audio for speaker diarization
    This would be implemented in production for accurate multiple speaker detection
    """

    def __init__(self):
        """
        Initialize with pyannote.audio
        Requires: pip install pyannote.audio
        And Hugging Face authentication token
        """
        logger.info("AdvancedAudioAnalyzer would use pyannote.audio")
        # from pyannote.audio import Pipeline
        # self.pipeline = Pipeline.from_pretrained("pyannote/speaker-diarization")
        pass

    def analyze_audio_segment(self, audio_file_path: str) -> Dict:
        """
        Perform speaker diarization on audio segment

        Returns:
            Number of unique speakers and timeline
        """
        # diarization = self.pipeline(audio_file_path)
        # num_speakers = len(diarization.labels())
        # return {'num_speakers': num_speakers, 'timeline': diarization}
        pass
