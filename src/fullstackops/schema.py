from typing import Literal
from datetime import datetime, timezone
from pydantic import BaseModel, ConfigDict, Field, model_validator
class Strict(BaseModel): model_config=ConfigDict(extra="forbid", strict=True)
class File(Strict):
    path: str
    content: str
class Action(Strict):
    step_number: int
    tool_name: str
    tool_arguments: str
    observed_output: str
    exit_code: int
    action_result: str
    next_action: str
class TestResult(Strict):
    phase: Literal["baseline","fault","fixed","syntax"]
    command: str
    exit_code: int
    output: str
    verification_kind: Literal["static_policy","syntax","trusted_python"]
class Provenance(Strict):
    source_url: str
    repository_identifier: str
    commit_revision: str
    file_path: str
    attribution: str
    collected_at: str
    redistribution_allowed: bool
    provenance_category: str
    template_id: str
    mutation_id: str
    source_family: str
    lineage: str
class Record(Strict):
    record_id: str
    schema_version: Literal["1.0"] = "1.0"
    task_category: str
    task_subcategory: str
    programming_language: str
    framework: str
    difficulty: Literal["easy","medium","hard"]
    instruction: str
    environment: dict[str,str]
    repository_context: str
    input_files: list[File]
    observations: list[str]
    error_logs: list[str]
    agent_actions: list[Action]
    expected_behavior: str
    generated_patch: list[File]
    test_commands: list[str]
    test_results: list[TestResult]
    verification_status: Literal["static_validated","synthetic_unverified","syntax_validated","runtime_verified"]
    quality_state: Literal["RAW","NORMALIZED","SYNTHETIC_UNVERIFIED","VALIDATION_FAILED","VALIDATED","REVIEWED"]
    quality_score: float = Field(ge=0,le=1)
    source_type: Literal["original_synthetic","reviewed_local"]
    source_license: str
    source_reference: str
    source_commit: str
    provenance: Provenance
    created_at: str
    content_hash: str
    record_split: Literal["train","validation","test","heldout"]
    @model_validator(mode="after")
    def honest(self):
        if not self.provenance.redistribution_allowed: raise ValueError("permission missing")
        if self.source_type == "original_synthetic" and self.verification_status in ("static_validated","runtime_verified"):
            phases={r.phase:r.exit_code for r in self.test_results}
            if phases.get("baseline")!=0 or phases.get("fault",0)==0 or phases.get("fixed")!=0:
                raise ValueError("baseline/fault/fix evidence incomplete")
        if [a.step_number for a in self.agent_actions] != list(range(1,len(self.agent_actions)+1)):
            raise ValueError("nonsequential trajectory")
        return self

def now(): return datetime.now(timezone.utc).isoformat()
