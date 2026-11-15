
import re
import os
import wave
import winsound
import tempfile
import threading
import pyttsx3

from pathlib import Path
from piper import PiperVoice, SynthesisConfig


class ELOVoice:
    def __init__(self):
        self.lock = threading.Lock()
        self.piper_voice = None
        self.model_path = self.find_model()

    def find_model(self):
        current = Path(__file__).resolve()

        for parent in current.parents:
            model = (
                parent
                / "models"
                / "voices"
                / "en_US-amy-medium.onnx"
            )

            if model.exists():
                return model

        print("ELO Voice: Piper model not found!")
        return None

    def clean_text(self, text):
        text = str(text)

        # Pronounce ELO naturally
        text = re.sub(
            r"\bE[\s.-]*L[\s.-]*O\b",
            "Eh-low",
            text,
            flags=re.IGNORECASE
        )

        # Remove emojis and unsupported symbols
        text = re.sub(
            r"""[^\w\s.,!?;:'"()-]""",
            " ",
            text,
            flags=re.UNICODE
        )

        return re.sub(r"\s+", " ", text).strip()

    def load_piper(self):
        if self.piper_voice is None:
            if not self.model_path:
                raise FileNotFoundError(
                    "Piper Amy model not found!"
                )

            self.piper_voice = PiperVoice.load(
                str(self.model_path)
            )

            print("ELO Voice: Piper Amy loaded!")

        return self.piper_voice

    def speak_piper(self, text):
        voice = self.load_piper()
        temp_file = None

        syn_config = SynthesisConfig(
            length_scale=0.85,
            volume=1.0
        )

        try:
            with tempfile.NamedTemporaryFile(
                suffix=".wav",
                delete=False
            ) as temp:
                temp_file = temp.name

            with wave.open(temp_file, "wb") as wav_file:
                voice.synthesize_wav(
                    text,
                    wav_file,
                    syn_config=syn_config
                )

            winsound.PlaySound(
                temp_file,
                winsound.SND_FILENAME
            )

        finally:
            if temp_file and os.path.exists(temp_file):
                os.remove(temp_file)

    def speak_zira(self, text):
        engine = None

        try:
            engine = pyttsx3.init("sapi5")
            voices = engine.getProperty("voices")

            female_voice = next(
                (
                    voice for voice in voices
                    if "zira" in voice.name.lower()
                ),
                None
            )

            if female_voice:
                engine.setProperty(
                    "voice",
                    female_voice.id
                )

            engine.setProperty("rate", 165)
            engine.setProperty("volume", 1.0)

            engine.say(text)
            engine.runAndWait()

        finally:
            if engine:
                engine.stop()

    def speak(self, text):
        if not text:
            return

        clean_text = self.clean_text(text)

        if not clean_text:
            return

        def run():
            with self.lock:
                try:
                    self.speak_piper(clean_text)

                except Exception as e:
                    print(f"Piper Error: {e}")
                    print(
                        "ELO Voice: Switching to Microsoft Zira..."
                    )

                    try:
                        self.speak_zira(clean_text)

                    except Exception as fallback_error:
                        print(
                            f"Zira Voice Error: {fallback_error}"
                        )

        threading.Thread(
            target=run,
            daemon=True
        ).start()


elo_voice = ELOVoice()
