import csv
import json
from io import BytesIO, StringIO

from openpyxl import Workbook
from openpyxl.styles import Font

from xml.sax.saxutils import escape as xml_escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)


def _display(value):
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False, default=str)
    return "" if value is None else str(value)


def build_csv_report(report_data):
    output = StringIO()
    writer = csv.writer(output)

    writer.writerow(["Section", "Record", "Field", "Value"])

    for group in ("metadata", "summary"):
        for field, value in report_data.get(group, {}).items():
            writer.writerow([group, "", field, _display(value)])

    for section, records in report_data.get("sections", {}).items():
        if not records:
            writer.writerow([section, "", "No records", ""])
            continue

        if isinstance(records, list):
            for index, record in enumerate(records, start=1):
                if isinstance(record, dict):
                    for field, value in record.items():
                        writer.writerow([
                            section, index, field, _display(value)
                        ])
                else:
                    writer.writerow([
                        section, index, "Value", _display(record)
                    ])
        elif isinstance(records, dict):
            for field, value in records.items():
                writer.writerow([
                    section, "", field, _display(value)
                ])

    return output.getvalue().encode("utf-8-sig")


def build_excel_report(report_data):
    workbook = Workbook()
    workbook.remove(workbook.active)

    def write_rows(sheet_name, headers, rows):
        sheet = workbook.create_sheet(sheet_name)
        sheet.append(headers)

        for cell in sheet[1]:
            cell.font = Font(bold=True)

        for row in rows:
            sheet.append([_display(value) for value in row])

        sheet.freeze_panes = "A2"
        sheet.auto_filter.ref = sheet.dimensions

        for column in sheet.columns:
            width = max(
                len(str(cell.value or "")) for cell in column
            ) + 2
            sheet.column_dimensions[column[0].column_letter].width = min(
                width, 50
            )

    for group in ("metadata", "summary"):
        values = report_data.get(group, {})
        write_rows(
            group.title(),
            ["Field", "Value"],
            [[key, value] for key, value in values.items()]
        )

    sheet_names = {
        "exposures": "Exposures",
        "validations": "Validations",
        "remediations": "Remediations",
        "exceptions": "Exceptions",
        "framework_mappings": "Framework Mappings",
        "exposure_trend_by_month": "Exposure Trend",
    }

    for section, records in report_data.get("sections", {}).items():
        rows = records if isinstance(records, list) else []

        if not rows:
            write_rows(
                sheet_names.get(section, section[:31]),
                ["Information"],
                [["No records available"]]
            )
            continue

        if all(isinstance(row, dict) for row in rows):
            headers = list(dict.fromkeys(
                key for row in rows for key in row
            ))
            write_rows(
                sheet_names.get(section, section[:31]),
                headers,
                [[row.get(key) for key in headers] for row in rows]
            )
        else:
            write_rows(
                sheet_names.get(section, section[:31]),
                ["Value"],
                [[value] for value in rows]
            )

    output = BytesIO()
    workbook.save(output)
    return output.getvalue()

def build_pdf_report(report_data):
    output = BytesIO()

    doc = SimpleDocTemplate(
        output,
        pagesize=landscape(A4),
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=18 * mm,
        title=report_data.get("metadata", {}).get(
            "report_name", "CTEM Report"
        ),
    )

    styles = getSampleStyleSheet()
    story = []

    def paragraph(value, style="BodyText"):
        text = xml_escape(_display(value)).replace("\n", "<br/>")
        return Paragraph(text or " ", styles[style])

    def add_key_value_table(items):
        rows = [[paragraph("Field", "Heading4"),
                 paragraph("Value", "Heading4")]]

        for key, value in items:
            rows.append([paragraph(key), paragraph(value)])

        table = Table(
            rows,
            colWidths=[doc.width * 0.25, doc.width * 0.75],
            repeatRows=1,
        )
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
            ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]))
        story.append(table)
        story.append(Spacer(1, 10))

    metadata = report_data.get("metadata", {})
    report_name = metadata.get("report_name", "CTEM Report")

    story.append(Paragraph(xml_escape(str(report_name)), styles["Title"]))
    story.append(Paragraph("CTEM Security Report", styles["Heading2"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph("Report Information", styles["Heading1"]))
    add_key_value_table(metadata.items())

    story.append(Paragraph("Executive Summary", styles["Heading1"]))
    add_key_value_table(report_data.get("summary", {}).items())

    section_titles = {
        "exposures": "Exposures",
        "validations": "Validations",
        "remediations": "Remediations",
        "exceptions": "Exceptions",
        "framework_mappings": "Framework Mappings",
        "exposure_trend_by_month": "Exposure Trend by Month",
    }

    for section, records in report_data.get("sections", {}).items():
        title = section_titles.get(section, section.replace("_", " ").title())
        story.append(Paragraph(xml_escape(title), styles["Heading1"]))

        if not records:
            story.append(Paragraph(
                "No records available for this section.",
                styles["BodyText"],
            ))
            story.append(Spacer(1, 8))
            continue

        if isinstance(records, dict):
            add_key_value_table(records.items())
            continue

        for index, record in enumerate(records, start=1):
            if isinstance(record, dict):
                story.append(Paragraph(
                    f"Record {index}", styles["Heading3"]
                ))
                add_key_value_table(record.items())
            else:
                story.append(paragraph(record))
                story.append(Spacer(1, 6))

    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 9)
        canvas.drawRightString(
            document.pagesize[0] - 15 * mm,
            8 * mm,
            f"Page {document.page}",
        )
        canvas.restoreState()

    doc.build(
        story,
        onFirstPage=add_page_number,
        onLaterPages=add_page_number,
    )

    return output.getvalue()