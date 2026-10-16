"""High-level extraction service coordinating validation, Gemini client, and review lifecycle (Task C06 · RF-06, RF-09–RF-11, RF-29–RF-31).

Guarantees:
- Distinguishes clearly between SUCCESS, PARTIAL_SUCCESS, REJECTED, TIMEOUT, UNAVAILABLE, and UNUSABLE.
- Preserves the original text and existing confirmed groups across all failure and success modes.
- Never allows an error or timeout to wipe out work or block the manual quotation workflow.
"""

from typing import List, Optional

from backend.app.extraction.client import GeminiExtractionClient
from backend.app.extraction.exceptions import (
    ConfirmationRequiredError,
    ExtractionValidationError,
    GeminiQuotaExceededError,
    GeminiRejectionError,
    GeminiTimeoutError,
    GeminiUnavailableError,
    GeminiUnusableResponseError,
)
from backend.app.extraction.group_validator import parse_extraction_response
from backend.app.extraction.models import (
    AnalysisStatus,
    ExtractionInputRequest,
    ExtractionServiceResponse,
    ProposedSpaceGroup,
)
from backend.app.extraction.proposal_manager import ProposalReviewSession
from backend.app.extraction.validator import validate_extraction_request


class ExtractionService:
    """Service facade exposing assisted extraction and review operations."""

    def __init__(self, client: Optional[GeminiExtractionClient] = None):
        self.client = client or GeminiExtractionClient()

    def analyze_description(
        self,
        request: ExtractionInputRequest,
        existing_confirmed_groups: Optional[List[ProposedSpaceGroup]] = None,
    ) -> ExtractionServiceResponse:
        """Process confirmed text extraction request and return typed, distinguishable status response (C06)."""
        confirmed_groups = list(existing_confirmed_groups or [])

        # 1. Validate request (RF-30, RF-31)
        try:
            validate_extraction_request(request, strict=True)
        except ConfirmationRequiredError as exc:
            return ExtractionServiceResponse(
                status=AnalysisStatus.REJECTED,
                original_text=request.text,
                confirmed_groups=confirmed_groups,
                fallback_to_manual=True,
                message=exc.message,
                error_code="CONFIRMATION_REQUIRED",
                warnings=["Se requiere confirmación explícita del texto antes de enviar a Gemini."],
            )
        except ExtractionValidationError as exc:
            return ExtractionServiceResponse(
                status=AnalysisStatus.VALIDATION_ERROR,
                original_text=request.text,
                confirmed_groups=confirmed_groups,
                fallback_to_manual=True,
                message=exc.message,
                error_code=exc.code,
                warnings=[exc.message],
            )

        # 2. Call Gemini server-side with failure handling (RF-11, RF-29)
        try:
            raw_response = self.client.call_gemini(request.text)
        except GeminiTimeoutError as exc:
            return ExtractionServiceResponse(
                status=AnalysisStatus.TIMEOUT,
                original_text=request.text,
                confirmed_groups=confirmed_groups,
                fallback_to_manual=True,
                message=exc.message,
                error_code=exc.code,
                warnings=["Tiempo de espera excedido. El borrador y el texto están a salvo para continuar manualmente."],
            )
        except GeminiRejectionError as exc:
            return ExtractionServiceResponse(
                status=AnalysisStatus.REJECTED,
                original_text=request.text,
                confirmed_groups=confirmed_groups,
                fallback_to_manual=True,
                message=exc.message,
                error_code=exc.code,
                warnings=["Solicitud rechazada por filtros de seguridad. Puede ingresar los datos en el formulario manual."],
            )
        except (GeminiUnavailableError, GeminiQuotaExceededError) as exc:
            return ExtractionServiceResponse(
                status=AnalysisStatus.UNAVAILABLE,
                original_text=request.text,
                confirmed_groups=confirmed_groups,
                fallback_to_manual=True,
                message=exc.message,
                error_code=exc.code,
                warnings=["Servicio de IA no disponible temporalmente. El camino manual permanece habilitado."],
            )
        except GeminiUnusableResponseError as exc:
            return ExtractionServiceResponse(
                status=AnalysisStatus.UNUSABLE,
                original_text=request.text,
                confirmed_groups=confirmed_groups,
                fallback_to_manual=True,
                message=exc.message,
                error_code=exc.code,
                warnings=["La IA devolvió una respuesta no utilizable. Puede continuar mediante el formulario manual."],
            )
        except Exception as exc:
            return ExtractionServiceResponse(
                status=AnalysisStatus.UNAVAILABLE,
                original_text=request.text,
                confirmed_groups=confirmed_groups,
                fallback_to_manual=True,
                message=f"Error inesperado al consultar Gemini: {exc}",
                error_code="UNEXPECTED_ERROR",
                warnings=["Ocurrió un error en el servidor. Puede continuar manualmente."],
            )

        # 3. Parse and validate proposals separately (RF-09, RF-29)
        analysis_result = parse_extraction_response(raw_response, original_text=request.text)

        # 4. Integrate into review session without duplicating confirmed groups (RF-10)
        session = ProposalReviewSession(
            original_text=request.text,
            confirmed_groups=confirmed_groups,
        )
        session.reanalyze_without_duplicating_confirmed(analysis_result)

        # 5. Determine observable status
        revisable_count = len(session.revisable_groups)
        defective_count = len(analysis_result.defective_groups)

        if revisable_count > 0 and defective_count == 0:
            status = AnalysisStatus.SUCCESS
            msg = f"Extracción exitosa: {revisable_count} grupo(s) identificados y listos para revisión."
            fallback_manual = False
        elif revisable_count > 0 and defective_count > 0:
            status = AnalysisStatus.PARTIAL_SUCCESS
            msg = f"Extracción parcial: {revisable_count} grupo(s) revisable(s) y {defective_count} defectuoso(s) señalados."
            fallback_manual = False
        else:
            status = AnalysisStatus.UNUSABLE
            msg = "No se identificaron espacios revisables en la descripción. Continúe con el formulario manual."
            fallback_manual = True

        return ExtractionServiceResponse(
            status=status,
            original_text=request.text,
            revisable_groups=session.revisable_groups,
            defective_groups=analysis_result.defective_groups,
            confirmed_groups=session.confirmed_groups,
            fallback_to_manual=fallback_manual,
            message=msg,
            warnings=analysis_result.warnings,
        )
