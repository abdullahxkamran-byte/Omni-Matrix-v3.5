import os
import re
import json
import time
import urllib.request
import urllib.error

class LLM_Gateway:
    def __init__(self):
        self.keys = {
            "gemini": os.getenv("GEMINI_API_KEY", ""),
            "openai": os.getenv("OPENAI_API_KEY", "")
        }
        self.max_retries = 3
        self.retry_delay = 2

    def _clean_json(self, raw_text: str) -> dict:
        cleaned = raw_text.strip()
        cleaned = re.sub(r"^```json\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"^```\s*", "", cleaned, flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        start_idx = cleaned.find('{')
        end_idx = cleaned.rfind('}')
        if start_idx != -1 and end_idx != -1:
            cleaned = cleaned[start_idx:end_idx + 1]
        return json.loads(cleaned)

    def _call_gemini(self, prompt: str, system_prompt: str, model: str, temperature: float, timeout: int) -> dict:
        if not self.keys["gemini"]:
            raise ValueError("[LLM001] GEMINI_API_KEY missing in environment.")
        
        url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-flash-latest:generateContent"
        headers = {
            "Content-Type": "application/json",
            "X-goog-api-key": self.keys["gemini"]
        }
        
        full_prompt = f"SYSTEM DIRECTIVE:\n{system_prompt}\n\nUSER PROMPT:\n{prompt}"
        payload = {
            "contents": [{"parts": [{"text": full_prompt}]}],
            "generationConfig": {
                "response_mime_type": "application/json",
                "temperature": temperature
            }
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                text_content = res_json['candidates'][0]['content']['parts'][0]['text']
                return self._clean_json(text_content)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"[LLM004] Gemini HTTP Error {e.code}: {e.reason}")

    def _call_openai(self, prompt: str, system_prompt: str, model: str, temperature: float, timeout: int) -> dict:
        if not self.keys["openai"]:
            raise ValueError("[LLM001] OPENAI_API_KEY missing in environment.")
        
        url = "https://api.openai.com/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.keys['openai']}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"},
            "temperature": temperature
        }

        data_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(url, data=data_bytes, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                res_body = response.read().decode("utf-8")
                res_json = json.loads(res_body)
                text_content = res_json["choices"][0]["message"]["content"]
                return self._clean_json(text_content)
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"[LLM004] OpenAI HTTP Error {e.code}: {e.reason}")

    def generate(self, prompt: str, system_prompt: str = "Output valid JSON.", 
                 provider_chain: list = None, temperature: float = 0.3, timeout: int = 60,
                 required_keys: list = None, project_id: str = "UNKNOWN_PROJECT") -> dict:
        
        if provider_chain is None:
            provider_chain = [
                {"provider": "gemini", "model": "gemini-flash-latest"},
                {"provider": "openai", "model": "gpt-4o-mini"}
            ]

        start_time = time.time()
        last_error = ""

        for config in provider_chain:
            provider = config.get("provider", "").lower()
            model = config.get("model", "")

            for attempt in range(1, self.max_retries + 1):
                try:
                    print(f"[LLM_Gateway] Routing: {provider.upper()} | Model: {model} | Temp: {temperature} | Attempt: {attempt}/{self.max_retries}", flush=True)
                    
                    if provider == "gemini":
                        data = self._call_gemini(prompt, system_prompt, model, temperature, timeout)
                    elif provider == "openai":
                        data = self._call_openai(prompt, system_prompt, model, temperature, timeout)
                    else:
                        raise ValueError(f"[LLM005] Unknown provider requested: {provider}")

                    if required_keys:
                        missing_keys = [k for k in required_keys if k not in data]
                        if missing_keys:
                            raise ValueError(f"[LLM003] Strict Validation Failed. Missing Schema Keys: {missing_keys}")

                    return {
                        "data": data,
                        "metrics": {
                            "project_id": project_id,
                            "provider": provider.upper(),
                            "model": model,
                            "execution_time_sec": round(time.time() - start_time, 2),
                            "retry_count": attempt
                        }
                    }

                except Exception as e:
                    last_error = str(e)
                    print(f"[LLM_Gateway] Error: {last_error}", flush=True)
                    if "LLM001" in last_error:
                        break  
                    if attempt < self.max_retries:
                        time.sleep(self.retry_delay)

        raise RuntimeError(f"[LLM002] SYSTEM HALT: All Nodes in Provider Chain Exhausted. Traceback: {last_error}")
