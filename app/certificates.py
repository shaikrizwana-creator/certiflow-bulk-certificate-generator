from pathlib import Path
from reportlab.lib import colors
from reportlab.lib.pagesizes import landscape, A4
from reportlab.pdfgen import canvas

def generate_certificate(output_path: str, name: str, course_name: str, completion_date: str) -> None:
    """Render one certificate PDF using the single built-in template."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    page = landscape(A4)
    pdf = canvas.Canvas(str(path), pagesize=page)
    width, height = page

    # White background, double navy/gold border, and centered typography.
    pdf.setFillColor(colors.HexColor("#FBFAF6"))
    pdf.rect(0, 0, width, height, fill=1, stroke=0)
    pdf.setStrokeColor(colors.HexColor("#142B4A"))
    pdf.setLineWidth(5)
    pdf.rect(24, 24, width - 48, height - 48, fill=0, stroke=1)
    pdf.setStrokeColor(colors.HexColor("#C6A45D"))
    pdf.setLineWidth(1.5)
    pdf.rect(35, 35, width - 70, height - 70, fill=0, stroke=1)

    pdf.setFillColor(colors.HexColor("#142B4A"))
    pdf.setFont("Helvetica-Bold", 15)
    pdf.drawCentredString(width / 2, height - 105, "CERTIFLOW  •  CERTIFICATE OF COMPLETION")
    pdf.setFillColor(colors.HexColor("#9A793A"))
    pdf.setFont("Helvetica", 12)
    pdf.drawCentredString(width / 2, height - 145, "THIS CERTIFICATE IS PROUDLY PRESENTED TO")

    pdf.setFillColor(colors.HexColor("#142B4A"))
    pdf.setFont("Helvetica-Bold", 30)
    safe_name = name[:70]
    pdf.drawCentredString(width / 2, height - 205, safe_name)

    pdf.setFillColor(colors.HexColor("#333333"))
    pdf.setFont("Helvetica", 13)
    pdf.drawCentredString(width / 2, height - 245, "for successfully completing")
    pdf.setFillColor(colors.HexColor("#9A793A"))
    pdf.setFont("Helvetica-Bold", 20)
    pdf.drawCentredString(width / 2, height - 278, course_name[:90])

    pdf.setFillColor(colors.HexColor("#333333"))
    pdf.setFont("Helvetica", 11)
    pdf.drawCentredString(width / 2, 100, f"Completion date: {completion_date}")
    pdf.setStrokeColor(colors.HexColor("#142B4A"))
    pdf.line(width / 2 - 80, 75, width / 2 + 80, 75)
    pdf.setFont("Helvetica", 9)
    pdf.drawCentredString(width / 2, 60, "Authorized Signature")
    pdf.save()
