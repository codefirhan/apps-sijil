import os
import datetime
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
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

def build_person_story(data: dict) -> list:
    """
    Menyusun elemen flowables (story) untuk satu lembar laporan detail resmi per orang.
    """
    story = []

    # 1. Judul Laporan
    title_style = ParagraphStyle(
        'ReportTitle',
        fontName=FONT_NAME_BOLD,
        fontSize=13,
        leading=16,
        alignment=1, # Center
        spaceAfter=15
    )
    story.append(Paragraph("<b>LAPORAN PELAKSANAAN AMANAH</b>", title_style))
    story.append(Spacer(1, 8))

    # 2. Metadata Header: NAMA, AHAD KE, BULAN, POSKO
    header_style = ParagraphStyle(
        'MetaHeader',
        fontName=FONT_NAME_BOLD,
        fontSize=9.5,
        leading=12
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
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # 3. Tabel Utama Pelaksanaan Amanah
    cell_style_center = ParagraphStyle(
        'CellCenter',
        fontName=FONT_NAME,
        fontSize=8.5,
        leading=11,
        alignment=1 # Center
    )

    cell_style_center_bold = ParagraphStyle(
        'CellCenterBold',
        fontName=FONT_NAME_BOLD,
        fontSize=9,
        leading=12,
        alignment=1 # Center
    )

    cell_style_left_bold = ParagraphStyle(
        'CellLeftBold',
        fontName=FONT_NAME_BOLD,
        fontSize=9,
        leading=12,
        alignment=0 # Left
    )

    cell_style_keterangan = ParagraphStyle(
        'CellKeterangan',
        fontName=FONT_NAME,
        fontSize=8,
        leading=10.5,
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
    row_heights = [26]
    for key, label in row_configs:
        ket_text = keterangan_rows.get(key, "")
        line_count = len([line for line in ket_text.split("<br/>") if line.strip()]) if ket_text else 1
        min_h = 36 if key in ["solat_malam", "dhuha", "puasa", "rowatib"] else 26
        calculated_h = max(min_h, line_count * 12 + 8)
        row_heights.append(calculated_h)

    main_table = Table(table_rows, colWidths=col_widths, rowHeights=row_heights, repeatRows=1)
    main_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.75, colors.black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 4),
        ('RIGHTPADDING', (0, 0), (-1, -1), 4),
    ]))

    story.append(main_table)
    story.append(Spacer(1, 14))

    # 4. Bagian Bawah: PENGAJIAN, PIKET, TATA KRAMA
    bottom_style = ParagraphStyle(
        'BottomStyle',
        fontName=FONT_NAME,
        fontSize=9,
        leading=13
    )
    bottom_bold = ParagraphStyle(
        'BottomBold',
        fontName=FONT_NAME_BOLD,
        fontSize=9,
        leading=13
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
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))

    story.append(bottom_table)
    story.append(Spacer(1, 14))

    # 5. Keterangan Penjelasan di bagian bawah
    keterangan_footnote = """
    <b>Keterangan :</b><br/>
    1. Solat Malam diisi dengan waktu mulai didirikan<br/>
    2. Solat Dhuha diisi dengan waktu mulai didirikan<br/>
    3. Puasa Senin & Kamis diisi dengan ceklis di senin dan kamis<br/>
    4. Solat Rowatib diisi dengan berapa waktu menjalankan
    """
    story.append(Paragraph(keterangan_footnote, bottom_style))

    return story

def build_rekap_story(all_data: list, week_meta: dict) -> list:
    """
    Menyusun elemen flowables (story) untuk lembar Rekapitulasi Keseluruhan Anggota.
    """
    story = []

    # 1. Judul Laporan Rekapitulasi
    title_style = ParagraphStyle(
        'RekapTitle',
        fontName=FONT_NAME_BOLD,
        fontSize=13,
        leading=16,
        alignment=1, # Center
        spaceAfter=15
    )
    story.append(Paragraph("<b>LAPORAN REKAPITULASI PELAKSANAAN AMANAH PER POSKO</b>", title_style))
    story.append(Spacer(1, 8))

    # 2. Metadata Header: POSKO, AHAD KE, BULAN, TOTAL ANGGOTA
    header_style = ParagraphStyle(
        'RekapMetaHeader',
        fontName=FONT_NAME_BOLD,
        fontSize=9.5,
        leading=12
    )

    posko = str(week_meta.get("posko") or os.getenv("POSKO_NAME", "TANGKIL")).upper()
    ahad_ke = str(week_meta.get("ahad_ke", "1"))
    bulan = week_meta.get("bulan", "")
    total_anggota = len(all_data)

    header_table_data = [
        [
            Paragraph(f"POSKO : {posko}", header_style),
            Paragraph(f"AHAD KE : {ahad_ke}", header_style),
            Paragraph(f"BULAN : {bulan}", header_style),
            Paragraph(f"TOTAL ANGGOTA : {total_anggota} ORANG", header_style),
        ]
    ]
    header_table = Table(header_table_data, colWidths=[150, 130, 340, 150])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('RIGHTPADDING', (0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 8))

    # 3. Tabel Rekapitulasi Utama
    cell_center = ParagraphStyle(
        'RekapCellCenter',
        fontName=FONT_NAME,
        fontSize=8,
        leading=10.5,
        alignment=1
    )
    cell_center_bold = ParagraphStyle(
        'RekapCellCenterBold',
        fontName=FONT_NAME_BOLD,
        fontSize=8.5,
        leading=11,
        alignment=1
    )
    cell_left_bold = ParagraphStyle(
        'RekapCellLeftBold',
        fontName=FONT_NAME_BOLD,
        fontSize=8.5,
        leading=11,
        alignment=0
    )
    cell_ket = ParagraphStyle(
        'RekapCellKet',
        fontName=FONT_NAME,
        fontSize=7.5,
        leading=9.5,
        alignment=0
    )

    col_widths = [26, 95, 54, 80, 60, 65, 80, 65, 60, 185] # Total = 770 pt
    table_rows = [
        [
            Paragraph("NO", cell_center_bold),
            Paragraph("NAMA", cell_center_bold),
            Paragraph("TERISI", cell_center_bold),
            Paragraph("SOLAT MALAM", cell_center_bold),
            Paragraph("DHUHA", cell_center_bold),
            Paragraph("PUASA", cell_center_bold),
            Paragraph("ROWATIB", cell_center_bold),
            Paragraph("PENGAJIAN", cell_center_bold),
            Paragraph("JIJYAH", cell_center_bold),
            Paragraph("RINGKASAN KETERANGAN / ALASAN", cell_center_bold),
        ]
    ]

    for idx, person in enumerate(all_data):
        days = person.get("days", {})
        sm_count = sum(1 for d in days.values() if d.get("solat_malam") and d.get("solat_malam") != "-")
        dh_count = sum(1 for d in days.values() if d.get("dhuha") == "✓")
        p_senin = days.get("SENIN", {}).get("puasa") == "✓"
        p_kamis = days.get("KAMIS", {}).get("puasa") == "✓"
        p_count = (1 if p_senin else 0) + (1 if p_kamis else 0)

        rw_vals = [d.get("rowatib") for d in days.values() if d.get("rowatib")]
        if not rw_vals:
            rw_text = "-"
        elif all(v == "5 waktu" for v in rw_vals):
            rw_text = "5 waktu"
        else:
            rw_text = "Sebagian < 5"

        pengajian_text = "Hadir (✓)" if person.get("pengajian_status") == 1 else "Tidak (✓)"
        j_val = person.get("tata_krama_jijyah")
        jijyah_text = f"Rp {j_val}" if j_val else "-"

        # Ringkasan alasan/keterangan
        k_rows = person.get("keterangan_rows", {})
        ket_items = []
        for k_key, k_lbl in [("solat_malam", "SM"), ("dhuha", "Dhuha"), ("puasa", "Puasa"), ("rowatib", "Rowatib")]:
            val_str = k_rows.get(k_key, "").strip()
            if val_str:
                clean_str = val_str.replace("<br/>", ", ")
                ket_items.append(f"• <b>{k_lbl}:</b> {clean_str}")

        ket_text = "<br/>".join(ket_items) if ket_items else "Lengkap / Tanpa uzur"

        table_rows.append([
            Paragraph(str(idx + 1), cell_center),
            Paragraph(person.get("nama", "-"), cell_left_bold),
            Paragraph(f"{person.get('filled_days_count', 0)}/7 hr", cell_center),
            Paragraph(f"{sm_count}/7 hr", cell_center),
            Paragraph(f"{dh_count}/7 hr", cell_center),
            Paragraph(f"{p_count}/2 hr", cell_center),
            Paragraph(rw_text, cell_center),
            Paragraph(pengajian_text, cell_center),
            Paragraph(jijyah_text, cell_center),
            Paragraph(ket_text, cell_ket),
        ])

    rekap_table = Table(table_rows, colWidths=col_widths, repeatRows=1)
    rekap_table.setStyle(TableStyle([
        ('GRID', (0, 0), (-1, -1), 0.75, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.whitesmoke),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 3),
        ('RIGHTPADDING', (0, 0), (-1, -1), 3),
    ]))
    story.append(rekap_table)
    story.append(Spacer(1, 14))

    # Catatan Rekapitulasi
    bottom_style = ParagraphStyle(
        'RekapBottom',
        fontName=FONT_NAME,
        fontSize=8.5,
        leading=12
    )
    rekap_footnote = """
    <b>Catatan Rekapitulasi:</b><br/>
    1. Lembar ini merangkum keterisian amanah seluruh anggota posko pada pekan bersangkutan.<br/>
    2. Rincian lembar laporan resmi harian (Senin - Minggu) beserta alasan keterangan per ibadah untuk masing-masing anggota terlampir lengkap pada halaman-halaman berikutnya.
    """
    story.append(Paragraph(rekap_footnote, bottom_style))

    return story

def generate_pdf_report(filename: str, data: dict) -> str:
    """
    Menghasilkan file PDF Laporan Pelaksanaan Amanah untuk 1 orang dengan tata letak
    persis template dokumen resmi.
    """
    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=30,
        bottomMargin=25
    )
    story = build_person_story(data)
    doc.build(story)
    return filename

def generate_pdf_combined_report(filename: str, all_data: list, week_meta: dict) -> str:
    """
    Menghasilkan file PDF Gabungan (Multi-page Landscape A4):
    - Halaman 1: Rekapitulasi Keseluruhan Anggota Posko
    - Halaman 2..N: Lembar Detail Resmi & Keterangan Masing-Masing Anggota
    """
    doc = SimpleDocTemplate(
        filename,
        pagesize=landscape(A4),
        leftMargin=36,
        rightMargin=36,
        topMargin=30,
        bottomMargin=25
    )
    story = []
    # 1. Halaman Rekapitulasi
    story.extend(build_rekap_story(all_data, week_meta))

    # 2. Halaman Detail Masing-Masing Orang
    for person_data in all_data:
        story.append(PageBreak())
        story.extend(build_person_story(person_data))

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
    Menghasilkan file PDF gabungan (multi-page) sekaligus file Gambar (PNG) untuk setiap halaman.
    Mengembalikan tuple (pdf_path, list_of_img_paths).
    """
    generate_pdf_combined_report(pdf_path, all_data, week_meta)

    img_paths = []
    doc = fitz.open(pdf_path)
    for i, page in enumerate(doc):
        if i == 0:
            name_suffix = "01_Rekapitulasi"
        else:
            p_idx = i - 1
            p_name = all_data[p_idx]["nama"] if p_idx < len(all_data) else f"Anggota_{i}"
            name_suffix = f"{i+1:02d}_Detail_{p_name}"

        page_img_path = f"{img_prefix}_{name_suffix}.png"
        pix = page.get_pixmap(dpi=dpi)
        pix.save(page_img_path)
        img_paths.append(page_img_path)
    doc.close()

    return pdf_path, img_paths
