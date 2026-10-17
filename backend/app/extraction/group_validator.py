"""Validation of proposed space groups and separation of revisable vs. defective groups (RF-07, RF-08, RF-09, RF-29).

Rules:
- A group is REVISABLE if it identifies a space with a name or type backed by a text snippet,
  and its present values can be represented, even if mandatory attributes are missing.
- A group is DEFECTIVE if it lacks identification or contains unrepresentable data.
- Defective groups are flagged and isolated without being incorporated into confirmed groups.
- If all groups are defective (or no groups found), fallback_to_manual is triggered (RF-29 / RF-11).
"""

import math
import re
import uuid
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Optional, Tuple

from backend.app.extraction.models import (
    AttributeCondition,
    AttributeProvenance,
    DefectiveSpaceGroup,
    ExtractionAnalysisResult,
    ProposedSpaceGroup,
)


def _positive_integer(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean is not an integer quantity")
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ValueError("not numeric") from None
    if not number.is_finite() or number != number.to_integral_value() or number <= 0:
        raise ValueError("not a positive integer")
    return int(number)


def _positive_area(value: Any) -> float:
    if isinstance(value, bool):
        raise ValueError("boolean is not an area")
    try:
        number = float(value)
    except (ValueError, TypeError, OverflowError):
        raise ValueError("not numeric") from None
    if not math.isfinite(number) or number <= 0:
        raise ValueError("not a finite positive area")
    return number


def _number_is_backed(value: int | float, fragment: str) -> bool:
    number = format(value, "g")
    pattern = rf"(?<!\d){re.escape(number).replace(r'\.', '[.,]')}(?!\d)"
    return re.search(pattern, fragment) is not None


def _condition_is_backed(value: str, fragment: str) -> bool:
    words = {
        "bueno": ("bueno", "buena", "buen"),
        "regular": ("regular",),
        "malo": ("malo", "mala", "mal"),
    }[value]
    return any(re.search(rf"\b{word}\b", fragment.casefold()) for word in words)


def _visits_are_backed(value: int, fragment: str) -> bool:
    number = str(value)
    return bool(
        re.search(rf"\b{number}\s+(?:visitas?|veces)\b", fragment.casefold())
        or re.search(rf"\b(?:visitas?|veces)\s+{number}\b", fragment.casefold())
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
            quantity = _positive_integer(quantity)
        except ValueError:
            defect_reasons.append(f"Cantidad no numérica o inválida (recibido: {quantity}).")

    unit_area = raw_group.get("unit_area_m2")
    if unit_area is not None:
        try:
            unit_area = _positive_area(unit_area)
        except ValueError:
            defect_reasons.append(f"Superficie por unidad no numérica o inválida (recibido: {unit_area}).")

    total_area = raw_group.get("total_area_m2")
    if total_area is not None:
        try:
            total_area = _positive_area(total_area)
        except ValueError:
            defect_reasons.append(f"Superficie total no numérica o inválida (recibido: {total_area}).")

    visits_per_day = raw_group.get("visits_per_day")
    if visits_per_day is not None:
        try:
            visits_per_day = _positive_integer(visits_per_day)
        except ValueError:
            defect_reasons.append(f"Visitas por día no numéricas (recibido: {visits_per_day}).")

    raw_condition = raw_group.get("condition")
    if raw_condition is not None and raw_condition not in ("bueno", "regular", "malo"):
        defect_reasons.append("El estado propuesto no puede representarse.")
    cleaning_type = raw_group.get("cleaning_type")
    if cleaning_type is not None and cleaning_type not in ("general", "especializado"):
        defect_reasons.append("El tipo de trabajo propuesto no puede representarse.")
    service_days = raw_group.get("service_days")
    if service_days is not None and (
        not isinstance(service_days, list)
        or any(not isinstance(day, str) or not day.strip() for day in service_days)
    ):
        defect_reasons.append("Los días de servicio propuestos no pueden representarse.")
    conflicting_conds = raw_group.get("conflicting_conditions")
    if conflicting_conds is not None and (
        not isinstance(conflicting_conds, list)
        or any(not isinstance(value, str) for value in conflicting_conds)
    ):
        defect_reasons.append("Los valores contradictorios no pueden representarse.")

    # If any defect was found, classify as defective (RF-09, RF-29)
    if defect_reasons:
        return None, DefectiveSpaceGroup(raw_data=raw_group, defect_reasons=defect_reasons)

    # 3. Build revisable group with attribute provenance (RF-07, RF-08, RF-09)
    warnings: List[str] = []
    attributes: Dict[str, AttributeProvenance] = {}

    for field, value in (("quantity", quantity), ("unit_area_m2", unit_area),
                         ("total_area_m2", total_area), ("visits_per_day", visits_per_day)):
        if value is not None and not _number_is_backed(value, source_fragment):
            warnings.append(f"{field} no tiene respaldo numérico en el fragmento; queda pendiente de revisión.")
            if field == "quantity":
                quantity = None
            elif field == "unit_area_m2":
                unit_area = None
            elif field == "total_area_m2":
                total_area = None
            else:
                visits_per_day = None
    if visits_per_day is not None and not _visits_are_backed(visits_per_day, source_fragment):
        visits_per_day = None
        warnings.append("Las visitas por día no tienen respaldo en el fragmento; quedan pendientes.")
    if service_days and any(day.casefold() not in source_fragment.casefold() for day in service_days):
        service_days = None
        warnings.append("Los días de servicio no tienen respaldo en el fragmento; quedan pendientes.")

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
        if total_area is None and quantity is not None and quantity > 0:
            from backend.app.extraction.provenance import derive_total_area
            total_area, total_prov = derive_total_area(name, unit_area, quantity, source_fragment)
            attributes["total_area_m2"] = total_prov
            warnings.append(f"Superficie total derivada: {total_prov.operation}.")
    elif total_area is not None and quantity is not None and quantity > 0:
        # Derivation: e.g. 280 m² ÷ 8 oficinas = 35 m² por unidad (RF-07)
        from backend.app.extraction.provenance import derive_unit_area
        unit_area, unit_prov = derive_unit_area(name, total_area, quantity, source_fragment)
        attributes["unit_area_m2"] = unit_prov
        warnings.append(f"Superficie por unidad derivada: {unit_prov.operation}.")
    else:
        attributes["unit_area_m2"] = AttributeProvenance(
            value=None,
            condition=AttributeCondition.ABSENT,
        )
        warnings.append("Superficie no especificada en el texto; pendiente de completar.")

    if total_area is not None and "total_area_m2" not in attributes:
        attributes["total_area_m2"] = AttributeProvenance(
            value=total_area,
            condition=AttributeCondition.EXPLICIT,
            source_fragment=source_fragment,
        )

    # Attribute: condition (bueno, regular, malo, contradictorio o ausente)
    if conflicting_conds and len(conflicting_conds) > 1:
        # Contradiction detected (RF-08)
        from backend.app.extraction.provenance import build_contradictory_provenance
        attributes["condition"] = build_contradictory_provenance(
            conflicting_values=conflicting_conds,
            source_fragment=source_fragment,
        )
        warnings.append(
            f"Conflicto de estado detectado ({', '.join(str(c) for c in conflicting_conds)}). "
            "Requiere resolución humana."
        )
        condition_val = None
    elif raw_condition in ("bueno", "regular", "malo") and _condition_is_backed(raw_condition, source_fragment):
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
    if cleaning_type in ("general", "especializado") and cleaning_type in source_fragment.casefold():
        attributes["cleaning_type"] = AttributeProvenance(
            value=cleaning_type,
            condition=AttributeCondition.EXPLICIT,
            source_fragment=source_fragment,
        )
    else:
        attributes["cleaning_type"] = AttributeProvenance(
            value=None,
            condition=AttributeCondition.ABSENT,
        )
        cleaning_type = None
        warnings.append("Tipo de trabajo no especificado en el texto; pendiente de completar.")

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
        can_be_confirmed=False,
        warnings=warnings,
    )

    from backend.app.extraction.provenance import check_group_confirmation_eligibility
    can_confirm, _ = check_group_confirmation_eligibility(proposal)
    proposal.can_be_confirmed = can_confirm

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

    if not isinstance(raw_spaces, list):
        raw_spaces = []
        warnings.append("La respuesta de Gemini no contiene una lista de espacios revisable.")

    for idx, raw_group in enumerate(raw_spaces, start=1):
        if not isinstance(raw_group, dict):
            defective_groups.append(
                DefectiveSpaceGroup(
                    raw_data={"raw": raw_group},
                    defect_reasons=["El elemento no tiene estructura de diccionario."],
                )
            )
            continue

        fragment = raw_group.get("source_fragment")
        if original_text and isinstance(fragment, str) and fragment.strip() and fragment.strip().casefold() not in original_text.casefold():
            defective_groups.append(
                DefectiveSpaceGroup(
                    raw_data=raw_group,
                    defect_reasons=["El fragmento de respaldo del espacio no aparece en el texto confirmado."],
                )
            )
            continue
        name = raw_group.get("name")
        if isinstance(name, str) and isinstance(fragment, str) and name.strip() and name.strip().casefold() not in fragment.casefold():
            defective_groups.append(
                DefectiveSpaceGroup(
                    raw_data=raw_group,
                    defect_reasons=["El nombre o tipo de espacio no tiene respaldo en el fragmento."],
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
