"""Data models for text extraction input, proposal validation, and attribute provenance (RF-06, RF-07, RF-08, RF-09, RF-29, RF-30, RF-31)."""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class TextValidationResult(BaseModel):
    """Result of validating confirmed text or uploaded TXT content."""
    is_valid: bool
    code_point_count: int = Field(ge=0, description="Unicode code points count")
    text: str = Field(default="", description="Original preserved text")
    error_message: Optional[str] = None
    error_code: Optional[str] = None


class ExtractionInputRequest(BaseModel):
    """Request payload containing confirmed text to send to Gemini (RF-30)."""
    text: str = Field(description="Exact text to analyze")
    confirmed: bool = Field(
        default=False,
        description="Explicit user confirmation after review and personal data warning"
    )
    personal_data_warning_acknowledged: bool = Field(
        default=False,
        description="Acknowledged warning that text may contain personal data"
    )


class AttributeCondition(str, Enum):
    """Condition of an extracted attribute (RF-07, RF-08, RF-09)."""
    EXPLICIT = "explicit"
    DERIVED = "derived"
    ABSENT = "absent"
    CONTRADICTORY = "contradictory"
    HUMAN_CORRECTED = "human_corrected"


class AttributeProvenance(BaseModel):
    """Provenance and evidence of a proposed space attribute (RF-07, RF-09)."""
    value: Any = None
    condition: AttributeCondition
    source_fragment: Optional[str] = None
    operation: Optional[str] = None
    origin_values: Optional[Dict[str, Any]] = None
    conflicting_values: Optional[List[Any]] = None


class ProposedSpaceGroup(BaseModel):
    """A valid, revisable space group proposal extracted from text (RF-09, RF-29)."""
    id: str = Field(description="Unique proposal identifier")
    name: str = Field(description="Name or type of space (e.g. oficinas, bodegas)")
    quantity: Optional[int] = None
    unit_area_m2: Optional[float] = None
    total_area_m2: Optional[float] = None
    condition: Optional[str] = None  # bueno, regular, malo
    cleaning_type: Optional[str] = None  # general, especializado
    service_days: Optional[List[str]] = None
    visits_per_day: Optional[int] = None
    source_fragment: str = Field(description="Text snippet identifying the space")
    attributes: Dict[str, AttributeProvenance] = Field(default_factory=dict)
    is_revisable: bool = Field(default=True)
    can_be_confirmed: bool = Field(
        default=False,
        description="Whether group has all mandatory attributes and no unresolved contradictions"
    )
    warnings: List[str] = Field(default_factory=list)



class DefectiveSpaceGroup(BaseModel):
    """A defective proposal that cannot be represented or lacks identification (RF-09, RF-29)."""
    raw_data: Dict[str, Any] = Field(default_factory=dict)
    defect_reasons: List[str] = Field(default_factory=list)
    is_revisable: bool = Field(default=False)


class ExtractionAnalysisResult(BaseModel):
    """Full extraction analysis result containing revisable and defective proposals (RF-09, RF-29)."""
    original_text: str
    revisable_groups: List[ProposedSpaceGroup] = Field(default_factory=list)
    defective_groups: List[DefectiveSpaceGroup] = Field(default_factory=list)
    has_revisable_groups: bool = Field(default=False)
    fallback_to_manual: bool = Field(default=False)
    warnings: List[str] = Field(default_factory=list)
