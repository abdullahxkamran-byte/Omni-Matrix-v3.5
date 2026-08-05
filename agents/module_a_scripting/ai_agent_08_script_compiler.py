import json
from core.llm_gateway import LLM_Gateway
from core.state_manager import State_Manager
from core.prompt_manager import Prompt_Manager

class Ai_Agent_08_Script_Compiler:
    def __init__(self):
        self.agent_name = "Ai_Agent_08_Script_Compiler"
        self.required_blueprint_keys = [
            "project_metadata",
            "editorial_audit",
            "master_scenes"
        ]

    def _validate_blueprint_deep(self, blueprint: dict, expected_scene_count: int) -> bool:
        if not isinstance(blueprint, dict):
            return False

        for key in self.required_blueprint_keys:
            if key not in blueprint:
                print(f"[{self.agent_name}] Validation Failed: Missing root key '{key}'.", flush=True)
                return False

        audit = blueprint.get("editorial_audit", {})
        if not isinstance(audit, dict) or "cohesion_score" not in audit:
            return False
            
        score = audit["cohesion_score"]
        if not isinstance(score, int) or score < 1 or score > 100:
            print(f"[{self.agent_name}] Validation Failed: Cohesion score '{score}' out of bounds.", flush=True)
            return False

        scenes = blueprint.get("master_scenes", [])
        if not isinstance(scenes, list):
            return False
            
        if len(scenes) != expected_scene_count:
            print(f"[{self.agent_name}] Validation Failed: Zipping Error. Expected {expected_scene_count} master scenes, got {len(scenes)}.", flush=True)
            return False

        for scene in scenes:
            if not isinstance(scene, dict) or "scene_id" not in scene:
                return False
            if "narration_block" not in scene or "visual_block" not in scene or "audio_block" not in scene:
                print(f"[{self.agent_name}] Validation Failed: Master scene {scene.get('scene_id')} is missing critical blocks.", flush=True)
                return False

        return True

    def execute(self, state: dict) -> dict:
        schema_version = state.get("schema_version", "3.0")
        if schema_version != "3.0":
            print(f"[{self.agent_name}] Warning: Schema mismatch.", flush=True)

        workspace_dir = state.get("workspace_dir", "")
        if not workspace_dir:
            raise ValueError(f"[{self.agent_name}] [AG001] CRITICAL: 'workspace_dir' missing.")

        sm = State_Manager(workspace_dir)
        runtime_data = state.setdefault("runtime_data", {})
        module_scripting = runtime_data.setdefault("module_a_scripting", {})

        if "agent_08_master_blueprint" in module_scripting:
            del module_scripting["agent_08_master_blueprint"]

        # Fetch all previous fragments
        script_scenes = module_scripting.get("agent_02_script", [])
        storyboard_panels = module_scripting.get("agent_03_storyboard", [])
        tension_data = module_scripting.get("agent_04_tension_analysis", [])
        arc_data = module_scripting.get("agent_05_story_arc", {})
        word_guard_data = module_scripting.get("agent_06_word_guard", [])
        vibe_data = module_scripting.get("agent_07_vibe", {})

        if not (script_scenes and storyboard_panels and tension_data and word_guard_data and vibe_data):
            raise ValueError(f"[{self.agent_name}] [AG002] CRITICAL: Missing upstream fragments. Agents 02-07 must complete first.")

        expected_scene_count = len(script_scenes)
        project_id = state.get("project_id", "UNKNOWN_PROJECT")

        global_config = state.get("global_config", {})
        medium = global_config.get("medium", "Dynamic/Unbound")
        rendering_engine = global_config.get("rendering_engine", "Dynamic/Unbound")
        color_lighting = global_config.get("color_lighting", "Dynamic/Unbound")
        kinetic_framing = global_config.get("kinetic_framing", "Dynamic/Unbound")

        prompts_dir = state.get("paths", {}).get("prompts_dir", "prompts")
        variables = {
            "medium": medium,
            "rendering_engine": rendering_engine,
            "color_lighting": color_lighting,
            "kinetic_framing": kinetic_framing,
            "vibe_json": json.dumps(vibe_data, indent=2),
            "arc_json": json.dumps(arc_data, indent=2),
            "script_json": json.dumps(script_scenes, indent=2),
            "storyboard_json": json.dumps(storyboard_panels, indent=2),
            "tension_json": json.dumps(tension_data, indent=2),
            "word_guard_json": json.dumps(word_guard_data, indent=2)
        }
        
        prompt = Prompt_Manager.load(prompts_dir, "agent_08_compiler.txt", variables)

        # High Temperature for Editorial Synthesis
        gateway = LLM_Gateway()
        response = gateway.generate(
            prompt=prompt,
            system_prompt="You are the OmniMatrix Chief Script Compiler. Output strictly valid JSON.",
            temperature=0.3,
            required_keys=["agent_08_master_blueprint"],
            project_id=project_id
        )

        blueprint = response["data"]["agent_08_master_blueprint"]
        
        if not self._validate_blueprint_deep(blueprint, expected_scene_count):
            raise ValueError(f"[{self.agent_name}] [AG003] Validation Failed: Zipped payload corruption detected.")

        module_scripting["agent_08_master_blueprint"] = blueprint
        state.setdefault("metrics", {})[self.agent_name] = response["metrics"]

        # USER REQUESTED LOGIC: Orchestrator Handoff Protocol
        pipeline_status = state.setdefault("pipeline_status", {})
        pipeline_status["last_active_agent"] = self.agent_name
        pipeline_status[self.agent_name] = "COMPLETED"
        pipeline_status["module_a_status"] = "FULLY_COMPILED"
        pipeline_status["ready_for_orchestrator"] = True  # The magic key for universal routing!

        sm.save_state(state)

        exec_time = response["metrics"]["execution_time_sec"]
        provider = response["metrics"]["provider"]
        score = blueprint.get("editorial_audit", {}).get("cohesion_score", 0)
        
        print(f"[{self.agent_name}] INFO: Module A Compilation Complete! Cohesion Score: {score}/100. Payload ready for Orchestrator. (Time: {exec_time}s via {provider})", flush=True)

        return state
