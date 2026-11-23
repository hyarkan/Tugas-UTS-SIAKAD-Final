"""HTML preview and PDF output from the same transcript data."""
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape
from jinja2 import Environment, FileSystemLoader, select_autoescape
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    CondPageBreak,
    Image as ReportLabImage,
    LongTable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

TEMPLATES = Path(__file__).resolve().parent.parent / 'templates'
APP_DIR = TEMPLATES.parent
LOGO_PATH = APP_DIR / 'static' / 'images' / 'logo_istn.png'
LOGO_URL = '/static/images/logo_istn.png'
ENV = Environment(loader=FileSystemLoader(str(TEMPLATES)), autoescape=select_autoescape(['html']))


def render_transcript_html(t: dict, logo_src: str = LOGO_URL) -> str:
    return ENV.get_template('transcript.html').render(t=t, logo_src=logo_src)


def render_transcript_pdf(t: dict) -> bytes:
    """Render the transcript with WeasyPrint or the portable ReportLab fallback.

    Windows without GTK/Pango uses ReportLab to avoid native installation failures.
    """
    try:
        from weasyprint import HTML
        html = render_transcript_html(t, logo_src=LOGO_PATH.as_uri())
        return HTML(string=html, base_url=str(APP_DIR)).write_pdf()
    except (ImportError, OSError):
        return _render_reportlab_fallback(t)


def _render_reportlab_fallback(t: dict) -> bytes:
    """Portable fallback when WeasyPrint native libraries are unavailable."""
    if not LOGO_PATH.is_file():
        raise FileNotFoundError(f"ISTN logo asset not found: {LOGO_PATH}")

    buf = BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=17*mm, rightMargin=17*mm,
                            topMargin=14*mm, bottomMargin=20*mm,
                            title='Transkrip Akademik - ' + t['nim'],
                            author='Institut Sains dan Teknologi Nasional')
    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name='TranscriptTitle', parent=styles['Heading1'], alignment=TA_CENTER,
                              textColor=colors.HexColor('#16436b'), fontSize=17, leading=20, spaceAfter=3))
    styles.add(ParagraphStyle(name='TranscriptInstitution', parent=styles['Normal'], alignment=TA_CENTER,
                              textColor=colors.HexColor('#16436b'), fontName='Helvetica-Bold',
                              fontSize=10, leading=12))
    styles.add(ParagraphStyle(name='TranscriptCell', parent=styles['Normal'], fontSize=7.5, leading=9))
    styles.add(ParagraphStyle(name='TranscriptLabel', parent=styles['Normal'], fontSize=8,
                              leading=10, fontName='Helvetica-Bold'))
    styles.add(ParagraphStyle(name='TranscriptNote', parent=styles['Normal'], fontSize=8, leading=11,
                              textColor=colors.HexColor('#4d5b6a')))
    styles.add(ParagraphStyle(name='TranscriptSimulation', parent=styles['TranscriptNote'],
                              alignment=TA_CENTER, spaceBefore=2))
    styles.add(ParagraphStyle(name='TranscriptSummary', parent=styles['Normal'], fontSize=10,
                              leading=13, textColor=colors.HexColor('#16436b')))

    def cell(value, style='TranscriptCell'):
        return Paragraph(escape(str(value if value is not None else '—')), styles[style])

    logo = ReportLabImage(str(LOGO_PATH), width=20*mm, height=20*mm,
                          kind='proportional', mask='auto')
    institution = [
        Paragraph('INSTITUT SAINS DAN TEKNOLOGI NASIONAL (ISTN)',
                  styles['TranscriptInstitution']),
        Paragraph('TRANSKRIP AKADEMIK', styles['TranscriptTitle']),
        Paragraph('SIMULASI AKADEMIK — BUKAN DOKUMEN RESMI',
                  styles['TranscriptSimulation']),
    ]
    header = Table([[logo, institution]], colWidths=[23*mm, 153*mm], hAlign='LEFT')
    header.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LINEBELOW', (0, 0), (-1, -1), 1.5, colors.HexColor('#16436b')),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
    ]))
    story = [header, Spacer(1, 5*mm)]

    info = [
        [cell('NIM', 'TranscriptLabel'), cell(t['nim']),
         cell('Angkatan', 'TranscriptLabel'), cell(t['angkatan'])],
        [cell('Nama', 'TranscriptLabel'), cell(t['nama']),
         cell('Program Studi', 'TranscriptLabel'), cell(t['program_studi'])],
        [cell('Fakultas', 'TranscriptLabel'), cell(t['fakultas']), '', ''],
    ]
    info_table = Table(info, colWidths=[20*mm, 65*mm, 28*mm, 63*mm], hAlign='LEFT')
    info_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(info_table)
    if t.get('angkatan_dari_nim', True) and str(t.get('angkatan', '')).isdigit():
        story.append(Paragraph(
            'Angkatan diperkirakan dari empat digit awal NIM, bukan data akademik terverifikasi.',
            styles['TranscriptNote'],
        ))

    for semester in t['semester']:
        story.append(CondPageBreak(32*mm))
        heading = Paragraph(
            'Semester ' + escape(str(semester['semester'])) +
            ' | IPS ' + escape(str(semester['ips'])),
            styles['Heading2'],
        )
        data = [[cell(label) for label in [
            'Kode MK', 'Nama Mata Kuliah', 'SKS', 'Nilai', 'Mutu',
            'Dihitung dalam IPK',
        ]]]
        for course in semester['mata_kuliah']:
            data.append([
                cell(course['kode_mk']),
                cell(course['nama_mk']),
                cell(course['sks']),
                cell(course['nilai']),
                cell(course['mutu']),
                cell('Ya' if course['dihitung_ipk'] else 'Tidak'),
            ])
        table = LongTable(
            data,
            colWidths=[22*mm, 71*mm, 13*mm, 16*mm, 20*mm, 34*mm],
            repeatRows=1,
            hAlign='LEFT',
        )
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf0f6')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#16436b')),
            ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#c6d0da')),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('LEFTPADDING', (0, 0), (-1, -1), 3),
            ('RIGHTPADDING', (0, 0), (-1, -1), 3),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        story.extend([heading, table, Spacer(1, 3*mm)])
    if not t['semester']:
        story.append(Paragraph('Belum ada KRS atau nilai akademik.', styles['Normal']))

    summary = Table([[
        cell(f"Total SKS Lulus: {t['total_sks_lulus']}", 'TranscriptSummary'),
        cell(f"IPK: {t['ipk']}", 'TranscriptSummary'),
    ]], colWidths=[110*mm, 66*mm], hAlign='LEFT')
    summary.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#eaf0f6')),
        ('BOX', (0, 0), (-1, -1), 0.8, colors.HexColor('#16436b')),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
        ('RIGHTPADDING', (0, 0), (-1, -1), 7),
        ('TOPPADDING', (0, 0), (-1, -1), 7),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 7),
    ]))
    story.extend([Spacer(1, 4*mm), summary])

    story.append(Paragraph('Riwayat Perubahan Nilai', styles['Heading2']))
    history = [[cell(label) for label in [
        'Waktu', 'Kode MK', 'Sebelum', 'Sesudah', 'Pengubah', 'Alasan',
    ]]]
    for entry in t['riwayat_perubahan']:
        history.append([
            cell(entry['changed_at']),
            cell(entry['kode_mk']),
            cell(entry['old_value']),
            cell(entry['new_value']),
            cell(entry['dosen_nama']),
            cell(entry['reason']),
        ])
    if len(history) == 1:
        history.append([cell('Belum ada perubahan nilai.'), '', '', '', '', ''])
    history_table = LongTable(
        history,
        colWidths=[31*mm, 21*mm, 20*mm, 20*mm, 31*mm, 45*mm],
        repeatRows=1,
        hAlign='LEFT',
    )
    history_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#eaf0f6')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor('#16436b')),
        ('GRID', (0, 0), (-1, -1), 0.4, colors.HexColor('#c6d0da')),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    story.extend([
        history_table,
        Spacer(1, 5*mm),
        Paragraph('<b>Predikat: ' + escape(t['predikat']) + '</b>', styles['Normal']),
        Paragraph(escape(t['catatan']), styles['TranscriptNote']),
        Spacer(1, 8*mm),
        Paragraph(
            '<b>Dekan</b><br/><br/><br/>(____________________________)<br/>'
            '<font size="8">Nama dan tanda tangan resmi belum tersedia — simulasi.</font>',
            styles['Normal'],
        ),
    ])

    def draw_page_footer(canvas, page_doc):
        canvas.saveState()
        canvas.setStrokeColor(colors.HexColor('#bcc9d5'))
        canvas.line(17*mm, 15*mm, A4[0] - 17*mm, 15*mm)
        canvas.setFont('Helvetica', 7)
        canvas.setFillColor(colors.HexColor('#596579'))
        canvas.drawString(17*mm, 10*mm, 'SIMULASI AKADEMIK — BUKAN DOKUMEN RESMI')
        canvas.drawRightString(A4[0] - 17*mm, 10*mm, f'Halaman {page_doc.page}')
        canvas.restoreState()

    doc.build(story, onFirstPage=draw_page_footer, onLaterPages=draw_page_footer)
    return buf.getvalue()
