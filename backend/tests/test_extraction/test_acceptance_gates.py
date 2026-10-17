"""Observable acceptance boundaries for C01, C03, C04 and C05."""

from unittest.mock import MagicMock

import pytest

from backend.app.extraction.client import GeminiExtractionClient
from backend.app.extraction.group_validator import (
    parse_extraction_response,
    validate_proposed_group,
)
from backend.app.extraction.models import (
    AnalysisStatus,
    AttributeCondition,
    ExtractionInputRequest,
)
from backend.app.extraction.proposal_manager import ProposalReviewSession
from backend.app.extraction.service import ExtractionService


@pytest.mark.parametrize("text", [" \t\n ", "a" * 50_001], ids=["blank", "over_limit"])
def test_invalid_confirmed_text_never_calls_gemini_and_is_preserved(text):
    client = MagicMock(spec=GeminiExtractionClient)
    response = ExtractionService(client=client).analyze_description(
        ExtractionInputRequest(text=text, confirmed=True)
    )

    assert response.status == AnalysisStatus.VALIDATION_ERROR
    assert response.original_text == text
    assert response.fallback_to_manual is True
    client.call_gemini.assert_not_called()


def test_group_identification_requires_a_fragment_from_confirmed_text():
    result = parse_extraction_response(
        {
            "spaces": [
                {"name": "oficinas", "source_fragment": "8 oficinas de 35 m²"},
                {"name": "bodega", "source_fragment": "bodega inventada"},
            ]
        },
        original_text="Se limpian 8 oficinas de 35 m².",
    )

    assert [group.name for group in result.revisable_groups] == ["oficinas"]
    assert len(result.defective_groups) == 1
    assert any("respaldo" in reason for reason in result.defective_groups[0].defect_reasons)


def test_space_name_must_be_supported_by_its_fragment():
    result = parse_extraction_response(
        {"spaces": [{"name": "hospital", "source_fragment": "8 oficinas de 35 m²"}]},
        original_text="Se limpian 8 oficinas de 35 m².",
    )

    assert result.revisable_groups == []
    assert len(result.defective_groups) == 1


def test_unbacked_area_and_condition_remain_absent_instead_of_becoming_facts():
    group, defective = validate_proposed_group(
        {
            "name": "taller mecánico",
            "quantity": 1,
            "unit_area_m2": 150,
            "condition": "malo",
            "source_fragment": "1 taller mecánico",
        }
    )

    assert defective is None
    assert group.unit_area_m2 is None
    assert group.condition is None
    assert group.attributes["unit_area_m2"].condition == AttributeCondition.ABSENT
    assert group.attributes["condition"].condition == AttributeCondition.ABSENT


def test_unbacked_schedule_attributes_remain_absent():
    group, defective = validate_proposed_group(
        {
            "name": "oficinas",
            "quantity": 2,
            "service_days": ["martes"],
            "visits_per_day": 2,
            "source_fragment": "2 oficinas los lunes",
        }
    )

    assert defective is None
    assert group.service_days is None
    assert group.visits_per_day is None
    assert group.attributes["service_days"].condition == AttributeCondition.ABSENT
    assert group.attributes["visits_per_day"].condition == AttributeCondition.ABSENT


@pytest.mark.parametrize(
    "attribute,value",
    [
        ("quantity", 2.5),
        ("quantity", True),
        ("unit_area_m2", float("nan")),
        ("total_area_m2", float("inf")),
        ("visits_per_day", 1.5),
    ],
)
def test_unrepresentable_numeric_values_are_defective(attribute, value):
    revisable, defective = validate_proposed_group(
        {"name": "oficinas", "source_fragment": "oficinas", attribute: value}
    )

    assert revisable is None
    assert defective is not None


def test_unmentioned_cleaning_type_remains_absent():
    group, defective = validate_proposed_group(
        {"name": "oficinas", "quantity": 8, "unit_area_m2": 35, "source_fragment": "8 oficinas de 35 m²"}
    )

    assert defective is None
    assert group.cleaning_type is None
    assert group.attributes["cleaning_type"].value is None
    assert group.attributes["cleaning_type"].condition == AttributeCondition.ABSENT


def test_merge_and_split_preserve_provenance_for_each_visible_attribute():
    first, _ = validate_proposed_group(
        {
            "name": "oficinas", "quantity": 2, "unit_area_m2": 35,
            "cleaning_type": "general", "service_days": ["lunes"], "visits_per_day": 1,
            "source_fragment": "2 oficinas de 35 m² los lunes",
        }
    )
    second, _ = validate_proposed_group(
        {
            "name": "oficinas", "quantity": 2, "unit_area_m2": 35,
            "cleaning_type": "general", "service_days": ["lunes"], "visits_per_day": 1,
            "source_fragment": "otras 2 oficinas de 35 m² los lunes",
        }
    )
    session = ProposalReviewSession(revisable_groups=[first, second])
    merged = session.merge_groups(first.id, second.id)
    children = session.split_group(merged.id, (1, 3))

    for group in (merged, *children):
        for field in ("name", "quantity", "unit_area_m2", "total_area_m2", "cleaning_type", "service_days", "visits_per_day"):
            value = getattr(group, field)
            if value is not None:
                assert field in group.attributes
                assert group.attributes[field].value == value
                assert group.attributes[field].source_fragment


def test_merge_incomplete_groups_retains_missing_area_for_review():
    first, _ = validate_proposed_group({"name": "aulas", "quantity": 2, "source_fragment": "2 aulas"})
    second, _ = validate_proposed_group({"name": "aulas", "quantity": 1, "source_fragment": "1 aula"})
    session = ProposalReviewSession(revisable_groups=[first, second])

    merged = session.merge_groups(first.id, second.id)

    assert merged.quantity == 3
    assert merged.unit_area_m2 is None
    assert merged.attributes["unit_area_m2"].condition == AttributeCondition.ABSENT


def test_unexpected_provider_error_never_exposes_api_key():
    secret = "gemini-secret-key-123"
    client = MagicMock(spec=GeminiExtractionClient)
    client.call_gemini.side_effect = RuntimeError(f"request failed with {secret}")

    response = ExtractionService(client=client).analyze_description(
        ExtractionInputRequest(text="8 oficinas", confirmed=True)
    )

    assert response.status == AnalysisStatus.UNAVAILABLE
    assert response.fallback_to_manual is True
    assert secret not in response.model_dump_json()


def test_unusable_provider_shape_preserves_text_and_manual_route():
    client = MagicMock(spec=GeminiExtractionClient)
    client.call_gemini.return_value = {"spaces": None}

    response = ExtractionService(client=client).analyze_description(
        ExtractionInputRequest(text="8 oficinas", confirmed=True)
    )

    assert response.status == AnalysisStatus.UNUSABLE
    assert response.original_text == "8 oficinas"
    assert response.fallback_to_manual is True


def test_bad_optional_value_does_not_discard_another_revisable_group():
    result = parse_extraction_response(
        {"spaces": [
            {"name": "oficinas", "quantity": 8, "source_fragment": "8 oficinas"},
            {"name": "bodega", "source_fragment": "1 bodega", "service_days": [42]},
        ]},
        original_text="8 oficinas y 1 bodega",
    )

    assert [group.name for group in result.revisable_groups] == ["oficinas"]
    assert len(result.defective_groups) == 1
