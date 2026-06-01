import threading
import time
import logging
import numpy as np
import cv2
from ayarlar import Ayarlar
from kamera import kare_al

log = logging.getLogger("trafik")

# Injected by main.py
model = None


def poli_icerik_orani(x1, y1, x2, y2, poly_pts):
    """
    Calculate the intersection ratio between a rectangle and a polygon.

    Mask-based approach: pixel-level accurate.
    """
    # Small mask (for performance, not bbox-sized but based on the original area)
    # Operate only within the bounding-box region
    if x2 <= x1 or y2 <= y1:
        return 0.0

    # Bounding box area
    kutu_alan = (x2 - x1) * (y2 - y1)
    if kutu_alan == 0:
        return 0.0

    # Create masks on a small canvas
    # Bring polygon and bounding box into a common coordinate system
    min_x = min(x1, int(poly_pts[:, 0, 0].min()))
    min_y = min(y1, int(poly_pts[:, 0, 1].min()))
    max_x = max(x2, int(poly_pts[:, 0, 0].max()))
    max_y = max(y2, int(poly_pts[:, 0, 1].max()))

    w = max_x - min_x + 1
    h = max_y - min_y + 1

    if w <= 0 or h <= 0 or w > 4000 or h > 4000:
        return 0.0

    # Polygon mask
    shifted = poly_pts - np.array([[[min_x, min_y]]])
    poli_maske = np.zeros((h, w), dtype=np.uint8)
    cv2.fillPoly(poli_maske, [shifted.astype(np.int32)], 255)

    # Bounding box mask
    kutu_maske = np.zeros((h, w), dtype=np.uint8)
    bx1 = max(0, x1 - min_x)
    by1 = max(0, y1 - min_y)
    bx2 = min(w, x2 - min_x)
    by2 = min(h, y2 - min_y)
    cv2.rectangle(kutu_maske, (bx1, by1), (bx2, by2), 255, -1)

    # Intersection
    kesisim = cv2.bitwise_and(poli_maske, kutu_maske)
    kesisim_alan = int(np.count_nonzero(kesisim))

    return kesisim_alan / kutu_alan


def arac_poligon_icinde_mi(x1, y1, x2, y2, poly_pts_list):
    """
    Determine whether a vehicle is inside a polygon using multiple methods.

    The vehicle is counted if any method returns True.

    Methods (in order):
    1. Center point
    2. Bottom-center point (wheels)
    3. Bounding box corners (4 points)
    4. Intersection ratio (30% threshold)
    """
    serit = -1
    en_iyi_oran = 0.0

    cx = (x1 + x2) // 2
    cy = (y1 + y2) // 2
    cy_alt = y2 - (y2 - y1) // 5  # Center point within the bottom 20% (wheels)

    # Test points:
    # center, bottom-center, 4 corners,
    # top-center, bottom-center, left-center, right-center
    test_pts = [
        (cx, cy),
        (cx, cy_alt),
        (x1 + 2, y1 + 2),
        (x2 - 2, y1 + 2),
        (x1 + 2, y2 - 2),
        (x2 - 2, y2 - 2),
        (cx, y2 - 2),
        (cx, y1 + 2),
    ]

    for i, pts in enumerate(poly_pts_list):
        # Point-based tests
        for px, py in test_pts:
            try:
                sonuc = cv2.pointPolygonTest(
                    pts,
                    (float(px), float(py)),
                    False
                )

                if sonuc >= 0:
                    return i

            except Exception:
                continue

        # Intersection-ratio test
        # (more expensive, but used as a fallback)
        if Ayarlar.KESISIM_ORANI > 0:
            try:
                oran = poli_icerik_orani(x1, y1, x2, y2, pts)

                if (
                    oran >= Ayarlar.KESISIM_ORANI
                    and oran > en_iyi_oran
                ):
                    en_iyi_oran = oran
                    serit = i

            except Exception:
                continue

    return serit


class SayimThread(threading.Thread):
    def __init__(self, kamera, poligonlar: list, veri, isik_thread):
        super().__init__(daemon=True, name="SayimThread")

        self.kamera = kamera
        self.poligonlar = poligonlar
        self.veri = veri
        self.isik = isik_thread
        self.dur_event = threading.Event()
        self.frame_sayaci = 0
        self._son_zaman = time.time()

        # Precomputed polygon arrays
        self._poly_pts = []

        for poly in poligonlar:
            pts = np.array(
                poly["points"],
                dtype=np.int32
            ).reshape((-1, 1, 2))

            self._poly_pts.append(pts)

        log.info(
            f"SayimThread initialized | "
            f"{len(poligonlar)} lanes | "
            f"conf={Ayarlar.GUVEN_ESIGI} | "
            f"iou={Ayarlar.IOU_ESIGI} | "
            f"imgsz={Ayarlar.GORUNTU_BOYUTU}"
        )

    def run(self):
        global model

        log.info("Counting thread started")

        while model is None and not self.dur_event.is_set():
            time.sleep(0.3)

        if self.dur_event.is_set():
            return

        # Warm-up
        log.info("🔥 Warming up model...")

        dummy = np.zeros(
            (
                Ayarlar.GORUNTU_BOYUTU,
                Ayarlar.GORUNTU_BOYUTU,
                3
            ),
            dtype=np.uint8
        )

        try:
            model(dummy, verbose=False)
            log.info("✅ Model warmed up")

        except Exception as e:
            log.warning(f"Warm-up error: {e}")

        log.info(
            f"🚦 Counting started | model={Ayarlar.MODEL} | "
            f"classes={Ayarlar.ARAC_SINIFLARI} | "
            f"conf={Ayarlar.GUVEN_ESIGI} | "
            f"imgsz={Ayarlar.GORUNTU_BOYUTU}"
        )

        while not self.dur_event.is_set():
            t0 = time.time()

            try:
                bgr = kare_al(self.kamera)

                if bgr is None:
                    time.sleep(0.1)
                    continue

                self.frame_sayaci += 1

                # BGR → RGB (YOLO expects RGB input)
                rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)

                # ── YOLO inference ──────────────────────────────────────────
                # agnostic_nms=True:
                # apply NMS even when overlapping detections belong
                # to different classes
                sonuclar = model.predict(
                    source=rgb,
                    imgsz=Ayarlar.GORUNTU_BOYUTU,
                    conf=Ayarlar.GUVEN_ESIGI,
                    iou=Ayarlar.IOU_ESIGI,
                    classes=Ayarlar.ARAC_SINIFLARI,
                    verbose=False,
                    device="cpu",
                    max_det=Ayarlar.MAX_TESPIT,
                    agnostic_nms=True,  # Cross-class NMS → fewer duplicates
                )

                kutular_raw = sonuclar[0].boxes

                toplam = (
                    len(kutular_raw)
                    if kutular_raw is not None
                    else 0
                )

                sayilar = [0] * len(self.poligonlar)
                tespitler = []

                if kutular_raw is not None and toplam > 0:
                    for kutu in kutular_raw:
                        try:
                            xyxy = kutu.xyxy[0].tolist()
                            x1, y1, x2, y2 = map(int, xyxy)

                            sinif_id = int(kutu.cls[0])
                            guven = float(kutu.conf[0])

                            # Advanced polygon membership test
                            serit = arac_poligon_icinde_mi(
                                x1,
                                y1,
                                x2,
                                y2,
                                self._poly_pts
                            )

                            if serit >= 0:
                                sayilar[serit] += 1

                            tespitler.append(
                                (
                                    x1,
                                    y1,
                                    x2,
                                    y2,
                                    serit,
                                    sinif_id,
                                    guven,
                                )
                            )

                        except Exception as e:
                            log.debug(
                                f"Bounding box processing error: {e}"
                            )
                            continue

                # ── Update shared data ──────────────────────────────────────
                gecen = max(
                    time.time() - self._son_zaman,
                    0.001
                )

                self._son_zaman = time.time()

                self.veri.guncelle(
                    sayilar,
                    tespitler,
                    toplam,
                    gecen
                )

                self.isik.sayim_guncelle(sayilar)

                # ── Logging ────────────────────────────────────────────────
                fps = 1.0 / max(time.time() - t0, 0.001)

                serit_str = " | ".join(
                    [
                        f"Road{i + 1}:{c}"
                        for i, c in enumerate(sayilar)
                    ]
                )

                toplam_sayilan = sum(sayilar)

                log.info(
                    f"#{self.frame_sayaci}: [{serit_str}] "
                    f"Detected={toplam} "
                    f"Counted={toplam_sayilan} | "
                    f"{fps:.1f}fps"
                )

                del sonuclar, kutular_raw, rgb, bgr

            except Exception as e:
                log.error(
                    f"Counting error: {e}",
                    exc_info=True
                )

                time.sleep(1.0)

            gecen_sure = time.time() - t0

            bekleme = max(
                0.0,
                Ayarlar.SAYIM_ARALIGI - gecen_sure
            )

            self.dur_event.wait(timeout=bekleme)

        log.info("Counting thread stopped")
