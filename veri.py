# Trafik_Kontrol/veri.py
import threading
import time
from collections import deque


class PaylasilanVeri:
    """
    Thread-safe shared data store.

    Transfers data between the counting thread,
    traffic light thread, and web dashboard.
    """

    def __init__(self, serit_sayisi: int):
        self.lock = threading.Lock()
        self.n = serit_sayisi
        self.sayilar = [0] * serit_sayisi
        self.kutular = []  # [(x1,y1,x2,y2, lane, class_id, confidence), ...]
        self.toplam = 0
        self.hazir = False
        self.fps = 0.0
        self.son_guncelle = time.time()

        # Statistics: last 60 seconds
        self._fps_buffer = deque(maxlen=30)

    def guncelle(
        self,
        sayilar: list,
        kutular: list,
        toplam: int,
        gecen_sure: float = 0
    ):
        now = time.time()

        with self.lock:
            self.sayilar = list(sayilar)
            self.kutular = list(kutular)
            self.toplam = toplam
            self.hazir = True
            self.son_guncelle = now

            if gecen_sure > 0:
                self._fps_buffer.append(1.0 / gecen_sure)
                self.fps = sum(self._fps_buffer) / len(self._fps_buffer)

    def oku(self):
        """Returns (counts, boxes, total, ready)."""
        with self.lock:
            return (
                list(self.sayilar),
                list(self.kutular),
                self.toplam,
                self.hazir,
            )

    def oku_tam(self):
        """Returns all fields as a dictionary."""
        with self.lock:
            return {
                "sayilar": list(self.sayilar),
                "kutular": list(self.kutular),
                "toplam": self.toplam,
                "hazir": self.hazir,
                "fps": round(self.fps, 1),
                "son_guncelle": self.son_guncelle,
            }
