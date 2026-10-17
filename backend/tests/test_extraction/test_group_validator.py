"""Unit tests for group proposal validation and mixed response separation (Task C03 · RF-07, RF-08, RF-09, RF-29)."""

import pytest

from backend.app.extraction.group_validator import (
    parse_extraction_response,
    validate_proposed_group,
)
from backend.app.extraction.models import AttributeCondition


class TestProposedGroupIdentification:
    """Verifies that a proposal is revisable only if it identifies a space backed by text (RF-09, RF-29)."""

    def test_valid_identifiable_group_is_revisable(self):
        raw_group = {
            "name": "oficinas",
            "quantity": 8,
            "unit_area_m2": 35.0,
            "condition": "regular",
            "source_fragment": "8 oficinas administrativas de 35 m² cada una en estado regular",
        }
        revisable, defective = validate_proposed_group(raw_group)
        assert defective is None
        assert revisable is not None
        assert revisable.is_revisable is True
        assert revisable.name == "oficinas"
        assert revisable.quantity == 8
        assert revisable.unit_area_m2 == 35.0
        assert revisable.attributes["name"].condition == AttributeCondition.EXPLICIT

    def test_revisable_group_with_missing_mandatory_attributes(self):
        """RF-29: Reusable for human review even if missing mandatory attributes."""
        raw_group = {
            "name": "bodega",
            "source_fragment": "bodega en el subsuelo",
            # quantity, unit_area_m2, condition are missing
        }
        revisable, defective = validate_proposed_group(raw_group)
        assert defective is None
        assert revisable is not None
        assert revisable.is_revisable is True
        assert revisable.quantity is None
        assert revisable.unit_area_m2 is None
        assert revisable.attributes["quantity"].condition == AttributeCondition.ABSENT
        assert revisable.attributes["unit_area_m2"].condition == AttributeCondition.ABSENT
        assert len(revisable.warnings) > 0


class TestDefectiveGroupRejection:
    """Verifies that groups without identification or with unrepresentable data are flagged as defective (RF-09, RF-29)."""

    def test_missing_name_makes_group_defective(self):
        raw_group = {
            "quantity": 5,
            "unit_area_m2": 20.0,
            "source_fragment": "5 espacios de 20 m²",
        }
        revisable, defective = validate_proposed_group(raw_group)
        assert revisable is None
        assert defective is not None
        assert defective.is_revisable is False
        assert any("nombre o tipo" in reason for reason in defective.defect_reasons)

    def test_missing_source_fragment_makes_group_defective(self):
        raw_group = {
            "name": "aulas",
            "quantity": 4,
            "unit_area_m2": 45.0,
            # Missing source_fragment
        }
        revisable, defective = validate_proposed_group(raw_group)
        assert revisable is None
        assert defective is not None
        assert defective.is_revisable is False
        assert any("fragmento de texto" in reason for reason in defective.defect_reasons)

    def test_unrepresentable_negative_numbers_make_group_defective(self):
        raw_group = {
            "name": "laboratorio",
            "quantity": -2,  # Invalid negative quantity
            "unit_area_m2": -50.0,  # Invalid negative area
            "source_fragment": "laboratorio con datos erróneos",
        }
        revisable, defective = validate_proposed_group(raw_group)
        assert revisable is None
        assert defective is not None
        assert len(defective.defect_reasons) >= 2


class TestMixedResponseSeparation:
    """Key acceptance test for C03: mixed response leaves identifiable group revisable and flags defective ones."""

    def test_mixed_response_separates_revisable_and_defective_groups(self):
        original_text = "Se requiere limpiar 8 oficinas de 35 m² y un espacio sin identificar de -10 m²"
        raw_response = {
            "spaces": [
                {
                    "name": "oficinas",
                    "quantity": 8,
                    "unit_area_m2": 35.0,
                    "condition": "bueno",
                    "source_fragment": "8 oficinas de 35 m²",
                },
                {
                    # Defective 1: Missing name
                    "quantity": 2,
                    "unit_area_m2": 20.0,
                    "source_fragment": "2 espacios sin identificar",
                },
                {
                    # Defective 2: Unrepresentable negative area
                    "name": "bodega",
                    "unit_area_m2": -10.0,
                    "source_fragment": "bodega de -10 m²",
                },
            ]
        }

        result = parse_extraction_response(raw_response, original_text=original_text)

        # Identifiable group is available for review
        assert len(result.revisable_groups) == 1
        assert result.revisable_groups[0].name == "oficinas"
        assert result.has_revisable_groups is True
        assert result.fallback_to_manual is False

        # Defective groups are isolated and flagged without incorporation
        assert len(result.defective_groups) == 2
        assert len(result.warnings) > 0
        assert "2 grupo(s) defectuoso(s)" in result.warnings[0]

    def test_response_with_no_revisable_groups_triggers_manual_fallback(self):
        """RF-29 / RF-11: if no proposal is revisable, fallback to manual is flagged."""
        raw_response = {
            "spaces": [
                {
                    # Missing name and snippet
                    "quantity": 10,
                }
            ]
        }
        result = parse_extraction_response(raw_response, original_text="Texto confuso")
        assert len(result.revisable_groups) == 0
        assert len(result.defective_groups) == 1
        assert result.has_revisable_groups is False
        assert result.fallback_to_manual is True
        assert any("manual" in w for w in result.warnings)


class TestDerivationsAndContradictions:
    """Verifies provenance, explicit derivations, and contradictory values (RF-07, RF-08)."""

    def test_derivation_unit_area_from_total_and_quantity(self):
        """RF-07: 280 m² ÷ 8 oficinas = 35 m² por unidad."""
        raw_group = {
            "name": "oficinas",
            "quantity": 8,
            "total_area_m2": 280.0,
            "source_fragment": "8 oficinas que en total suman 280 m²",
        }
        revisable, _ = validate_proposed_group(raw_group)
        assert revisable is not None
        assert revisable.unit_area_m2 == 35.0
        unit_attr = revisable.attributes["unit_area_m2"]
        assert unit_attr.condition == AttributeCondition.DERIVED
        assert "280" in unit_attr.operation
        assert "8" in unit_attr.operation
        assert "35" in unit_attr.operation

    def test_contradictory_condition_requires_human_resolution(self):
        """RF-08: Contradictory values stay in review without automatic selection."""
        raw_group = {
            "name": "pasillos",
            "quantity": 2,
            "unit_area_m2": 50.0,
            "conflicting_conditions": ["bueno", "malo"],
            "source_fragment": "pasillo principal bueno, pero pasillo secundario en mal estado",
        }
        revisable, _ = validate_proposed_group(raw_group)
        assert revisable is not None
        assert revisable.condition is None  # Not automatically picked
        attr = revisable.attributes["condition"]
        assert attr.condition == AttributeCondition.CONTRADICTORY
        assert attr.conflicting_values == ["bueno", "malo"]
        assert any("Conflicto de estado" in w for w in revisable.warnings)
