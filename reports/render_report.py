"""Render the assignment Markdown as a paginated PDF using ReportLab."""

from html import escape
from pathlib import Path
import re

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    Preformatted,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


REPORT_DIR = Path(__file__).parent
SOURCE = REPORT_DIR / "assignment_report.md"
OUTPUT = REPORT_DIR / "assignment_report.pdf"

styles = getSampleStyleSheet()
styles.add(ParagraphStyle(
    name="ReportTitle", parent=styles["Title"], fontName="Helvetica-Bold",
    fontSize=21, leading=25, alignment=TA_CENTER, textColor=colors.HexColor("#18364b"),
    spaceAfter=18,
))
styles.add(ParagraphStyle(
    name="Section", parent=styles["Heading1"], fontSize=16, leading=20,
    textColor=colors.HexColor("#18364b"), spaceBefore=15, spaceAfter=8,
    keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="Subsection", parent=styles["Heading2"], fontSize=12, leading=15,
    textColor=colors.HexColor("#176b68"), spaceBefore=10, spaceAfter=5,
    keepWithNext=True,
))
styles.add(ParagraphStyle(
    name="BodyCompact", parent=styles["BodyText"], fontSize=9, leading=12,
    spaceAfter=6,
))
styles.add(ParagraphStyle(
    name="CodeBlock", fontName="Courier", fontSize=7.2, leading=9,
    leftIndent=8, rightIndent=8, borderColor=colors.HexColor("#d4dde2"),
    borderWidth=0.5, borderPadding=6, backColor=colors.HexColor("#f3f6f7"),
    spaceBefore=3, spaceAfter=8,
))
styles.add(ParagraphStyle(
    name="TableCell", parent=styles["BodyText"], fontSize=7.4, leading=9,
    spaceAfter=0,
))
styles.add(ParagraphStyle(
    name="TableHead", parent=styles["TableCell"], fontName="Helvetica-Bold",
    textColor=colors.white,
))


def inline_markup(text):
    text = escape(text)
    text = re.sub(r"`([^`]+)`", r"<font name='Courier'>\1</font>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", text)
    return text


def split_table_row(line):
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def draw_page(canvas, document):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#d4dde2"))
    canvas.line(0.65 * inch, 0.55 * inch, 7.85 * inch, 0.55 * inch)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(colors.HexColor("#52636d"))
    canvas.drawString(0.68 * inch, 0.36 * inch, "Task Manager FastAPI | Code Quality Assignment")
    canvas.drawRightString(7.82 * inch, 0.36 * inch, str(document.page))
    canvas.restoreState()


def build_story(lines):
    story = []
    index = 0
    in_code = False
    code_lines = []
    while index < len(lines):
        line = lines[index]
        if line.startswith("```"):
            if in_code:
                story.append(Preformatted("\n".join(code_lines), styles["CodeBlock"], maxLineLength=105))
                code_lines = []
                in_code = False
            else:
                in_code = True
            index += 1
            continue
        if in_code:
            code_lines.append(line)
            index += 1
            continue
        if line.startswith("|"):
            table_lines = []
            while index < len(lines) and lines[index].startswith("|"):
                table_lines.append(lines[index])
                index += 1
            rows = []
            for row_number, table_line in enumerate(table_lines):
                if re.fullmatch(r"\|?[\s|:-]+\|?", table_line):
                    continue
                cells = split_table_row(table_line)
                style = "TableHead" if row_number == 0 else "TableCell"
                rows.append([Paragraph(inline_markup(cell), styles[style]) for cell in cells])
            if rows:
                column_count = max(len(row) for row in rows)
                page_width = letter[0] - 1.3 * inch
                table = Table(rows, colWidths=[page_width / column_count] * column_count, repeatRows=1)
                table.setStyle(TableStyle([
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#176b68")),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#c3cdd2")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 4),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f3f6f7")]),
                ]))
                story.extend([table, Spacer(1, 7)])
            continue
        if not line.strip():
            story.append(Spacer(1, 3))
        elif line.startswith("# "):
            story.append(Paragraph(inline_markup(line[2:]), styles["ReportTitle"]))
        elif line.startswith("## "):
            story.append(Paragraph(inline_markup(line[3:]), styles["Section"]))
        elif line.startswith("### "):
            story.append(Paragraph(inline_markup(line[4:]), styles["Subsection"]))
        elif line.startswith("- "):
            story.append(Paragraph(inline_markup(line[2:]), styles["BodyCompact"], bulletText="•"))
        elif re.match(r"^\d+\. ", line):
            item = re.sub(r"^\d+\. ", "", line)
            story.append(Paragraph(inline_markup(item), styles["BodyCompact"], bulletText="•"))
        else:
            story.append(Paragraph(inline_markup(line), styles["BodyCompact"]))
        index += 1
    return story


document = SimpleDocTemplate(
    str(OUTPUT), pagesize=letter, rightMargin=0.65 * inch, leftMargin=0.65 * inch,
    topMargin=0.65 * inch, bottomMargin=0.75 * inch,
    title="Task Manager FastAPI: Static Analysis and Code Quality Review",
    author="Project Assignment Report",
)
document.build(build_story(SOURCE.read_text(encoding="utf-8").splitlines()), onFirstPage=draw_page, onLaterPages=draw_page)
print(f"Created {OUTPUT}")
