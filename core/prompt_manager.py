import os

class Prompt_Manager:
    _prompt_cache = {}

    @classmethod
    def load(cls, prompts_dir: str, file_name: str, variables: dict = None) -> str:
        if not prompts_dir:
            raise ValueError("[PRM003] Prompts directory path is empty.")
            
        if ".." in file_name or os.path.isabs(file_name):
            raise ValueError(f"[PRM005] Security Risk: Invalid prompt file path detected -> {file_name}")

        prompt_path = os.path.join(prompts_dir, file_name)
        
        if prompt_path in cls._prompt_cache:
            template = cls._prompt_cache[prompt_path]
        else:
            if not os.path.exists(prompt_path):
                raise FileNotFoundError(f"[PRM001] Prompt file missing: {prompt_path}")
            
            with open(prompt_path, 'r', encoding='utf-8') as f:
                template = f.read()
                
            if not template.strip():
                raise ValueError(f"[PRM004] Prompt file is empty: {file_name}")
                
            cls._prompt_cache[prompt_path] = template
            
        if variables:
            try:
                return template.format(**variables)
            except KeyError as e:
                raise KeyError(f"[PRM002] Missing format variable {e} in prompt: {file_name}")
                
        return template
