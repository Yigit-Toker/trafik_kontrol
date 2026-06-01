# Trafik_Kontrol/isik_thread.py
import threading
import time
import logging
import numpy as np
from collections import deque
from ayarlar import Ayarlar
from gpio_kontrol import gpio

log = logging.getLogger("trafik")


class IsikThread(threading.Thread):
    """
    Adaptive traffic light control thread.

    Features:
    - Dynamic green duration based on vehicle density
      (vehicles * 3 seconds, min 5 / max 30)
    - Round-robin ordering starting from Road 1
    - Yellow → 5-second all-red wait → Next road green
    - Thread-safe snapshot API
    - Statistics tracking
    """

    KIRMIZI = 0
    SARI = 1
    YESIL = 2

    # ── Green duration constants ──────────────────────────────────────────────
    _SANIYE_PER_ARAC = 3      # 3 seconds per vehicle
    _MIN_YESIL = 5            # Minimum green duration (seconds)
    _MAX_YESIL = 30           # Maximum green duration (seconds)

    # ── Phase durations ───────────────────────────────────────────────────────
    _ALL_RED_SURE = 5         # Full-red waiting period after yellow (seconds)

    def __init__(self, serit_sayisi: int):
        super().__init__(daemon=True, name="IsikThread")
        self.lock = threading.Lock()
        self.dur_event = threading.Event()
        self.n = serit_sayisi

        # State
        self.durum = [self.KIRMIZI] * serit_sayisi
        self.aktif_serit = -1
        self.faz = "bekle"    # "bekle" | "yesil" | "sari" | "all_red"
        self.faz_bitis = time.time()

        # Data
        self.arac_sayilari = [0] * serit_sayisi
        self.hesap_sureler = [0.0] * serit_sayisi

        # ── Round-robin system ────────────────────────────────────────────────
        # Index of the next lane that will receive green
        # (locked during yellow phase)
        self._siradaki = -1

        # Round-robin counter:
        # starts from 0 → Road 1 starts first
        self._rr_sayac = 0

        # Statistics
        self.toplam_gecis = [0] * serit_sayisi
        self.toplam_bekleme = [0.0] * serit_sayisi

        # Initialize GPIO — all lights red
        for i in range(serit_sayisi):
            gpio.isik_ayarla(i, self.KIRMIZI)

    # ─── Public API ───────────────────────────────────────────────────────────

    def snapshot(self) -> dict:
        """Returns a thread-safe snapshot of the current state."""
        with self.lock:
            now = time.time()

            kalan = [
                max(0.0, self.faz_bitis - now)
                if i == self.aktif_serit else 0.0
                for i in range(self.n)
            ]

            return {
                "durum": list(self.durum),
                "kalan": kalan,
                "hesap": list(self.hesap_sureler),
                "aktif": self.aktif_serit,
                "faz": self.faz,
                "arac_sayilari": list(self.arac_sayilari),
                "gecis": list(self.toplam_gecis),
                "bekleme": list(self.toplam_bekleme),
                "rr_sayac": self._rr_sayac,
            }

    def sayim_guncelle(self, yeni_sayilar: list):
        """Vehicle count update from the counting thread."""
        with self.lock:
            self.arac_sayilari = list(yeni_sayilar)

            # Trigger only in waiting mode
            if self.aktif_serit == -1 and self.faz == "bekle":
                self._sonraki_yesil_bul_ve_ver()

    # ─── Internal Logic ───────────────────────────────────────────────────────

    def _yesil_sure_hesapla(self, serit: int) -> float:
        """
        Calculate adaptive green duration based on vehicle count.

        Formula:
            vehicle_count * 3 seconds

        Limits:
            minimum = 5 seconds
            maximum = 30 seconds
        """
        arac = self.arac_sayilari[serit]

        if arac < Ayarlar.MINIMUM_ARAC:
            return 0.0

        sure = arac * self._SANIYE_PER_ARAC
        return max(self._MIN_YESIL, min(self._MAX_YESIL, sure))

    def _sonraki_rr_bul(self, baslangic: int) -> int:
        """
        Find the next occupied lane using round-robin logic.

        Searches one full cycle starting from the given index.
        Returns -1 if no eligible lane is found.
        """
        for adim in range(self.n):
            aday = (baslangic + adim) % self.n

            if self.arac_sayilari[aday] >= Ayarlar.MINIMUM_ARAC:
                return aday

        return -1  # No lane contains enough vehicles

    def _sonraki_yesil_bul_ve_ver(self):
        """
        Find the next occupied lane according to round-robin order
        and assign the green light.

        Empty lanes are skipped.
        If all lanes are empty, the system enters waiting mode.
        """
        hedef = self._sonraki_rr_bul(self._rr_sayac)

        if hedef >= 0:
            # Prepare RR counter for the next cycle
            self._rr_sayac = (hedef + 1) % self.n
            self._yesil_ver(hedef)
        else:
            log.info("🔴 All lanes are empty, waiting...")

    def _yesil_ver(self, serit: int):
        """Assign a green light to the specified lane."""

        if serit < 0 or serit >= self.n:
            self.aktif_serit = -1
            self.faz = "bekle"
            self._siradaki = -1
            return

        sure = self._yesil_sure_hesapla(serit)

        if sure == 0.0:
            log.debug(f"Road{serit + 1} is empty, skipping")

            # This lane is empty:
            # advance RR counter and try again
            self._rr_sayac = (serit + 1) % self.n
            self._sonraki_yesil_bul_ve_ver()
            return

        # Turn previous active lane red
        if self.aktif_serit >= 0 and self.aktif_serit != serit:
            prev = self.aktif_serit
            self.durum[prev] = self.KIRMIZI
            gpio.isik_ayarla(prev, self.KIRMIZI)

        # Assign green to new lane
        self.aktif_serit = serit
        self.durum[serit] = self.YESIL
        self.hesap_sureler[serit] = sure
        self.faz = "yesil"
        self.faz_bitis = time.time() + sure
        self._siradaki = -1

        gpio.isik_ayarla(serit, self.YESIL)

        # Statistics
        self.toplam_gecis[serit] += 1
        self.toplam_bekleme[serit] += sure

        log.info(
            f"🟢 GREEN → Road{serit + 1} | "
            f"{self.arac_sayilari[serit]} vehicles | {sure:.0f}s"
        )

    # ─── Thread Loop ──────────────────────────────────────────────────────────

    def run(self):
        log.info("Traffic light thread started")

        while not self.dur_event.is_set():
            with self.lock:
                if self.aktif_serit >= 0:
                    kalan = self.faz_bitis - time.time()

                    if self.faz == "yesil" and kalan <= 0:
                        # ── Green finished → Switch to yellow ────────────────

                        # Determine the next lane now and lock it during
                        # yellow + all-red phases
                        hedef = self._sonraki_rr_bul(self._rr_sayac)

                        if hedef >= 0:
                            self._rr_sayac = (hedef + 1) % self.n

                        self._siradaki = hedef

                        self.durum[self.aktif_serit] = self.SARI
                        self.faz = "sari"
                        self.faz_bitis = (
                            time.time() + Ayarlar.SARI_SURE
                        )

                        gpio.isik_ayarla(self.aktif_serit, self.SARI)

                        log.info(
                            f"🟡 YELLOW → Road{self.aktif_serit + 1} | "
                            f"Next: "
                            f"{'Road' + str(self._siradaki + 1) if self._siradaki >= 0 else 'NONE'}"
                        )

                    elif self.faz == "sari" and kalan <= 0:
                        # ── Yellow finished → Enter all-red phase ───────────

                        self.durum[self.aktif_serit] = self.KIRMIZI
                        gpio.isik_ayarla(
                            self.aktif_serit,
                            self.KIRMIZI
                        )

                        self.faz = "all_red"
                        self.faz_bitis = (
                            time.time() + self._ALL_RED_SURE
                        )

                        log.info(
                            f"🔴 ALL-RED → Waiting {self._ALL_RED_SURE}s | "
                            f"Next: "
                            f"{'Road' + str(self._siradaki + 1) if self._siradaki >= 0 else 'NONE'}"
                        )

                    elif self.faz == "all_red" and kalan <= 0:
                        # ── All-red finished → Give green to next lane ─────

                        sonraki = self._siradaki

                        self._siradaki = -1
                        self.aktif_serit = -1
                        self.faz = "bekle"

                        if sonraki >= 0:
                            self._yesil_ver(sonraki)
                        else:
                            # No vehicles remain in any lane
                            log.info("🔴 All lanes are empty, waiting...")

            time.sleep(0.05)  # 20 Hz control loop

        # Set all lights to red on shutdown
        gpio.tum_kirmizi()
        log.info("Traffic light thread stopped")
