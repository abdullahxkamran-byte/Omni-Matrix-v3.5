import json
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_05_Story_Arc_Architect:
    def __init__(self):
        self.agent_name = "Ai_Agent_05_Story_Arc_Architect"
        self.required_arc_keys = [
            "retention_curve_type",
            "global_pacing_strategy",
            "acts"
        ]
        self.required_act_keys = [
            "act_name",
            "scene_ids_included",
            "act_purpose",
            "conflict_injection"
        ]

    def _validate_scene_coverage(self, acts: list, expected_scene_ids: set) -> bool:
        covered_scene_ids = set()
        for act in acts:
            if not isinstance(act.get("scene_ids_included"), list):
                print(f"[{self.agent_name}] Validation Failed: 'scene_ids_included' is not a list.", flush=True)
                return False
            for s_id in act["scene_ids_included"]:
                covered_scene_ids.add(s_id)
        
        missing_scenes = expected_scene_ids - covered_scene_ids
        hallucinated_scenes = covered_scene_ids - expected_scene_ids
        
        if missing_scenes:
            print(f"[{self.agent_name}] Validation Failed: Missing scenes in Acts -> {missing_scenes}", flush=True)
            return False
        if hallucinated_scenes:
            print(f"[{self.agent_name}] Validation Failed: AI hallucinated invalid scenes -> {hallucinated_scenes}", flush=True)
            return False
            
        return True

    def _validate_arc_deep(self, arc_data: dict, expected_scene_ids: set) -> bool:
        if not isinstance(arc_data, dict):
            return False

        for key in self.required_arc_keys:
            if key not in arc_data:
                print(f"[{self.agent_name}] Validation Failed: Missing root key '{key}'.", flush=True)
                return False

        acts = arc_data.get("acts", [])
        if not isinstance(acts, list) or len(acts) == 0:
            return False

        for act in acts:
            if not isinstance(act, dict):
                return False
            for key in self.required_act_keys:
                if key not in act:
                    print(f"[{self.agent_name}] Validation Failed: Missing act key '{key}'.", flush=True)
                    return False
                val = act[key]
                if isinstance(val, str) and len(val.strip()) == 0:
                    print(f"[{self.agent_name}] Validation Failed: Key '{key}' is empty.", flush=True)
                    return False

        return self._validate_scene_coverage(acts, expected_scene_ids)

    def execute(self, state: dict) -> dict:
        schema_version = state.get("schema_version", "3.0")
        if schema_version != "3.0":
             print(f"[{self.agent_name}] Warning: Schema version '{schema_version}' may not be fully compatible.", flush=True)

        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] CRITICAL: 'workspace_dir' missing in state.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_scripting = runtime_data.setdefault("module_a_scripting", {})

        if "agent_05_story_arc" in module_scripting:
            del module_scripting["agent_05_story_arc"]
            print(f"[{self.agent_name}] Idempotency sweep executed.", flush=True)

        script_scenes = module_scripting.get("agent_02_script", [])
        tension_data = module_scripting.get("agent_04_tension_analysis", [])

        if not script_scenes or not tension_data:
            raise ValueError(f"[{self.agent_name}] CRITICAL: Missing Script or Tension Analysis.")

        expected_scene_ids = {scene.get("scene_id") for scene in script_scenes if scene.get("scene_id")}
        
        script_json = json.dumps(script_scenes, indent=2)
        tension_json = json.dumps(tension_data, indent=2)
        project_id = state.get("project_id", "UNKNOWN_PROJECT")

        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "script_json": script_json,
            "tension_json": tension_json
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_05_story_arc.txt", variables)

        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Story Arc Architect. Return raw structured JSON.",
            temperature=0.6,
            required_keys=["agent_05_story_arc"],
            project_id=project_id
        )

        arc_data = response["data"]["agent_05_story_arc"]
        
        if not self._validate_arc_deep(arc_data, expected_scene_ids):
            raise ValueError(f"[{self.agent_name}] Deep Schema Validation Failed. Missing scenes or invalid structure.")

        module_scripting["agent_05_story_arc"] = arc_data
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"

        sm.save_state(state)

        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        curve_type = arc_data.get("retention_curve_type", "Unknown")
        print(f"[{self.agent_name}] INFO: Executed successfully! Mapped {len(expected_scene_ids)} scenes into {len(arc_data['acts'])} Acts using '{curve_type}'. (Time: {exec_time}s via {provider})", flush=True)

        return state
