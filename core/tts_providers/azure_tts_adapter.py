import os
import requests
from core.tts_providers.base_tts_adapter import Base_TTS_Adapter

class Azure_TTS_Adapter(Base_TTS_Adapter):
    def __init__(self):
        super().__init__()
        self.provider_name = "Azure_TTS"
        self.api_key = os.environ.get("AZURE_TTS_API_KEY", "")
        self.region = os.environ.get("AZURE_TTS_REGION", "")

    def get_capabilities(self) -> dict:
        return {
            "languages": ["dynamic_registry"],
            "emotion_support": True,
            "speaking_rate_support": True, 
            "ssml_support": True,
            "supported_formats": ["Riff16Khz16BitMonoPcm"]
        }

    def validate_config(self) -> bool:
        return bool(self.api_key and self.region)

    def _construct_ssml(self, text: str, registry_entry: dict, performance_data: dict) -> str:
        voice_id = registry_entry.get("voice_id", "")
        language = registry_entry.get("language", "en-US")
        provider_model = registry_entry.get("provider_model", "").lower()
        voice_characteristics = registry_entry.get("voice_characteristics", [])
        
        style = "general"
        emotion = performance_data.get("line_emotion", {}).get("primary", "").lower()
        
        if emotion and emotion in [c.lower() for c in voice_characteristics]:
            style = emotion
        elif "hd" in provider_model or "omni" in provider_model:
            style = emotion if emotion else "general"
            
        return f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='{language}'>
            <voice name='{voice_id}'>
                <mstts:express-as style='{style}'>
                    {text}
                </mstts:express-as>
            </voice>
        </speak>
        """

    def generate(self, text: str, registry_entry: dict, output_path: str, performance_data: dict) -> tuple:
        if not self.validate_config():
            raise ValueError(f"[{self.provider_name}] Config missing (Key or Region).")

        url = f"https://{self.region}.tts.speech.microsoft.com/cognitiveservices/v1"
        headers = {
            "Ocp-Apim-Subscription-Key": self.api_key,
            "Content-Type": "application/ssml+xml",
            "X-Microsoft-OutputFormat": "riff-16khz-16bit-mono-pcm",
            "User-Agent": "OmniMatrix/1.0"
        }

        ssml_payload = self._construct_ssml(text, registry_entry, performance_data)

        response = requests.post(url, headers=headers, data=ssml_payload.encode('utf-8'), timeout=20)
        
        if response.status_code in [401, 403]:
            raise PermissionError(f"[{self.provider_name}] Authentication failed.")
        elif response.status_code != 200:
            raise RuntimeError(f"[{self.provider_name}] API Error: {response.text}")

        with open(output_path, 'wb') as f:
            f.write(response.content)

        if not self.validate_audio_file(output_path):
            raise RuntimeError(f"[{self.provider_name}] Generated audio is invalid.")

        actual_duration = self.get_actual_duration(output_path)
        
        metadata = {
            "ssml_used": True,
            "express_as_style_mapped": True,
            "format": "riff-16khz-16bit-mono-pcm"
        }

        return actual_duration, metadata
