import json
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_04_Narrative_Tension_Analyzer:
    def __init__(self):
        self.agent_name = "Ai_Agent_04_Narrative_Tension_Analyzer"
        self.required_tension_keys = [
            "scene_id",
            "tension_score",
            "emotional_beat",
            "viewer_retention_risk",
            "pacing_adjustment_recommendation"
        ]

    def _validate_tension_deep(self, tension_data: list, expected_scene_count: int) -> bool:
        """Deep validation for strict mapping and numerical bounds."""
        if not isinstance(tension_data, list):
            print(f"[{self.agent_name}] Validation Failed: Output is not a list.", flush=True)
            return False
            
        if len(tension_data) != expected_scene_count:
            print(f"[{self.agent_name}] Validation Failed: Expected {expected_scene_count} tension blocks, got {len(tension_data)}.", flush=True)
            return False

        valid_risks = ["High", "Medium", "Low"]

        for beat in tension_data:
            if not isinstance(beat, dict):
                return False
            for key in self.required_tension_keys:
                if key not in beat:
                    print(f"[{self.agent_name}] Validation Failed: Missing key '{key}'.", flush=True)
                    return False
                
                val = beat[key]
                
                # Check integer boundary for tension score
                if key == "tension_score":
                    if not isinstance(val, int) or val < 1 or val > 10:
                        print(f"[{self.agent_name}] Validation Failed: tension_score '{val}' must be an integer between 1 and 10.", flush=True)
                        return False
                        
                # Check strict strings for retention risk
                if key == "viewer_retention_risk":
                    if val not in valid_risks:
                        print(f"[{self.agent_name}] Validation Failed: Invalid retention risk '{val}'.", flush=True)
                        return False

                if isinstance(val, str) and len(val.strip()) == 0:
                    print(f"[{self.agent_name}] Validation Failed: Key '{key}' is empty.", flush=True)
                    return False
        return True

    def execute(self, state: dict) -> dict:
        schema_version = state.get("schema_version", "3.0")
        if schema_version != "3.0":
             print(f"[{self.agent_name}] Warning: State schema version '{schema_version}' may not be fully compatible.", flush=True)

        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing in state.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_scripting = runtime_data.setdefault("module_a_scripting", {})

        # Idempotency Scrubbing
        if "agent_04_tension_analysis" in module_scripting:
            del module_scripting["agent_04_tension_analysis"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        # Retrieve Dependencies (Agent 02 & Agent 03)
        script_scenes = module_scripting.get("agent_02_script", [])
        storyboard_panels = module_scripting.get("agent_03_storyboard", [])

        if not script_scenes or not storyboard_panels:
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing Script or Storyboard. Agents 02 and 03 must run first.")

        if len(script_scenes) != len(storyboard_panels):
             raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Pipeline corruption. Script count ({len(script_scenes)}) and Storyboard count ({len(storyboard_panels)}) mismatch.")

        expected_scene_count = len(script_scenes)
        script_json = json.dumps(script_scenes, indent=2)
        storyboard_json = json.dumps(storyboard_panels, indent=2)
        project_id = state.get("project_id", "UNKNOWN_PROJECT")

        # Load Prompt
        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "script_json": script_json,
            "storyboard_json": storyboard_json
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_04_tension.txt", variables)

        # AI Generation via Central Gateway (Lower Temperature for Analytical Consistency)
        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Narrative Tension Analyzer. Generate raw structured JSON only.",
            temperature=0.4, 
            required_keys=["agent_04_tension_analysis"],
            project_id=project_id
        )

        tension_data = response["data"]["agent_04_tension_analysis"]
        
        # Deep Schema & Boundary Validation
        if not self._validate_tension_deep(tension_data, expected_scene_count):
            raise ValueError(f"[{self.agent_name}] [AG003] Deep Schema Validation Failed. Score bounds or count mismatch.")

        # Update State Memory
        module_scripting["agent_04_tension_analysis"] = tension_data
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        # Atomic Safe Save
        sm.save_state(state)

        # Log Execution
        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        avg_tension = round(sum(b["tension_score"] for b in tension_data) / len(tension_data), 1)
        
        print(f"[{self.agent_name}] INFO: Executed successfully! Analyzed {len(tension_data)} scenes. Avg Tension: {avg_tension}/10 (Time: {exec_time}s via {provider})", flush=True)

        return state
