# Trafik_Kontrol/kamera.py
import cv2
import numpy as np
import logging

log = logging.getLogger("trafik")


def kare_al(kamera):
    """
    Capture a frame from the camera.

    Always returns a valid BGR image regardless of whether the source is:
    - Picamera2 (RGB/RGBA)
    - USB camera wrapped through the compatibility layer
    """
    try:
        ham = kamera.capture_array()
    except Exception as e:
        log.debug(f"Frame capture failed: {e}")
        return None

    if ham is None:
        return None

    # Safety check for empty arrays
    if ham.size == 0:
        return None

    # Validate image shape
    if len(ham.shape) == 2:
        # Grayscale → BGR
        return cv2.cvtColor(ham, cv2.COLOR_GRAY2BGR)

    if len(ham.shape) == 3:
        ch = ham.shape[2]
        if ch == 4:
            # RGBA or BGRA → BGR
            # USB camera wrapper may return BGRA,
            # Picamera2 may return RGBA.
            # Take the first 3 channels and convert RGB → BGR.
            rgb = ham[:, :, :3]
            return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)

        elif ch == 3:
            # Picamera2 default output: RGB → BGR
            return cv2.cvtColor(ham, cv2.COLOR_RGB2BGR)

    # Unexpected format → return as-is
    return ham


def kamera_olustur(cozunurluk=(1280, 720), fps=30):
    """
    Automatically detect and initialize the available camera.

    Detection order:
        1. Picamera2
        2. USB / V4L2 camera
    """
    import time

    # ── Try Picamera2 first ───────────────────────────────────────────────────
    try:
        from picamera2 import Picamera2

        cam = Picamera2()
        config = cam.create_preview_configuration(
            main={"size": cozunurluk, "format": "RGB888"},
            controls={"FrameRate": fps}
        )
        cam.configure(config)
        cam.start()
        time.sleep(1.5)

        # Capture a test frame
        test = cam.capture_array()
        if test is None or test.size == 0:
            raise RuntimeError("Picamera2 test frame is empty")

        log.info(
            f"✅ Picamera2 ready "
            f"({cozunurluk[0]}x{cozunurluk[1]} @ {fps}fps) "
            f"| format: {test.shape}"
        )
        return cam, "picamera2"

    except Exception as e:
        log.warning(f"Failed to initialize Picamera2: {e}")

    # ── Try USB / V4L2 cameras ────────────────────────────────────────────────
    for idx in range(4):
        try:
            cap = cv2.VideoCapture(idx)

            if not cap.isOpened():
                continue

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, cozunurluk[0])
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, cozunurluk[1])
            cap.set(cv2.CAP_PROP_FPS, fps)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

            ret, test = cap.read()
            if not ret or test is None:
                cap.release()
                continue

            # Wrapper that makes a USB camera compatible
            # with the Picamera2-style API.
            class USBKamera:
                def __init__(self, capture, cam_idx):
                    self._cap = capture
                    self._idx = cam_idx

                def capture_array(self):
                    ret, frame = self._cap.read()

                    if not ret or frame is None:
                        return None

                    # USB cameras return BGR frames.
                    #
                    # Returning BGR directly would make kare_al()
                    # interpret it as RGB and convert it again,
                    # resulting in incorrect colors.
                    #
                    # Clean solution:
                    # Convert BGR → RGB here.
                    # Then kare_al() converts RGB → BGR,
                    # producing the correct final output.
                    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                def stop(self):
                    self._cap.release()

                def __repr__(self):
                    return f"USBKamera(index={self._idx})"

            cam = USBKamera(cap, idx)

            log.info(
                f"✅ USB camera ready "
                f"(index={idx}, {cozunurluk[0]}x{cozunurluk[1]})"
            )

            return cam, "usb"

        except Exception as e:
            log.warning(f"Failed to initialize USB camera {idx}: {e}")

    raise RuntimeError(
        "No camera detected. Please check the camera connection."
    )
