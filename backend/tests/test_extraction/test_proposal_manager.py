"""Unit tests for proposal lifecycle management: correct, merge, split, discard, and reanalysis (Task C05 · RF-08, RF-09, RF-10)."""

import pytest

from backend.app.extraction.group_validator import validate_proposed_group
from backend.app.extraction.models import (
    AttributeCondition,
    ExtractionAnalysisResult,
    ProposedSpaceGroup,
)
from backend.app.extraction.proposal_manager import ProposalReviewSession


def create_sample_group(name: str, quantity: int, unit_area: float, snippet: str) -> ProposedSpaceGroup:
    raw = {
        "name": name,
        "quantity": quantity,
        "unit_area_m2": unit_area,
        "condition": "bueno",
        "source_fragment": snippet,
    }
    group, _ = validate_proposed_group(raw)
    assert group is not None
    return group


class TestHumanAttributeCorrection:
    """Verifies that manual corrections transition to human_corrected while preserving text evidence (RF-09)."""

    def test_correct_quantity_updates_provenance_and_total_area(self):
        g = create_sample_group("oficinas", 8, 35.0, "8 oficinas de 35 m²")
        session = ProposalReviewSession(revisable_groups=[g])

        updated = session.correct_attribute(
            group_id=g.id,
            attribute_name="quantity",
            new_value=10,
            human_note="El cliente indicó 2 oficinas adicionales",
        )

        assert updated.quantity == 10
        # Recalculated total area: 10 * 35.0 = 350.0
        assert updated.total_area_m2 == 350.0
        attr_prov = updated.attributes["quantity"]
        assert attr_prov.condition == AttributeCondition.HUMAN_CORRECTED
        assert attr_prov.value == 10
        assert attr_prov.source_fragment == "8 oficinas de 35 m²"  # Evidence preserved
        assert "10" in attr_prov.operation


class TestMergeGroups:
    """Verifies that merging groups preserves attribute provenance from both parents (RF-09)."""

    def test_merge_two_compatible_office_groups(self):
        g1 = create_sample_group("oficinas piso 1", 4, 35.0, "4 oficinas en piso 1 de 35 m²")
        g2 = create_sample_group("oficinas piso 2", 4, 35.0, "4 oficinas en piso 2 de 35 m²")
        session = ProposalReviewSession(revisable_groups=[g1, g2])

        merged = session.merge_groups(
            group_id_1=g1.id,
            group_id_2=g2.id,
            merged_name="oficinas totales",
        )

        # Quantity: 4 + 4 = 8
        assert merged.quantity == 8
        assert merged.unit_area_m2 == 35.0
        assert merged.total_area_m2 == 280.0

        # Evidence survives merge (RF-09)
        assert "4 oficinas en piso 1" in merged.source_fragment
        assert "4 oficinas en piso 2" in merged.source_fragment
        assert merged.attributes["quantity"].source_fragment == merged.source_fragment
        assert merged.attributes["quantity"].condition == AttributeCondition.HUMAN_CORRECTED

        # Old groups were removed, only merged group remains
        assert len(session.revisable_groups) == 1
        assert session.revisable_groups[0].id == merged.id


class TestSplitGroup:
    """Verifies that splitting a group preserves the parent source fragment in both children (RF-09)."""

    def test_split_group_preserves_parent_source_fragment(self):
        parent = create_sample_group("oficinas", 8, 35.0, "8 oficinas administrativas con alfombra de 35 m²")
        session = ProposalReviewSession(revisable_groups=[parent])

        child1, child2 = session.split_group(
            group_id=parent.id,
            split_quantities=(5, 3),
            split_names=("oficinas sector norte", "oficinas sector sur"),
        )

        assert child1.quantity == 5
        assert child1.unit_area_m2 == 35.0
        assert child1.total_area_m2 == 175.0
        # Source fragment survives split (RF-09)
        assert child1.source_fragment == parent.source_fragment
        assert child1.attributes["name"].source_fragment == parent.source_fragment

        assert child2.quantity == 3
        assert child2.unit_area_m2 == 35.0
        assert child2.total_area_m2 == 105.0
        assert child2.source_fragment == parent.source_fragment

        # Parent is replaced by children in session
        assert len(session.revisable_groups) == 2
        assert parent not in session.revisable_groups

    def test_split_with_invalid_quantities_raises_error(self):
        parent = create_sample_group("oficinas", 8, 35.0, "8 oficinas")
        session = ProposalReviewSession(revisable_groups=[parent])

        with pytest.raises(ValueError):
            session.split_group(parent.id, split_quantities=(5, 4))  # Sum is 9, not 8


class TestDiscardAndConfirmProposal:
    """Verifies proposal discarding and confirmation rules (RF-08, RF-09)."""

    def test_discard_proposal_moves_it_to_discarded(self):
        g = create_sample_group("bodega", 1, 50.0, "1 bodega")
        session = ProposalReviewSession(revisable_groups=[g])

        discarded = session.discard_group(g.id)
        assert discarded.id == g.id
        assert len(session.revisable_groups) == 0
        assert len(session.discarded_groups) == 1

    def test_confirm_valid_proposal_incorporates_it(self):
        g = create_sample_group("aulas", 3, 40.0, "3 aulas de 40 m²")
        session = ProposalReviewSession(revisable_groups=[g])

        confirmed = session.confirm_group(g.id)
        assert confirmed.id == g.id
        assert len(session.revisable_groups) == 0
        assert len(session.confirmed_groups) == 1

    def test_confirm_group_with_contradiction_is_blocked(self):
        """RF-08: Contradiction prevents confirmation."""
        raw = {
            "name": "pasillo",
            "quantity": 1,
            "unit_area_m2": 30.0,
            "conflicting_conditions": ["bueno", "malo"],
            "source_fragment": "pasillo en estado contradictorio",
        }
        g, _ = validate_proposed_group(raw)
        session = ProposalReviewSession(revisable_groups=[g])

        with pytest.raises(ValueError) as exc_info:
            session.confirm_group(g.id)
        assert "contradictorios" in str(exc_info.value)
        assert len(session.confirmed_groups) == 0


class TestReanalysisPreservesConfirmedGroups:
    """Key acceptance test for RF-10: re-analyzing description does NOT duplicate confirmed groups."""

    def test_reanalysis_does_not_duplicate_already_confirmed_groups(self):
        # 1. User previously confirmed an office group
        confirmed_office = create_sample_group("oficinas", 8, 35.0, "8 oficinas de 35 m²")
        session = ProposalReviewSession(confirmed_groups=[confirmed_office])

        # 2. User re-analyzes a new or expanded description that extracts offices again plus bathrooms
        new_office = create_sample_group("oficinas", 8, 35.0, "8 oficinas de 35 m²")
        new_bathrooms = create_sample_group("baños", 2, 15.0, "2 baterías de baños de 15 m²")

        new_analysis = ExtractionAnalysisResult(
            original_text="Texto actualizado con oficinas y baños",
            revisable_groups=[new_office, new_bathrooms],
            has_revisable_groups=True,
        )

        session.reanalyze_without_duplicating_confirmed(new_analysis)

        # 3. Confirmed groups remain strictly at 1 (no duplicate offices added to confirmed)
        assert len(session.confirmed_groups) == 1
        assert session.confirmed_groups[0].id == confirmed_office.id

        # 4. Revisable groups contain the new proposals for human inspection
        assert len(session.revisable_groups) == 2
        # The re-extracted office has an advisory warning about previous confirmation
        matching_office = next(g for g in session.revisable_groups if g.name == "oficinas")
        assert any("previamente" in w for w in matching_office.warnings)
