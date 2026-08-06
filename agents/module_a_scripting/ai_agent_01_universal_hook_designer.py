import os
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager

class Ai_Agent_01_Universal_Hook_Designer:
    def __init__(self):
        self.agent_name = "Ai_Agent_01_Universal_Hook_Designer"
        self.expected_hook_count = 3
        self.required_hook_keys = [
            "hook_id", "hook_approach", "visual_camera_action",
            "foley_sfx_audio", "verbal_text_overlay",
            "retention_psychology_trigger", "pacing_tempo"
        ]

    def _validate_hooks_deep(self, hooks: list) -> bool:
        if not isinstance(hooks, list) or len(hooks) != self.expected_hook_count:
            return False
        for hook in hooks:
            if not isinstance(hook, dict):
                return False
            for key in self.required_hook_keys:
                if key not in hook:
                    return False
        return True

    def execute(self, state: dict) -> dict:
        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] CRITICAL: 'workspace_dir' missing in state.")

        sm = State_Manager(workspace_dir)

        runtime_data = state.setdefault("runtime_data", {})
        module_scripting = runtime_data.setdefault("module_a_scripting", {})

        if "agent_01_hooks" in module_scripting:
            del module_scripting["agent_01_hooks"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        core_topic = runtime_data.get("core_topic", state.get("user_prompt", ""))
        if not core_topic:
            raise ValueError(f"[{self.agent_name}] CRITICAL ERROR: 'core_topic' missing in state.")

        global_config = state.get("global_config", {})
        medium = global_config.get("medium", "Dynamic/Unbound")
        rendering_engine = global_config.get("rendering_engine", "Dynamic/Unbound")
        color_lighting = global_config.get("color_lighting", "Dynamic/Unbound")
        kinetic_framing = global_config.get("kinetic_framing", "Dynamic/Unbound")
        master_theme = runtime_data.get("master_theme_blueprint", f"{medium} - {rendering_engine}")
        project_id = state.get("project_id", "UNKNOWN_PROJECT")

        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        prompt_path = os.path.join(prompts_dir, "agent_01_hook.txt")
        
        if not os.path.exists(prompt_path):
            raise FileNotFoundError(f"[{self.agent_name}] Prompt file missing -> {prompt_path}")

        with open(prompt_path, 'r', encoding='utf-8') as f:
            prompt_template = f.read()

        prompt = prompt_template.format(
            core_topic=core_topic,
            master_theme=master_theme,
            medium=medium,
            rendering_engine=rendering_engine,
            color_lighting=color_lighting,
            kinetic_framing=kinetic_framing
        )

        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Universal Hook Designer. Return strict JSON.",
            temperature=0.8,
            required_keys=["agent_01_hooks"],
            project_id=project_id
        )

        hooks = response["data"]["agent_01_hooks"]
        if not self._validate_hooks_deep(hooks):
             raise ValueError(f"[{self.agent_name}] Deep Schema Validation Failed for inner hook fields.")

        module_scripting["agent_01_hooks"] = hooks
        
        auto_select = global_config.get("auto_select_hook", False)
        
        if auto_select:
            print(f"[{self.agent_name}] Auto-select mode ON. Defaulting to Hook 0.", flush=True)
            selected_index = 0
        else:
            print("\n" + "="*70)
            print("GENERATED HOOKS - PLEASE SELECT ONE TO CONTINUE:")
            print("="*70)
            for idx, hook in enumerate(hooks):
                print(f"\n[HOOK {idx}] - {hook.get('hook_approach', 'Unknown Approach')}")
                print(f"  Visual: {hook.get('visual_camera_action', 'N/A')}")
                print(f"  Text/Voice: {hook.get('verbal_text_overlay', 'N/A')}")
            print("-" * 70)
            
            while True:
                try:
                    choice = input(f"\nSelect Hook Index (0, 1, or 2) [Press Enter for 0]: ").strip()
                    if not choice:
                        print("No input detected. Defaulting to Hook 0.")
                        selected_index = 0
                        break
                    selected_index = int(choice)
                    if 0 <= selected_index < len(hooks):
                        break
                    else:
                        print(f"Invalid choice. Please enter a number between 0 and {len(hooks)-1}.")
                except ValueError:
                    print("Invalid input. Please enter a valid number.")
                    
        module_scripting["selected_hook_index"] = selected_index

        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)
        
        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        print(f"[{self.agent_name}] Executed successfully! {self.expected_hook_count} Hooks generated. Selected Hook: {selected_index} (Time: {exec_time}s via {provider})", flush=True)
        
        return state
