import os
import json
import requests
import time

class Voice_Research_Gateway:
    def __init__(self):
        self.primary_model = "gemini-pro-latest"
        self.api_key = os.environ.get("GEMINI_API_KEY", "")
        if not self.api_key:
            raise ValueError("[LLM001] CRITICAL: GEMINI_API_KEY environment variable is missing.")
        
        self.endpoint = f"https://generativelanguage.googleapis.com/v1beta/models/{self.primary_model}:generateContent?key={self.api_key}"

    def _clean_json_response(self, text: str) -> str:
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def generate_research(self, prompt: str, system_prompt: str, required_keys: list, project_id: str) -> dict:
        start_time = time.time()
        
        payload = {
            "contents": [
                {"role": "user", "parts": [{"text": prompt}]}
            ],
            "systemInstruction": {
                "parts": [{"text": system_prompt}]
            },
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json"
            },
            "tools": [
                {"googleSearch": {}}
            ]
        }

        headers = {"Content-Type": "application/json"}
        response = requests.post(self.endpoint, headers=headers, json=payload, timeout=45)

        if response.status_code != 200:
            raise RuntimeError(f"[LLM004] Voice Research Gateway failed: {response.text}")

        response_json = response.json()
        
        try:
            raw_text = response_json["candidates"][0]["content"]["parts"][0]["text"]
            clean_text = self._clean_json_response(raw_text)
            parsed_data = json.loads(clean_text)
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            raise ValueError(f"[LLM003] JSON Parsing Failed from Voice Research LLM: {str(e)}")

        for key in required_keys:
            if key not in parsed_data:
                raise ValueError(f"[LLM003] Missing required key in research response: {key}")

        execution_time = round(time.time() - start_time, 2)

        return {
            "data": parsed_data,
            "metrics": {
                "provider": "Gemini 1.5 Pro (Search Enabled)",
                "execution_time_sec": execution_time,
                "project_id": project_id
            }
        }
