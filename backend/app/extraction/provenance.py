"""Attribute provenance engine and contradiction management (Task C04 · RF-07, RF-08, RF-09).

Rules:
- RF-07: Unexpressed attributes stay empty and are marked ABSENT.
         Derived attributes (e.g. 280 m² ÷ 8 oficinas = 35 m² por unidad)
         must show origin values and exact arithmetic operation.
- RF-08: Contradictory values stay in review, show all conflicting values/snippets,
         and prevent group confirmation until human resolution.
- RF-09: Every visible value has provenance: explicit, derived, absent, contradictory,
         or human_corrected.
"""

from typing import Any, Dict, List, Optional, Tuple

from backend.app.extraction.models import (
    AttributeCondition,
    AttributeProvenance,
    ProposedSpaceGroup,
)


def derive_unit_area(
    name: str,
    total_area_m2: float,
    quantity: int,
    source_fragment: Optional[str] = None,
) -> Tuple[float, AttributeProvenance]:
    """Derive unit area from total area and quantity (RF-07).
    
    Example: 280 m² ÷ 8 oficinas = 35 m² por unidad.
    """
    if quantity <= 0:
        raise ValueError("La cantidad debe ser mayor a cero para derivar la superficie unitaria.")

    unit_area = round(total_area_m2 / quantity, 2)
    operation = f"{total_area_m2:g} m² ÷ {quantity} {name} = {unit_area:g} m² por unidad"
    origin_values = {
        "total_area_m2": total_area_m2,
        "quantity": quantity,
    }

    provenance = AttributeProvenance(
        value=unit_area,
        condition=AttributeCondition.DERIVED,
        source_fragment=source_fragment,
        operation=operation,
        origin_values=origin_values,
    )
    return unit_area, provenance


def derive_total_area(
    name: str,
    unit_area_m2: float,
    quantity: int,
    source_fragment: Optional[str] = None,
) -> Tuple[float, AttributeProvenance]:
    """Derive total area from unit area and quantity (RF-07).
    
    Example: 8 oficinas × 35 m² = 280 m² en total.
    """
    if quantity <= 0 or unit_area_m2 <= 0:
        raise ValueError("Cantidad y superficie unitaria deben ser positivas.")

    total_area = round(unit_area_m2 * quantity, 2)
    operation = f"{quantity} {name} × {unit_area_m2:g} m² = {total_area:g} m² en total"
    origin_values = {
        "unit_area_m2": unit_area_m2,
        "quantity": quantity,
    }

    provenance = AttributeProvenance(
        value=total_area,
        condition=AttributeCondition.DERIVED,
        source_fragment=source_fragment,
        operation=operation,
        origin_values=origin_values,
    )
    return total_area, provenance


def build_contradictory_provenance(
    conflicting_values: List[Any],
    source_fragment: Optional[str] = None,
) -> AttributeProvenance:
    """Build provenance for an attribute with conflicting/contradictory data (RF-08)."""
    return AttributeProvenance(
        value=None,
        condition=AttributeCondition.CONTRADICTORY,
        source_fragment=source_fragment,
        conflicting_values=conflicting_values,
    )


def check_group_confirmation_eligibility(
    group: ProposedSpaceGroup,
) -> Tuple[bool, List[str]]:
    """Verify if a proposed space group is ready to be confirmed into the draft (RF-08, RF-13).
    
    Returns:
        (can_be_confirmed, blocking_reasons)
    """
    blocking_reasons: List[str] = []

    # 1. Block if any attribute is contradictory (RF-08)
    for attr_name, prov in group.attributes.items():
        if prov.condition == AttributeCondition.CONTRADICTORY:
            conflicts = prov.conflicting_values or []
            blocking_reasons.append(
                f"El atributo '{attr_name}' tiene valores contradictorios ({conflicts}) "
                "y requiere resolución humana antes de confirmar."
            )

    # 2. Block if mandatory attributes are absent
    if not group.name or not group.name.strip():
        blocking_reasons.append("Falta el nombre del grupo.")

    if group.quantity is None or group.quantity <= 0:
        blocking_reasons.append("Falta la cantidad de espacios o no es positiva.")

    if group.unit_area_m2 is None or group.unit_area_m2 <= 0:
        blocking_reasons.append("Falta la superficie en m² por unidad o no es positiva.")

    can_confirm = len(blocking_reasons) == 0
    return can_confirm, blocking_reasons


def resolve_contradiction(
    group: ProposedSpaceGroup,
    attribute_name: str,
    chosen_value: Any,
    human_note: Optional[str] = None,
) -> ProposedSpaceGroup:
    """Resolve a contradictory attribute with human decision (RF-08, RF-09).
    
    Transitions the attribute condition from CONTRADICTORY to HUMAN_CORRECTED,
    preserving evidence and updating confirmation eligibility.
    """
    prov = group.attributes.get(attribute_name)
    if prov is None or prov.condition != AttributeCondition.CONTRADICTORY:
        raise ValueError(f"El atributo '{attribute_name}' no presenta un conflicto contradictorio.")

    # Record resolution with original conflict preserved
    resolved_prov = AttributeProvenance(
        value=chosen_value,
        condition=AttributeCondition.HUMAN_CORRECTED,
        source_fragment=prov.source_fragment,
        conflicting_values=prov.conflicting_values,
        operation=f"Resolución humana: seleccionado '{chosen_value}'" + (f" ({human_note})" if human_note else ""),
    )

    group.attributes[attribute_name] = resolved_prov

    # Also update top-level field if standard attribute
    if hasattr(group, attribute_name):
        setattr(group, attribute_name, chosen_value)

    # Re-evaluate confirmation readiness
    is_eligible, _ = check_group_confirmation_eligibility(group)
    group.can_be_confirmed = is_eligible

    return group
