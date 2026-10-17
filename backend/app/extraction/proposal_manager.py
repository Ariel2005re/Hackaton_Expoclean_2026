"""Proposal manager for human review: correct, merge, split, discard, and confirm (Task C05 · RF-08, RF-09, RF-10).

Rules:
- RF-08: Contradictory values must be resolved before confirmation.
- RF-09: Human corrections are identified as human_corrected.
         When merging or splitting groups, each resulting attribute preserves its source fragment.
- RF-10: Re-analyzing a text presents new proposals in review WITHOUT inserting or duplicating
         already confirmed groups.
"""

import uuid
from typing import Any, Dict, List, Optional, Tuple

from backend.app.extraction.models import (
    AttributeCondition,
    AttributeProvenance,
    DefectiveSpaceGroup,
    ExtractionAnalysisResult,
    ProposedSpaceGroup,
)
from backend.app.extraction.provenance import (
    check_group_confirmation_eligibility,
    derive_total_area,
)


class ProposalReviewSession:
    """Manages the lifecycle of extracted space proposals under human review (RF-09, RF-10)."""

    def __init__(
        self,
        original_text: str = "",
        revisable_groups: Optional[List[ProposedSpaceGroup]] = None,
        defective_groups: Optional[List[DefectiveSpaceGroup]] = None,
        confirmed_groups: Optional[List[ProposedSpaceGroup]] = None,
    ):
        self.original_text = original_text
        self.revisable_groups: List[ProposedSpaceGroup] = revisable_groups or []
        self.defective_groups: List[DefectiveSpaceGroup] = defective_groups or []
        self.confirmed_groups: List[ProposedSpaceGroup] = confirmed_groups or []
        self.discarded_groups: List[ProposedSpaceGroup] = []

    def get_group(self, group_id: str) -> Optional[ProposedSpaceGroup]:
        """Find a group in revisable_groups by id."""
        for g in self.revisable_groups:
            if g.id == group_id:
                return g
        return None

    def correct_attribute(
        self,
        group_id: str,
        attribute_name: str,
        new_value: Any,
        human_note: Optional[str] = None,
    ) -> ProposedSpaceGroup:
        """Correct a single attribute of a proposed group (RF-09).
        
        The attribute is tagged as human_corrected while preserving source fragment evidence.
        """
        group = self.get_group(group_id)
        if group is None:
            raise ValueError(f"No se encontró el grupo revisable con id '{group_id}'.")

        old_prov = group.attributes.get(attribute_name)
        old_val = old_prov.value if old_prov else getattr(group, attribute_name, None)
        source_frag = old_prov.source_fragment if (old_prov and old_prov.source_fragment) else group.source_fragment

        operation_desc = f"Corrección manual: '{old_val}' cambiado a '{new_value}'"
        if human_note:
            operation_desc += f" ({human_note})"

        # Update attribute provenance
        group.attributes[attribute_name] = AttributeProvenance(
            value=new_value,
            condition=AttributeCondition.HUMAN_CORRECTED,
            source_fragment=source_frag,
            operation=operation_desc,
        )

        # Update top-level field if applicable
        if hasattr(group, attribute_name):
            setattr(group, attribute_name, new_value)

        # Recalculate areas if quantity or unit_area changed
        if attribute_name in ("quantity", "unit_area_m2") and group.quantity and group.unit_area_m2:
            group.total_area_m2 = round(group.quantity * group.unit_area_m2, 2)
            group.attributes["total_area_m2"] = AttributeProvenance(
                value=group.total_area_m2,
                condition=AttributeCondition.DERIVED,
                source_fragment=source_frag,
                operation=f"{group.quantity} {group.name} × {group.unit_area_m2:g} m² = {group.total_area_m2:g} m² en total",
                origin_values={"quantity": group.quantity, "unit_area_m2": group.unit_area_m2},
            )

        # Re-evaluate confirmation eligibility
        can_confirm, _ = check_group_confirmation_eligibility(group)
        group.can_be_confirmed = can_confirm

        return group

    def merge_groups(
        self,
        group_id_1: str,
        group_id_2: str,
        merged_name: Optional[str] = None,
    ) -> ProposedSpaceGroup:
        """Combine two proposed groups into a single consolidated group (RF-09).
        
        Both source fragments are preserved in the merged attributes.
        """
        g1 = self.get_group(group_id_1)
        g2 = self.get_group(group_id_2)
        if g1 is None or g2 is None:
            raise ValueError("Uno o ambos grupos a combinar no fueron encontrados.")
        if group_id_1 == group_id_2:
            raise ValueError("Se requieren dos grupos distintos para combinar.")

        name = merged_name or g1.name
        q1 = g1.quantity or 0
        q2 = g2.quantity or 0
        combined_quantity = (q1 + q2) if g1.quantity is not None and g2.quantity is not None else None

        # Unit area: if matching, keep it; else weighted average
        u1 = g1.unit_area_m2
        u2 = g2.unit_area_m2
        if u1 is not None and u2 is not None:
            if u1 == u2:
                combined_unit_area = u1
            elif combined_quantity:
                t1 = (g1.total_area_m2 or (u1 * q1))
                t2 = (g2.total_area_m2 or (u2 * q2))
                combined_unit_area = round((t1 + t2) / combined_quantity, 2)
            else:
                combined_unit_area = u1
        else:
            combined_unit_area = None

        combined_total_area = None
        if combined_quantity and combined_unit_area:
            combined_total_area = round(combined_quantity * combined_unit_area, 2)

        combined_source = f"{g1.source_fragment} | {g2.source_fragment}"

        merged_attributes: Dict[str, AttributeProvenance] = {
            "name": AttributeProvenance(
                value=name,
                condition=AttributeCondition.HUMAN_CORRECTED,
                source_fragment=combined_source,
                operation=f"Combinación de '{g1.name}' y '{g2.name}'",
            ),
            "quantity": AttributeProvenance(
                value=combined_quantity,
                condition=AttributeCondition.HUMAN_CORRECTED if combined_quantity is not None else AttributeCondition.ABSENT,
                source_fragment=combined_source if combined_quantity is not None else None,
                operation=f"Suma de cantidades: {q1} + {q2} = {combined_quantity}" if combined_quantity is not None else None,
                origin_values={"group_1_quantity": q1, "group_2_quantity": q2} if combined_quantity is not None else None,
            ),
            "unit_area_m2": AttributeProvenance(
                value=combined_unit_area,
                condition=AttributeCondition.HUMAN_CORRECTED if combined_unit_area is not None else AttributeCondition.ABSENT,
                source_fragment=combined_source if combined_unit_area is not None else None,
                operation=f"Superficie unificada de grupos combinados: {combined_unit_area:g} m²" if combined_unit_area is not None else None,
            ),
        }

        if combined_total_area:
            merged_attributes["total_area_m2"] = AttributeProvenance(
                value=combined_total_area,
                condition=AttributeCondition.DERIVED,
                source_fragment=combined_source,
                operation=f"{combined_quantity} {name} × {combined_unit_area:g} m² = {combined_total_area:g} m²",
            )
        else:
            merged_attributes["total_area_m2"] = AttributeProvenance(
                value=None,
                condition=AttributeCondition.ABSENT,
            )

        def shared_attribute(field: str):
            first = getattr(g1, field)
            second = getattr(g2, field)
            if first is not None and first == second:
                return first, AttributeProvenance(
                    value=first,
                    condition=AttributeCondition.HUMAN_CORRECTED,
                    source_fragment=combined_source,
                    operation=f"Valor conservado al combinar: {field}",
                )
            if first is not None and second is not None:
                return None, AttributeProvenance(
                    value=None,
                    condition=AttributeCondition.CONTRADICTORY,
                    source_fragment=combined_source,
                    conflicting_values=[first, second],
                )
            return None, AttributeProvenance(value=None, condition=AttributeCondition.ABSENT)

        cond, merged_attributes["condition"] = shared_attribute("condition")
        cleaning_type, merged_attributes["cleaning_type"] = shared_attribute("cleaning_type")
        service_days, merged_attributes["service_days"] = shared_attribute("service_days")
        visits_per_day, merged_attributes["visits_per_day"] = shared_attribute("visits_per_day")

        merged_group = ProposedSpaceGroup(
            id=str(uuid.uuid4()),
            name=name,
            quantity=combined_quantity,
            unit_area_m2=combined_unit_area,
            total_area_m2=combined_total_area,
            condition=cond,
            cleaning_type=cleaning_type,
            service_days=service_days,
            visits_per_day=visits_per_day,
            source_fragment=combined_source,
            attributes=merged_attributes,
            is_revisable=True,
            warnings=[f"Grupo resultante de la combinación de dos propuestas ({g1.name} y {g2.name})."],
        )

        can_confirm, _ = check_group_confirmation_eligibility(merged_group)
        merged_group.can_be_confirmed = can_confirm

        # Remove old groups, add merged group
        self.revisable_groups = [g for g in self.revisable_groups if g.id not in (group_id_1, group_id_2)]
        self.revisable_groups.append(merged_group)

        return merged_group

    def split_group(
        self,
        group_id: str,
        split_quantities: Tuple[int, int],
        split_names: Optional[Tuple[str, str]] = None,
    ) -> Tuple[ProposedSpaceGroup, ProposedSpaceGroup]:
        """Split a group into two groups with distinct quantities (RF-09).
        
        Both resulting groups retain the source fragment backing of the parent group.
        """
        parent = self.get_group(group_id)
        if parent is None:
            raise ValueError(f"No se encontró el grupo con id '{group_id}'.")

        q1, q2 = split_quantities
        total_q = (parent.quantity or 0)
        if q1 <= 0 or q2 <= 0 or (q1 + q2 != total_q):
            raise ValueError(
                f"Las cantidades de separación ({q1} + {q2} = {q1 + q2}) "
                f"deben ser positivas y sumar la cantidad original ({total_q})."
            )

        name1 = split_names[0] if split_names else f"{parent.name} (Parte 1)"
        name2 = split_names[1] if split_names else f"{parent.name} (Parte 2)"

        def build_child(name: str, qty: int, part_num: int) -> ProposedSpaceGroup:
            tot = round(qty * parent.unit_area_m2, 2) if parent.unit_area_m2 else None
            attrs = {
                "name": AttributeProvenance(
                    value=name,
                    condition=AttributeCondition.HUMAN_CORRECTED,
                    source_fragment=parent.source_fragment,  # Preserves origin snippet (RF-09)
                    operation=f"Separación de '{parent.name}' (parte {part_num})",
                ),
                "quantity": AttributeProvenance(
                    value=qty,
                    condition=AttributeCondition.HUMAN_CORRECTED,
                    source_fragment=parent.source_fragment,  # Preserves origin snippet (RF-09)
                    operation=f"Separación de cantidad: {qty} de {total_q}",
                    origin_values={"parent_quantity": total_q, "split_quantity": qty},
                ),
            }
            attrs["unit_area_m2"] = parent.attributes.get(
                "unit_area_m2",
                AttributeProvenance(value=None, condition=AttributeCondition.ABSENT),
            ).model_copy(deep=True)
            if tot:
                attrs["total_area_m2"] = AttributeProvenance(
                    value=tot,
                    condition=AttributeCondition.DERIVED,
                    source_fragment=parent.source_fragment,
                    operation=f"{qty} {name} × {parent.unit_area_m2:g} m² = {tot:g} m²",
                )
            else:
                attrs["total_area_m2"] = AttributeProvenance(value=None, condition=AttributeCondition.ABSENT)
            for field in ("condition", "cleaning_type", "service_days", "visits_per_day"):
                attrs[field] = parent.attributes.get(
                    field,
                    AttributeProvenance(value=None, condition=AttributeCondition.ABSENT),
                ).model_copy(deep=True)

            child = ProposedSpaceGroup(
                id=str(uuid.uuid4()),
                name=name,
                quantity=qty,
                unit_area_m2=parent.unit_area_m2,
                total_area_m2=tot,
                condition=parent.condition,
                cleaning_type=parent.cleaning_type,
                service_days=parent.service_days,
                visits_per_day=parent.visits_per_day,
                source_fragment=parent.source_fragment,  # Backed by original snippet (RF-09)
                attributes=attrs,
                is_revisable=True,
                warnings=[f"Grupo obtenido al separar '{parent.name}'."],
            )
            can_confirm, _ = check_group_confirmation_eligibility(child)
            child.can_be_confirmed = can_confirm
            return child

        child1 = build_child(name1, q1, 1)
        child2 = build_child(name2, q2, 2)

        # Replace parent with both children
        self.revisable_groups = [g for g in self.revisable_groups if g.id != group_id]
        self.revisable_groups.extend([child1, child2])

        return child1, child2

    def discard_group(self, group_id: str) -> ProposedSpaceGroup:
        """Discard an unneeded proposal (RF-09)."""
        group = self.get_group(group_id)
        if group is None:
            raise ValueError(f"No se encontró el grupo con id '{group_id}'.")

        self.revisable_groups = [g for g in self.revisable_groups if g.id != group_id]
        self.discarded_groups.append(group)
        return group

    def confirm_group(self, group_id: str) -> ProposedSpaceGroup:
        """Confirm a proposal and incorporate it into confirmed_groups (RF-09).
        
        Raises ValueError if group has unresolved contradictions or missing mandatory attributes.
        """
        group = self.get_group(group_id)
        if group is None:
            raise ValueError(f"No se encontró el grupo revisable con id '{group_id}'.")

        can_confirm, reasons = check_group_confirmation_eligibility(group)
        if not can_confirm:
            reasons_str = "; ".join(reasons)
            raise ValueError(f"No se puede confirmar el grupo '{group.name}': {reasons_str}")

        self.revisable_groups = [g for g in self.revisable_groups if g.id != group_id]
        self.confirmed_groups.append(group)
        return group

    def reanalyze_without_duplicating_confirmed(
        self,
        new_analysis: ExtractionAnalysisResult,
    ) -> None:
        """Apply a new Gemini extraction result without duplicating confirmed groups (RF-10).
        
        Preserves existing confirmed groups completely.
        """
        self.original_text = new_analysis.original_text
        self.defective_groups = new_analysis.defective_groups

        # Keep existing confirmed groups untouched! (RF-10)
        # Place new proposals in revisable_groups, flagging any that match already confirmed groups
        confirmed_signatures = {
            (cg.name.lower().strip(), cg.source_fragment.strip())
            for cg in self.confirmed_groups
        }

        updated_revisable: List[ProposedSpaceGroup] = []
        for prop in new_analysis.revisable_groups:
            sig = (prop.name.lower().strip(), prop.source_fragment.strip())
            if sig in confirmed_signatures:
                prop.warnings.append("Aviso: este espacio coincide con uno ya confirmado previamente en este borrador.")
            updated_revisable.append(prop)

        self.revisable_groups = updated_revisable
