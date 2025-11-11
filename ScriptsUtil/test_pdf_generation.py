#!/usr/bin/env python3
"""
Test PDF generation functionality.
"""
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from datetime import datetime, timedelta
import plotly.graph_objects as go
import pandas as pd
from io import BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.lib import colors

def test_pdf_generation():
    """Test generating a simple PDF with a Plotly chart."""
    print("=" * 80)
    print("Testing PDF Generation")
    print("=" * 80)

    # Create sample data
    timestamps = pd.date_range(start='2025-09-01', end='2025-09-30', freq='1H')
    values = [1 if i % 5 != 0 else 0 for i in range(len(timestamps))]  # Some downtime

    df = pd.DataFrame({
        'Timestamp': timestamps,
        'Maximum': values
    })

    print(f"\n✅ Created sample data: {len(df)} datapoints")

    # Create a Plotly chart
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df['Timestamp'],
        y=df['Maximum'],
        mode='lines+markers',
        line=dict(color='#1f77b4', width=2),
        marker=dict(size=4)
    ))

    fig.update_layout(
        title=dict(
            text="SRVERPQA - Disp: 97.9%",
            x=0.5,
            xanchor='center',
            font=dict(size=16, family='Arial, sans-serif', color='black')
        ),
        height=300,
        margin=dict(l=30, r=20, t=50, b=40),
        xaxis=dict(title="", gridcolor='lightgray', showgrid=True),
        yaxis=dict(
            title="", gridcolor='lightgray', showgrid=True,
            tickmode='array', tickvals=[0, 1], ticktext=['0', '1'],
            range=[-0.1, 1.1]
        ),
        plot_bgcolor='white',
        paper_bgcolor='white'
    )

    print("✅ Created Plotly chart")

    # Try to convert to image
    try:
        img_bytes = fig.to_image(format="png", width=350, height=300)
        print(f"✅ Converted chart to image ({len(img_bytes)} bytes)")
    except Exception as e:
        print(f"❌ Failed to convert chart to image: {e}")
        return

    # Create PDF
    try:
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        story = []

        # Styles
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#000000'),
            spaceAfter=30,
            alignment=TA_CENTER
        )

        # Title
        title_text = "Métricas de Ping Desde 01/09/2025 hasta 30/09/2025"
        story.append(Paragraph(title_text, title_style))
        story.append(Spacer(1, 0.3 * inch))

        # Add chart as image
        img = Image(BytesIO(img_bytes), width=3.5*inch, height=3*inch)
        story.append(img)

        # Build PDF
        doc.build(story)
        buffer.seek(0)

        # Save to file
        output_path = "/tmp/test_report.pdf"
        with open(output_path, 'wb') as f:
            f.write(buffer.read())

        print(f"✅ PDF generated successfully: {output_path}")
        print(f"   File size: {os.path.getsize(output_path)} bytes")

    except Exception as e:
        print(f"❌ Failed to generate PDF: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "=" * 80)
    print("✅ PDF generation test PASSED")
    print("=" * 80)

if __name__ == "__main__":
    test_pdf_generation()
