from gpiozero import LED
from time import sleep
import sys

class TrafikLambasi:
    def __init__(self):
        try:
            # Initialize LEDs
            self.kirmizi = LED(14)
            self.sari = LED(18)
            self.yesil = LED(15)

            # Turn all LEDs off
            self.kirmizi.off()
            self.sari.off()
            self.yesil.off()

            print("✅ Traffic light ready!")
            print(f"   Red: GPIO 14 (Pin 8)")
            print(f"   Yellow: GPIO 18 (Pin 12)")
            print(f"   Green: GPIO 15 (Pin 10)")

        except Exception as e:
            print(f"❌ Initialization error: {e}")
            print("\nSuggested solutions:")
            print("1. sudo apt update && sudo apt install python3-gpiozero")
            print("2. Check LED connections")
            print("3. Try another GPIO pin (e.g. 23, 24, 25)")
            sys.exit(1)

    def test_et(self):
        """Test all LEDs one by one"""
        print("\n🧪 Starting LED Test...")

        print("🔴 Red test (3 seconds)")
        self.kirmizi.on()
        sleep(3)
        self.kirmizi.off()

        print("🟡 Yellow test (2 seconds)")
        self.sari.on()
        sleep(2)
        self.sari.off()

        print("🟢 Green test (3 seconds)")
        self.yesil.on()
        sleep(3)
        self.yesil.off()

        print("✅ Test completed!")

    def trafik_dongusu(self, tekrar=3):
        """Real traffic light cycle"""
        print(f"\n🚦 Traffic Light Simulation ({tekrar} cycles)")

        for i in range(tekrar):
            print(f"\nCycle {i+1}:")

            # Red
            print("🔴 STOP - Red")
            self.kirmizi.on()
            sleep(4)
            self.kirmizi.off()

            # Yellow
            print("🟡 GET READY - Yellow")
            self.sari.on()
            sleep(2)
            self.sari.off()

            # Green
            print("🟢 GO - Green")
            self.yesil.on()
            sleep(4)
            self.yesil.off()

            # Yellow again (after green)
            print("🟡 CAUTION - Yellow")
            self.sari.on()
            sleep(1)
            self.sari.off()

    def temizle(self):
        self.kirmizi.off()
        self.sari.off()
        self.yesil.off()
        self.kirmizi.close()
        self.sari.close()
        self.yesil.close()
        print("\n🧹 Cleanup completed")


# Main program
if __name__ == "__main__":
    lamba = TrafikLambasi()

    try:
        # Quick LED test first
        lamba.test_et()

        # Then run the traffic light simulation
        input("\nPress ENTER to start the traffic light simulation...")
        lamba.trafik_dongusu(3)

    except KeyboardInterrupt:
        print("\n⚠️ Program interrupted")

    finally:
        lamba.temizle()
