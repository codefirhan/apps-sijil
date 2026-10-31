import sqlite3
import datetime
import os
from typing import Dict, Any, List, Optional, Tuple

def get_db_path() -> str:
    """Mengambil path file database SQLite, mendukung DATA_DIR untuk Docker persistence"""
    custom_dir = os.getenv("DATA_DIR")
    root_dir = os.path.dirname(os.path.abspath(__file__))
    if custom_dir:
        os.makedirs(custom_dir, exist_ok=True)
        target_path = os.path.join(custom_dir, "amanah_report.db")
        # Jika di root ada file DB tapi di data/ belum ada, salin otomatis
        old_path = os.path.join(root_dir, "amanah_report.db")
        if not os.path.exists(target_path) and os.path.exists(old_path):
            try:
                import shutil
                shutil.copy2(old_path, target_path)
            except Exception:
                pass
        return target_path
    return os.path.join(root_dir, "amanah_report.db")

def get_connection():
    conn = sqlite3.connect(get_db_path())
    conn.row_factory = sqlite3.Row
    return conn

HARI_INDONESIA = {
    0: "SENIN",
    1: "SELASA",
    2: "RABU",
    3: "KAMIS",
    4: "JUM'AT",
    5: "SABTU",
    6: "MINGGU"
}

BULAN_INDONESIA = {
    1: "Januari",
    2: "Februari",
    3: "Maret",
    4: "April",
    5: "Mei",
    6: "Juni",
    7: "Juli",
    8: "Agustus",
    9: "September",
    10: "Oktober",
    11: "November",
    12: "Desember"
}

def init_db():
    """Inisialisasi tabel database SQLite, migrasi kolom dan data nama awal"""
    with get_connection() as conn:
        cursor = conn.cursor()
        
        # Tabel Laporan Harian
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS laporan (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER,
                nama TEXT NOT NULL,
                tanggal TEXT NOT NULL,
                hari TEXT NOT NULL,
                ahad_ke INTEGER NOT NULL,
                solat_malam_status INTEGER DEFAULT 1,
                solat_malam_jam TEXT DEFAULT '',
                solat_malam_alasan TEXT DEFAULT '',
                jumlah_dzikir TEXT DEFAULT '',
                dhuha_status INTEGER DEFAULT 1,
                dhuha_alasan TEXT DEFAULT '',
                puasa_status INTEGER DEFAULT 0,
                puasa_alasan TEXT DEFAULT '',
                rowatib TEXT DEFAULT '5 waktu',
                rowatib_alasan TEXT DEFAULT '',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(nama, tanggal)
            )
        """)
        
        # Tabel Informasi Pekanan (Ahad Ke, Pengajian, Piket, Tata Krama)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pekan_info (
                nama TEXT NOT NULL,
                monday_date TEXT NOT NULL,
                ahad_ke INTEGER,
                pengajian_status INTEGER DEFAULT 0,
                piket_status INTEGER DEFAULT 0,
                tata_krama_nominal TEXT DEFAULT '',
                tata_krama_ahad TEXT DEFAULT '',
                tata_krama_jijyah TEXT DEFAULT '',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (nama, monday_date)
            )
        """)

        # Migrasi kolom ahad_ke jika tabel pekan_info sudah ada sebelumnya
        cursor.execute("PRAGMA table_info(pekan_info)")
        pekan_cols = [r[1] for r in cursor.fetchall()]
        if "ahad_ke" not in pekan_cols:
            cursor.execute("ALTER TABLE pekan_info ADD COLUMN ahad_ke INTEGER")

        # Tabel Daftar Nama (Dinamis - bisa banyak nama)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS daftar_nama (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nama TEXT UNIQUE NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Masukkan nama default jika tabel daftar_nama masih kosong
        cursor.execute("SELECT COUNT(*) FROM daftar_nama")
        if cursor.fetchone()[0] == 0:
            cursor.execute("INSERT OR IGNORE INTO daftar_nama (nama) VALUES ('FIRHAN')")
            cursor.execute("INSERT OR IGNORE INTO daftar_nama (nama) VALUES ('INDRI')")

        # Masukkan nama-nama yang sudah ada di tabel laporan jika belum tercatat
        cursor.execute("SELECT DISTINCT nama FROM laporan")
        for r in cursor.fetchall():
            if r["nama"]:
                cursor.execute("INSERT OR IGNORE INTO daftar_nama (nama) VALUES (?)", (r["nama"].upper(),))

        # Tabel Preferensi Pengguna
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                chat_id INTEGER PRIMARY KEY,
                selected_nama TEXT DEFAULT 'FIRHAN',
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()

# ==================== PENGELOLAAN DAFTAR NAMA ====================

def get_all_names() -> List[str]:
    """Mengambil seluruh daftar nama pelapor yang terdaftar"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT nama FROM daftar_nama ORDER BY nama ASC")
        rows = cursor.fetchall()
        names = [r["nama"] for r in rows]
        if not names:
            names = ["FIRHAN", "INDRI"]
        return names

def add_name(nama: str) -> bool:
    """Menambahkan nama baru ke daftar nama pelapor (idempotent)"""
    nama_clean = nama.strip().upper()
    if not nama_clean:
        return False
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("INSERT OR IGNORE INTO daftar_nama (nama) VALUES (?)", (nama_clean,))
        conn.commit()
        return True

def delete_name(nama: str) -> bool:
    """Menghapus nama dari daftar (minimal harus ada 1 nama tersisa)"""
    nama_clean = nama.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM daftar_nama")
        count = cursor.fetchone()[0]
        if count <= 1:
            return False # Minimal harus ada 1 nama tersisa
        cursor.execute("DELETE FROM daftar_nama WHERE nama = ?", (nama_clean,))
        conn.commit()
        return True

# ==================== PERHITUNGAN KALENDER & LAPORAN ====================

def calculate_week_info(target_date: datetime.date) -> Tuple[datetime.date, datetime.date, int, str]:
    """
    Menghitung tanggal awal pekan (Senin), akhir pekan (Minggu), Ahad ke berapa,
    dan string bulan (contoh: '07 - 13 September 2026').
    """
    monday = target_date - datetime.timedelta(days=target_date.weekday())
    sunday = monday + datetime.timedelta(days=6)
    
    # Ahad ke dalam bulan
    ahad_ke = (sunday.day - 1) // 7 + 1
    
    if monday.month == sunday.month:
        bulan_str = f"{monday.day:02d} - {sunday.day:02d} {BULAN_INDONESIA[monday.month]} {monday.year}"
    else:
        bulan_str = f"{monday.day:02d} {BULAN_INDONESIA[monday.month]} - {sunday.day:02d} {BULAN_INDONESIA[sunday.month]} {sunday.year}"
        
    return monday, sunday, ahad_ke, bulan_str

def save_laporan(data: Dict[str, Any]):
    """Menyimpan atau memperbarui laporan harian dan menyinkronkan ahad_ke ke pekan_info"""
    nama_clean = data["nama"].strip().upper()
    add_name(nama_clean)

    data_copy = dict(data)
    data_copy["nama"] = nama_clean

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO laporan (
                chat_id, nama, tanggal, hari, ahad_ke,
                solat_malam_status, solat_malam_jam, solat_malam_alasan,
                jumlah_dzikir,
                dhuha_status, dhuha_alasan,
                puasa_status, puasa_alasan,
                rowatib, rowatib_alasan,
                updated_at
            ) VALUES (
                :chat_id, :nama, :tanggal, :hari, :ahad_ke,
                :solat_malam_status, :solat_malam_jam, :solat_malam_alasan,
                :jumlah_dzikir,
                :dhuha_status, :dhuha_alasan,
                :puasa_status, :puasa_alasan,
                :rowatib, :rowatib_alasan,
                CURRENT_TIMESTAMP
            )
            ON CONFLICT(nama, tanggal) DO UPDATE SET
                chat_id = excluded.chat_id,
                hari = excluded.hari,
                ahad_ke = excluded.ahad_ke,
                solat_malam_status = excluded.solat_malam_status,
                solat_malam_jam = excluded.solat_malam_jam,
                solat_malam_alasan = excluded.solat_malam_alasan,
                jumlah_dzikir = excluded.jumlah_dzikir,
                dhuha_status = excluded.dhuha_status,
                dhuha_alasan = excluded.dhuha_alasan,
                puasa_status = excluded.puasa_status,
                puasa_alasan = excluded.puasa_alasan,
                rowatib = excluded.rowatib,
                rowatib_alasan = excluded.rowatib_alasan,
                updated_at = CURRENT_TIMESTAMP
        """, data_copy)

        if data_copy.get("monday_date") and data_copy.get("ahad_ke"):
            cursor.execute("""
                INSERT INTO pekan_info (nama, monday_date, ahad_ke, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(nama, monday_date) DO UPDATE SET
                    ahad_ke = excluded.ahad_ke,
                    updated_at = CURRENT_TIMESTAMP
            """, (nama_clean, data_copy["monday_date"], data_copy["ahad_ke"]))

        conn.commit()

def save_pekan_info(nama: str, monday_date: str, pengajian_status: int, tata_krama_nominal: str, tata_krama_ahad: str, tata_krama_jijyah: str, ahad_ke: Optional[int] = None):
    """Menyimpan preferensi pekanan (ahad_ke, pengajian, tata krama)"""
    nama_clean = nama.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        if ahad_ke is not None:
            cursor.execute("""
                INSERT INTO pekan_info (
                    nama, monday_date, ahad_ke, pengajian_status, piket_status,
                    tata_krama_nominal, tata_krama_ahad, tata_krama_jijyah, updated_at
                ) VALUES (
                    ?, ?, ?, ?, 0, ?, ?, ?, CURRENT_TIMESTAMP
                )
                ON CONFLICT(nama, monday_date) DO UPDATE SET
                    ahad_ke = excluded.ahad_ke,
                    pengajian_status = excluded.pengajian_status,
                    tata_krama_nominal = excluded.tata_krama_nominal,
                    tata_krama_ahad = excluded.tata_krama_ahad,
                    tata_krama_jijyah = excluded.tata_krama_jijyah,
                    updated_at = CURRENT_TIMESTAMP
            """, (nama_clean, monday_date, ahad_ke, pengajian_status, tata_krama_nominal, tata_krama_ahad, tata_krama_jijyah))
        else:
            cursor.execute("""
                INSERT INTO pekan_info (
                    nama, monday_date, pengajian_status, piket_status,
                    tata_krama_nominal, tata_krama_ahad, tata_krama_jijyah, updated_at
                ) VALUES (
                    ?, ?, ?, 0, ?, ?, ?, CURRENT_TIMESTAMP
                )
                ON CONFLICT(nama, monday_date) DO UPDATE SET
                    pengajian_status = excluded.pengajian_status,
                    tata_krama_nominal = excluded.tata_krama_nominal,
                    tata_krama_ahad = excluded.tata_krama_ahad,
                    tata_krama_jijyah = excluded.tata_krama_jijyah,
                    updated_at = CURRENT_TIMESTAMP
            """, (nama_clean, monday_date, pengajian_status, tata_krama_nominal, tata_krama_ahad, tata_krama_jijyah))
        conn.commit()

def save_pekan_ahad_ke(nama: str, monday_date: str, ahad_ke: int):
    """Memperbarui nilai ahad_ke untuk pekan tertentu"""
    nama_clean = nama.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pekan_info (nama, monday_date, ahad_ke, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(nama, monday_date) DO UPDATE SET
                ahad_ke = excluded.ahad_ke,
                updated_at = CURRENT_TIMESTAMP
        """, (nama_clean, monday_date, ahad_ke))
        
        monday_dt = datetime.datetime.strptime(monday_date, "%Y-%m-%d").date()
        sunday_dt = monday_dt + datetime.timedelta(days=6)
        cursor.execute("""
            UPDATE laporan SET ahad_ke = ?
            WHERE nama = ? AND tanggal >= ? AND tanggal <= ?
        """, (ahad_ke, nama_clean, monday_date, sunday_dt.strftime("%Y-%m-%d")))
        conn.commit()

def save_pekan_jijyah(nama: str, monday_date: str, jijyah_val: str):
    """Memperbarui nilai jijyah untuk pekan tertentu"""
    nama_clean = nama.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO pekan_info (nama, monday_date, tata_krama_jijyah, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(nama, monday_date) DO UPDATE SET
                tata_krama_jijyah = excluded.tata_krama_jijyah,
                updated_at = CURRENT_TIMESTAMP
        """, (nama_clean, monday_date, jijyah_val))
        conn.commit()

def get_pekan_info(nama: str, monday_date: str) -> Dict[str, Any]:
    """Mengambil informasi pekanan (ahad_ke, pengajian, tata krama)"""
    nama_clean = nama.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM pekan_info WHERE nama = ? AND monday_date = ?", (nama_clean, monday_date))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return {
            "nama": nama_clean,
            "monday_date": monday_date,
            "ahad_ke": None,
            "pengajian_status": 0,
            "piket_status": 0,
            "tata_krama_nominal": "",
            "tata_krama_ahad": "",
            "tata_krama_jijyah": ""
        }

def get_laporan_by_date(nama: str, tanggal: str) -> Optional[Dict[str, Any]]:
    """Mengambil laporan berdasarkan nama dan tanggal (YYYY-MM-DD)"""
    nama_clean = nama.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM laporan WHERE nama = ? AND tanggal = ?", (nama_clean, tanggal))
        row = cursor.fetchone()
        if row:
            return dict(row)
        return None

def update_laporan(nama: str, tanggal: str, fields: Dict[str, Any]) -> bool:
    """Memperbarui satu atau beberapa kolom pada laporan tertentu"""
    nama_clean = nama.strip().upper()
    if not fields:
        return False
    
    set_clauses = []
    values = []
    for k, v in fields.items():
        set_clauses.append(f"{k} = ?")
        values.append(v)
    
    set_clauses.append("updated_at = CURRENT_TIMESTAMP")
    values.extend([nama_clean, tanggal])
    
    query = f"UPDATE laporan SET {', '.join(set_clauses)} WHERE nama = ? AND tanggal = ?"
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, values)
        updated = cursor.rowcount > 0
        conn.commit()
        return updated

def delete_laporan(nama: str, tanggal: str) -> bool:
    """Menghapus laporan harian berdasarkan nama dan tanggal (YYYY-MM-DD)"""
    nama_clean = nama.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM laporan WHERE nama = ? AND tanggal = ?", (nama_clean, tanggal))
        deleted = cursor.rowcount > 0
        conn.commit()
        return deleted

def get_recent_laporan(nama: str, limit: int = 7) -> List[Dict[str, Any]]:
    """Mengambil daftar laporan terbaru untuk nama tertentu"""
    nama_clean = nama.strip().upper()
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM laporan 
            WHERE nama = ? 
            ORDER BY tanggal DESC 
            LIMIT ?
        """, (nama_clean, limit))
        rows = cursor.fetchall()
        return [dict(r) for r in rows]

def get_laporan_week(nama: str, monday_date: datetime.date) -> Dict[str, Any]:
    """
    Mengambil data satu pekan (Senin sampai Minggu) untuk nama tertentu.
    Jika ada hari yang belum diisi, akan diberikan nilai default / kosong.
    Memprioritaskan nilai ahad_ke yang dipilih oleh user.
    """
    nama_clean = nama.strip().upper()
    monday, sunday, calculated_ahad_ke, bulan_str = calculate_week_info(monday_date)
    
    start_str = monday.strftime("%Y-%m-%d")
    end_str = sunday.strftime("%Y-%m-%d")
    
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT * FROM laporan 
            WHERE nama = ? AND tanggal >= ? AND tanggal <= ?
            ORDER BY tanggal ASC
        """, (nama_clean, start_str, end_str))
        rows = cursor.fetchall()
        
    db_by_day = {}
    db_ahad_ke = None
    for r in rows:
        db_by_day[r["hari"]] = dict(r)
        if r["ahad_ke"] is not None:
            db_ahad_ke = r["ahad_ke"]
        
    days_result = {}
    col_names = ["SENIN", "SELASA", "RABU", "KAMIS", "JUM'AT", "SABTU", "MINGGU"]
    
    keterangan_solat_malam = []
    keterangan_dhuha = []
    keterangan_puasa = []
    keterangan_rowatib = []

    for i, day_name in enumerate(col_names):
        rec = db_by_day.get(day_name)
        
        if rec:
            if rec["solat_malam_status"] == 1:
                sm_val = rec["solat_malam_jam"] or "03:30 s/d 04:10"
                dzikir_val = rec["jumlah_dzikir"] or "10000"
            else:
                sm_val = "-"
                dzikir_val = "-"
                sm_alasan = rec["solat_malam_alasan"] or "Terlewat"
                keterangan_solat_malam.append(f"{day_name}: {sm_alasan}")

            if rec["dhuha_status"] == 1:
                dhuha_val = "✓"
            else:
                dhuha_val = "-"
                dh_alasan = rec["dhuha_alasan"] or "Terlewat"
                keterangan_dhuha.append(f"{day_name}: {dh_alasan}")

            if rec["puasa_status"] == 1:
                puasa_val = "✓"
            else:
                puasa_val = "-" if day_name in ["SENIN", "KAMIS"] else ""
                if day_name in ["SENIN", "KAMIS"]:
                    p_alasan = rec["puasa_alasan"] or "Tidak Puasa"
                    keterangan_puasa.append(f"{day_name}: {p_alasan}")

            rowatib_val = rec["rowatib"] or "5 waktu"
            if rowatib_val != "5 waktu":
                rw_alasan = rec["rowatib_alasan"] or "Halangan"
                keterangan_rowatib.append(f"{day_name}: {rw_alasan}")
            elif rec["rowatib_alasan"]:
                keterangan_rowatib.append(f"{day_name}: {rec['rowatib_alasan']}")

            days_result[day_name] = {
                "solat_malam": sm_val,
                "solat_malam_alasan": rec.get("solat_malam_alasan", ""),
                "jumlah_dzikir": dzikir_val,
                "dhuha": dhuha_val,
                "dhuha_alasan": rec.get("dhuha_alasan", ""),
                "puasa": puasa_val,
                "puasa_alasan": rec.get("puasa_alasan", ""),
                "rowatib": rowatib_val,
                "rowatib_alasan": rec.get("rowatib_alasan", "")
            }
        else:
            days_result[day_name] = {
                "solat_malam": "",
                "solat_malam_alasan": "",
                "jumlah_dzikir": "",
                "dhuha": "",
                "dhuha_alasan": "",
                "puasa": "",
                "puasa_alasan": "",
                "rowatib": "",
                "rowatib_alasan": ""
            }

    keterangan_rows = {
        "solat_malam": "<br/>".join(keterangan_solat_malam),
        "jumlah_dzikir": "",
        "dhuha": "<br/>".join(keterangan_dhuha),
        "puasa": "<br/>".join(keterangan_puasa),
        "rowatib": "<br/>".join(keterangan_rowatib),
    }

    pekan_meta = get_pekan_info(nama_clean, start_str)

    final_ahad_ke = calculated_ahad_ke
    if pekan_meta.get("ahad_ke") is not None:
        final_ahad_ke = pekan_meta["ahad_ke"]
    elif db_ahad_ke is not None:
        final_ahad_ke = db_ahad_ke

    return {
        "nama": nama_clean,
        "ahad_ke": final_ahad_ke,
        "bulan": bulan_str,
        "posko": os.getenv("POSKO_NAME", "TANGKIL"),
        "monday_date": start_str,
        "sunday_date": end_str,
        "filled_days_count": len(db_by_day),
        "days": days_result,
        "keterangan_rows": keterangan_rows,
        "pengajian_status": pekan_meta.get("pengajian_status", 0),
        "piket_status": 0,
        "tata_krama_nominal": pekan_meta.get("tata_krama_nominal", ""),
        "tata_krama_ahad": pekan_meta.get("tata_krama_ahad", ""),
        "tata_krama_jijyah": pekan_meta.get("tata_krama_jijyah", "")
    }

def get_available_weeks(nama: Optional[str] = None) -> List[Dict[str, Any]]:
    """Mengambil daftar pekan yang terdapat input laporan di database (per nama atau seluruh anggota jika nama=None)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        if nama:
            nama_clean = nama.strip().upper()
            cursor.execute("SELECT DISTINCT tanggal, ahad_ke, nama FROM laporan WHERE nama = ? ORDER BY tanggal DESC", (nama_clean,))
        else:
            cursor.execute("SELECT DISTINCT tanggal, ahad_ke, nama FROM laporan ORDER BY tanggal DESC")
        date_rows = cursor.fetchall()
        
    weeks = {}
    for r in date_rows:
        d = datetime.datetime.strptime(r["tanggal"], "%Y-%m-%d").date()
        mon, sun, calc_ahad, b_str = calculate_week_info(d)
        mon_str = mon.strftime("%Y-%m-%d")
        if mon_str not in weeks:
            row_nama = r["nama"] if r["nama"] else (nama.strip().upper() if nama else "FIRHAN")
            pekan_meta = get_pekan_info(row_nama, mon_str)
            ahad_val = pekan_meta.get("ahad_ke") or r["ahad_ke"] or calc_ahad
            weeks[mon_str] = {
                "monday": mon,
                "sunday": sun,
                "ahad_ke": ahad_val,
                "bulan_str": b_str,
                "monday_str": mon_str
            }
    return list(weeks.values())

def get_user_setting(chat_id: int) -> str:
    """Mengambil nama yang dipilih user (default ke nama pertama yang tersedia)"""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT selected_nama FROM user_settings WHERE chat_id = ?", (chat_id,))
        row = cursor.fetchone()
        if row and row["selected_nama"]:
            return row["selected_nama"]
        
        cursor.execute("SELECT nama FROM daftar_nama ORDER BY id ASC LIMIT 1")
        first_name = cursor.fetchone()
        if first_name and first_name[0]:
            return first_name[0]
        return "FIRHAN"

def set_user_setting(chat_id: int, nama: str):
    """Menyimpan nama yang dipilih user (bisa nama apa saja)"""
    nama_clean = nama.strip().upper()
    if not nama_clean:
        return
    
    add_name(nama_clean)

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO user_settings (chat_id, selected_nama, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(chat_id) DO UPDATE SET
                selected_nama = excluded.selected_nama,
                updated_at = CURRENT_TIMESTAMP
        """, (chat_id, nama_clean))
        conn.commit()

# Inisialisasi DB saat modul di-import
init_db()
