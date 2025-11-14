"""
llm_api.py — stubbed LLM calls for the meta-agent pipeline.

Pipeline:
Human Spec (free text)
    ->  (LLM interpretation)            interpret_human_spec_to_intermediate()
Intermediate Spec (structured)
    ->  (LLM YAML generation)           generate_yaml_from_intermediate()
YAML Workflow (validated)
    ->  (Meta-agent compilation)        (handled elsewhere)
Executable DAG + Tests
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict
import re


# -------------------------
# RESULT CONTAINERS
# -------------------------

@dataclass
class IntermediateSpecResult:
    """ Structured, human-readable summary produced from human spec """
    content_md: str
    clarifications: List[str]


@dataclass
class YAMLGenerationResult:
    """ YAML text and any notes/warnings from the generator """
    yaml_text: str
    warnings: List[str]


@dataclass
class AlignmentSummary:
    """ High-level check that the YAML and intermediate spec reflect the human spec """
    ok: bool
    notes: List[str]
    missing_items: List[str]
    extra_items: List[str]


# --------------------------
# MINIMAL LLM CLIENT STUB
# --------------------------

class LLMClient:
    """
    A fake/dummy LLM client.
    Replace `generate()` with a real provider (OpenAI/Anthropic/Self-hosted.).
    """

    def __init__(self, model_name: str = "stubbed-llm", temperature: float = 0.0):
        self.model_name = model_name
        self.temperature = temperature

    def generate(self, prompt: str, input: str, task: str) -> str:
        """
        Deterministic template-based output. This is NOT a real LLM call.
        """
        if task == "intermediate_spec":
            # Send prompt and input to LLM, then ...
            with open("specs/intermediate/order_refund.md", "r") as f:
                return f.read()
        elif task == "yaml_generation":
            with open("specs/yaml/order_refund.yaml", "r") as f:
                return f.read()

        # Fallback
        return "STUB: No matching task found."


# -------------------------
# PUBLIC API
# -------------------------

def interpret_human_spec_to_intermediate(human_text: str, llm: Optional[LLMClient] = None) -> IntermediateSpecResult:
    """
    Convert free-text human spec -> structured intermediate spec (Markdown).
    """
    llm = llm or LLMClient()
    with open("prompts/intermediate_prompt.txt", "r") as f:
        prompt = f.read()
        md = llm.generate(prompt, human_text, task="intermediate_spec")
        clarifications = _extract_clarifications(md)
        return IntermediateSpecResult(content_md=md, clarifications=clarifications)


def generate_yaml_from_intermediate(intermediate_md: str, llm: Optional[LLMClient] = None) -> YAMLGenerationResult:
    """
    Convert intermediate Markdown -> YAML workflow conforming to your schema.
    """
    llm = llm or LLMClient()
    with open("prompts/yaml_generation_prompt.txt", "r") as f:
        prompt = f.read()
        yaml_text = llm.generate(prompt, intermediate_md, task="yaml_generation")
        warnings = _extract_yaml_warnings(yaml_text)

        return YAMLGenerationResult(yaml_text=yaml_text, warnings=warnings)


def validate_yaml_against_schema(yaml_text: str, schema: Dict) -> Tuple[bool, List[str]]:
    """
    Simple validation stub. Replace with schema.
    Returns (ok, errors).
    """
    errors: List[str] = []

    required_top = schema.get("required", [])
    for field in required_top:
        pattern = rf"^{field}:\s*"
        if not re.search(pattern, yaml_text, flags=re.MULTILINE):
            errors.append(f"Missing required top-level field: {field}")

    # Example: ensure steps looks like a YAML list of dicts with 'id' and 'type'
    if "steps" in required_top:
        steps_section = _extract_yaml_block(yaml_text, "steps")
        if not steps_section:
            errors.append("Missing 'steps' block.")
        else:
            if "- id:" not in steps_section or "- type:" not in yaml_text:
                # coarse check; tighten as your schema matures
                pass

    return (len(errors) == 0, errors)


def summarise_alignment(human_text: str, intermediate_md: str, yaml_text: str) -> AlignmentSummary:
    """
    Use for demo/testing.  Replace later with a real checker/LLM call.
    """
    notes: List[str] = []
    missing: List[str] = []
    extra: List[str] = []

    # Look for obvious nouns/verbs in human spec and see if they reappear.
    human_keywords = _extract_keywords(human_text)
    for kw in human_keywords:
        if kw not in intermediate_md and kw not in yaml_text:
            missing.append(kw)

    # Look for things that appear in YAML but not in human spec (could be overreach)
    yaml_keywords = _extract_keywords(yaml_text)
    for kw in yaml_keywords:
        if kw not in human_keywords:
            extra.append(kw)

    ok = len(missing) == 0
    if ok:
        notes.append("High-level alignment looks OK (no missing human-keywords detected).")
    else:
        notes.append("Some human-intent keywords were not reflected downstream.")

    return AlignmentSummary(ok=ok, notes=notes, missing_items=missing, extra_items=extra)



# -------------------------
# HELPERS
# -------------------------

def _extract_clarifications(md: str) -> List[str]:
    """
    Extraction of clarifications from intermediate spec Markdown.
    Looks for a section starting with "Clarifications" or similar.
    """
    clarifications: List[str] = []
    pattern = r"(?im)^#*\s*Clarifications\s*\n(.*?)(?=^#|\Z)"
    match = re.search(pattern, md, flags=re.DOTALL | re.IGNORECASE)
    if match:
        clarif_text = match.group(1).strip()
        lines = clarif_text.splitlines()
        for line in lines:
            line = line.strip("-* \n")
            if line:
                clarifications.append(line)
    return clarifications

# I'll probably ditch this.  Warnings should not be making it this far.
def _extract_yaml_warnings(yaml_text: str) -> List[str]:
    """
    Extraction of warnings from YAML text.
    Looks for comments starting with "WARNING:".
    """
    warnings: List[str] = []

    # Basic sanity checks, for example:
    if "steps:" not in yaml_text:
        warnings.append("YAML contains no 'steps:' section.")
    if "name:" not in yaml_text:
        warnings.append("YAML contains no 'name:' field.")

    pattern = r"#\s*WARNING:\s*(.*)"
    matches = re.findall(pattern, yaml_text)
    for match in matches:
        warnings.append(match.strip())
    return warnings

def _extract_yaml_block(yml: str, key: str) -> str:
    """Extract a simple YAML block by key (indented lines following 'key:')."""
    pattern = rf"^{key}:\s*$"
    lines = yml.splitlines()
    out: List[str] = []
    capturing = False
    base_indent = None
    for line in lines:
        if re.match(pattern, line):
            capturing = True
            base_indent = None
            continue
        if capturing:
            if not line.strip():
                out.append(line)
                continue
            indent = len(line) - len(line.lstrip(" "))
            if base_indent is None:
                base_indent = indent
            if indent >= base_indent:
                out.append(line)
            else:
                break
    return "\n".join(out)

def _extract_keywords(text: str) -> List[str]:
    words = re.findall(r"[A-Za-z]{4,}", text.lower())
    stop = {
        "this", "that", "with", "from", "into", "about", "which", "have",
        "will", "should", "then", "when", "after", "within", "where",
        "policy", "rules", "steps", "inputs", "goal", "success", "failure",
        "process", "using", "based", "there", "their", "these", "those",
        "section", "criteria", "allowed", "action", "checks", "apply"
    }
    return sorted(set(w for w in words if w not in stop))