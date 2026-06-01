#!/usr/bin/env python3
# Trafik_Kontrol/main.py

import sys
import time
import logging
import argparse
import os
import signal
import socket

import cv2
import numpy as np
from ultralytics import YOLO

from ayarlar import Ayarlar
from kamera import kare_al, kamera_olustur
from gpio_kontrol import gpio
from veri import PaylasilanVeri
from isik_thread import IsikThread
from sayim_thread import SayimThread
from web_panel import WebPanel
from poligon_secici import PoligonSecici

# ─── Logging ──────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  [%(name)-12s]  %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("trafik.main")
logging.getLogger("werkzeug").setLevel(logging.ERROR)
logging.getLogger("ultralytics").setLevel(logging.WARNING)

# ─── Model table ────────────────────────────────────────────────────────────
MODEL_FILES = {
    "nano":   "yolo11n.pt",
    "small":  "yolo11s.pt",
    "medium": "yolo11m.pt",
    "large":  "yolo11l.pt",
    "xlarge": "yolo11x.pt",
}

CLASS_NAMES = Ayarlar.SINIF_ISIMLERI


def parse_args():
    p = argparse.ArgumentParser(description="Smart Traffic Management System")
    p.add_argument("--model",      default=Ayarlar.MODEL,
                   choices=list(MODEL_FILES), help="Model size")
    p.add_argument("--conf",       type=float, default=Ayarlar.GUVEN_ESIGI,
                   help="Confidence threshold (0.0–1.0)")
    p.add_argument("--iou",        type=float, default=Ayarlar.IOU_ESIGI,
                   help="IoU threshold")
    p.add_argument("--imgsz",      type=int,   default=Ayarlar.GORUNTU_BOYUTU,
                   help="YOLO input size (320/640/1280)")
    p.add_argument("--no-display", action="store_true",
                   help="Do not open OpenCV window (headless mode)")
    p.add_argument("--port",       type=int,   default=Ayarlar.WEB_PORT,
                   help="Web panel port")
    return p.parse_args()


def draw_frame(bgr, polygons, snap, full_data):
    """Draws polygon, traffic light and info layers on the video frame."""
    counts = full_data["counts"]
    boxes = full_data["boxes"]
    fps     = full_data.get("fps", 0)

    # ── Polygons ────────────────────────────────────────────────────────────
    for i, p in enumerate(polygons):
        pts   = np.array(p["points"], np.int32)
        active = (i == snap["active"])
        color  = p.get("color", (0, 255, 80))

        overlay = bgr.copy()
        cv2.fillPoly(overlay, [pts], color if active else (60, 60, 60))
        cv2.addWeighted(
            overlay, 0.1 if active else 0.05,
            bgr,     0.9 if active else 0.95,
            0, bgr
        )

        thickness = 3 if active else 1
        cv2.polylines(bgr, [pts], True, color if active else (80, 80, 80), thickness)

        cx = int(np.mean(pts[:, 0]))
        cy = int(np.mean(pts[:, 1]))

        # ── Traffic light symbol ────────────────────────────────────────────
        d     = snap["state"][i]
        light = [(0, 0, 220), (0, 185, 255), (0, 220, 0)][d]
        shadow = [(0, 0,  80), (0,  60, 100), (0,  80, 0)][d]

        lx, ly = cx + 55, cy - 55
        cv2.rectangle(bgr, (lx-14, ly-42), (lx+14, ly+14), (30, 30, 30), -1)
        cv2.rectangle(bgr, (lx-14, ly-42), (lx+14, ly+14), (70, 70, 70),  1)

        for bulb_y in [ly-28, ly-8, ly+8]:
            cv2.circle(bgr, (lx, bulb_y), 8, shadow, -1)

        active_y = [ly-28, ly-8, ly+8][d]
        cv2.circle(bgr, (lx, active_y), 9, light, -1)
        cv2.circle(bgr, (lx, active_y), 9, (255, 255, 255), 1)

        remaining = snap["remaining"][i]
        if remaining > 0:
            cv2.putText(bgr, f"{remaining:.0f}s", (lx-12, ly+28),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

        label = f"Lane{i+1}: {counts[i]} vehicles"
        (ew, eh), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
        cv2.rectangle(bgr, (cx-ew//2-6, cy-eh-8), (cx+ew//2+6, cy+4), (0, 0, 0), -1)
        cv2.putText(bgr, label, (cx-ew//2, cy),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)

    # ── Detection boxes ───────────────────────────────────────────────────────
    for det in boxes:
        try:
            x1, y1, x2, y2, lane, class_id, confidence = det
            inside = lane >= 0
            color    = (0, 230, 120) if inside else (80, 80, 200)
            cv2.rectangle(bgr, (x1, y1), (x2, y2), color, 1)

            name     = CLASS_NAMES.get(class_id, str(class_id))
            label = f"{name} {confidence:.2f}"
            (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.rectangle(bgr, (x1, y1-th-6), (x1+tw+6, y1), color, -1)
            cv2.putText(bgr, label, (x1+3, y1-3),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (0, 0, 0), 1)
        except Exception:
            continue

    # ─── Info panel ──────────────────────────────────────────────────────────
    total     = full_data["total"]
    active_lane_no = f"Lane{snap['active']+1}" if snap["active"] >= 0 else "—"
    lines = [
        (f"TOTAL VEHICLES: {total}",                                              (0, 230, 130)),
        (f"Active: {active_lane_no}  Phase: {snap['phase'].upper()}",                    (200, 200, 200)),
        (f"Model: {Ayarlar.MODEL}  Conf: {Ayarlar.GUVEN_ESIGI}  FPS: {fps:.1f}", (160, 160, 160)),
        ("S: Screenshot  |  ESC: Exit",                                   (120, 120, 120)),
    ]
    panel_h = len(lines) * 26 + 12
    panel_w = 440
    overlay2 = bgr.copy()
    cv2.rectangle(overlay2, (4, 4), (panel_w, panel_h), (10, 10, 10), -1)
    cv2.addWeighted(overlay2, 0.7, bgr, 0.3, 0, bgr)
    cv2.rectangle(bgr, (4, 4), (panel_w, panel_h), (50, 50, 50), 1)
    for idx, (text, color) in enumerate(lines):
        cv2.putText(bgr, text, (12, 26 + idx*26),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 1)

    return bgr


def main():
    args = parse_args()

    # Apply arguments to Settings
    Ayarlar.MODEL          = args.model
    Ayarlar.GUVEN_ESIGI    = args.conf
    Ayarlar.IOU_ESIGI      = args.iou
    Ayarlar.GORUNTU_BOYUTU = args.imgsz
    Ayarlar.WEB_PORT       = args.port
    display = not args.no_display

    banner = """
╔══════════════════════════════════════════════════════════╗
║         SMART TRAFFIC MANAGEMENT SYSTEM v2.0            ║
║         YOLO11 · Raspberry Pi · Real-Time               ║
╚══════════════════════════════════════════════════════════╝"""
    log.info(banner)

    # ── 1. CAMERA ─────────────────────────────────────────────────────────────
    log.info("[1/5] Starting camera…")
    try:
        camera, camera_type = kamera_olustur(resolution=(1280, 720), fps=30)
    except RuntimeError as e:
        log.error(str(e))
        return

    # ── 2. FIRST FRAME + POLYGON SELECTION ─────────────────────────────────────────
    log.info("[2/5] Waiting for polygon selection…")

    # Get first valid frame (try a few times)
    first = None
    for _ in range(10):
        first = kare_al(camera)
        if first is not None and first.size > 0:
            break
        time.sleep(0.2)

    if first is None or first.size == 0:
        log.error("Could not get image from camera! Check connection.")
        camera.stop()
        return

    log.info(f"✅ First frame captured: {first.shape}")

    selector     = PoligonSecici()
    polygons = selector.run(first)
    if not polygons:
        log.error("No polygon selected, exiting.")
        camera.stop()
        return

    n = len(polygons)
    log.info(f"✅ {n} lanes selected")

    # ── 3. MODEL ──────────────────────────────────────────────────────────────
    model_file = MODEL_FILES.get(Ayarlar.MODEL, "yolo11s.pt")
    log.info(f"[3/5] Loading model: {model_file} …")
    try:
        model = YOLO(model_file)
        log.info(f"✅ Model ready  (classes: {Ayarlar.ARAC_SINIFLARI})")
    except Exception as e:
        log.error(f"Model could not be loaded: {e}")
        camera.stop()
        return

    import sayim_thread as st_module
    st_module.model = model

    # ── 4. THREADS ─────────────────────────────────────────────────────────
    log.info("[4/5] Starting threads…")
    data  = PaylasilanVeri(n)
    light  = IsikThread(n)
    counter = SayimThread(camera, polygons, data, light)
    web   = WebPanel(light, data)

    light.start()
    counter.start()
    web.start()

    try:
        ip = socket.gethostbyname(socket.gethostname())
    except Exception:
        ip = "localhost"

    log.info("[5/5] ✅ System ready!")
    log.info(f"  🌐 Web panel  → http://{ip}:{Ayarlar.WEB_PORT}")
    log.info(f"  📡 API        → http://{ip}:{Ayarlar.WEB_PORT}/api")
    log.info(f"  📊 Settings    → http://{ip}:{Ayarlar.WEB_PORT}/api/settings")
    if display:
        log.info("  🖥️  Window   → ESC to exit  |  S: Screenshot")
    log.info("")

    # ── Graceful shutdown ─────────────────────────────────────────────────────
    def shutdown(signum=None, frame=None):
        log.info("Shutting down…")
        counter.stop_event.set()
        light.stop_event.set()
        counter.join(timeout=3)
        light.join(timeout=2)
        cv2.destroyAllWindows()
        camera.stop()
        gpio.cleanup()
        log.info("Program terminated")
        sys.exit(0)

    signal.signal(signal.SIGINT,  shutdown)
    signal.signal(signal.SIGTERM, shutdown)

    # ── 5. MAIN DISPLAY LOOP ────────────────────────────────────────────────
    # Create and resize window beforehand
    if display:
        cv2.namedWindow("SMART TRAFFIC CONTROL", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("SMART TRAFFIC CONTROL", 1280, 720)

    try:
        while True:
            bgr = kare_al(camera)

            # Invalid frame check
            if bgr is None or bgr.size == 0:
                time.sleep(0.05)
                continue

            snap     = light.snapshot()
            full_data = data.read_full()

            if display:
                # .copy() preserves original frame — draw_frame draws on it
                bgr_display = draw_frame(bgr.copy(), polygons, snap, full_data)
                cv2.imshow("SMART TRAFFIC CONTROL", bgr_display)

                key = cv2.waitKey(1) & 0xFF
                if key == 27:       # ESC → exit
                    break
                elif key == ord('s'):   # S → save screenshot
                    file = f"screenshot_{int(time.time())}.jpg"
                    cv2.imwrite(file, bgr_display)
                    log.info(f"📸 Screenshot saved: {file}")
            else:
                time.sleep(0.03)

    except KeyboardInterrupt:
        log.info("User stopped (Ctrl+C)")
    finally:
        shutdown()


if __name__ == "__main__":
    main()
