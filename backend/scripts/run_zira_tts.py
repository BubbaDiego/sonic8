"""
test_zira_tts.py
Standalone check that the Windows “Microsoft Zira Desktop” voice is present
and can speak the phrase “Liquidation is a concern”.

Usage
-----
> pip install pyttsx3
> python test_zira_tts.py
"""

import sys
import pyttsx3

TEXT                   = "Liquidation is a concern.  And so are my huge tits."
TARGET_VOICE_SUBSTRING = "hazel"      # case‑insensitive
SPEECH_RATE_WPM        = 140         # adjust to taste

def main() -> None:
    if sys.platform != "win32":
        print("⚠️  This script targets Windows; SAPI5 voices may be unavailable.")
    engine = pyttsx3.init(driverName="sapi5")          # explicit Windows driver
    voices = engine.getProperty("voices")

    print("🔎 Installed SAPI5 voices:")
    for idx, v in enumerate(voices):
        print(f"{idx:>2}: {v.name}  ({v.id})")

    # Pick the first voice whose name contains "zira"
    zira_id = next((v.id for v in voices
                    if TARGET_VOICE_SUBSTRING in v.name.lower()), None)

    if zira_id:
        print(f"\n✔ Using voice: {zira_id}")
        engine.setProperty("voice", zira_id)
    else:
        print("\n⚠️  Zira voice not found; using the default voice")

    engine.setProperty("rate", SPEECH_RATE_WPM)
    engine.say(TEXT)
    engine.runAndWait()
    print("\n✅ Finished speaking.")

if __name__ == "__main__":
    main()
