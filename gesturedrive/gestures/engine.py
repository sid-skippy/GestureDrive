import math


class GestureEngine:
    """
    Converts raw MediaPipe hand-landmark results into game control values
    (steering, throttle, brake, handbrake, gear up/down).
    """

    # Steering scale applied on top of sensitivity
    _STEER_SCALE = 1.5

    def __init__(self, config: dict, calib: dict) -> None:
        self.update_config(config)
        self.update_calib(calib)

    # -- config / calibration hot-reload ---------------------------------------

    def update_config(self, config: dict) -> None:
        self.steer_dead_zone  = config.get("dead_zone",            0.25)
        self.steer_sens       = config.get("steering_sensitivity", 1.0)
        self.throttle_sens    = config.get("throttle_sensitivity", 1.0)
        self.smooth           = config.get("smoothing",            0.2)
        self.pinky_threshold  = config.get("pinky_threshold",      0.12)
        self.index_threshold  = config.get("index_threshold",      0.13)

    def update_calib(self, calib: dict) -> None:
        self.thumb_y_scale   = calib.get("THUMB_Y_SCALE",   0.12)
        self.brake_threshold = calib.get("BRAKE_THRESHOLD", 0.08)

    # -- raw gesture extractors ------------------------------------------------

    def is_right_index_out(self, lm) -> bool:
        """True when the right index finger is extended (gear up gesture)."""
        dx = lm[5].x - lm[8].x
        dy = lm[5].y - lm[8].y
        return math.hypot(dx, dy) > self.index_threshold

    def is_right_pinky_out(self, lm) -> bool:
        """True when the right little finger is extended (gear down gesture)."""
        dx = lm[17].x - lm[20].x
        dy = lm[17].y - lm[20].y
        return math.hypot(dx, dy) > self.pinky_threshold

    def is_left_hand_open(self, lm) -> bool:
        """True when at least three fingers on the left hand are raised (handbrake)."""
        open_fingers = sum([
            lm[8].y  < lm[6].y,
            lm[12].y < lm[10].y,
            lm[16].y < lm[14].y,
            lm[20].y < lm[18].y,
        ])
        return open_fingers >= 3

    def get_thumb_y_level(self, lm) -> float:
        """
        Return throttle level [0, 1] based on right thumb elevation.
        Returns 0 when the thumb is near the index finger (pinch position).
        """
        dx = lm[4].x - lm[8].x
        dy = lm[4].y - lm[8].y
        if math.hypot(dx, dy) < 0.06 and lm[4].y <= lm[8].y + 0.02:
            return 0.0

        rise = lm[2].y - lm[4].y
        return max(0.0, min(1.0, (rise / self.thumb_y_scale) * self.throttle_sens))

    def get_hand_tilt_level(self, lm) -> float:
        """
        Return steering level [-1, 1] based on left fist tilt.
        Positive = right, negative = left.
        """
        index = lm[5]
        pinky = lm[17]
        dx    = pinky.x - index.x

        if abs(dx) < 0.01:
            return 0.0

        tilt = (pinky.y - index.y) / dx
        return max(-1.0, min(1.0, tilt * self._STEER_SCALE * self.steer_sens))

    # -- full-frame processing -------------------------------------------------

    def process(
        self,
        result,
        smooth_steering: float,
        smooth_throttle: float,
        smooth_brake: float,
    ) -> dict:
        """
        Given a MediaPipe result and the previous smoothed values, return a
        dict with all current control values ready to send to the gamepad.
        """
        steering_val   = 0.0
        thumb_y        = 0.0
        is_braking     = False
        handbrake      = False
        gear_up        = False
        gear_down      = False
        left_detected  = False
        right_detected = False
        confidence     = 0.0

        if result and result.hand_landmarks:
            confidence = len(result.hand_landmarks) / 2.0  # 0.5 per hand, max 1.0

            for i, hand_landmarks in enumerate(result.hand_landmarks):
                raw   = result.handedness[i][0].display_name
                # MediaPipe labels are mirrored — swap them for user perspective
                label = "Left" if raw == "Right" else "Right"

                if label == "Left":
                    left_detected = True
                    steer         = self.get_hand_tilt_level(hand_landmarks)
                    dz            = self.steer_dead_zone

                    if abs(steer) > dz:
                        intensity    = (abs(steer) - dz) / (1.0 - dz)
                        clamped      = max(0.1, min(1.0, intensity))
                        steering_val = -clamped if steer < 0 else clamped
                    else:
                        steering_val = 0.0

                    handbrake = self.is_left_hand_open(hand_landmarks)

                elif label == "Right":
                    right_detected = True
                    thumb_y        = self.get_thumb_y_level(hand_landmarks)
                    is_braking     = thumb_y < self.brake_threshold
                    gear_up        = self.is_right_index_out(hand_landmarks)
                    gear_down      = self.is_right_pinky_out(hand_landmarks)

        # Zero out controls for hands that aren't visible
        if not left_detected:
            steering_val = 0.0
            handbrake    = False
        if not right_detected:
            thumb_y    = 0.0
            is_braking = False
            gear_up    = False
            gear_down  = False

        # Exponential smoothing
        s = self.smooth
        new_steering = smooth_steering + s * (steering_val - smooth_steering)
        new_throttle = smooth_throttle + s * ((0.0 if is_braking else thumb_y) - smooth_throttle)
        new_brake    = smooth_brake    + s * ((1.0 if is_braking else 0.0)     - smooth_brake)

        return {
            "steering":       new_steering,
            "throttle":       new_throttle,
            "brake":          new_brake,
            "handbrake":      handbrake,
            "gear_up":        gear_up,
            "gear_down":      gear_down,
            "left_detected":  left_detected,
            "right_detected": right_detected,
            "confidence":     confidence,
            "hand_landmarks": result.hand_landmarks if result else [],
            "handedness":     result.handedness     if result else [],
        }
