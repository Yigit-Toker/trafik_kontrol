# Trafik_Kontrol/gpio_kontrol.py
import logging
from ayarlar import Ayarlar

log = logging.getLogger("trafik")

try:
    from gpiozero import LED

    GPIO_KUTUPHANE = True
    GPIO_KUTUPHANE_ADI = "gpiozero"
    log.info("gpiozero library found")
except ImportError:
    GPIO_KUTUPHANE = False
    GPIO_KUTUPHANE_ADI = "Not Available"
    log.warning("No GPIO library found")


class GPIOKontrol:
    KIRMIZI = 0
    SARI = 1
    YESIL = 2

    def __init__(self):
        self.aktif = False
        self.led_objects = {}  # Store gpiozero LED objects

        log.info("Initializing GPIO...")
        log.info(f"  - GPIO_AKTIF setting: {Ayarlar.GPIO_AKTIF}")
        log.info(f"  - GPIO library: {GPIO_KUTUPHANE_ADI}")
        log.info(f"  - Number of lanes: {len(Ayarlar.GPIO_PINLER)}")
        log.info(f"  - Pin configuration: {Ayarlar.GPIO_PINLER}")

        if not Ayarlar.GPIO_AKTIF:
            log.info("GPIO: Simulation mode (ayarlar.py → GPIO_AKTIF=False)")
            log.info("💡 To enable lights, set GPIO_AKTIF = True in ayarlar.py")
            return

        if not GPIO_KUTUPHANE:
            log.warning(
                "GPIO: gpiozero library not found, switching to simulation mode"
            )
            log.warning("💡 Installation: sudo apt install python3-gpiozero")
            return

        try:
            self._baslat_gpiozero()
            self.aktif = True
            log.info(
                f"✅ GPIO: {len(Ayarlar.GPIO_PINLER)} roads configured successfully"
            )

        except Exception as e:
            log.error(f"❌ GPIO initialization error: {e}")
            import traceback
            log.error(traceback.format_exc())

    def _baslat_gpiozero(self):
        """Initialize GPIO pins using the gpiozero library."""
        log.info("Initializing GPIO with gpiozero...")

        for i, yol in enumerate(Ayarlar.GPIO_PINLER):
            log.info(f"Initializing pins for Road {i + 1}: {yol}")

            serit_leds = {}

            for renk, pin in yol.items():
                try:
                    # Create gpiozero LED object - START OFF
                    led = LED(pin)
                    led.off()  # IMPORTANT: Start in OFF state

                    serit_leds[renk] = led
                    log.info(f"  ✅ {renk}: GPIO{pin} ready")

                except Exception as e:
                    log.error(
                        f"  ❌ Failed to initialize {renk} pin GPIO{pin}: {e}"
                    )

            self.led_objects[i] = serit_leds

    def isik_ayarla(self, serit: int, durum: int):
        """
        serit: Zero-based lane index
        durum: 0=RED, 1=YELLOW, 2=GREEN
        """
        durum_isimleri = {
            0: "RED",
            1: "YELLOW",
            2: "GREEN"
        }

        renk_haritasi = {
            0: "red",
            1: "yellow",
            2: "green"
        }

        if not self.aktif:
            log.debug(
                f"GPIO inactive - Road{serit + 1} "
                f"{durum_isimleri.get(durum, '?')} simulated"
            )
            return

        if serit >= len(Ayarlar.GPIO_PINLER):
            log.error(
                f"Invalid lane: {serit} "
                f"(max: {len(Ayarlar.GPIO_PINLER) - 1})"
            )
            return

        try:
            serit_leds = self.led_objects.get(serit, {})
            istenen_renk = renk_haritasi.get(durum)

            if not serit_leds:
                log.error(f"No LED object found for Road{serit + 1}!")
                return

            # IMPORTANT CHANGE:
            # Turn off all LEDs first, then enable the requested one.
            for renk, led in serit_leds.items():
                led.off()

            # Turn on the requested LED
            if istenen_renk and istenen_renk in serit_leds:
                serit_leds[istenen_renk].on()

                emoji = {
                    "red": "🔴",
                    "yellow": "🟡",
                    "green": "🟢"
                }

                log.info(
                    f"{emoji.get(istenen_renk, '💡')} "
                    f"Road{serit + 1} "
                    f"{durum_isimleri.get(durum)} - "
                    f"GPIO{Ayarlar.GPIO_PINLER[serit][istenen_renk]}"
                )

        except Exception as e:
            log.error(
                f"GPIO write error "
                f"(Road{serit + 1}, {durum_isimleri.get(durum, '?')}): {e}"
            )

    def tum_kirmizi(self):
        """Set all lanes to red (emergency/shutdown state)."""
        log.info("Switching all lights to red...")

        for i in range(len(Ayarlar.GPIO_PINLER)):
            self.isik_ayarla(i, self.KIRMIZI)

        log.info("✅ All lights are red")

    def test_modu(self):
        """Test all LEDs sequentially."""
        if not self.aktif:
            log.warning("GPIO is not active, test cannot be performed!")
            return

        log.info("🧪 Starting GPIO test mode...")

        import time

        for serit in range(len(Ayarlar.GPIO_PINLER)):
            log.info(f"Testing Road {serit + 1}...")

            # Red test (2 seconds)
            self.isik_ayarla(serit, self.KIRMIZI)
            time.sleep(2)

            # Yellow test (1 second)
            self.isik_ayarla(serit, self.SARI)
            time.sleep(1)

            # Green test (2 seconds)
            self.isik_ayarla(serit, self.YESIL)
            time.sleep(2)

        # Return all lights to red after testing
        self.tum_kirmizi()

        log.info("✅ GPIO test mode completed")

    def temizle(self):
        """Clean up GPIO pins."""
        try:
            # Turn off all LEDs first
            for serit_leds in self.led_objects.values():
                for led in serit_leds.values():
                    led.off()
                    led.close()

            self.led_objects.clear()
            self.aktif = False

            log.info("✅ GPIO cleaned up")

        except Exception as e:
            log.warning(f"GPIO cleanup error: {e}")


# Module-level singleton instance
gpio = GPIOKontrol()
