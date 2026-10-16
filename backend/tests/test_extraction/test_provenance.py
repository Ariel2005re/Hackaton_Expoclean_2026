"""Unit tests for attribute provenance, explicit derivations, and contradiction blocking (Task C04 · RF-07, RF-08, RF-09)."""

import pytest

from backend.app.extraction.group_validator import validate_proposed_group
from backend.app.extraction.models import (
    AttributeCondition,
    AttributeProvenance,
    ProposedSpaceGroup,
)
from backend.app.extraction.provenance import (
    build_contradictory_provenance,
    check_group_confirmation_eligibility,
    derive_total_area,
    derive_unit_area,
    resolve_contradiction,
)


class TestExplicitDerivations:
    """Tests the arithmetic derivation of areas with exact origin values and operations (RF-07)."""

    def test_derive_unit_area_exact_case_280_div_8(self):
        """RF-07: 280 m² ÷ 8 oficinas = 35 m² por unidad."""
        unit_area, prov = derive_unit_area(
            name="oficinas",
            total_area_m2=280.0,
            quantity=8,
            source_fragment="280 m² distribuidos en 8 oficinas",
        )
        assert unit_area == 35.0
        assert prov.value == 35.0
        assert prov.condition == AttributeCondition.DERIVED
        assert prov.operation == "280 m² ÷ 8 oficinas = 35 m² por unidad"
        assert prov.origin_values == {"total_area_m2": 280.0, "quantity": 8}
        assert prov.source_fragment == "280 m² distribuidos en 8 oficinas"

    def test_derive_total_area_from_unit_and_quantity(self):
        """RF-07: 4 aulas × 50 m² = 200 m² en total."""
        total_area, prov = derive_total_area(
            name="aulas",
            unit_area_m2=50.0,
            quantity=4,
            source_fragment="4 aulas de 50 m²",
        )
        assert total_area == 200.0
        assert prov.value == 200.0
        assert prov.condition == AttributeCondition.DERIVED
        assert prov.operation == "4 aulas × 50 m² = 200 m² en total"
        assert prov.origin_values == {"unit_area_m2": 50.0, "quantity": 4}

    def test_derive_with_zero_or_negative_quantity_raises_error(self):
        with pytest.raises(ValueError):
            derive_unit_area(name="oficinas", total_area_m2=280.0, quantity=0)

        with pytest.raises(ValueError):
            derive_total_area(name="oficinas", unit_area_m2=35.0, quantity=-1)


class TestContradictionManagementAndConfirmationBlocking:
    """Tests that contradictory values stay unconfirmed until human resolution (RF-08)."""

    def test_contradictory_provenance_structure(self):
        prov = build_contradictory_provenance(
            conflicting_values=["bueno", "regular"],
            source_fragment="piso 1 bueno pero oficinas regulares",
        )
        assert prov.value is None  # Never automatically guessed
        assert prov.condition == AttributeCondition.CONTRADICTORY
        assert prov.conflicting_values == ["bueno", "regular"]

    def test_group_with_contradiction_cannot_be_confirmed(self):
        """Key C04 requirement: las contradicciones permanecen sin confirmar."""
        raw_group = {
            "name": "aulas",
            "quantity": 5,
            "unit_area_m2": 40.0,
            "conflicting_conditions": ["bueno", "malo"],
            "source_fragment": "aula 1 en buen estado, otras aulas en mal estado",
        }
        group, defective = validate_proposed_group(raw_group)
        assert defective is None
        assert group is not None

        # Group is in review, but cannot be confirmed yet
        assert group.is_revisable is True
        assert group.can_be_confirmed is False
        assert group.condition is None

        can_confirm, reasons = check_group_confirmation_eligibility(group)
        assert can_confirm is False
        assert any("valores contradictorios" in r for r in reasons)

    def test_resolving_contradiction_enables_confirmation(self):
        """RF-08, RF-09: human resolution transitions condition to human_corrected and unblocks confirmation."""
        raw_group = {
            "name": "aulas",
            "quantity": 5,
            "unit_area_m2": 40.0,
            "conflicting_conditions": ["bueno", "malo"],
            "source_fragment": "aulas con estados dispares",
        }
        group, _ = validate_proposed_group(raw_group)
        assert group.can_be_confirmed is False

        # Human resolves the contradiction by choosing 'regular'
        resolved_group = resolve_contradiction(
            group=group,
            attribute_name="condition",
            chosen_value="regular",
            human_note="Acordado con el cliente como estado promedio",
        )

        assert resolved_group.condition == "regular"
        attr_prov = resolved_group.attributes["condition"]
        assert attr_prov.condition == AttributeCondition.HUMAN_CORRECTED
        assert attr_prov.value == "regular"
        assert "regular" in attr_prov.operation

        # All mandatory attributes are now valid and contradiction is resolved
        assert resolved_group.can_be_confirmed is True


class TestAttributeProvenanceCompleteness:
    """Verifies that every visible value has explicit origin or operation (RF-09)."""

    def test_all_visible_values_have_condition_and_provenance(self):
        raw_group = {
            "name": "oficinas",
            "quantity": 8,
            "total_area_m2": 280.0,
            "condition": "regular",
            "source_fragment": "8 oficinas administrativas con 280 m² en estado regular",
        }
        group, _ = validate_proposed_group(raw_group)
        assert group is not None

        # Name
        assert group.attributes["name"].condition == AttributeCondition.EXPLICIT
        assert group.attributes["name"].source_fragment is not None

        # Quantity
        assert group.attributes["quantity"].condition == AttributeCondition.EXPLICIT
        assert group.attributes["quantity"].value == 8

        # Derived Unit Area
        assert group.attributes["unit_area_m2"].condition == AttributeCondition.DERIVED
        assert group.attributes["unit_area_m2"].operation is not None
        assert group.attributes["unit_area_m2"].origin_values is not None

        # Absent attributes
        assert group.attributes["service_days"].condition == AttributeCondition.ABSENT
        assert group.attributes["service_days"].value is None
