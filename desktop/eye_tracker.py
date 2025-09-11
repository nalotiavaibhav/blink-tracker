"""
Eye Blink Counter with MediaPipe Integration
Based on: https://github.com/wellnessatwork/eye-tracker-share
Adapted for WaW Desktop Application
"""

import json
import queue
import threading
import time
from collections import deque
from datetime import datetime
from typing import Callable, Dict, Optional

import cv2
import mediapipe as mp
import numpy as np

# Initialize MediaPipe Face Mesh and drawing utils
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

# https://github.com/tensorflow/tfjs-models/blob/838611c02f51159afdd77469ce67f0e26b7bbb23/face-landmarks-detection/src/mediapipe-facemesh/keypoints.ts
# for better facial landmarks and improvised tracking
# Eye landmark indices for left and right eyes (from MediaPipe Face Mesh)
LEFT_EYE = [33, 160, 158, 133, 153, 144]
RIGHT_EYE = [362, 385, 387, 263, 373, 380]


def euclidean_dist(pt1, pt2):
    """Calculate Euclidean distance between two points."""
    return np.linalg.norm(np.array(pt1) - np.array(pt2))


def eye_aspect_ratio(eye_landmarks):
    """
    Compute the eye aspect ratio (EAR) for blink detection.
    EAR = (|p2-p6| + |p3-p5|) / (2 * |p1-p4|)
    """
    A = euclidean_dist(eye_landmarks[1], eye_landmarks[5])
    B = euclidean_dist(eye_landmarks[2], eye_landmarks[4])
    C = euclidean_dist(eye_landmarks[0], eye_landmarks[3])
    ear = (A + B) / (2.0 * C)
    return ear


class EyeTracker:
    """
    Eye blink tracking class for WaW Desktop Application.
    Provides real-time blink detection with callback support.
    """

    def __init__(
        self,
        ear_threshold: float = 0.21,
        consecutive_frames: int = 2,
        callback: Optional[Callable[[Dict], None]] = None,
        min_blink_interval_s: float = 0.35,
        open_frames_required: int = 2,
        hysteresis_delta: float = 0.03,
        smooth_window: int = 3,
    ):
        """
        Initialize the Eye Tracker.

        Args:
            ear_threshold: Eye Aspect Ratio threshold for blink detection
            consecutive_frames: Number of consecutive frames needed to confirm a blink
            callback: Optional callback function to receive blink data
        """
        # Thresholds and detection tuning
        self.ear_threshold = ear_threshold  # close threshold
        self.consecutive_frames = (
            consecutive_frames  # frames below close threshold to mark closed
        )
        self.min_blink_interval_s = min_blink_interval_s  # refractory period
        self.open_frames_required = (
            open_frames_required  # frames above open threshold to mark open
        )
        self.hysteresis_delta = hysteresis_delta  # open threshold offset
        self.open_threshold = ear_threshold + hysteresis_delta
        self.smooth_window = max(1, int(smooth_window))
        self.callback = callback

        # Tracking state
        self.blink_count = 0
        self.frame_counter = 0
        self.is_running = False
        self.cap = None
        self.face_mesh = None

        # Smoothing and state
        self._ear_history = deque(maxlen=self.smooth_window)
        self.eye_closed = False
        self.closed_frames = 0
        self.open_frames = 0

        # Threading
        self.thread = None
        self.data_queue = queue.Queue()

        # Session tracking
        self.session_start = None
        self.last_blink_time = None

    def start_tracking(self) -> bool:
        """Start the eye tracking in a separate thread."""
        if self.is_running:
            return False

        try:
            self.cap = cv2.VideoCapture(0)
            if not self.cap.isOpened():
                raise Exception("Cannot access camera")

            self.is_running = True
            self.session_start = datetime.utcnow()
            self.thread = threading.Thread(target=self._tracking_loop, daemon=True)
            self.thread.start()
            return True

        except Exception as e:
            print(f"Failed to start eye tracking: {e}")
            self.stop_tracking()
            return False

    def stop_tracking(self):
        """Stop the eye tracking."""
        self.is_running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        if self.cap:
            self.cap.release()
        cv2.destroyAllWindows()

    def _tracking_loop(self):
        """Main tracking loop running in separate thread."""
        try:
            with mp_face_mesh.FaceMesh(
                max_num_faces=1,
                refine_landmarks=True,
                min_detection_confidence=0.5,
                min_tracking_confidence=0.5,
            ) as face_mesh:
                while self.is_running:
                    ret, frame = self.cap.read()
                    if not ret:
                        break

                    # Process frame
                    blink_data = self._process_frame(frame, face_mesh)

                    # Send data via callback
                    if self.callback and blink_data:
                        self.callback(blink_data)

                    # Optional: Display frame (for debugging)
                    # cv2.imshow('Eye Tracker', frame)
                    # if cv2.waitKey(1) & 0xFF == 27:  # ESC to quit
                    #     break

        except Exception as e:
            print(f"Error in tracking loop: {e}")
        finally:
            self.is_running = False

    def _process_frame(self, frame, face_mesh) -> Optional[Dict]:
        """Process a single frame for blink detection."""
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        results = face_mesh.process(rgb)

        current_time = datetime.utcnow()
        blink_detected = False

        if results.multi_face_landmarks:
            h, w, _ = frame.shape
            for face_landmarks in results.multi_face_landmarks:
                # Get eye landmarks
                left_eye = [
                    (
                        int(face_landmarks.landmark[i].x * w),
                        int(face_landmarks.landmark[i].y * h),
                    )
                    for i in LEFT_EYE
                ]
                right_eye = [
                    (
                        int(face_landmarks.landmark[i].x * w),
                        int(face_landmarks.landmark[i].y * h),
                    )
                    for i in RIGHT_EYE
                ]

                # Calculate EAR and apply simple smoothing
                left_ear = eye_aspect_ratio(left_eye)
                right_ear = eye_aspect_ratio(right_eye)
                ear_raw = (left_ear + right_ear) / 2.0
                self._ear_history.append(ear_raw)
                ear = (
                    float(np.mean(self._ear_history)) if self._ear_history else ear_raw
                )

                # State-machine with hysteresis and refractory period
                if ear < self.ear_threshold:
                    self.closed_frames += 1
                    self.open_frames = 0
                    # Mark eye as closed after enough consecutive closed frames
                    if (
                        not self.eye_closed
                        and self.closed_frames >= self.consecutive_frames
                    ):
                        self.eye_closed = True
                elif ear > self.open_threshold:
                    self.open_frames += 1
                    self.closed_frames = 0
                    # Transition from closed->open counts as one blink
                    if (
                        self.eye_closed
                        and self.open_frames >= self.open_frames_required
                    ):
                        # Refractory period to prevent multiple counts per blink
                        if (
                            self.last_blink_time is None
                            or (current_time - self.last_blink_time).total_seconds()
                            >= self.min_blink_interval_s
                        ):
                            self.blink_count += 1
                            self.last_blink_time = current_time
                            blink_detected = True
                        self.eye_closed = False
                else:
                    # Between thresholds: do not change state, allow counters to persist
                    pass

                # Optional: Draw eye landmarks on frame
                # for pt in left_eye + right_eye:
                #     cv2.circle(frame, pt, 2, (0, 255, 0), -1)
                # cv2.putText(frame, f'Blinks: {self.blink_count}',
                #            (30, 50), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)

        # Return blink data
        return {
            "timestamp": current_time.isoformat(),
            "blink_count": self.blink_count,
            "blink_detected": blink_detected,
            "session_duration": (current_time - self.session_start).total_seconds()
            if self.session_start
            else 0,
            "last_blink_time": self.last_blink_time.isoformat()
            if self.last_blink_time
            else None,
        }

    def get_current_stats(self) -> Dict:
        """Get current tracking statistics."""
        current_time = datetime.utcnow()
        return {
            "blink_count": self.blink_count,
            "is_tracking": self.is_running,
            "session_start": self.session_start.isoformat()
            if self.session_start
            else None,
            "session_duration": (current_time - self.session_start).total_seconds()
            if self.session_start
            else 0,
            "last_blink_time": self.last_blink_time.isoformat()
            if self.last_blink_time
            else None,
        }

    def reset_session(self):
        """Reset the current tracking session."""
        self.blink_count = 0
        self.frame_counter = 0
        self.session_start = datetime.utcnow() if self.is_running else None
        self.last_blink_time = None


def main():
    """Test function for standalone eye tracking."""

    def blink_callback(data):
        if data["blink_detected"]:
            print(f"Blink detected! Total: {data['blink_count']}")
        print(json.dumps(data, indent=2))

    tracker = EyeTracker(callback=blink_callback)

    print("Starting eye tracking... Press Ctrl+C to stop")
    try:
        if tracker.start_tracking():
            # Keep main thread alive
            while tracker.is_running:
                time.sleep(1)
                stats = tracker.get_current_stats()
                print(
                    f"Current stats: {stats['blink_count']} blinks in {stats['session_duration']:.1f}s"
                )
        else:
            print("Failed to start tracking")
    except KeyboardInterrupt:
        print("\nStopping eye tracking...")
    finally:
        tracker.stop_tracking()


if __name__ == "__main__":
    main()
