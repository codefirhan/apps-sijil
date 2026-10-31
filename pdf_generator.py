import os
import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import fitz # PyMuPDF untuk render PDF ke Gambar (PNG)

FONT_NAME = "Helvetica"
FONT_NAME_BOLD = "Helvetica-Bold"

# Coba daftarkan font TrueType yang mendukung karakter UTF-8 seperti ceklis (✓)
font_candidates = [
    ("/System/Library/Fonts/Supplemental/Arial Unicode.ttf", "/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    ("/System/Library/Fonts/Supplemental/Arial.ttf", "/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
    ("/Library/Fonts/Arial.ttf", "/Library/Fonts/Arial Bold.ttf"),
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
    (os.path.join(os.path.dirname(__file__), "assets", "fonts", "DejaVuSans.ttf"),
     os.path.join(os.path.dirname(__file__), "assets", "fonts", "DejaVuSans-Bold.ttf"))
]

for normal_path, bold_path in font_candidates:
    if os.path.exists(normal_path):
        try:
            pdfmetrics.registerFont(TTFont("CustomUnicodeFont", normal_path))
            FONT_NAME = "CustomUnicodeFont"
            if os.path.exists(bold_path):
                pdfmetrics.registerFont(TTFont("CustomUnicodeFont-Bold", bold_path))
                FONT_NAME_BOLD = "CustomUnicodeFont-Bold"
            else:
                FONT_NAME_BOLD = "CustomUnicodeFont"
            break
        except Exception:
            continue

def build_person_story(
    data: dict,
    include_title: bool = True,
    include_footnote: bool = True,
    compact: bool = False
) -> list:
    """
    Menyusun elemen flowables (story) untuk tabel laporan detail resmi per orang
    lengkap dari Senin s/d Minggu beserta jam Solat Malam, Jumlah Dzikir, Dhuha,
    Puasa Senin & Kamis, Solat Rowatib, Keterangan, Pengajian, Piket, dan Tata Krama
    tanpa disingkat.
    """
    story = []

    # 1. Judul Laporan (opsional jika digabung dalam laporan per posko)
    if include_title:
        title_style = ParagraphStyle(
            'ReportTitle',
            fontName=FONT_NAME_BOLD,
            fontSize=12 if compact else 13,
            leading=14 if compact else 16,
            alignment=1, # Center
            spaceAfter=6 if compact else 15
        )
        story.append(Paragraph("<b>LAPORAN PELAKSANAAN AMANAH</b>", title_style))
        if not compact:
            story.append(Spacer(1, 8))

    # 2. Metadata Header: NAMA, AHAD KE, BULAN, POSKO
    header_style = ParagraphStyle(
        'MetaHeader',
        fontName=FONT_NAME_BOLD,
        fontSize=9 if compact else 9.5,
        leading=11 if compact else 12
    )

    nama = data.get("nama", "FIRHAN").upper()
    ahad_ke = str(data.get("ahad_ke", "2"))
    bulan = data.get("bulan", "")
    posko = str(data.get("posko") or os.getenv("POSKO_NAME", "TANGKIL")).upper()

    header_table_data = [
        [
            Paragraph(f"NAMA : {nama}", header_style),
            Paragraph(f"AHAD KE : {ahad_ke}", header_style),
            Paragraph(f"BULAN : {bulan}", header_style),
            Paragraph(f"POSKO : {posko}", header_style),
        ]
    ]
    # Total lebar tabel = 770 pt (841.89 - 72 = 769.89 pt)
    header_table = Table(header_table_data, colWidths=[150, 130, 340, 150])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2 if compact else 4),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 3 if compact else 8))

    # 3. Tabel Utama Pelaksanaan Amanah (Senin - Minggu Lengkap Tanpa Disingkat)
    cell_style_center = ParagraphStyle(
        'CellCenter',
        fontName=FONT_NAME,
        fontSize=8 if compact else 8.5,
        leading=9.5 if compact else 11,
        alignment=1 # Center
    )

    cell_style_center_bold = ParagraphStyle(
        'CellCenterBold',
        fontName=FONT_NAME_BOLD,
        fontSize=8.5 if compact else 9,
        leading=10 if compact else 12,
        alignment=1 # Center
    )

    cell_style_left_bold = ParagraphStyle(
        'CellLeftBold',
        fontName=FONT_NAME_BOLD,
        fontSize=8.5 if compact else 9,
        leading=10 if compact else 12,
        alignment=0 # Left
    )

    cell_style_keterangan = ParagraphStyle(
        'CellKeterangan',
        fontName=FONT_NAME,
        fontSize=7.5 if compact else 8,
        leading=9.5 if compact else 10.5,
        alignment=0 # Left
    )

    col_names = ["SENIN", "SELASA", "RABU", "KAMIS", "JUM'AT", "SABTU", "MINGGU"]
    
    # Header baris tabel
    table_rows = [
        [
            Paragraph("AMANAH", cell_style_left_bold),
            *[Paragraph(col, cell_style_center_bold) for col in col_names],
            Paragraph("KETERANGAN", cell_style_center_bold)
        ]
    ]

    days_data = data.get("days", {})
    keterangan_rows = data.get("keterangan_rows", {})

    row_configs = [
        ("solat_malam", "SOLAT MALAM"),
        ("jumlah_dzikir", "JUMLAH DZIKIR"),
        ("dhuha", "DHUHA"),
        ("puasa", "PUASA SENIN & KAMIS"),
        ("rowatib", "SOLAT ROWATIB"),
    ]

    for key, label in row_configs:
        row = [Paragraph(label, cell_style_left_bold)]
        for day in col_names:
            val = days_data.get(day, {}).get(key, "")
            if val is None or val == "":
                row.append(Paragraph("", cell_style_center))
            else:
                row.append(Paragraph(str(val), cell_style_center))
        
        # Kolom Keterangan
        ket_text = keterangan_rows.get(key, "")
        row.append(Paragraph(ket_text, cell_style_keterangan))
        table_rows.append(row)

    # Lebar kolom: AMANAH (115), 7 hari x 70 = 490, KETERANGAN (165) => Total 770 pt
    col_widths = [115, 70, 70, 70, 70, 70, 70, 70, 165]
    header_h = 20 if compact else 26
    row_heights = [header_h]
    for key, label in row_configs:
        ket_text = keterangan_rows.get(key, "")
        line_count = len([line for line in ket_text.split("<br/>") if line.strip()]) if ket_text else 1
        if compact:
            min_h = 24 if key == "solat_malam" else 20
            calculated_h = max(min_h, line_count * 10 + 6)
        else:
            min_h = 36 if key in ["solat_malam", "dhuha", "puasa", "rowatib"] else 26
            calculated_h = max(min_h, line_count * 12 + 8)
        row_heights.append(calculated_h)

    v_pad = 2 if compact else 3
    main_table = Table(table_rows, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
    main_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.75, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), v_pad),
        ('BOTTOMPADDING', (0, 0), (-1, -1), v_pad),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))

    story.append(main_table)
    story.append(Spacer(1, 5 if compact else 14))

    # 4. Bagian Bawah: PENGAJIAN, PIKET, TATA KRAMA
    bottom_style = ParagraphStyle(
        'BottomStyle',
        fontName=FONT_NAME,
        fontSize=8.5 if compact else 9,
        leading=10.5 if compact else 13
    )
    bottom_bold = ParagraphStyle(
        'BottomBold',
        fontName=FONT_NAME_BOLD,
        fontSize=8.5 if compact else 9,
        leading=10.5 if compact else 13
    )

    # Pengajian: jika Hadir (1) maka 'Hadir : ✓', jika Tidak (0) maka 'Tidak : ✓'
    pengajian_status = data.get("pengajian_status", 0)
    pengajian_hadir_str = "Hadir : ✓" if pengajian_status == 1 else "Hadir :"
    pengajian_tidak_str = "Tidak :" if pengajian_status == 1 else "Tidak : ✓"

    # Piket: statis Tidak
    piket_hadir_str = "Hadir :"
    piket_tidak_str = "Tidak : ✓"

    # Tata Krama: nominal Ahad dan/atau Jijyah
    tk_ahad = str(data.get("tata_krama_ahad", "")).strip()
    tk_jijyah = str(data.get("tata_krama_jijyah", "")).strip()

    tk_ahad_str = f"Ahad : {tk_ahad}" if tk_ahad else "Ahad :"
    tk_jijyah_str = f"Jijyah : {tk_jijyah}" if tk_jijyah else "Jijyah :"

    bottom_table_data = [
        [
            Paragraph("PENGAJIAN", bottom_bold),
            Paragraph(pengajian_hadir_str, bottom_style),
            Paragraph(pengajian_tidak_str, bottom_style),
            Paragraph("", bottom_style),
        ],
        [
            Paragraph("PIKET", bottom_bold),
            Paragraph(piket_hadir_str, bottom_style),
            Paragraph(piket_tidak_str, bottom_style),
            Paragraph("", bottom_style),
        ],
        [
            Paragraph("TATA KRAMA", bottom_bold),
            Paragraph(tk_ahad_str, bottom_style),
            Paragraph(tk_jijyah_str, bottom_style),
            Paragraph("", bottom_style),
        ]
    ]

    bottom_table = Table(bottom_table_data, colWidths=[115, 110, 110, 435])
    bottom_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 1 if compact else 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1 if compact else 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    story.append(bottom_table)

    # 5. Keterangan Penjelasan di bagian bawah
    if include_footnote:
        story.append(Spacer(1, 8 if compact else 14))
        keterangan_footnote = """
        <b>Keterangan :</b><br/>
        1. Solat Malam diisi dengan waktu mulai didirikan<br/>
        2. Solat Dhuha diisi dengan waktu mulai didirikan<br/>
        3. Puasa Senin & Kamis diisi dengan ceklis di senin dan kamis<br/>
        4. Solat Rowatib diisi dengan berapa waktu menjalankan
        """
        story.append(Paragraph(keterangan_footnote, bottom_style))

    return story

def generate_pdf_report(filename: str, data: dict) -> str:
    """
    Menghasilkan file PDF Laporan Pelaksanaan Amanah untuk 1 orang dengan tata letak
    persis template dokumen resmi (detail penuh Senin s/d Minggu tanpa disingkat).
    """
    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=30,
        bottomMargin=25
    )
    story = build_person_story(data, include_title=True, include_footnote=True, compact=False)
    doc.build(story)
    return filename

def generate_pdf_combined_report(filename: str, all_data: list, week_meta: dict) -> str:
    """
    Menghasilkan file PDF Gabungan Per Posko (Landscape A4) yang menampilkan
    Tabel Laporan Detail Resmi Lengkap (Senin s/d Minggu: Jam Solat Malam, Jumlah Dzikir,
    Dhuha, Puasa Senin & Kamis, Solat Rowatib, Keterangan, Pengajian, Piket, Tata Krama)
    untuk setiap anggota posko secara utuh tanpa disingkat.
    """
    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=20,
        bottomMargin=18
    )
    story = []

    # 1. Judul Utama Laporan Per Posko
    title_style = ParagraphStyle(
        'PoskoReportTitle',
        fontName=FONT_NAME_BOLD,
        fontSize=12.5,
        leading=15,
        alignment=1, # Center
        spaceAfter=4
    )
    posko = str(week_meta.get("posko") or os.getenv("POSKO_NAME", "TANGKIL")).upper()
    ahad_ke = str(week_meta.get("ahad_ke", "1"))
    bulan = week_meta.get("bulan", "")
    total_anggota = len(all_data)

    story.append(Paragraph("<b>LAPORAN PELAKSANAAN AMANAH PER POSKO</b>", title_style))

    sub_style = ParagraphStyle(
        'PoskoSubHeader',
        fontName=FONT_NAME_BOLD,
        fontSize=8.5,
        leading=11,
        alignment=1,
        spaceAfter=8
    )
    story.append(Paragraph(
        f"POSKO : {posko} &nbsp;&nbsp;|&nbsp;&nbsp; AHAD KE : {ahad_ke} &nbsp;&nbsp;|&nbsp;&nbsp; "
        f"BULAN : {bulan} &nbsp;&nbsp;|&nbsp;&nbsp; TOTAL ANGGOTA : {total_anggota} ORANG",
        sub_style
    ))

    # 2. Tabel Detail Lengkap Masing-Masing Anggota (Tanpa Disingkat)
    for idx, person_data in enumerate(all_data):
        person_block = build_person_story(
            person_data,
            include_title=False,
            include_footnote=False,
            compact=True
        )
        if idx < len(all_data) - 1:
            person_block.append(Spacer(1, 10))
        story.append(KeepTogether(person_block))

    # 3. Keterangan Penjelasan di bagian akhir dokumen
    story.append(Spacer(1, 6))
    footnote_style = ParagraphStyle(
        'CombinedFootnote',
        fontName=FONT_NAME,
        fontSize=8,
        leading=10
    )
    keterangan_footnote = (
        "<b>Keterangan :</b> "
        "1. Solat Malam diisi dengan waktu mulai didirikan &nbsp;|&nbsp; "
        "2. Solat Dhuha diisi dengan waktu mulai didirikan &nbsp;|&nbsp; "
        "3. Puasa Senin & Kamis diisi dengan ceklis di senin dan kamis &nbsp;|&nbsp; "
        "4. Solat Rowatib diisi dengan berapa waktu menjalankan"
    )
    story.append(Paragraph(keterangan_footnote, footnote_style))

    doc.build(story)
    return filename

def generate_report_bundle(pdf_path: str, img_path: str, data: dict, dpi: int = 200) -> tuple:
    """
    Menghasilkan file PDF sekaligus file Gambar (PNG) untuk 1 orang (200 DPI).
    Mengembalikan tuple (pdf_path, img_path).
    """
    generate_pdf_report(pdf_path, data)

    doc = fitz.open(pdf_path)
    page = doc[0]
    pix = page.get_pixmap(dpi=dpi)
    pix.save(img_path)
    doc.close()

    return pdf_path, img_path

def generate_combined_report_bundle(pdf_path: str, img_prefix: str, all_data: list, week_meta: dict, dpi: int = 200) -> tuple:
    """
    Menghasilkan file PDF gabungan per posko sekaligus file Gambar (PNG) untuk setiap halaman.
    Mengembalikan tuple (pdf_path, list_of_img_paths).
    """
    generate_pdf_combined_report(pdf_path, all_data, week_meta)

    img_paths = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        page_img_path = f"{img_prefix}_Halaman_{i+1:02d}.png"
        pix = page.get_pixmap(dpi=dpi)
        pix.save(page_img_path)
        img_paths.append(page_img_path)
    doc.close()

    return pdf_path, img_paths
