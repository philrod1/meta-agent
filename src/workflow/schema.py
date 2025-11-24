from typing import List, Optional, Dict, Any, Tuple
from pydantic import BaseModel, Field, ValidationError


# Unused at the moment
class Guard(BaseModel):
    condition: str
    action: Optional[Dict[str, Any]] = None
    decomposition: Optional[Dict[str, Any]] = None  # loose for now


class NodeSpec(BaseModel):
    id: str
    type: str
    params: Dict[str, Any] = Field(default_factory=dict)
    inputs: Optional[Dict[str, Any]] = None
    outputs: Optional[Dict[str, Any]] = None
    tests: Optional[List[str]] = None
    description: Optional[str] = None
    io: Optional[Dict[str, Any]] = None


class EdgeSpec(BaseModel):
    src: str = Field(alias="from")
    dest: str = Field(alias="to")
    when: str = "true"
    class Config:
        allow_population_by_field_name = True


class WorkflowSpec(BaseModel):
    name: str
    description: Optional[str] = None

    version: Optional[int] = None

    inputs: Optional[List[str]] = None
    outputs: Optional[List[str]] = None
    combiner: Optional[Dict[str, Any]] = None
    verifier: Optional[Dict[str, Any]] = None
    tests: Optional[List[str]] = None
    notes: Optional[List[str]] = None

    preconditions: Optional[List[str]] = None
    success_criteria: Optional[List[str]] = None
    failure_conditions: Optional[List[str]] = None

    nodes: List[NodeSpec] = Field(default_factory=list)
    edges: List[EdgeSpec] = Field(default_factory=list)

    class Config:
        extra = "forbid"  # Unexpected keys in the YAML (we might want to allow this)


def _model_to_dict(model: BaseModel) -> Dict[str, Any]:
    # support for both pydantic v2 and v1
    if hasattr(model, "model_dump"):   # v2
        return model.model_dump()
    return model.dict()                # v1


def validate_workflow(raw: Dict[str, Any]) -> Tuple[WorkflowSpec, Dict[str, Any]]:
    """Validate a raw YAML dict against WorkflowSpec."""
    try:
        if hasattr(WorkflowSpec, "model_validate"):     # v2
            spec = WorkflowSpec.model_validate(raw)
        else:                                           # v1
            spec = WorkflowSpec.parse_obj(raw)
        return spec, _model_to_dict(spec)
    except ValidationError as e:
        raise ValueError(f"YAML validation error: {e}")
    