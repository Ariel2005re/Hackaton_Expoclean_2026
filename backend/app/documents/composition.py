"""E01: compose a customer quotation PDF from a fixed commercial snapshot.

The caller supplies already calculated dates and amounts. Validation, pricing,
version identity, and persistence belong to later tasks.
"""

from dataclasses import dataclass
from decimal import Decimal
from html import escape
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


@dataclass(frozen=True)
class GroupSchedule:
    spaces: str
    days: str
    visits_per_day: int
    hours: str


@dataclass(frozen=True)
class QuotePdfSnapshot:
    company: str
    client: str
    service_address: str
    scope: str
    period: str
    groups: tuple[GroupSchedule, ...]
    subtotal: Decimal
    tax: Decimal
    total: Decimal


_INK = colors.HexColor("#172B3A")
_MUTED = colors.HexColor("#526473")
_ACCENT = colors.HexColor("#087F8C")
_LIGHT = colors.HexColor("#EAF4F5")
_RULE = colors.HexColor("#D7E2E6")

_TITLE = ParagraphStyle(
    "Title",
    fontName="Helvetica-Bold",
    fontSize=19,
    leading=23,
    textColor=_INK,
    spaceAfter=4 * mm,
)
_SECTION = ParagraphStyle(
    "Section",
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=13,
    textColor=_ACCENT,
    spaceBefore=6 * mm,
    spaceAfter=2 * mm,
)
_BODY = ParagraphStyle(
    "Body",
    fontName="Helvetica",
    fontSize=9,
    leading=13,
    textColor=_INK,
)
_LABEL = ParagraphStyle(
    "Label",
    parent=_BODY,
    fontName="Helvetica-Bold",
    textColor=_MUTED,
)
_TABLE_HEADER = ParagraphStyle(
    "TableHeader",
    parent=_BODY,
    fontName="Helvetica-Bold",
    fontSize=8,
    textColor=_INK,
)
_AMOUNT = ParagraphStyle(
    "Amount",
    parent=_BODY,
    alignment=TA_RIGHT,
)
_TOTAL = ParagraphStyle(
    "Total",
    parent=_AMOUNT,
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=15,
    textColor=_ACCENT,
)


def _paragraph(value: str, style: ParagraphStyle = _BODY) -> Paragraph:
    return Paragraph(escape(value).replace("\n", "<br/>"), style)


def _money(value: Decimal) -> str:
    return f"USD {value:,.2f}"


def _footer(canvas, document):
    canvas.saveState()
    width, _ = A4
    canvas.setStrokeColor(_RULE)
    canvas.line(18 * mm, 17 * mm, width - 18 * mm, 17 * mm)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(_MUTED)
    canvas.drawString(18 * mm, 12 * mm, "Cotización de servicio")
    canvas.drawRightString(width - 18 * mm, 12 * mm, f"Página {document.page}")
    canvas.restoreState()


def compose_quote_pdf(snapshot: QuotePdfSnapshot) -> bytes:
    """Return an A4 PDF containing the supplied customer-facing quote data."""
    stream = BytesIO()
    document = SimpleDocTemplate(
        stream,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=19 * mm,
        bottomMargin=25 * mm,
        title="Cotización de servicio",
        author=snapshot.company,
    )
    content_width = A4[0] - 36 * mm
    story = [
        _paragraph(snapshot.company, _LABEL),
        Spacer(1, 3 * mm),
        _paragraph("COTIZACIÓN DE SERVICIO", _TITLE),
        HRFlowable(width="100%", thickness=1.2, color=_ACCENT),
        _paragraph("Cliente", _SECTION),
        _paragraph(snapshot.client),
        _paragraph("Dirección del servicio", _SECTION),
        _paragraph(snapshot.service_address),
        _paragraph("Alcance", _SECTION),
        _paragraph(snapshot.scope),
        _paragraph("Período", _SECTION),
        _paragraph(snapshot.period),
        _paragraph("Calendario por grupo", _SECTION),
    ]

    rows = [[
        _paragraph("Espacios", _TABLE_HEADER),
        _paragraph("Días de servicio", _TABLE_HEADER),
        _paragraph("Visitas", _TABLE_HEADER),
        _paragraph("Horario", _TABLE_HEADER),
    ]]
    for group in snapshot.groups:
        visit_word = "visita" if group.visits_per_day == 1 else "visitas"
        rows.append([
            _paragraph(group.spaces),
            _paragraph(group.days),
            _paragraph(f"{group.visits_per_day} {visit_word} por día"),
            _paragraph(group.hours),
        ])
    calendar = Table(
        rows,
        colWidths=[content_width * fraction for fraction in (0.29, 0.30, 0.20, 0.21)],
        hAlign="LEFT",
        repeatRows=1,
    )
    calendar.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), _LIGHT),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
        ("RIGHTPADDING", (0, 0), (-1, -1), 8),
        ("TOPPADDING", (0, 0), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
        ("LINEBELOW", (0, 0), (-1, 0), 0.7, _ACCENT),
        ("LINEBELOW", (0, 1), (-1, -1), 0.4, _RULE),
    ]))
    story.extend([calendar, Spacer(1, 7 * mm)])

    amounts = Table(
        [
            [_paragraph("Subtotal", _LABEL), _paragraph(_money(snapshot.subtotal), _AMOUNT)],
            [_paragraph("Impuestos", _LABEL), _paragraph(_money(snapshot.tax), _AMOUNT)],
            [_paragraph("Total", _TOTAL), _paragraph(_money(snapshot.total), _TOTAL)],
        ],
        colWidths=[content_width * 0.55, content_width * 0.45],
        hAlign="RIGHT",
    )
    amounts.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("LINEABOVE", (0, 2), (-1, 2), 0.8, _ACCENT),
    ]))
    story.append(amounts)

    document.build(story, onFirstPage=_footer, onLaterPages=_footer)
    return stream.getvalue()
