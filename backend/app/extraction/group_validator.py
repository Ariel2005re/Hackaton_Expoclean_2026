"""Validation of proposed space groups and separation of revisable vs. defective groups (RF-07, RF-08, RF-09, RF-29).

Rules:
- A group is REVISABLE if it identifies a space with a name or type backed by a text snippet,
  and its present values can be represented, even if mandatory attributes are missing.
- A group is DEFECTIVE if it lacks identification or contains unrepresentable data.
- Defective groups are flagged and isolated without being incorporated into confirmed groups.
- If all groups are defective (or no groups found), fallback_to_manual is triggered (RF-29 / RF-11).
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


def validate_proposed_group(
    raw_group: Dict[str, Any],
    index: int = 1,
) -> Tuple[Optional[ProposedSpaceGroup], Optional[DefectiveSpaceGroup]]:
    """Validate a single space group proposal from Gemini.
    
    Returns:
        (ProposedSpaceGroup, None) if revisable, or (None, DefectiveSpaceGroup) if defective.
    """
    defect_reasons: List[str] = []

    # 1. Check space identification (RF-09, RF-29)
    name = raw_group.get("name")
    if not name or not isinstance(name, str) or not name.strip():
        defect_reasons.append("Falta el nombre o tipo de espacio identificado.")
    else:
        name = name.strip()

    source_fragment = raw_group.get("source_fragment")
    if not source_fragment or not isinstance(source_fragment, str) or not source_fragment.strip():
        defect_reasons.append("Carece de fragmento de texto de respaldo para el espacio.")
    else:
        source_fragment = source_fragment.strip()

    # 2. Check numeric representability (RF-29)
    quantity = raw_group.get("quantity")
    if quantity is not None:
        try:
            quantity = int(quantity)
            if quantity <= 0:
                defect_reasons.append(f"La cantidad debe ser un entero positivo (recibido: {quantity}).")
        except (ValueError, TypeError):
            defect_reasons.append(f"Cantidad no numérica o inválida (recibido: {quantity}).")

    unit_area = raw_group.get("unit_area_m2")
    if unit_area is not None:
        try:
            unit_area = float(unit_area)
            if unit_area <= 0:
                defect_reasons.append(f"La superficie por unidad debe ser positiva (recibido: {unit_area}).")
        except (ValueError, TypeError):
            defect_reasons.append(f"Superficie por unidad no numérica o inválida (recibido: {unit_area}).")

    total_area = raw_group.get("total_area_m2")
    if total_area is not None:
        try:
            total_area = float(total_area)
            if total_area <= 0:
                defect_reasons.append(f"La superficie total debe ser positiva (recibido: {total_area}).")
        except (ValueError, TypeError):
            defect_reasons.append(f"Superficie total no numérica o inválida (recibido: {total_area}).")

    visits_per_day = raw_group.get("visits_per_day")
    if visits_per_day is not None:
        try:
            visits_per_day = int(visits_per_day)
            if visits_per_day <= 0:
                defect_reasons.append(f"Las visitas por día deben ser un entero positivo (recibido: {visits_per_day}).")
        except (ValueError, TypeError):
            defect_reasons.append(f"Visitas por día no numéricas (recibido: {visits_per_day}).")

    # If any defect was found, classify as defective (RF-09, RF-29)
    if defect_reasons:
        return None, DefectiveSpaceGroup(raw_data=raw_group, defect_reasons=defect_reasons)

    # 3. Build revisable group with attribute provenance (RF-07, RF-08, RF-09)
    warnings: List[str] = []
    attributes: Dict[str, AttributeProvenance] = {}

    # Attribute: name
    attributes["name"] = AttributeProvenance(
        value=name,
        condition=AttributeCondition.EXPLICIT,
        source_fragment=source_fragment,
    )

    # Attribute: quantity
    if quantity is not None:
        attributes["quantity"] = AttributeProvenance(
            value=quantity,
            condition=AttributeCondition.EXPLICIT,
            source_fragment=source_fragment,
        )
    else:
        attributes["quantity"] = AttributeProvenance(
            value=None,
            condition=AttributeCondition.ABSENT,
        )
        warnings.append("Cantidad no especificada en el texto; pendiente de completar.")

    # Attribute: unit_area_m2 & total_area_m2 with explicit derivation (RF-07)
    if unit_area is not None:
        attributes["unit_area_m2"] = AttributeProvenance(
            value=unit_area,
            condition=AttributeCondition.EXPLICIT,
            source_fragment=source_fragment,
        )
    elif total_area is not None and quantity is not None and quantity > 0:
        # Derivation: e.g. 280 m² ÷ 8 oficinas = 35 m² por unidad
        unit_area = round(total_area / quantity, 2)
        operation = f"{total_area:g} m² ÷ {quantity} {name} = {unit_area:g} m² por unidad"
        attributes["unit_area_m2"] = AttributeProvenance(
            value=unit_area,
            condition=AttributeCondition.DERIVED,
            source_fragment=source_fragment,
            operation=operation,
        )
        warnings.append(f"Superficie por unidad derivada: {operation}.")
    else:
        attributes["unit_area_m2"] = AttributeProvenance(
            value=None,
            condition=AttributeCondition.ABSENT,
        )
        warnings.append("Superficie no especificada en el texto; pendiente de completar.")

    if total_area is not None:
        attributes["total_area_m2"] = AttributeProvenance(
            value=total_area,
            condition=AttributeCondition.EXPLICIT,
            source_fragment=source_fragment,
        )

    # Attribute: condition (bueno, regular, malo, contradictorio o ausente)
    raw_condition = raw_group.get("condition")
    conflicting_conds = raw_group.get("conflicting_conditions")
    if conflicting_conds and len(conflicting_conds) > 1:
        # Contradiction detected (RF-08)
        attributes["condition"] = AttributeProvenance(
            value=None,
            condition=AttributeCondition.CONTRADICTORY,
            source_fragment=source_fragment,
            conflicting_values=conflicting_conds,
        )
        warnings.append(
            f"Conflicto de estado detectado ({', '.join(str(c) for c in conflicting_conds)}). "
            "Requiere resolución humana."
        )
        condition_val = None
    elif raw_condition in ("bueno", "regular", "malo"):
        attributes["condition"] = AttributeProvenance(
            value=raw_condition,
            condition=AttributeCondition.EXPLICIT,
            source_fragment=source_fragment,
        )
        condition_val = raw_condition
    else:
        attributes["condition"] = AttributeProvenance(
            value=None,
            condition=AttributeCondition.ABSENT,
        )
        condition_val = None
        warnings.append("Estado físico (bueno/regular/malo) ausente; pendiente de seleccionar.")

    # Attribute: cleaning_type
    cleaning_type = raw_group.get("cleaning_type")
    if cleaning_type in ("general", "especializado"):
        attributes["cleaning_type"] = AttributeProvenance(
            value=cleaning_type,
            condition=AttributeCondition.EXPLICIT,
            source_fragment=source_fragment,
        )
    else:
        attributes["cleaning_type"] = AttributeProvenance(
            value="general",
            condition=AttributeCondition.EXPLICIT,
            source_fragment=source_fragment,
        )
        cleaning_type = "general"

    # Attribute: visits_per_day
    if visits_per_day is not None:
        attributes["visits_per_day"] = AttributeProvenance(
            value=visits_per_day,
            condition=AttributeCondition.EXPLICIT,
            source_fragment=source_fragment,
        )
    else:
        attributes["visits_per_day"] = AttributeProvenance(
            value=None,
            condition=AttributeCondition.ABSENT,
        )

    # Attribute: service_days
    service_days = raw_group.get("service_days")
    if service_days and isinstance(service_days, list):
        attributes["service_days"] = AttributeProvenance(
            value=service_days,
            condition=AttributeCondition.EXPLICIT,
            source_fragment=source_fragment,
        )
    else:
        attributes["service_days"] = AttributeProvenance(
            value=None,
            condition=AttributeCondition.ABSENT,
        )
        service_days = None

    proposal = ProposedSpaceGroup(
        id=str(uuid.uuid4()),
        name=name,
        quantity=quantity,
        unit_area_m2=unit_area,
        total_area_m2=total_area,
        condition=condition_val,
        cleaning_type=cleaning_type,
        service_days=service_days,
        visits_per_day=visits_per_day,
        source_fragment=source_fragment,
        attributes=attributes,
        is_revisable=True,
        warnings=warnings,
    )
    return proposal, None


def parse_extraction_response(
    raw_response: Dict[str, Any],
    original_text: str = "",
) -> ExtractionAnalysisResult:
    """Validate each proposed group separately and produce ExtractionAnalysisResult (RF-09, RF-29).
    
    - Separates revisable proposals from defective proposals.
    - If no revisable proposals exist, flags fallback_to_manual (RF-29 / RF-11).
    """
    raw_spaces = raw_response.get("spaces", [])
    revisable_groups: List[ProposedSpaceGroup] = []
    defective_groups: List[DefectiveSpaceGroup] = []
    warnings: List[str] = []

    for idx, raw_group in enumerate(raw_spaces, start=1):
        if not isinstance(raw_group, dict):
            defective_groups.append(
                DefectiveSpaceGroup(
                    raw_data={"raw": raw_group},
                    defect_reasons=["El elemento no tiene estructura de diccionario."],
                )
            )
            continue

        revisable, defective = validate_proposed_group(raw_group, index=idx)
        if revisable is not None:
            revisable_groups.append(revisable)
        elif defective is not None:
            defective_groups.append(defective)

    has_revisable = len(revisable_groups) > 0
    fallback_to_manual = not has_revisable

    if defective_groups:
        warnings.append(
            f"Se detectaron {len(defective_groups)} grupo(s) defectuoso(s) que no fueron incorporados."
        )

    if not has_revisable:
        warnings.append(
            "No se identificaron propuestas revisables en la respuesta de Gemini. "
            "Se conserva el texto y el borrador para continuar mediante el formulario manual (RF-11, RF-29)."
        )

    return ExtractionAnalysisResult(
        original_text=original_text,
        revisable_groups=revisable_groups,
        defective_groups=defective_groups,
        has_revisable_groups=has_revisable,
        fallback_to_manual=fallback_to_manual,
        warnings=warnings,
    )
