import os
import wave

class Base_TTS_Adapter:
    def __init__(self):
        self.provider_name = "BASE"

    def get_capabilities(self) -> dict:
        raise NotImplementedError("Adapters must define their capabilities.")

    def validate_config(self) -> bool:
        raise NotImplementedError("Adapters must validate their API keys/config.")

    def get_actual_duration(self, file_path: str) -> float:
        if not os.path.exists(file_path):
            return 0.0
        try:
            with wave.open(file_path, 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                duration = frames / float(rate)
                return round(duration, 2)
        except Exception:
            return 0.0

    def validate_audio_file(self, file_path: str) -> bool:
        if not os.path.exists(file_path):
            return False
        if os.path.getsize(file_path) == 0:
            return False
        if self.get_actual_duration(file_path) <= 0.0:
            return False
        return True

    def generate(self, text: str, voice_id: str, output_path: str, performance_data: dict) -> tuple:
        raise NotImplementedError("Adapters must implement the generate method.")
