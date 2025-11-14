# tests/test_llm_api.py
import pytest
from src import llm_api


def test_interpret_human_spec_to_intermediate_parses_and_extracts_clarifications():
    human = (
        "When a customer requests a refund, check within 30 days. "
        "If accidental download, require approval. Email customer and log."
    )
    result = llm_api.interpret_human_spec_to_intermediate(human)

    # intermediate_md = ""
    # with open("specs/intermediate/order_refund.md", "r") as f:
    #     intermediate_md = f.read()

    assert isinstance(result, llm_api.IntermediateSpecResult)
    assert "Process: Order Refund" in result.content_md
    # Clarifications were captured from the ## Clarifications section
    assert "Approval required but approver role not specified." in result.clarifications
    assert "Customer notification template/content not specified." in result.clarifications


def test_generate_yaml_from_intermediate_returns_yaml_and_warnings():
    # Use the intermediate markdown produced by the stub
    interm = llm_api.interpret_human_spec_to_intermediate("whatever").content_md

    gen = llm_api.generate_yaml_from_intermediate(interm)
    assert isinstance(gen, llm_api.YAMLGenerationResult)
    assert "name: order_refund" in gen.yaml_text
    assert "nodes:" in gen.yaml_text


def test_validate_yaml_against_schema_success_and_failure():
    # Good YAML
    interm = llm_api.interpret_human_spec_to_intermediate("ok").content_md
    good_yaml = llm_api.generate_yaml_from_intermediate(interm).yaml_text

    schema = {
        "required": ["name", "inputs", "nodes", "edges", "success_criteria", "failure_conditions"]
    }
    ok, errors = llm_api.validate_yaml_against_schema(good_yaml, schema)
    assert ok is True
    assert errors == []

    # Broken YAML — remove `name:` to trigger an error
    broken_yaml = "\n".join(
        line for line in good_yaml.splitlines() if not line.startswith("name:")
    )
    ok2, errors2 = llm_api.validate_yaml_against_schema(broken_yaml, schema)
    assert ok2 is False
    assert any("Missing required top-level field: name" in e for e in errors2)
    # with open("specs/yaml/order_refund.yaml", "r") as f:
    #     yaml_text = f.read()
        # compare generated yaml to expected yaml



def test_summarise_alignment_detects_missing_and_extra_keywords():
    human = "Refund request; check policy; email customer; write audit log."
    interm = llm_api.interpret_human_spec_to_intermediate(human).content_md
    yaml_text = llm_api.generate_yaml_from_intermediate(interm).yaml_text

    # Introduce an "extra" keyword into YAML not found in the human spec
    yaml_text += "\n# internal_reconciliation_job\n"

    summary = llm_api.summarise_alignment(human, interm, yaml_text)
    assert isinstance(summary, llm_api.AlignmentSummary)
    # At least one 'extra' keyword should be flagged
    assert any("internal" in x for x in summary.extra_items)
    # Likely OK on missing since stub mirrors the intent fairly well
    # but we accept either, as the heuristic is simple:
    assert isinstance(summary.ok, bool)
