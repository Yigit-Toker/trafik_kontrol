import cv2
import numpy as np


# Lane colors (BGR)
SERIT_RENKLERI = [
    (0, 255, 80),    # Green
    (0, 180, 255),   # Orange
    (255, 80, 80),   # Blue
    (200, 0, 255),   # Purple
    (0, 255, 255),   # Yellow
    (255, 255, 0),   # Cyan
]


class PoligonSecici:
    """
    Interactive polygon selection tool.

    Usage:
    - Left click  : Add a point
    - Right click : Complete polygon (requires ≥3 points)
    - C           : Switch to drawing mode
    - S           : Switch to delete mode
    - X           : Clear everything
    - Z           : Undo last point
    - ENTER       : Confirm
    - ESC         : Cancel
    """

    def __init__(self):
        self.poligonlar = []
        self.cizim      = []
        self.mod        = "cizim"
        self.fare_pos   = (0, 0)

    def _renk(self, idx: int):
        return SERIT_RENKLERI[idx % len(SERIT_RENKLERI)]

    def fare_callback(self, event, x, y, flags, param):
        self.fare_pos = (x, y)

        if self.mod == "cizim":
            if event == cv2.EVENT_LBUTTONDOWN:
                self.cizim.append((x, y))
                print(f"  📍 Point added: ({x},{y})  [Total: {len(self.cizim)}]")

            elif event == cv2.EVENT_RBUTTONDOWN:
                if len(self.cizim) >= 3:
                    idx = len(self.poligonlar)
                    self.poligonlar.append({
                        "points": self.cizim.copy(),
                        "renk":   self._renk(idx)
                    })
                    print(
                        f"  ✅ Lane {idx+1} completed! "
                        f"({len(self.cizim)} points)"
                    )
                    self.cizim = []
                else:
                    print(f"  ⚠️  At least 3 points required! (Current: {len(self.cizim)})")

        elif self.mod == "sil":
            if event == cv2.EVENT_LBUTTONDOWN:
                for i, p in enumerate(self.poligonlar):
                    pts = np.array(p["points"], np.int32).reshape(-1, 1, 2)
                    if cv2.pointPolygonTest(pts, (float(x), float(y)), False) >= 0:
                        del self.poligonlar[i]
                        print(f"  🗑️  Lane {i+1} deleted")
                        break

    def _goster(self, ilk_kare: np.ndarray) -> np.ndarray:
        """Draws all polygons and helper information on the image."""
        frame = ilk_kare.copy()
        h, w  = frame.shape[:2]

        # ── Existing polygons ────────────────────────────────────────────────
        for i, p in enumerate(self.poligonlar):
            pts  = np.array(p["points"], np.int32)
            renk = p.get("renk", self._renk(i))

            # Semi-transparent fill
            overlay = frame.copy()
            cv2.fillPoly(overlay, [pts], renk)
            cv2.addWeighted(overlay, 0.15, frame, 0.85, 0, frame)

            # Border line
            cv2.polylines(frame, [pts], True, renk, 2)

            # Corner points
            for pt in pts:
                cv2.circle(frame, tuple(pt), 5, (255, 255, 255), -1)
                cv2.circle(frame, tuple(pt), 5, renk, 2)

            # Label (center)
            cx = int(np.mean(pts[:, 0]))
            cy = int(np.mean(pts[:, 1]))
            etiket = f"YOL {i+1}  ({len(p['points'])} nokta)"
            (tw, th), _ = cv2.getTextSize(etiket, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)
            cv2.rectangle(frame, (cx-tw//2-6, cy-th-8), (cx+tw//2+6, cy+6), (0,0,0), -1)
            cv2.putText(frame, etiket, (cx-tw//2, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.7, renk, 2)

        # ── Polygon currently being drawn ────────────────────────────────────
        if self.cizim:
            cur_renk = self._renk(len(self.poligonlar))
            if len(self.cizim) >= 2:
                for j in range(1, len(self.cizim)):
                    cv2.line(frame, self.cizim[j-1], self.cizim[j], cur_renk, 2)

            # Mouse cursor guide line
            cv2.line(frame, self.cizim[-1], self.fare_pos, cur_renk, 1, cv2.LINE_AA)

            # Closing guide line (3+ points)
            if len(self.cizim) >= 3:
                cv2.line(frame, self.cizim[0], self.fare_pos, cur_renk, 1, cv2.LINE_AA)

            for pt in self.cizim:
                cv2.circle(frame, pt, 5, (255, 255, 255), -1)
                cv2.circle(frame, pt, 5, cur_renk, 2)

        # ── Information panel (top-left) ─────────────────────────────────────
        panel_y = 15
        panel_bilgiler = [
            (f"MOD: {'CIZIM' if self.mod == 'cizim' else 'SIL'}", (255, 220, 0)),
            (f"Poligon: {len(self.poligonlar)}  Cizim noktasi: {len(self.cizim)}", (200, 200, 200)),
        ]
        cv2.rectangle(frame, (8, 8), (380, 65), (0, 0, 0), -1)
        cv2.rectangle(frame, (8, 8), (380, 65), (80, 80, 80), 1)

        for j, (metin, renk) in enumerate(panel_bilgiler):
            cv2.putText(frame, metin, (16, panel_y + j*25),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, renk, 2)

        # ── Shortcut guide (bottom) ──────────────────────────────────────────
        kisayollar = [
            "LEFT CLICK: Point",
            "RIGHT CLICK: Complete",
            "C: Draw",
            "S: Delete",
            "Z: Undo",
            "X: Clear",
            "ENTER: Confirm",
            "ESC: Cancel",
        ]

        bar_h = 30
        cv2.rectangle(frame, (0, h-bar_h), (w, h), (20, 20, 20), -1)

        x_off = 10
        for k in kisayollar:
            (kw, _), _ = cv2.getTextSize(k, cv2.FONT_HERSHEY_SIMPLEX, 0.45, 1)
            cv2.putText(frame, k, (x_off, h-9),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.45, (180, 180, 180), 1)
            x_off += kw + 20

        return frame

    def calistir(self, ilk_kare: np.ndarray) -> list:
        """
        Collect polygon selections from the user.

        Returns the confirmed polygon list
        (each item: {"points": [...], "renk": (b,g,r)}).
        """
        cv2.namedWindow("POLIGON SECIMI", cv2.WINDOW_NORMAL)
        cv2.resizeWindow("POLIGON SECIMI", 1280, 720)
        cv2.setMouseCallback("POLIGON SECIMI", self.fare_callback)

        print("\n" + "═" * 55)
        print("  🚦 TRAFFIC CONTROL — AREA SELECTION TOOL")
        print("═" * 55)
        print("  LEFT CLICK  : Add polygon point")
        print("  RIGHT CLICK : Complete polygon (≥3 points)")
        print("  C           : Switch to drawing mode")
        print("  S           : Switch to delete mode")
        print("  Z           : Undo last point")
        print("  X           : Clear all polygons")
        print("  ENTER       : Confirm and start system")
        print("  ESC         : Cancel")
        print("═" * 55 + "\n")

        while True:
            frame = self._goster(ilk_kare)
            cv2.imshow("POLIGON SECIMI", frame)
            tus = cv2.waitKey(1) & 0xFF

            if tus == 13:   # ENTER
                if self.cizim:
                    print("⚠️  There is an unfinished polygon! Complete it with right click.")
                    continue

                if not self.poligonlar:
                    print("⚠️  At least one area must be selected!")
                    continue

                print(f"\n✅ {len(self.poligonlar)} area(s) confirmed!\n")
                break

            elif tus == ord('c'):
                self.mod = "cizim"
                print("Mode → DRAW")

            elif tus == ord('s'):
                self.mod = "sil"
                print("Mode → DELETE")

            elif tus == ord('z'):
                if self.cizim:
                    removed = self.cizim.pop()
                    print(f"  ↩ Last point removed: {removed}")
                else:
                    print("  ↩ No point to undo")

            elif tus == ord('x'):
                self.poligonlar.clear()
                self.cizim.clear()
                print("🗑  All polygons cleared")

            elif tus == 27:   # ESC
                self.poligonlar.clear()
                print("❌ Cancelled")
                break

        cv2.destroyWindow("POLIGON SECIMI")
        return self.poligonlar
