"""FastAPI router for assisted extraction and proposal review (Task C06 · RF-06, RF-09–RF-11, RF-29–RF-31)."""

from fastapi import APIRouter, File, HTTPException, UploadFile
from pydantic import BaseModel

from backend.app.extraction.models import (
    AnalyzeSpacesPayload,
    ConfirmReviewPayload,
    CorrectReviewPayload,
    DiscardReviewPayload,
    ExtractionInputRequest,
    ExtractionServiceResponse,
    MergeReviewPayload,
    ReviewSessionState,
    SplitReviewPayload,
    TextValidationResult,
)
from backend.app.extraction.proposal_manager import ProposalReviewSession
from backend.app.extraction.service import ExtractionService
from backend.app.extraction.validator import (
    validate_confirmed_text,
    validate_txt_file,
)

extraction_router = APIRouter(prefix="/extraction", tags=["extraction"])

_global_service = ExtractionService()


def get_extraction_service() -> ExtractionService:
    return _global_service


@extraction_router.post(
    "/analyze",
    response_model=ExtractionServiceResponse,
    summary="Analizar texto confirmado con Gemini (RF-06, RF-29, RF-30)",
)
def analyze_spaces(
    payload: AnalyzeSpacesPayload,
) -> ExtractionServiceResponse:
    """Analyze confirmed space description using Gemini with fallback and distinguishable statuses."""
    service = get_extraction_service()
    req = ExtractionInputRequest(
        text=payload.text,
        confirmed=payload.confirmed,
        personal_data_warning_acknowledged=payload.personal_data_warning_acknowledged,
    )
    return service.analyze_description(req, existing_confirmed_groups=payload.existing_confirmed)


class ValidateTextPayload(BaseModel):
    text: str


@extraction_router.post(
    "/validate-text",
    response_model=TextValidationResult,
    summary="Validar texto antes de confirmar envío (RF-30, RF-31)",
)
def validate_text(payload: ValidateTextPayload) -> TextValidationResult:
    """Check text length, blanks, and Unicode code points without sending to Gemini."""
    return validate_confirmed_text(payload.text, strict=False)


@extraction_router.post(
    "/upload-txt",
    response_model=TextValidationResult,
    summary="Cargar y validar archivo TXT UTF-8 (RF-31)",
)
async def upload_txt(file: UploadFile = File(...)) -> TextValidationResult:
    """Read TXT file bytes, ensure UTF-8 encoding, and validate content limits."""
    content_bytes = await file.read()
    return validate_txt_file(content_bytes, filename=file.filename, strict=False)


def _review_session(state: ReviewSessionState) -> ProposalReviewSession:
    session = ProposalReviewSession(
        original_text=state.original_text,
        revisable_groups=list(state.revisable_groups),
        defective_groups=list(state.defective_groups),
        confirmed_groups=list(state.confirmed_groups),
    )
    session.discarded_groups = list(state.discarded_groups)
    return session


def _review_state(session: ProposalReviewSession) -> ReviewSessionState:
    return ReviewSessionState(
        original_text=session.original_text,
        revisable_groups=session.revisable_groups,
        defective_groups=session.defective_groups,
        confirmed_groups=session.confirmed_groups,
        discarded_groups=session.discarded_groups,
    )


@extraction_router.post("/review/correct", response_model=ReviewSessionState)
def correct_review(payload: CorrectReviewPayload) -> ReviewSessionState:
    session = _review_session(payload.session)
    try:
        session.correct_attribute(**payload.action.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _review_state(session)


@extraction_router.post("/review/merge", response_model=ReviewSessionState)
def merge_review(payload: MergeReviewPayload) -> ReviewSessionState:
    session = _review_session(payload.session)
    try:
        session.merge_groups(**payload.action.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _review_state(session)


@extraction_router.post("/review/split", response_model=ReviewSessionState)
def split_review(payload: SplitReviewPayload) -> ReviewSessionState:
    session = _review_session(payload.session)
    try:
        session.split_group(**payload.action.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _review_state(session)


@extraction_router.post("/review/discard", response_model=ReviewSessionState)
def discard_review(payload: DiscardReviewPayload) -> ReviewSessionState:
    session = _review_session(payload.session)
    try:
        session.discard_group(**payload.action.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _review_state(session)


@extraction_router.post("/review/confirm", response_model=ReviewSessionState)
def confirm_review(payload: ConfirmReviewPayload) -> ReviewSessionState:
    session = _review_session(payload.session)
    try:
        session.confirm_group(**payload.action.model_dump())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _review_state(session)
