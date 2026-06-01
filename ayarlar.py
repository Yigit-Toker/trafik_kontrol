# Trafik_Kontrol/ayarlar.py

class Ayarlar:
    # ─── MODEL ────────────────────────────────────────────────────────────────
    # "nano" / "small" / "medium" / "large" / "xlarge"
    MODEL = "small"

    # ─── VEHICLE DETECTION — CRITICAL PARAMETERS ──────────────────────────────────
    GUVEN_ESIGI     = 0.08        # Lower → more vehicles detected
    IOU_ESIGI       = 0.30        # Lower → overlapping boxes also counted
    GORUNTU_BOYUTU  = 1280        # Higher resolution = small vehicles visible
    SAYIM_ARALIGI   = 0.5         # Count every 0.5 sec
    MAX_TESPIT      = 200         # Upper limit

    # COCO class IDs — ALL LAND VEHICLES
    # 1:bicycle  2:car  3:motorcycle  5:bus  7:truck
    ARAC_SINIFLARI = [1, 2, 3, 5, 7]

    # Class names (visualization)
    SINIF_ISIMLERI = {
        1: "bicycle", 2: "car",  3: "motorcycle",
        4: "airplane",     5: "bus", 6: "train",
        7: "truck",   8: "boat",
    }
    # ─── WEB PANEL ───────────────────────────────────────────────────────────
    WEB_KULLANICI = "admin"
    WEB_SIFRE_HASH = "240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9" # Password is admin123

    # ─── ADVANCED DETECTION ─────────────────────────────────────────────────────
    KOSELI_SAYIM    = True        # Corner-based counting
    KESISIM_ORANI   = 0.3         # 30% overlap is sufficient

    # ─── TRAFFIC LIGHT ─────────────────────────────────────────────────────────
    MIN_YESIL       = 5
    MAX_YESIL       = 60
    SARI_SURE       = 3
    SANIYE_PER_ARAC = 3
    MINIMUM_ARAC    = 1
    ADAPTIF_MOD     = True

    # ─── LANE COUNT ─────────────────────────────────────────────────────────
    SERIT_SAYISI = 4  # Total number of lanes

    # ─── GPIO ─────────────────────────────────────────────────────────────────
    GPIO_AKTIF = True,
    
    # GPIO pin definitions for each lane
    GPIO_PINLER = [
        {"red": 14, "yellow": 18, "green": 15},   # Lane 1
        {"red": 23, "yellow": 24, "green": 25},   # Lane 2
        {"red": 8,  "yellow": 7,  "green": 12},   # Lane 3
        {"red": 16, "yellow": 20, "green": 21},   # Lane 4
    ]

    # ─── WEB ──────────────────────────────────────────────────────────────────
    WEB_PORT  = 8080
    WEB_HOST  = '0.0.0.0'

    # ─── LOGGING ────────────────────────────────────────────────────────────────
    KAYIT_AKTIF   = False 
    KAYIT_DOSYASI = "traffic_log.csv"
