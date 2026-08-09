import os
import json
import subprocess
from typing import Tuple


class Base_TTS_Adapter:
    def __init__(self):
        self.provider_name = "BASE"

    def get_capabilities(self) -> dict:
        raise NotImplementedError(
            "Adapters must define their capabilities."
        )

    def validate_config(self) -> bool:
        raise NotImplementedError(
            "Adapters must validate their API keys/config."
        )

    def generate(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        performance_data: dict
    ) -> Tuple[float, dict]:
        raise NotImplementedError(
            "Adapters must implement the generate method."
        )

    def _probe_audio(self, file_path: str) -> dict:
        if not file_path or not os.path.isfile(file_path):
            return {
                "valid": False,
                "duration": 0.0,
                "format": "",
                "codec": "",
                "sample_rate": 0,
                "channels": 0
            }

        try:
            if os.path.getsize(file_path) <= 0:
                return {
                    "valid": False,
                    "duration": 0.0,
                    "format": "",
                    "codec": "",
                    "sample_rate": 0,
                    "channels": 0
                }

            command = [
                "ffprobe",
                "-v", "error",
                "-show_entries", "format=format_name,duration",
                "-show_entries", "stream=codec_name,sample_rate,channels",
                "-of", "json",
                file_path
            ]

            result = subprocess.run(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=15,
                check=False
            )

            if result.returncode != 0:
                return {
                    "valid": False,
                    "duration": 0.0,
                    "format": "",
                    "codec": "",
                    "sample_rate": 0,
                    "channels": 0
                }

            data = json.loads(result.stdout)
            format_data = data.get("format", {})
            streams = data.get("streams", [])

            audio_stream = None

            for stream in streams:
                if isinstance(stream, dict) and stream.get("codec_name"):
                    audio_stream = stream
                    break

            if audio_stream is None:
                return {
                    "valid": False,
                    "duration": 0.0,
                    "format": format_data.get("format_name", ""),
                    "codec": "",
                    "sample_rate": 0,
                    "channels": 0
                }

            try:
                duration = float(format_data.get("duration", 0))
            except (TypeError, ValueError):
                duration = 0.0

            try:
                sample_rate = int(
                    audio_stream.get("sample_rate", 0)
                )
            except (TypeError, ValueError):
                sample_rate = 0

            try:
                channels = int(
                    audio_stream.get("channels", 0)
                )
            except (TypeError, ValueError):
                channels = 0

            audio_format = format_data.get("format_name", "")
            codec = audio_stream.get("codec_name", "")

            valid = (
                duration > 0.0
                and bool(codec)
                and sample_rate > 0
                and channels > 0
            )

            return {
                "valid": valid,
                "duration": round(duration, 3),
                "format": audio_format,
                "codec": codec,
                "sample_rate": sample_rate,
                "channels": channels
            }

        except (
            FileNotFoundError,
            subprocess.TimeoutExpired,
            subprocess.SubprocessError,
            json.JSONDecodeError,
            OSError,
            ValueError
        ):
            return {
                "valid": False,
                "duration": 0.0,
                "format": "",
                "codec": "",
                "sample_rate": 0,
                "channels": 0
            }

    def get_actual_duration(self, file_path: str) -> float:
        probe = self._probe_audio(file_path)

        if not probe["valid"]:
            return 0.0

        return probe["duration"]

    def validate_audio_file(self, file_path: str) -> bool:
        probe = self._probe_audio(file_path)

        if not probe["valid"]:
            return False

        if probe["duration"] <= 0.0:
            return False

        if not probe["codec"]:
            return False

        if probe["sample_rate"] <= 0:
            return False

        if probe["channels"] <= 0:
            return False

        return True

    def get_audio_metadata(self, file_path: str) -> dict:
        probe = self._probe_audio(file_path)

        return {
            "valid": probe["valid"],
            "duration_sec": probe["duration"],
            "format": probe["format"],
            "codec": probe["codec"],
            "sample_rate_hz": probe["sample_rate"],
            "channels": probe["channels"]
        }