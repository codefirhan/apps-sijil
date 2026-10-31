import os
import logging
import datetime
from typing import Dict, Any

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters,
)
from dotenv import load_dotenv

import database
import pdf_generator

load_dotenv()

# Konfigurasi Logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# States untuk ConversationHandler
(
    STATE_INPUT_DATE,
    STATE_MANUAL_DATE,
    STATE_AHAD_KE,
    STATE_SOLAT_MALAM,
    STATE_SM_TIME,
    STATE_SM_REASON,
    STATE_DZIKIR,
    STATE_DHUHA,
    STATE_DHUHA_REASON,
    STATE_PUASA,
    STATE_PUASA_REASON,
    STATE_ROWATIB,
    STATE_ROWATIB_REASON,
    STATE_PENGAJIAN,
    STATE_TATAKRAMA,
    STATE_TATAKRAMA_MANUAL,
    STATE_CONFIRMATION,
    STATE_PRINT_DATE,
    STATE_PRINT_MANUAL_DATE,
    STATE_PRINT_SETTINGS,
    STATE_PRINT_MANUAL_JIJYAH,
    STATE_PRINT_FORMAT,
    STATE_ADD_NAME,
    STATE_DELETE_NAME,
    STATE_EDIT_SELECT_DATE,
    STATE_EDIT_MANUAL_DATE,
    STATE_EDIT_MENU,
    STATE_EDIT_SM_STATUS,
    STATE_EDIT_SM_TIME,
    STATE_EDIT_SM_REASON,
    STATE_EDIT_DZIKIR,
    STATE_EDIT_DHUHA_STATUS,
    STATE_EDIT_DHUHA_REASON,
    STATE_EDIT_PUASA_STATUS,
    STATE_EDIT_PUASA_REASON,
    STATE_EDIT_ROWATIB,
    STATE_EDIT_ROWATIB_REASON,
    STATE_EDIT_AHAD_KE,
    STATE_EDIT_JIJYAH,
    STATE_EDIT_JIJYAH_MANUAL,
    STATE_EDIT_DELETE_CONFIRM,
) = range(41)

def build_main_menu(chat_id: int):
    selected_name = database.get_user_setting(chat_id)
    text = (
        "🕌 *BOT LAPORAN PELAKSANAAN AMANAH*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Nama Pelapor Aktif:* `{selected_name}`\n"
        f"🏢 *Posko:* `TANGKIL` (Statis)\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Silakan pilih menu di bawah ini:"
    )
    keyboard = [
        [InlineKeyboardButton("📝 Input Laporan Harian", callback_data="menu_input")],
        [InlineKeyboardButton("✏️ Edit Data Inputan", callback_data="menu_edit")],
        [InlineKeyboardButton("📄 Cetak Laporan (Gambar / PDF)", callback_data="menu_print")],
        [InlineKeyboardButton("📊 Rekap Data Pekan Ini", callback_data="menu_recap")],
        [InlineKeyboardButton("👤 Ganti / Kelola Nama Pelapor", callback_data="menu_switch_name")],
        [InlineKeyboardButton("ℹ️ Bantuan & Format", callback_data="menu_help")]
    ]
    return text, InlineKeyboardMarkup(keyboard)

def build_name_menu(chat_id: int):
    selected_name = database.get_user_setting(chat_id)
    all_names = database.get_all_names()

    text = (
        "👤 *PENGELOLAAN NAMA PELAPOR*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"Pelapor Aktif Saat Ini: *{selected_name}*\n\n"
        "Pilih nama di bawah untuk berganti pelapor, atau tambahkan nama baru:"
    )

    keyboard = []
    # Susun nama dalam baris per 2 tombol
    row = []
    for name in all_names:
        is_active = (name == selected_name)
        label = f"✅ {name}" if is_active else f"👤 {name}"
        row.append(InlineKeyboardButton(label, callback_data=f"set_name_{name}"))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    # Tombol aksi tambah dan hapus nama
    keyboard.append([
        InlineKeyboardButton("➕ Tambah Nama Baru", callback_data="act_add_name"),
        InlineKeyboardButton("🗑️ Hapus Nama", callback_data="act_del_name_menu")
    ])
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data="menu_main")])

    return text, InlineKeyboardMarkup(keyboard)

# ==================== HANDLER MENU UTAMA ====================

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    text, reply_markup = build_main_menu(chat_id)
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
    return ConversationHandler.END

async def menu_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id

    if data == "menu_main":
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    elif data == "menu_switch_name":
        text, reply_markup = build_name_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    elif data.startswith("set_name_"):
        new_name = data.replace("set_name_", "").strip().upper()
        database.set_user_setting(chat_id, new_name)
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(
            text=f"✅ *Nama aktif berhasil diubah menjadi: {new_name}*\n\n" + text,
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    elif data == "menu_recap":
        cur_name = database.get_user_setting(chat_id)
        today = datetime.date.today()
        mon, sun, calc_ahad, b_str = database.calculate_week_info(today)
        report = database.get_laporan_week(cur_name, mon)

        pengajian_status_str = "Hadir (✓)" if report["pengajian_status"] == 1 else "Tidak (✓)"
        jijyah_val = report["tata_krama_jijyah"] or "-"

        text = (
            f"📊 *REKAP PEKAN INI*\n"
            f"👤 Pelapor: `{cur_name}`\n"
            f"📅 Pekan: `{b_str}` (Ahad ke-{report['ahad_ke']})\n"
            f"🏢 Posko: `TANGKIL` (Statis)\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
        )
        days = ["SENIN", "SELASA", "RABU", "KAMIS", "JUM'AT", "SABTU", "MINGGU"]
        for d in days:
            d_data = report["days"][d]
            if d_data["solat_malam"] != "":
                text += f"✅ *{d}:* SM: {d_data['solat_malam']}, Dz: {d_data['jumlah_dzikir']}, Dh: {d_data['dhuha']}, P: {d_data['puasa'] or '-'}, Rw: {d_data['rowatib']}\n"
            else:
                text += f"⚪ *{d}:* _Belum diisi_\n"

        text += (
            f"\nTotal terisi: *{report['filled_days_count']} / 7 hari*\n"
            f"🗓 *Ahad Ke:* {report['ahad_ke']}\n"
            f"🕌 *Pengajian:* {pengajian_status_str}\n"
            f"🧹 *Piket:* Tidak (✓) [Statis]\n"
            f"💰 *Jijyah (Tata Krama):* {jijyah_val}\n"
        )

        keyboard = [
            [InlineKeyboardButton("📄 Cetak Laporan Pekan Ini", callback_data=f"quick_print_{mon.strftime('%Y-%m-%d')}")],
            [InlineKeyboardButton("✏️ Edit Data Inputan", callback_data="menu_edit")],
            [InlineKeyboardButton("📝 Input Laporan", callback_data="menu_input")],
            [InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="menu_main")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END

    elif data == "menu_help":
        help_text = (
            "ℹ️ *PANDUAN & ATURAN LAPORAN*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "1. *Kelola Nama*: Anda dapat menambahkan nama pelapor baru sebanyak mungkin dan beralih pelapor dengan mudah.\n"
            "2. *Ahad Ke*: Menentukan pekan ke berapa (1, 2, 3, 4, 5) dan tersimpan sesuai pilihan Anda.\n"
            "3. *Solat Malam*: Rentang jam mulai s/d selesai (contoh: `03:30 s/d 04:10`) & jumlah dzikir (`10.000` / `20.000`). Jika tidak, sertakan alasan.\n"
            "4. *Solat Dhuha*: Pilih Ya (✓) atau Tidak (sertakan alasan).\n"
            "5. *Puasa Senin & Kamis*: Pilih Ya (✓) atau Tidak (sertakan alasan).\n"
            "6. *Solat Rowatib*: Pilihan 1 - 5 waktu.\n"
            "7. *Pengajian*: Pilih Hadir (Iya) atau Tidak untuk pekan tersebut.\n"
            "8. *Piket*: Dibuat statis Tidak (`Tidak : ✓`).\n"
            "9. *Jijyah*: Pilihan antara 2000 atau 67000 atau input nominal manual.\n"
            "10. *Posko*: Selalu otomatis `TANGKIL` (statis).\n"
            "11. *Format Laporan*: Bisa dicetak dalam format *Gambar (Foto)* langsung di Telegram atau file *PDF Dokumen*.\n"
            "12. *Edit Inputan*: Memperbaiki per butir (Solat Malam, Dhuha, Puasa, Rowatib, Ahad Ke) atau menghapus data inputan yang salah."
        )
        keyboard = [[InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="menu_main")]]
        await query.edit_message_text(text=help_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END

    return ConversationHandler.END

# ==================== FLOW PENGELOLAAN NAMA ====================

async def start_add_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "✏️ *TAMBAH NAMA PELAPOR BARU*\n\n"
        "Silakan ketik nama pelapor yang ingin ditambahkan:\n"
        "(Contoh: `AHMAD`, `SITI`, `RAHMAT`, dll)"
    )
    keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data="menu_switch_name")]]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_ADD_NAME

async def handle_name_added(update: Update, context: ContextTypes.DEFAULT_TYPE):
    raw_name = update.message.text.strip().upper()
    chat_id = update.effective_chat.id

    if not raw_name:
        await update.message.reply_text("⚠️ Nama tidak boleh kosong. Silakan ketik nama:")
        return STATE_ADD_NAME

    # Tambahkan nama ke database
    success = database.add_name(raw_name)
    # Jadikan nama aktif
    database.set_user_setting(chat_id, raw_name)

    if success:
        msg = f"✅ Nama *{raw_name}* berhasil ditambahkan dan dijadikan pelapor aktif!"
    else:
        msg = f"ℹ️ Nama *{raw_name}* sudah ada di daftar dan kini dijadikan pelapor aktif!"

    text, reply_markup = build_main_menu(chat_id)
    await update.message.reply_text(
        text=f"{msg}\n\n" + text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def start_del_name_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = update.effective_chat.id
    all_names = database.get_all_names()

    if len(all_names) <= 1:
        await query.answer("Minimal harus ada 1 nama tersisa di sistem.", show_alert=True)
        return ConversationHandler.END

    text = (
        "🗑️ *HAPUS NAMA PELAPOR*\n\n"
        "Pilih nama yang ingin dihapus dari daftar sistem:"
    )
    keyboard = []
    for name in all_names:
        keyboard.append([InlineKeyboardButton(f"❌ Hapus {name}", callback_data=f"del_name_{name}")])
    keyboard.append([InlineKeyboardButton("🔙 Batal", callback_data="menu_switch_name")])

    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_DELETE_NAME

async def handle_name_deleted(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id

    target_name = data.replace("del_name_", "").strip().upper()
    success = database.delete_name(target_name)

    if not success:
        await query.answer("Gagal menghapus. Minimal harus ada 1 nama tersisa.", show_alert=True)
    else:
        # Jika nama yang aktif dihapus, beralih ke nama pertama yang tersedia
        cur_name = database.get_user_setting(chat_id)
        if cur_name == target_name:
            all_names = database.get_all_names()
            database.set_user_setting(chat_id, all_names[0])

    text, reply_markup = build_name_menu(chat_id)
    await query.edit_message_text(
        text=f"🗑️ Nama *{target_name}* telah dihapus dari daftar.\n\n" + text,
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# ==================== FLOW INPUT LAPORAN HARIAN ====================

async def input_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)

    today_hari = database.HARI_INDONESIA[today.weekday()]
    yesterday_hari = database.HARI_INDONESIA[yesterday.weekday()]

    text = (
        f"📝 *INPUT LAPORAN PELAKSANAAN AMANAH*\n"
        f"👤 Pelapor: `{cur_name}`\n"
        f"🏢 Posko: `TANGKIL` (Statis)\n\n"
        f"Silakan pilih tanggal yang ingin diinput:"
    )
    keyboard = [
        [InlineKeyboardButton(f"📅 Hari Ini ({today_hari}, {today.strftime('%d-%m-%Y')})", callback_data=f"date_pick_{today.strftime('%Y-%m-%d')}")],
        [InlineKeyboardButton(f"📅 Kemarin ({yesterday_hari}, {yesterday.strftime('%d-%m-%Y')})", callback_data=f"date_pick_{yesterday.strftime('%Y-%m-%d')}")],
        [InlineKeyboardButton("📆 Pilih / Ketik Tanggal Lain", callback_data="date_pick_custom")],
        [InlineKeyboardButton("🔙 Batal / Menu Utama", callback_data="input_cancel")]
    ]
    if query:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_INPUT_DATE

async def input_date_picked(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "date_pick_custom":
        text = (
            "📆 *Ketik Tanggal Laporan*\n\n"
            "Silakan kirimkan tanggal dengan format `DD-MM-YYYY` atau `YYYY-MM-DD`\n"
            "(Contoh: `07-09-2026` atau `2026-09-07`):"
        )
        keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_MANUAL_DATE

    date_str = data.replace("date_pick_", "")
    target_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    return await proceed_with_date(target_date, update, context)

async def input_manual_date(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_input = update.message.text.strip()
    target_date = None

    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            target_date = datetime.datetime.strptime(text_input, fmt).date()
            break
        except ValueError:
            pass

    if not target_date:
        await update.message.reply_text(
            "⚠️ Format tanggal tidak dikenali. Gunakan contoh `07-09-2026` atau `2026-09-07`.\nSilakan coba ketik lagi:"
        )
        return STATE_MANUAL_DATE

    return await proceed_with_date(target_date, update, context)

async def proceed_with_date(target_date: datetime.date, update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)
    hari = database.HARI_INDONESIA[target_date.weekday()]
    monday, sunday, calc_ahad_ke, bulan_str = database.calculate_week_info(target_date)

    monday_str = monday.strftime("%Y-%m-%d")
    pekan_meta = database.get_pekan_info(cur_name, monday_str)
    active_ahad_ke = pekan_meta.get("ahad_ke") or calc_ahad_ke

    context.user_data["input_form"] = {
        "chat_id": chat_id,
        "nama": cur_name,
        "tanggal": target_date.strftime("%Y-%m-%d"),
        "hari": hari,
        "ahad_ke": active_ahad_ke,
        "monday_date": monday_str,
        "bulan_str": bulan_str,
    }

    existing_rec = database.get_laporan_by_date(cur_name, target_date.strftime("%Y-%m-%d"))
    existing_note = ""
    if existing_rec:
        existing_note = "⚠️ _Catatan: Laporan untuk tanggal ini sudah pernah diisi. Melanjutkan akan menimpa data lama. Untuk mengubah bagian tertentu saja, gunakan menu ✏️ Edit Data Inputan di menu utama._\n\n"

    text = (
        f"{existing_note}"
        f"📅 Tanggal: *{hari}, {target_date.strftime('%d-%m-%Y')}*\n"
        f"Pekan: `{bulan_str}`\n\n"
        f"Tercatat saat ini sebagai *Ahad ke-{active_ahad_ke}*.\n"
        "Apakah ingin lanjut dengan nilai ini atau ingin mengubah Ahad ke?"
    )
    keyboard = [
        [InlineKeyboardButton(f"➡️ Lanjut (Ahad ke-{active_ahad_ke})", callback_data=f"ahad_set_{active_ahad_ke}")],
        [
            InlineKeyboardButton("Ahad 1", callback_data="ahad_set_1"),
            InlineKeyboardButton("Ahad 2", callback_data="ahad_set_2"),
            InlineKeyboardButton("Ahad 3", callback_data="ahad_set_3"),
            InlineKeyboardButton("Ahad 4", callback_data="ahad_set_4"),
            InlineKeyboardButton("Ahad 5", callback_data="ahad_set_5"),
        ],
        [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_AHAD_KE

async def input_ahad_ke_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    ahad_val = int(data.replace("ahad_set_", ""))
    context.user_data["input_form"]["ahad_ke"] = ahad_val

    form = context.user_data["input_form"]
    text = (
        f"🌙 *1. SOLAT MALAM*\n\n"
        f"Hari: *{form['hari']}*, {form['tanggal']} (Ahad ke-{ahad_val})\n"
        f"Apakah Anda melaksanakan Solat Malam?"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ Ya (Melaksanakan)", callback_data="sm_ya"),
            InlineKeyboardButton("❌ Tidak", callback_data="sm_tidak")
        ],
        [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_SOLAT_MALAM

# --- Step: Solat Malam ---

async def sm_status_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "sm_ya":
        context.user_data["input_form"]["solat_malam_status"] = 1
        context.user_data["input_form"]["solat_malam_alasan"] = ""
        text = (
            "🕒 *Masukkan Jam Pelaksanaan Solat Malam*\n\n"
            "Pilih opsi cepat atau ketik manual (contoh: `03:30 s/d 04:10`):"
        )
        keyboard = [
            [
                InlineKeyboardButton("03:30 s/d 04:10", callback_data="smtime_03:30 s/d 04:10"),
                InlineKeyboardButton("03:40 s/d 04:20", callback_data="smtime_03:40 s/d 04:20")
            ],
            [
                InlineKeyboardButton("03:35 s/d 04:15", callback_data="smtime_03:35 s/d 04:15"),
                InlineKeyboardButton("03:15 s/d 03:50", callback_data="smtime_03:15 s/d 03:50")
            ],
            [InlineKeyboardButton("✏️ Ketik Jam Manual", callback_data="smtime_manual")],
            [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_SM_TIME
    else:
        context.user_data["input_form"]["solat_malam_status"] = 0
        context.user_data["input_form"]["solat_malam_jam"] = "-"
        context.user_data["input_form"]["jumlah_dzikir"] = "-"
        text = (
            "❌ *Alasan Tidak Solat Malam*\n\n"
            "Pilih alasan cepat atau ketik alasan manual:"
        )
        keyboard = [
            [
                InlineKeyboardButton("Terlewat", callback_data="smreason_Terlewat"),
                InlineKeyboardButton("Kesiangan", callback_data="smreason_Kesiangan")
            ],
            [
                InlineKeyboardButton("Halangan", callback_data="smreason_Halangan"),
                InlineKeyboardButton("Sakit", callback_data="smreason_Sakit")
            ],
            [
                InlineKeyboardButton("Uzur Syar'i", callback_data="smreason_Uzur Syar'i"),
                InlineKeyboardButton("Kelelahan / Safar", callback_data="smreason_Kelelahan / Safar")
            ],
            [InlineKeyboardButton("✏️ Ketik Alasan Manual", callback_data="smreason_manual")],
            [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_SM_REASON

async def sm_time_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "smtime_manual":
        text = "🕒 Silakan ketik jam pelaksanaan Solat Malam (contoh: `03:30 s/d 04:10`):"
        await query.edit_message_text(text=text, parse_mode="Markdown")
        return STATE_SM_TIME

    time_val = data.replace("smtime_", "")
    context.user_data["input_form"]["solat_malam_jam"] = time_val
    return await ask_dzikir(update, context)

async def sm_time_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_val = update.message.text.strip()
    context.user_data["input_form"]["solat_malam_jam"] = time_val
    return await ask_dzikir(update, context)

async def ask_dzikir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📿 *Masukkan Jumlah Dzikir*\n\n"
        "Pilih jumlah dzikir cepat atau ketik manual:"
    )
    keyboard = [
        [
            InlineKeyboardButton("10.000", callback_data="dzikir_10000"),
            InlineKeyboardButton("20.000", callback_data="dzikir_20000")
        ],
        [
            InlineKeyboardButton("15.000", callback_data="dzikir_15000"),
            InlineKeyboardButton("5.000", callback_data="dzikir_5000")
        ],
        [InlineKeyboardButton("✏️ Ketik Jumlah Manual", callback_data="dzikir_manual")],
        [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_DZIKIR

async def sm_reason_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "smreason_manual":
        text = "✏️ Silakan ketik alasan tidak melaksanakan Solat Malam:"
        await query.edit_message_text(text=text, parse_mode="Markdown")
        return STATE_SM_REASON

    reason_val = data.replace("smreason_", "")
    context.user_data["input_form"]["solat_malam_alasan"] = reason_val
    return await ask_dhuha(update, context)

async def sm_reason_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason_val = update.message.text.strip()
    context.user_data["input_form"]["solat_malam_alasan"] = reason_val
    return await ask_dhuha(update, context)

async def dzikir_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "dzikir_manual":
        text = "📿 Silakan ketik jumlah dzikir (contoh: `10000` atau `20.000`):"
        await query.edit_message_text(text=text, parse_mode="Markdown")
        return STATE_DZIKIR

    dzikir_val = data.replace("dzikir_", "")
    if dzikir_val == "10000":
        dzikir_val = "10000"
    elif dzikir_val == "20000":
        dzikir_val = "20.000"
    context.user_data["input_form"]["jumlah_dzikir"] = dzikir_val
    return await ask_dhuha(update, context)

async def dzikir_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dzikir_val = update.message.text.strip()
    context.user_data["input_form"]["jumlah_dzikir"] = dzikir_val
    return await ask_dhuha(update, context)

# --- Step: Solat Dhuha ---

async def ask_dhuha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "☀️ *2. SOLAT DHUHA*\n\n"
        "Apakah Anda melaksanakan Solat Dhuha?"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ Ya (Melaksanakan)", callback_data="dhuha_ya"),
            InlineKeyboardButton("❌ Tidak", callback_data="dhuha_tidak")
        ],
        [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_DHUHA

async def dhuha_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "dhuha_ya":
        context.user_data["input_form"]["dhuha_status"] = 1
        context.user_data["input_form"]["dhuha_alasan"] = ""
        return await ask_puasa(update, context)
    else:
        context.user_data["input_form"]["dhuha_status"] = 0
        text = (
            "❌ *Alasan Tidak Solat Dhuha*\n\n"
            "Pilih alasan cepat atau ketik manual:"
        )
        keyboard = [
            [
                InlineKeyboardButton("Terlewat", callback_data="dhreason_Terlewat"),
                InlineKeyboardButton("Halangan", callback_data="dhreason_Halangan")
            ],
            [
                InlineKeyboardButton("Uzur Syar'i", callback_data="dhreason_Uzur Syar'i"),
                InlineKeyboardButton("Sakit", callback_data="dhreason_Sakit")
            ],
            [
                InlineKeyboardButton("Di Perjalanan / Safar", callback_data="dhreason_Safar"),
                InlineKeyboardButton("Tugas / Sibuk", callback_data="dhreason_Ada Keperluan Mendesak")
            ],
            [InlineKeyboardButton("✏️ Ketik Alasan Manual", callback_data="dhreason_manual")],
            [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_DHUHA_REASON

async def dhuha_reason_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "dhreason_manual":
        text = "✏️ Silakan ketik alasan tidak melaksanakan Solat Dhuha:"
        await query.edit_message_text(text=text, parse_mode="Markdown")
        return STATE_DHUHA_REASON

    reason_val = data.replace("dhreason_", "")
    context.user_data["input_form"]["dhuha_alasan"] = reason_val
    return await ask_puasa(update, context)

async def dhuha_reason_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason_val = update.message.text.strip()
    context.user_data["input_form"]["dhuha_alasan"] = reason_val
    return await ask_puasa(update, context)

# --- Step: Puasa Senin & Kamis ---

async def ask_puasa(update: Update, context: ContextTypes.DEFAULT_TYPE):
    form = context.user_data["input_form"]
    hari = form["hari"]

    text = (
        f"🍃 *3. PUASA SENIN & KAMIS*\n\n"
        f"Hari: *{hari}*\n"
        "Apakah Anda melaksanakan Puasa Sunnah?"
    )
    keyboard = [
        [
            InlineKeyboardButton("✅ Ya (Melaksanakan)", callback_data="puasa_ya"),
            InlineKeyboardButton("❌ Tidak", callback_data="puasa_tidak")
        ],
        [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_PUASA

async def puasa_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "puasa_ya":
        context.user_data["input_form"]["puasa_status"] = 1
        context.user_data["input_form"]["puasa_alasan"] = ""
        return await ask_rowatib(update, context)
    else:
        context.user_data["input_form"]["puasa_status"] = 0
        form = context.user_data["input_form"]
        hari = form["hari"]

        extra_btn = [InlineKeyboardButton("Bukan Jadwal Puasa", callback_data="preason_Bukan Jadwal Puasa")] if hari not in ["SENIN", "KAMIS"] else []

        text = (
            "❌ *Alasan Tidak Berpuasa*\n\n"
            "Pilih alasan cepat atau ketik manual:"
        )
        keyboard = [
            [
                InlineKeyboardButton("Halangan", callback_data="preason_Halangan"),
                InlineKeyboardButton("Terlewat", callback_data="preason_Terlewat")
            ],
            [
                InlineKeyboardButton("Tidak Puasa", callback_data="preason_Tidak Puasa"),
                InlineKeyboardButton("Sakit", callback_data="preason_Sakit")
            ],
            [
                InlineKeyboardButton("Uzur Syar'i", callback_data="preason_Uzur Syar'i"),
                InlineKeyboardButton("Safar", callback_data="preason_Safar")
            ],
            *( [extra_btn] if extra_btn else [] ),
            [InlineKeyboardButton("✏️ Ketik Alasan Manual", callback_data="preason_manual")],
            [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_PUASA_REASON

async def puasa_reason_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "preason_manual":
        text = "✏️ Silakan ketik alasan tidak berpuasa:"
        await query.edit_message_text(text=text, parse_mode="Markdown")
        return STATE_PUASA_REASON

    reason_val = data.replace("preason_", "")
    if reason_val == "Bukan Jadwal Puasa":
        reason_val = ""
    context.user_data["input_form"]["puasa_alasan"] = reason_val
    return await ask_rowatib(update, context)

async def puasa_reason_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason_val = update.message.text.strip()
    context.user_data["input_form"]["puasa_alasan"] = reason_val
    return await ask_rowatib(update, context)

# --- Step: Solat Rowatib ---

async def ask_rowatib(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🕌 *4. SOLAT ROWATIB*\n\n"
        "Berapa waktu Solat Rowatib yang Anda laksanakan?"
    )
    keyboard = [
        [
            InlineKeyboardButton("5 Waktu", callback_data="rowatib_5 waktu"),
            InlineKeyboardButton("4 Waktu", callback_data="rowatib_4 waktu")
        ],
        [
            InlineKeyboardButton("3 Waktu", callback_data="rowatib_3 waktu"),
            InlineKeyboardButton("2 Waktu", callback_data="rowatib_2 waktu")
        ],
        [
            InlineKeyboardButton("1 Waktu", callback_data="rowatib_1 waktu"),
            InlineKeyboardButton("0 (Tidak)", callback_data="rowatib_0 waktu")
        ],
        [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_ROWATIB

async def rowatib_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    rowatib_val = data.replace("rowatib_", "")
    context.user_data["input_form"]["rowatib"] = rowatib_val

    # Jika full 5 waktu, tidak perlu alasan
    if rowatib_val == "5 waktu":
        context.user_data["input_form"]["rowatib_alasan"] = ""
        return await proceed_after_rowatib(update, context)
    else:
        # Jika tidak full (4, 3, 2, 1, 0 waktu), tanyakan alasannya
        text = (
            f"❌ *Alasan Tidak Full Solat Rowatib*\n\n"
            f"Anda memilih: *{rowatib_val}* (tidak full 5 waktu).\n"
            "Silakan pilih alasan atau ketik manual:"
        )
        keyboard = [
            [
                InlineKeyboardButton("Halangan", callback_data="rwreason_Halangan"),
                InlineKeyboardButton("Terlewat", callback_data="rwreason_Terlewat")
            ],
            [
                InlineKeyboardButton("Sakit", callback_data="rwreason_Sakit"),
                InlineKeyboardButton("Uzur Syar'i", callback_data="rwreason_Uzur Syar'i")
            ],
            [
                InlineKeyboardButton("Safar / Perjalanan", callback_data="rwreason_Safar"),
                InlineKeyboardButton("Ada Keperluan", callback_data="rwreason_Ada Keperluan Mendesak")
            ],
            [InlineKeyboardButton("✏️ Ketik Alasan Manual", callback_data="rwreason_manual")],
            [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_ROWATIB_REASON

async def rowatib_reason_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "rwreason_manual":
        text = "✏️ Silakan ketik alasan tidak full Solat Rowatib:"
        await query.edit_message_text(text=text, parse_mode="Markdown")
        return STATE_ROWATIB_REASON

    reason_val = data.replace("rwreason_", "")
    context.user_data["input_form"]["rowatib_alasan"] = reason_val
    return await proceed_after_rowatib(update, context)

async def rowatib_reason_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason_val = update.message.text.strip()
    context.user_data["input_form"]["rowatib_alasan"] = reason_val
    return await proceed_after_rowatib(update, context)

async def proceed_after_rowatib(update: Update, context: ContextTypes.DEFAULT_TYPE):
    form = context.user_data["input_form"]

    # Jika hari yang diinput adalah MINGGU, tanyakan juga Pengajian dan Jijyah pekan ini
    if form["hari"] == "MINGGU":
        text = (
            "🕌 *5. PENGAJIAN PEKAN INI*\n\n"
            "Apakah Anda menghadiri Pengajian pada pekan ini?"
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ Ya (Hadir)", callback_data="pengajian_set_1"),
                InlineKeyboardButton("❌ Tidak", callback_data="pengajian_set_0")
            ],
            [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
        ]
        if update.callback_query:
            await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        else:
            await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_PENGAJIAN

    return await show_input_summary(update, context)

async def pengajian_input_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    val = 1 if "set_1" in data else 0
    context.user_data["input_form"]["pengajian_status"] = val

    text = (
        "💰 *6. JIJYAH (TATA KRAMA) PEKAN INI*\n\n"
        "Pilih nominal untuk Jijyah (atau ketik manual):"
    )
    keyboard = [
        [
            InlineKeyboardButton("💰 2000", callback_data="jset_2000"),
            InlineKeyboardButton("💰 67000", callback_data="jset_67000")
        ],
        [
            InlineKeyboardButton("✏️ Ketik Manual", callback_data="jset_manual"),
            InlineKeyboardButton("⏭️ Lewati / Kosongkan", callback_data="jset_none")
        ],
        [InlineKeyboardButton("🔙 Batal", callback_data="input_cancel")]
    ]
    await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_TATAKRAMA

async def tatakrama_input_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data

    if data == "input_cancel":
        chat_id = update.effective_chat.id
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "jset_manual":
        text = "✏️ Silakan ketik nominal untuk Jijyah (contoh: `2000`, `67000`, `50000`):"
        await query.edit_message_text(text=text, parse_mode="Markdown")
        return STATE_TATAKRAMA_MANUAL

    choice = data.replace("jset_", "")
    if choice == "none":
        context.user_data["input_form"]["tata_krama_jijyah"] = ""
    else:
        context.user_data["input_form"]["tata_krama_jijyah"] = choice

    context.user_data["input_form"]["tata_krama_ahad"] = ""
    return await show_input_summary(update, context)

async def tatakrama_manual_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    context.user_data["input_form"]["tata_krama_jijyah"] = val
    context.user_data["input_form"]["tata_krama_ahad"] = ""
    return await show_input_summary(update, context)

async def show_input_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    form = context.user_data["input_form"]

    sm_summary = f"Ya ({form.get('solat_malam_jam', '-')}, Dzikir: {form.get('jumlah_dzikir', '-')})" if form.get("solat_malam_status") == 1 else f"Tidak (Alasan: {form.get('solat_malam_alasan', '-')})"
    dh_summary = "Ya (✓)" if form.get("dhuha_status") == 1 else f"Tidak (Alasan: {form.get('dhuha_alasan', '-')})"
    p_summary = "Ya (✓)" if form.get("puasa_status") == 1 else (f"Tidak (Alasan: {form.get('puasa_alasan', '-')})" if form.get("puasa_alasan") else "Tidak")
    rw_alasan_str = f" (Alasan: {form['rowatib_alasan']})" if form.get("rowatib") != "5 waktu" and form.get("rowatib_alasan") else ""

    extra_minggu_text = ""
    if "pengajian_status" in form:
        p_stat_str = "Hadir (✓)" if form["pengajian_status"] == 1 else "Tidak (✓)"
        j_str = form.get("tata_krama_jijyah") or "-"
        extra_minggu_text = (
            f"🕌 *Pengajian:* {p_stat_str}\n"
            f"🧹 *Piket:* Tidak (✓) [Statis]\n"
            f"💰 *Jijyah (Tata Krama):* `{j_str}`\n"
        )

    summary_text = (
        "📋 *RINGKASAN LAPORAN AMANAH*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Nama:* `{form['nama']}`\n"
        f"📅 *Hari/Tanggal:* *{form['hari']}*, `{form['tanggal']}`\n"
        f"🗓 *Ahad Ke:* `{form['ahad_ke']}` (Pekan: {form['bulan_str']})\n"
        f"🏢 *Posko:* `TANGKIL` (Statis)\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌙 *Solat Malam:* {sm_summary}\n"
        f"☀️ *Solat Dhuha:* {dh_summary}\n"
        f"🍃 *Puasa:* {p_summary}\n"
        f"🕌 *Solat Rowatib:* `{form['rowatib']}`{rw_alasan_str}\n"
        f"{extra_minggu_text}"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Apakah data di atas sudah sesuai dan ingin disimpan?"
    )
    keyboard = [
        [InlineKeyboardButton("💾 Simpan Data", callback_data="save_confirm")],
        [InlineKeyboardButton("🔄 Ulangi dari Awal", callback_data="input_restart")],
        [InlineKeyboardButton("❌ Batal", callback_data="input_cancel")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text=summary_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=summary_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_CONFIRMATION

async def confirmation_handled(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id

    if data == "input_cancel":
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "input_restart":
        return await input_start(update, context)

    if data == "save_confirm":
        form = context.user_data.get("input_form", {})
        database.save_laporan(form)

        if "pengajian_status" in form or "tata_krama_jijyah" in form:
            database.save_pekan_info(
                nama=form["nama"],
                monday_date=form["monday_date"],
                pengajian_status=form.get("pengajian_status", 0),
                tata_krama_nominal="",
                tata_krama_ahad="",
                tata_krama_jijyah=form.get("tata_krama_jijyah", ""),
                ahad_ke=form.get("ahad_ke")
            )

        tgl = datetime.datetime.strptime(form["tanggal"], "%Y-%m-%d").date()
        mon, sun, calc_ahad, b_str = database.calculate_week_info(tgl)

        success_text = (
            "✅ *Laporan Berhasil Disimpan!*\n\n"
            f"👤 Nama: `{form['nama']}`\n"
            f"📅 Hari/Tanggal: *{form['hari']}*, `{form['tanggal']}`\n"
            f"🗓 Ahad Ke: *{form['ahad_ke']}*\n\n"
            "Anda dapat menginput hari lainnya atau langsung mencetak laporan (Gambar / PDF)."
        )
        keyboard = [
            [InlineKeyboardButton("📝 Input Hari Lainnya", callback_data="menu_input")],
            [InlineKeyboardButton("📄 Cetak Laporan Pekan Ini", callback_data=f"quick_print_{mon.strftime('%Y-%m-%d')}")],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_main")]
        ]
        await query.edit_message_text(text=success_text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return ConversationHandler.END

# ==================== FLOW EDIT DATA INPUTAN ====================

async def edit_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    recent_reports = database.get_recent_laporan(cur_name, limit=7)

    text = (
        "✏️ *EDIT DATA INPUTAN LAPORAN*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Pelapor Aktif:* `{cur_name}`\n\n"
    )

    keyboard = []
    if recent_reports:
        text += "Pilih data laporan harian yang ingin Anda edit:"
        for r in recent_reports:
            tgl_dt = datetime.datetime.strptime(r["tanggal"], "%Y-%m-%d").date()
            tgl_display = tgl_dt.strftime("%d-%m-%Y")
            btn_text = f"📅 {r['hari']}, {tgl_display} (Ahad {r['ahad_ke']})"
            keyboard.append([InlineKeyboardButton(btn_text, callback_data=f"editsel_{r['tanggal']}")])
    else:
        text += "ℹ️ Belum ada riwayat input laporan yang tersimpan untuk pelapor ini."

    keyboard.append([InlineKeyboardButton("📆 Ketik Tanggal Lain", callback_data="edit_date_custom")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu Utama", callback_data="menu_main")])

    if query:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_EDIT_SELECT_DATE

async def edit_date_selected(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id

    if data == "menu_main":
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "edit_date_custom":
        text = (
            "📆 *Ketik Tanggal Laporan yang Ingin Diedit*\n\n"
            "Silakan kirimkan tanggal dengan format `DD-MM-YYYY` atau `YYYY-MM-DD`\n"
            "(Contoh: `26-10-2026` atau `2026-10-26`):"
        )
        keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data="edit_back_select")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_MANUAL_DATE

    if data.startswith("editsel_"):
        tgl_str = data.replace("editsel_", "")
        context.user_data["edit_target_date"] = tgl_str
        return await render_edit_dashboard(update, context, tgl_str)

    return STATE_EDIT_SELECT_DATE

async def edit_manual_date_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_input = update.message.text.strip()
    target_date = None

    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            target_date = datetime.datetime.strptime(text_input, fmt).date()
            break
        except ValueError:
            pass

    if not target_date:
        await update.message.reply_text(
            "⚠️ Format tanggal tidak dikenali. Gunakan contoh `26-10-2026` atau `2026-10-26`.\nSilakan coba ketik lagi:"
        )
        return STATE_EDIT_MANUAL_DATE

    tgl_str = target_date.strftime("%Y-%m-%d")
    cur_name = database.get_user_setting(update.effective_chat.id)
    rec = database.get_laporan_by_date(cur_name, tgl_str)

    if not rec:
        text = (
            f"⚠️ *Tidak ditemukan data laporan* pada tanggal `{tgl_str}` untuk pelapor *{cur_name}*.\n\n"
            "Pastikan tanggal tersebut sudah pernah diinput sebelumnya."
        )
        keyboard = [
            [InlineKeyboardButton("📆 Ketik Tanggal Lain", callback_data="edit_date_custom")],
            [InlineKeyboardButton("🔙 Pilih dari Daftar", callback_data="edit_back_select")],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_main")]
        ]
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_MANUAL_DATE

    context.user_data["edit_target_date"] = tgl_str
    return await render_edit_dashboard(update, context, tgl_str)

async def render_edit_dashboard(update: Update, context: ContextTypes.DEFAULT_TYPE, tgl_str: str, prefix_msg: str = ""):
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)
    rec = database.get_laporan_by_date(cur_name, tgl_str)

    if not rec:
        return await edit_start(update, context)

    tgl_dt = datetime.datetime.strptime(tgl_str, "%Y-%m-%d").date()
    mon, sun, calc_ahad, b_str = database.calculate_week_info(tgl_dt)
    mon_str = mon.strftime("%Y-%m-%d")
    pekan_meta = database.get_pekan_info(cur_name, mon_str)

    sm_summary = f"Ya ({rec['solat_malam_jam'] or '-'}, Dz: {rec['jumlah_dzikir'] or '-'})" if rec["solat_malam_status"] == 1 else f"Tidak (Alasan: {rec['solat_malam_alasan'] or '-'})"
    dh_summary = "Ya (✓)" if rec["dhuha_status"] == 1 else f"Tidak (Alasan: {rec['dhuha_alasan'] or '-'})"
    p_summary = "Ya (✓)" if rec["puasa_status"] == 1 else (f"Tidak (Alasan: {rec['puasa_alasan']})" if rec["puasa_alasan"] else "Tidak")
    rw_alasan_str = f" (Alasan: {rec['rowatib_alasan']})" if rec.get("rowatib") != "5 waktu" and rec.get("rowatib_alasan") else ""
    rw_summary = (rec["rowatib"] or "5 waktu") + rw_alasan_str

    extra_minggu = ""
    if rec["hari"] == "MINGGU":
        p_stat = "Hadir (✓)" if pekan_meta.get("pengajian_status") == 1 else "Tidak (✓)"
        j_val = pekan_meta.get("tata_krama_jijyah") or "-"
        extra_minggu = (
            f"🕌 *Pengajian:* {p_stat}\n"
            f"🧹 *Piket:* Tidak (✓) [Statis]\n"
            f"💰 *Jijyah:* `{j_val}`\n"
        )

    tgl_display = tgl_dt.strftime("%d-%m-%Y")
    text = (
        f"{prefix_msg}"
        "✏️ *DETAIL DATA LAPORAN*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Pelapor:* `{cur_name}`\n"
        f"📅 *Hari/Tanggal:* *{rec['hari']}*, `{tgl_display}`\n"
        f"🗓 *Ahad Ke:* `{rec['ahad_ke']}` (Pekan: {b_str})\n"
        f"🏢 *Posko:* `TANGKIL` (Statis)\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🌙 *Solat Malam:* {sm_summary}\n"
        f"☀️ *Solat Dhuha:* {dh_summary}\n"
        f"🍃 *Puasa:* {p_summary}\n"
        f"🕌 *Solat Rowatib:* `{rw_summary}`\n"
        f"{extra_minggu}"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "Pilih bagian yang ingin Anda edit:"
    )

    keyboard = [
        [
            InlineKeyboardButton("🌙 Edit Solat Malam", callback_data="edit_act_sm"),
            InlineKeyboardButton("☀️ Edit Solat Dhuha", callback_data="edit_act_dhuha")
        ],
        [
            InlineKeyboardButton("🍃 Edit Puasa", callback_data="edit_act_puasa"),
            InlineKeyboardButton("🕌 Edit Solat Rowatib", callback_data="edit_act_rowatib")
        ],
        [
            InlineKeyboardButton("🗓 Ubah Ahad Ke", callback_data="edit_act_ahad")
        ]
    ]

    if rec["hari"] == "MINGGU":
        keyboard.append([
            InlineKeyboardButton("🕌 Ubah Pengajian", callback_data="edit_act_pengajian"),
            InlineKeyboardButton("💰 Ubah Jijyah", callback_data="edit_act_jijyah")
        ])

    keyboard.append([
        InlineKeyboardButton("🗑️ Hapus Inputan Ini", callback_data="edit_act_del")
    ])
    keyboard.append([
        InlineKeyboardButton("🔙 Pilih Tanggal Lain", callback_data="edit_back_select"),
        InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_main")
    ])

    markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=markup, parse_mode="Markdown")
    return STATE_EDIT_MENU

async def edit_menu_dispatcher(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)
    tgl_str = context.user_data.get("edit_target_date")

    if data == "menu_main":
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data in ("edit_dashboard_back", "edit_back_dashboard"):
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "edit_back_select":
        return await edit_start(update, context)

    rec = database.get_laporan_by_date(cur_name, tgl_str)
    if not rec:
        return await edit_start(update, context)

    if data == "edit_act_sm":
        text = (
            f"🌙 *EDIT SOLAT MALAM*\n\n"
            f"Tanggal: *{rec['hari']}*, `{rec['tanggal']}`\n\n"
            "Apakah Anda melaksanakan Solat Malam?"
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ Ya (Melaksanakan)", callback_data="editsm_ya"),
                InlineKeyboardButton("❌ Tidak", callback_data="editsm_tidak")
            ],
            [InlineKeyboardButton("🔙 Batal Ubah", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_SM_STATUS

    elif data == "edit_act_dhuha":
        text = (
            f"☀️ *EDIT SOLAT DHUHA*\n\n"
            f"Tanggal: *{rec['hari']}*, `{rec['tanggal']}`\n\n"
            "Apakah Anda melaksanakan Solat Dhuha?"
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ Ya (Melaksanakan)", callback_data="editdh_ya"),
                InlineKeyboardButton("❌ Tidak", callback_data="editdh_tidak")
            ],
            [InlineKeyboardButton("🔙 Batal Ubah", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_DHUHA_STATUS

    elif data == "edit_act_puasa":
        text = (
            f"🍃 *EDIT PUASA SENIN & KAMIS*\n\n"
            f"Tanggal: *{rec['hari']}*, `{rec['tanggal']}`\n\n"
            "Apakah Anda berpuasa sunnah?"
        )
        keyboard = [
            [
                InlineKeyboardButton("✅ Ya (Berpuasa)", callback_data="editp_ya"),
                InlineKeyboardButton("❌ Tidak", callback_data="editp_tidak")
            ],
            [InlineKeyboardButton("🔙 Batal Ubah", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_PUASA_STATUS

    elif data == "edit_act_rowatib":
        text = (
            f"🕌 *EDIT SOLAT ROWATIB*\n\n"
            f"Tanggal: *{rec['hari']}*, `{rec['tanggal']}`\n"
            f"Saat ini: `{rec['rowatib']}`\n\n"
            "Pilih berapa waktu Solat Rowatib yang Anda laksanakan:"
        )
        keyboard = [
            [
                InlineKeyboardButton("5 Waktu", callback_data="editrowatib_5 waktu"),
                InlineKeyboardButton("4 Waktu", callback_data="editrowatib_4 waktu")
            ],
            [
                InlineKeyboardButton("3 Waktu", callback_data="editrowatib_3 waktu"),
                InlineKeyboardButton("2 Waktu", callback_data="editrowatib_2 waktu")
            ],
            [
                InlineKeyboardButton("1 Waktu", callback_data="editrowatib_1 waktu"),
                InlineKeyboardButton("0 (Tidak)", callback_data="editrowatib_0 waktu")
            ],
            [InlineKeyboardButton("🔙 Batal Ubah", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_ROWATIB

    elif data == "edit_act_ahad":
        text = (
            f"🗓 *EDIT AHAD KE*\n\n"
            f"Tanggal: *{rec['hari']}*, `{rec['tanggal']}`\n"
            f"Ahad ke saat ini: *{rec['ahad_ke']}*\n\n"
            "Pilih Ahad ke berapa untuk laporan pekan ini:"
        )
        keyboard = [
            [
                InlineKeyboardButton("Ahad 1", callback_data="editahad_1"),
                InlineKeyboardButton("Ahad 2", callback_data="editahad_2"),
                InlineKeyboardButton("Ahad 3", callback_data="editahad_3"),
                InlineKeyboardButton("Ahad 4", callback_data="editahad_4"),
                InlineKeyboardButton("Ahad 5", callback_data="editahad_5"),
            ],
            [InlineKeyboardButton("🔙 Batal Ubah", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_AHAD_KE

    elif data == "edit_act_pengajian":
        tgl_dt = datetime.datetime.strptime(tgl_str, "%Y-%m-%d").date()
        mon, _, _, _ = database.calculate_week_info(tgl_dt)
        mon_str = mon.strftime("%Y-%m-%d")
        current_meta = database.get_pekan_info(cur_name, mon_str)
        new_stat = 0 if current_meta.get("pengajian_status") == 1 else 1
        database.save_pekan_info(
            nama=cur_name,
            monday_date=mon_str,
            pengajian_status=new_stat,
            tata_krama_nominal="",
            tata_krama_ahad=current_meta.get("tata_krama_ahad", ""),
            tata_krama_jijyah=current_meta.get("tata_krama_jijyah", ""),
            ahad_ke=current_meta.get("ahad_ke")
        )
        status_label = "Hadir (✓)" if new_stat == 1 else "Tidak (✓)"
        return await render_edit_dashboard(update, context, tgl_str, prefix_msg=f"✅ *Pengajian pekan ini diubah menjadi: {status_label}!*\n\n")

    elif data == "edit_act_jijyah":
        tgl_dt = datetime.datetime.strptime(tgl_str, "%Y-%m-%d").date()
        mon, _, _, _ = database.calculate_week_info(tgl_dt)
        mon_str = mon.strftime("%Y-%m-%d")
        current_meta = database.get_pekan_info(cur_name, mon_str)
        cur_jijyah = current_meta.get("tata_krama_jijyah") or "Belum diisi"
        text = (
            f"💰 *EDIT JIJYAH (TATA KRAMA) PEKAN INI*\n\n"
            f"Saat ini: `{cur_jijyah}`\n\n"
            "Pilih nominal cepat atau ketik manual:"
        )
        keyboard = [
            [
                InlineKeyboardButton("💰 2000", callback_data="editjset_2000"),
                InlineKeyboardButton("💰 67000", callback_data="editjset_67000")
            ],
            [
                InlineKeyboardButton("✏️ Ketik Manual", callback_data="editjset_manual"),
                InlineKeyboardButton("❌ Kosongkan", callback_data="editjset_none")
            ],
            [InlineKeyboardButton("🔙 Batal Ubah", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_JIJYAH

    elif data == "edit_act_del":
        text = (
            "⚠️ *KONFIRMASI PENGHAPUSAN LAPORAN*\n\n"
            f"Apakah Anda yakin ingin menghapus data laporan:\n"
            f"👤 Pelapor: *{cur_name}*\n"
            f"📅 Tanggal: *{rec['hari']}*, `{rec['tanggal']}`?\n\n"
            "❗ _Data yang telah dihapus tidak dapat dipulihkan kembali._"
        )
        keyboard = [
            [InlineKeyboardButton("🗑️ Ya, Hapus Data Ini", callback_data="editdel_yes")],
            [InlineKeyboardButton("❌ Batal / Jangan Hapus", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_DELETE_CONFIRM

    return STATE_EDIT_MENU

# --- Handlers Edit Solat Malam ---

async def edit_sm_status_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "editsm_ya":
        text = (
            "🕒 *Pilih Jam Pelaksanaan Solat Malam*\n\n"
            "Pilih opsi cepat atau ketik manual (contoh: `03:30 s/d 04:10`):"
        )
        keyboard = [
            [
                InlineKeyboardButton("03:30 s/d 04:10", callback_data="editsmtime_03:30 s/d 04:10"),
                InlineKeyboardButton("03:40 s/d 04:20", callback_data="editsmtime_03:40 s/d 04:20")
            ],
            [
                InlineKeyboardButton("03:35 s/d 04:15", callback_data="editsmtime_03:35 s/d 04:15"),
                InlineKeyboardButton("03:15 s/d 03:50", callback_data="editsmtime_03:15 s/d 03:50")
            ],
            [InlineKeyboardButton("✏️ Ketik Jam Manual", callback_data="editsmtime_manual")],
            [InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_SM_TIME
    else:
        text = (
            "❌ *Pilih Alasan Tidak Solat Malam*\n\n"
            "Pilih alasan cepat atau ketik manual:"
        )
        keyboard = [
            [
                InlineKeyboardButton("Terlewat", callback_data="editsmreason_Terlewat"),
                InlineKeyboardButton("Kesiangan", callback_data="editsmreason_Kesiangan")
            ],
            [
                InlineKeyboardButton("Halangan", callback_data="editsmreason_Halangan"),
                InlineKeyboardButton("Sakit", callback_data="editsmreason_Sakit")
            ],
            [
                InlineKeyboardButton("Uzur Syar'i", callback_data="editsmreason_Uzur Syar'i"),
                InlineKeyboardButton("Kelelahan / Safar", callback_data="editsmreason_Kelelahan / Safar")
            ],
            [InlineKeyboardButton("✏️ Ketik Alasan Manual", callback_data="editsmreason_manual")],
            [InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_SM_REASON

async def edit_sm_time_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "editsmtime_manual":
        text = "🕒 Silakan ketik jam pelaksanaan Solat Malam (contoh: `03:30 s/d 04:10`):"
        keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_SM_TIME

    time_val = data.replace("editsmtime_", "")
    context.user_data["edit_sm_jam"] = time_val
    return await ask_edit_dzikir(update, context)

async def edit_sm_time_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    time_val = update.message.text.strip()
    context.user_data["edit_sm_jam"] = time_val
    return await ask_edit_dzikir(update, context)

async def ask_edit_dzikir(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📿 *Masukkan Jumlah Dzikir*\n\n"
        "Pilih jumlah dzikir cepat atau ketik manual:"
    )
    keyboard = [
        [
            InlineKeyboardButton("10.000", callback_data="editdzikir_10000"),
            InlineKeyboardButton("20.000", callback_data="editdzikir_20000")
        ],
        [
            InlineKeyboardButton("15.000", callback_data="editdzikir_15000"),
            InlineKeyboardButton("5.000", callback_data="editdzikir_5000")
        ],
        [InlineKeyboardButton("✏️ Ketik Jumlah Manual", callback_data="editdzikir_manual")],
        [InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]
    ]
    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_EDIT_DZIKIR

async def edit_dzikir_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "editdzikir_manual":
        text = "📿 Silakan ketik jumlah dzikir (contoh: `10000` atau `20.000`):"
        keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_DZIKIR

    dzikir_val = data.replace("editdzikir_", "")
    if dzikir_val == "10000":
        dzikir_val = "10000"
    elif dzikir_val == "20000":
        dzikir_val = "20.000"

    jam_val = context.user_data.get("edit_sm_jam", "03:30 s/d 04:10")
    database.update_laporan(cur_name, tgl_str, {
        "solat_malam_status": 1,
        "solat_malam_jam": jam_val,
        "solat_malam_alasan": "",
        "jumlah_dzikir": dzikir_val
    })
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Solat Malam berhasil diperbarui!*\n\n")

async def edit_dzikir_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    dzikir_val = update.message.text.strip()
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)
    jam_val = context.user_data.get("edit_sm_jam", "03:30 s/d 04:10")

    database.update_laporan(cur_name, tgl_str, {
        "solat_malam_status": 1,
        "solat_malam_jam": jam_val,
        "solat_malam_alasan": "",
        "jumlah_dzikir": dzikir_val
    })
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Solat Malam berhasil diperbarui!*\n\n")

async def edit_sm_reason_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "editsmreason_manual":
        text = "✏️ Silakan ketik alasan tidak melaksanakan Solat Malam:"
        keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_SM_REASON

    reason_val = data.replace("editsmreason_", "")
    database.update_laporan(cur_name, tgl_str, {
        "solat_malam_status": 0,
        "solat_malam_jam": "-",
        "solat_malam_alasan": reason_val,
        "jumlah_dzikir": "-"
    })
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Solat Malam berhasil diperbarui!*\n\n")

async def edit_sm_reason_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason_val = update.message.text.strip()
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    database.update_laporan(cur_name, tgl_str, {
        "solat_malam_status": 0,
        "solat_malam_jam": "-",
        "solat_malam_alasan": reason_val,
        "jumlah_dzikir": "-"
    })
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Solat Malam berhasil diperbarui!*\n\n")

# --- Handlers Edit Solat Dhuha ---

async def edit_dhuha_status_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "editdh_ya":
        database.update_laporan(cur_name, tgl_str, {
            "dhuha_status": 1,
            "dhuha_alasan": ""
        })
        return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Solat Dhuha berhasil diperbarui!*\n\n")
    else:
        text = (
            "❌ *Pilih Alasan Tidak Solat Dhuha*\n\n"
            "Pilih alasan cepat atau ketik manual:"
        )
        keyboard = [
            [
                InlineKeyboardButton("Terlewat", callback_data="editdhreason_Terlewat"),
                InlineKeyboardButton("Halangan", callback_data="editdhreason_Halangan")
            ],
            [
                InlineKeyboardButton("Uzur Syar'i", callback_data="editdhreason_Uzur Syar'i"),
                InlineKeyboardButton("Sakit", callback_data="editdhreason_Sakit")
            ],
            [
                InlineKeyboardButton("Di Perjalanan / Safar", callback_data="editdhreason_Safar"),
                InlineKeyboardButton("Tugas / Sibuk", callback_data="editdhreason_Ada Keperluan Mendesak")
            ],
            [InlineKeyboardButton("✏️ Ketik Alasan Manual", callback_data="editdhreason_manual")],
            [InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_DHUHA_REASON

async def edit_dhuha_reason_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "editdhreason_manual":
        text = "✏️ Silakan ketik alasan tidak melaksanakan Solat Dhuha:"
        keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_DHUHA_REASON

    reason_val = data.replace("editdhreason_", "")
    database.update_laporan(cur_name, tgl_str, {
        "dhuha_status": 0,
        "dhuha_alasan": reason_val
    })
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Solat Dhuha berhasil diperbarui!*\n\n")

async def edit_dhuha_reason_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason_val = update.message.text.strip()
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    database.update_laporan(cur_name, tgl_str, {
        "dhuha_status": 0,
        "dhuha_alasan": reason_val
    })
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Solat Dhuha berhasil diperbarui!*\n\n")

# --- Handlers Edit Puasa ---

async def edit_puasa_status_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "editp_ya":
        database.update_laporan(cur_name, tgl_str, {
            "puasa_status": 1,
            "puasa_alasan": ""
        })
        return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Puasa berhasil diperbarui!*\n\n")
    else:
        rec = database.get_laporan_by_date(cur_name, tgl_str)
        hari = rec["hari"] if rec else ""
        extra_btn = [InlineKeyboardButton("Bukan Jadwal Puasa", callback_data="editpreason_Bukan Jadwal Puasa")] if hari not in ["SENIN", "KAMIS"] else []

        text = (
            "❌ *Pilih Alasan Tidak Berpuasa*\n\n"
            "Pilih alasan cepat atau ketik manual:"
        )
        keyboard = [
            [
                InlineKeyboardButton("Halangan", callback_data="editpreason_Halangan"),
                InlineKeyboardButton("Terlewat", callback_data="editpreason_Terlewat")
            ],
            [
                InlineKeyboardButton("Tidak Puasa", callback_data="editpreason_Tidak Puasa"),
                InlineKeyboardButton("Sakit", callback_data="editpreason_Sakit")
            ],
            [
                InlineKeyboardButton("Uzur Syar'i", callback_data="editpreason_Uzur Syar'i"),
                InlineKeyboardButton("Safar", callback_data="editpreason_Safar")
            ],
            *( [extra_btn] if extra_btn else [] ),
            [InlineKeyboardButton("✏️ Ketik Alasan Manual", callback_data="editpreason_manual")],
            [InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_PUASA_REASON

async def edit_puasa_reason_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "editpreason_manual":
        text = "✏️ Silakan ketik alasan tidak berpuasa:"
        keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_PUASA_REASON

    reason_val = data.replace("editpreason_", "")
    if reason_val == "Bukan Jadwal Puasa":
        reason_val = ""

    database.update_laporan(cur_name, tgl_str, {
        "puasa_status": 0,
        "puasa_alasan": reason_val
    })
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Puasa berhasil diperbarui!*\n\n")

async def edit_puasa_reason_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason_val = update.message.text.strip()
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    database.update_laporan(cur_name, tgl_str, {
        "puasa_status": 0,
        "puasa_alasan": reason_val
    })
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Puasa berhasil diperbarui!*\n\n")

# --- Handlers Edit Solat Rowatib ---

async def edit_rowatib_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    rowatib_val = data.replace("editrowatib_", "")
    if rowatib_val == "5 waktu":
        database.update_laporan(cur_name, tgl_str, {
            "rowatib": "5 waktu",
            "rowatib_alasan": ""
        })
        return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Solat Rowatib berhasil diperbarui menjadi 5 waktu!*\n\n")
    else:
        context.user_data["edit_temp_rowatib"] = rowatib_val
        text = (
            f"❌ *Alasan Tidak Full Solat Rowatib*\n\n"
            f"Anda memilih: *{rowatib_val}* (tidak full 5 waktu).\n"
            "Silakan pilih alasan atau ketik manual:"
        )
        keyboard = [
            [
                InlineKeyboardButton("Halangan", callback_data="editrwreason_Halangan"),
                InlineKeyboardButton("Terlewat", callback_data="editrwreason_Terlewat")
            ],
            [
                InlineKeyboardButton("Sakit", callback_data="editrwreason_Sakit"),
                InlineKeyboardButton("Uzur Syar'i", callback_data="editrwreason_Uzur Syar'i")
            ],
            [
                InlineKeyboardButton("Safar / Perjalanan", callback_data="editrwreason_Safar"),
                InlineKeyboardButton("Ada Keperluan", callback_data="editrwreason_Ada Keperluan Mendesak")
            ],
            [InlineKeyboardButton("✏️ Ketik Alasan Manual", callback_data="editrwreason_manual")],
            [InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_ROWATIB_REASON

async def edit_rowatib_reason_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "editrwreason_manual":
        text = "✏️ Silakan ketik alasan tidak full Solat Rowatib:"
        keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_ROWATIB_REASON

    reason_val = data.replace("editrwreason_", "")
    rowatib_val = context.user_data.get("edit_temp_rowatib", "5 waktu")
    database.update_laporan(cur_name, tgl_str, {
        "rowatib": rowatib_val,
        "rowatib_alasan": reason_val
    })
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg=f"✅ *Solat Rowatib berhasil diperbarui menjadi {rowatib_val} ({reason_val})!*\n\n")

async def edit_rowatib_reason_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    reason_val = update.message.text.strip()
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)
    rowatib_val = context.user_data.get("edit_temp_rowatib", "5 waktu")

    database.update_laporan(cur_name, tgl_str, {
        "rowatib": rowatib_val,
        "rowatib_alasan": reason_val
    })
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg=f"✅ *Solat Rowatib berhasil diperbarui menjadi {rowatib_val} ({reason_val})!*\n\n")

# --- Handlers Edit Ahad Ke ---

async def edit_ahad_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    ahad_val = int(data.replace("editahad_", ""))
    database.update_laporan(cur_name, tgl_str, {"ahad_ke": ahad_val})

    tgl_dt = datetime.datetime.strptime(tgl_str, "%Y-%m-%d").date()
    mon, _, _, _ = database.calculate_week_info(tgl_dt)
    mon_str = mon.strftime("%Y-%m-%d")
    database.save_pekan_ahad_ke(cur_name, mon_str, ahad_val)

    return await render_edit_dashboard(update, context, tgl_str, prefix_msg=f"✅ *Ahad Ke berhasil diperbarui menjadi Ahad ke-{ahad_val}!*\n\n")

# --- Handlers Edit Jijyah ---

async def edit_jijyah_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "editjset_manual":
        text = "✏️ Silakan ketik nominal untuk Jijyah (contoh: `2000`, `67000`, `50000`):"
        keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data="edit_dashboard_back")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_JIJYAH_MANUAL

    tgl_dt = datetime.datetime.strptime(tgl_str, "%Y-%m-%d").date()
    mon, _, _, _ = database.calculate_week_info(tgl_dt)
    mon_str = mon.strftime("%Y-%m-%d")

    choice = data.replace("editjset_", "")
    val = "" if choice == "none" else choice
    database.save_pekan_jijyah(cur_name, mon_str, val)
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Nominal Jijyah berhasil diperbarui!*\n\n")

async def edit_jijyah_manual_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    tgl_dt = datetime.datetime.strptime(tgl_str, "%Y-%m-%d").date()
    mon, _, _, _ = database.calculate_week_info(tgl_dt)
    mon_str = mon.strftime("%Y-%m-%d")

    database.save_pekan_jijyah(cur_name, mon_str, val)
    return await render_edit_dashboard(update, context, tgl_str, prefix_msg="✅ *Nominal Jijyah berhasil diperbarui!*\n\n")

# --- Handlers Edit Delete Record ---

async def edit_delete_confirmed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    tgl_str = context.user_data.get("edit_target_date")
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    if data == "edit_dashboard_back":
        return await render_edit_dashboard(update, context, tgl_str)

    if data == "editdel_yes":
        success = database.delete_laporan(cur_name, tgl_str)
        if success:
            msg = f"🗑️ *Data laporan tanggal `{tgl_str}` untuk `{cur_name}` telah berhasil dihapus.*"
        else:
            msg = "⚠️ Gagal menghapus data atau data sudah tidak ada."

        keyboard = [
            [InlineKeyboardButton("✏️ Edit Laporan Lain", callback_data="edit_back_select")],
            [InlineKeyboardButton("🏠 Menu Utama", callback_data="menu_main")]
        ]
        await query.edit_message_text(text=msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_EDIT_MENU

    return STATE_EDIT_MENU

# ==================== FLOW CETAK LAPORAN (GAMBAR / PDF) ====================

async def print_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if query:
        await query.answer()
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)

    today = datetime.date.today()
    mon_this_week, sun_this_week, calc_this, b_this = database.calculate_week_info(today)

    last_week_dt = today - datetime.timedelta(days=7)
    mon_last_week, sun_last_week, calc_last, b_last = database.calculate_week_info(last_week_dt)

    available_weeks = database.get_available_weeks(cur_name)

    pekan_this = database.get_pekan_info(cur_name, mon_this_week.strftime('%Y-%m-%d'))
    ahad_this = pekan_this.get("ahad_ke") or calc_this

    pekan_last = database.get_pekan_info(cur_name, mon_last_week.strftime('%Y-%m-%d'))
    ahad_last = pekan_last.get("ahad_ke") or calc_last

    text = (
        "📄 *CETAK LAPORAN PELAKSANAAN AMANAH*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Nama Pelapor:* `{cur_name}`\n"
        f"🏢 *Posko:* `TANGKIL` (Statis)\n\n"
        "Silakan pilih pekan / tanggal laporan yang ingin dicetak:"
    )

    keyboard = [
        [InlineKeyboardButton(f"📅 Pekan Ini ({b_this} - Ahad {ahad_this})", callback_data=f"sel_week_{mon_this_week.strftime('%Y-%m-%d')}")],
        [InlineKeyboardButton(f"📅 Pekan Lalu ({b_last} - Ahad {ahad_last})", callback_data=f"sel_week_{mon_last_week.strftime('%Y-%m-%d')}")],
    ]

    for w in available_weeks[:4]:
        mon_str = w["monday_str"]
        if mon_str not in [mon_this_week.strftime('%Y-%m-%d'), mon_last_week.strftime('%Y-%m-%d')]:
            keyboard.append([InlineKeyboardButton(f"📆 {w['bulan_str']} (Ahad {w['ahad_ke']})", callback_data=f"sel_week_{mon_str}")])

    keyboard.append([InlineKeyboardButton("✏️ Pilih Berdasarkan Tanggal Bebas", callback_data="print_date_manual")])
    keyboard.append([InlineKeyboardButton("🔙 Kembali ke Menu", callback_data="menu_main")])

    if query:
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_PRINT_DATE

async def print_date_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id

    if data == "menu_main":
        text, reply_markup = build_main_menu(chat_id)
        await query.edit_message_text(text=text, reply_markup=reply_markup, parse_mode="Markdown")
        return ConversationHandler.END

    if data == "print_date_manual":
        text = (
            "✏️ *Ketik Tanggal untuk Cetak Laporan*\n\n"
            "Kirimkan tanggal sembarang dalam pekan yang ingin dicetak.\n"
            "Format: `DD-MM-YYYY` atau `YYYY-MM-DD` (contoh: `07-09-2026`):"
        )
        keyboard = [[InlineKeyboardButton("🔙 Batal", callback_data="menu_main")]]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_PRINT_MANUAL_DATE

    if data.startswith("sel_week_") or data.startswith("quick_print_"):
        mon_str = data.replace("sel_week_", "").replace("quick_print_", "")
        context.user_data["print_mon_str"] = mon_str
        return await show_print_settings(update, context)

    return ConversationHandler.END

async def print_manual_date_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text_input = update.message.text.strip()
    target_date = None

    for fmt in ("%d-%m-%Y", "%Y-%m-%d", "%d/%m/%Y", "%Y/%m/%d"):
        try:
            target_date = datetime.datetime.strptime(text_input, fmt).date()
            break
        except ValueError:
            pass

    if not target_date:
        await update.message.reply_text(
            "⚠️ Format tanggal tidak dikenali. Ketik kembali contoh: `07-09-2026`:"
        )
        return STATE_PRINT_MANUAL_DATE

    monday_date = target_date - datetime.timedelta(days=target_date.weekday())
    context.user_data["print_mon_str"] = monday_date.strftime("%Y-%m-%d")
    return await show_print_settings(update, context)

async def show_print_settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)
    mon_str = context.user_data.get("print_mon_str")
    monday_date = datetime.datetime.strptime(mon_str, "%Y-%m-%d").date()

    week_data = database.get_laporan_week(cur_name, monday_date)

    pengajian_display = "✅ Hadir (✓)" if week_data["pengajian_status"] == 1 else "❌ Tidak (✓)"
    jijyah_val = week_data["tata_krama_jijyah"] or "-"

    text = (
        f"⚙️ *PENGATURAN PEKAN SEBELUM CETAK*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👤 *Nama:* `{cur_name}`\n"
        f"📅 *Pekan:* `{week_data['bulan']}`\n"
        f"🗓 *Ahad Ke:* `{week_data['ahad_ke']}`\n"
        f"📊 *Data Terisi:* {week_data['filled_days_count']} dari 7 hari\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🕌 *Pengajian:* {pengajian_display}\n"
        f"🧹 *Piket:* Tidak (✓) [Statis]\n"
        f"💰 *Jijyah:* `{jijyah_val}`\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        "Silakan sesuaikan Ahad Ke, Pengajian, atau Jijyah jika diperlukan:"
    )

    toggle_pengajian_text = "Ubah Pengajian (ke Tidak)" if week_data["pengajian_status"] == 1 else "Ubah Pengajian (ke Hadir)"
    cur_ahad = week_data["ahad_ke"]

    keyboard = [
        [
            InlineKeyboardButton(f"{'✅ ' if cur_ahad==1 else ''}Ahad 1", callback_data="set_ahadke_1"),
            InlineKeyboardButton(f"{'✅ ' if cur_ahad==2 else ''}Ahad 2", callback_data="set_ahadke_2"),
            InlineKeyboardButton(f"{'✅ ' if cur_ahad==3 else ''}Ahad 3", callback_data="set_ahadke_3"),
            InlineKeyboardButton(f"{'✅ ' if cur_ahad==4 else ''}Ahad 4", callback_data="set_ahadke_4"),
            InlineKeyboardButton(f"{'✅ ' if cur_ahad==5 else ''}Ahad 5", callback_data="set_ahadke_5"),
        ],
        [InlineKeyboardButton(f"🕌 {toggle_pengajian_text}", callback_data="toggle_pengajian")],
        [
            InlineKeyboardButton("💰 Jijyah: 2000", callback_data="set_jijyah_2000"),
            InlineKeyboardButton("💰 Jijyah: 67000", callback_data="set_jijyah_67000")
        ],
        [
            InlineKeyboardButton("✏️ Jijyah: Manual (Ketik)", callback_data="set_jijyah_manual"),
            InlineKeyboardButton("❌ Kosongkan Jijyah", callback_data="set_jijyah_none")
        ],
        [InlineKeyboardButton("🚀 LANJUT PILIH FORMAT CETAK", callback_data="proceed_format")],
        [InlineKeyboardButton("🔙 Pilih Pekan Lain", callback_data="menu_print")]
    ]

    if update.callback_query:
        await update.callback_query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    else:
        await update.message.reply_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    return STATE_PRINT_SETTINGS

async def print_settings_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)
    mon_str = context.user_data.get("print_mon_str")

    current_meta = database.get_pekan_info(cur_name, mon_str)

    if data == "menu_print":
        return await print_start(update, context)

    if data.startswith("set_ahadke_"):
        ahad_val = int(data.replace("set_ahadke_", ""))
        database.save_pekan_ahad_ke(cur_name, mon_str, ahad_val)
        return await show_print_settings(update, context)

    elif data == "toggle_pengajian":
        new_status = 0 if current_meta["pengajian_status"] == 1 else 1
        database.save_pekan_info(
            cur_name, mon_str, new_status,
            "",
            current_meta.get("tata_krama_ahad", ""),
            current_meta.get("tata_krama_jijyah", ""),
            ahad_ke=current_meta.get("ahad_ke")
        )
        return await show_print_settings(update, context)

    elif data == "set_jijyah_2000":
        database.save_pekan_jijyah(cur_name, mon_str, "2000")
        return await show_print_settings(update, context)

    elif data == "set_jijyah_67000":
        database.save_pekan_jijyah(cur_name, mon_str, "67000")
        return await show_print_settings(update, context)

    elif data == "set_jijyah_none":
        database.save_pekan_jijyah(cur_name, mon_str, "")
        return await show_print_settings(update, context)

    elif data == "set_jijyah_manual":
        text = (
            "✏️ *Ketikkan Nominal Jijyah Manual*\n\n"
            "Silakan ketik nominal yang diinginkan (contoh: `2000`, `67000`, `50000`):"
        )
        await query.edit_message_text(text=text, parse_mode="Markdown")
        return STATE_PRINT_MANUAL_JIJYAH

    elif data == "proceed_format":
        text = (
            "🖨 *PILIH FORMAT CETAK LAPORAN*\n\n"
            "Hasil laporan siap dicetak. Pilih format yang Anda inginkan:\n\n"
            "• *🖼 Gambar (Foto):* Tampil langsung di chat, mudah disimpan dan diteruskan ke WA/Telegram.\n"
            "• *📄 Dokumen PDF:* Format resmi dokumen siap cetak kertas (Landscape A4).\n"
            "• *📦 Keduanya:* Kirimkan Gambar pratinjau sekaligus dokumen PDF."
        )
        keyboard = [
            [InlineKeyboardButton("🖼 Kirim Sebagai Gambar (Foto)", callback_data="fmt_img")],
            [InlineKeyboardButton("📄 Kirim Sebagai Dokumen PDF", callback_data="fmt_pdf")],
            [InlineKeyboardButton("📦 Kirim Keduanya (Gambar + PDF)", callback_data="fmt_both")],
            [InlineKeyboardButton("🔙 Kembali ke Pengaturan", callback_data="back_settings")]
        ]
        await query.edit_message_text(text=text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
        return STATE_PRINT_FORMAT

async def print_manual_jijyah_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    val = update.message.text.strip()
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)
    mon_str = context.user_data.get("print_mon_str")

    database.save_pekan_jijyah(cur_name, mon_str, val)
    return await show_print_settings(update, context)

async def print_format_chosen(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    chat_id = update.effective_chat.id
    cur_name = database.get_user_setting(chat_id)
    mon_str = context.user_data.get("print_mon_str")
    monday_date = datetime.datetime.strptime(mon_str, "%Y-%m-%d").date()

    if data == "back_settings":
        return await show_print_settings(update, context)

    fmt_choice = data.replace("fmt_", "")
    return await execute_report_output(monday_date, cur_name, fmt_choice, update, context)

async def execute_report_output(monday_date: datetime.date, nama: str, fmt: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    await update.callback_query.edit_message_text("⏳ *Sedang menyusun dan merender laporan...*", parse_mode="Markdown")

    week_data = database.get_laporan_week(nama, monday_date)

    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    base_name = f"Laporan_Amanah_{nama}_{week_data['monday_date']}_{timestamp}"
    pdf_filename = f"{base_name}.pdf"
    img_filename = f"{base_name}.png"
    pdf_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), pdf_filename)
    img_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), img_filename)

    try:
        pdf_generator.generate_report_bundle(pdf_path, img_path, week_data)

        caption_text = (
            f"📄 *LAPORAN PELAKSANAAN AMANAH*\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n"
            f"👤 *Nama:* `{nama}`\n"
            f"🗓 *Ahad Ke:* `{week_data['ahad_ke']}`\n"
            f"📅 *Pekan:* `{week_data['bulan']}`\n"
            f"🏢 *Posko:* `TANGKIL` (Statis)\n"
            f"🕌 *Pengajian:* {'Hadir (✓)' if week_data['pengajian_status'] == 1 else 'Tidak (✓)'}\n"
            f"🧹 *Piket:* Tidak (✓) [Statis]\n"
            f"💰 *Jijyah:* `{week_data['tata_krama_jijyah'] or '-'}`\n"
            f"📊 *Status:* {week_data['filled_days_count']} dari 7 hari terisi"
        )

        if fmt in ["img", "both"]:
            with open(img_path, "rb") as photo_file:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo_file,
                    caption=caption_text if fmt == "img" else (caption_text + "\n*(Pratinjau Gambar)*"),
                    parse_mode="Markdown"
                )

        if fmt in ["pdf", "both"]:
            with open(pdf_path, "rb") as doc_file:
                await context.bot.send_document(
                    chat_id=chat_id,
                    document=doc_file,
                    filename=f"Laporan_Amanah_{nama}_Ahad_Ke_{week_data['ahad_ke']}.pdf",
                    caption=caption_text if fmt == "pdf" else "📄 *File Dokumen PDF Resmi*",
                    parse_mode="Markdown"
                )

        for path in [pdf_path, img_path]:
            try:
                if os.path.exists(path):
                    os.remove(path)
            except Exception:
                pass

        text, reply_markup = build_main_menu(chat_id)
        await context.bot.send_message(
            chat_id=chat_id,
            text="✅ *Laporan berhasil dikirim!*\nSilakan pilih menu selanjutnya:",
            reply_markup=reply_markup,
            parse_mode="Markdown"
        )

    except Exception as e:
        logger.exception("Gagal menghasilkan laporan: %s", e)
        err_text = f"❌ Terjadi kesalahan saat menghasilkan laporan: {str(e)}"
        await context.bot.send_message(chat_id=chat_id, text=err_text)

    return ConversationHandler.END

# ==================== MAIN APPLICATION ====================

def main():
    token = os.getenv("BOT_TOKEN")
    if not token or token == "YOUR_TELEGRAM_BOT_TOKEN_HERE":
        print("=" * 60)
        print("⚠️ PERINGATAN: BOT_TOKEN belum diset di file .env!")
        print("Silakan buka file .env dan isi dengan Token Bot Telegram dari @BotFather.")
        print("=" * 60)
        return

    database.init_db()

    app = ApplicationBuilder().token(token).build()

    # Conversation Handler untuk Input Laporan
    input_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(input_start, pattern="^menu_input$"),
            CommandHandler("input", input_start)
        ],
        states={
            STATE_INPUT_DATE: [
                CallbackQueryHandler(input_date_picked, pattern="^(date_pick_|input_cancel)")
            ],
            STATE_MANUAL_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, input_manual_date),
                CallbackQueryHandler(input_date_picked, pattern="^input_cancel$")
            ],
            STATE_AHAD_KE: [
                CallbackQueryHandler(input_ahad_ke_chosen, pattern="^(ahad_set_|input_cancel)")
            ],
            STATE_SOLAT_MALAM: [
                CallbackQueryHandler(sm_status_chosen, pattern="^(sm_ya|sm_tidak|input_cancel)")
            ],
            STATE_SM_TIME: [
                CallbackQueryHandler(sm_time_chosen, pattern="^(smtime_|input_cancel)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, sm_time_text)
            ],
            STATE_SM_REASON: [
                CallbackQueryHandler(sm_reason_chosen, pattern="^(smreason_|input_cancel)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, sm_reason_text)
            ],
            STATE_DZIKIR: [
                CallbackQueryHandler(dzikir_chosen, pattern="^(dzikir_|input_cancel)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, dzikir_text)
            ],
            STATE_DHUHA: [
                CallbackQueryHandler(dhuha_chosen, pattern="^(dhuha_ya|dhuha_tidak|input_cancel)")
            ],
            STATE_DHUHA_REASON: [
                CallbackQueryHandler(dhuha_reason_chosen, pattern="^(dhreason_|input_cancel)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, dhuha_reason_text)
            ],
            STATE_PUASA: [
                CallbackQueryHandler(puasa_chosen, pattern="^(puasa_ya|puasa_tidak|input_cancel)")
            ],
            STATE_PUASA_REASON: [
                CallbackQueryHandler(puasa_reason_chosen, pattern="^(preason_|input_cancel)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, puasa_reason_text)
            ],
            STATE_ROWATIB: [
                CallbackQueryHandler(rowatib_chosen, pattern="^(rowatib_|input_cancel)")
            ],
            STATE_ROWATIB_REASON: [
                CallbackQueryHandler(rowatib_reason_chosen, pattern="^(rwreason_|input_cancel)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, rowatib_reason_text)
            ],
            STATE_PENGAJIAN: [
                CallbackQueryHandler(pengajian_input_chosen, pattern="^(pengajian_set_|input_cancel)")
            ],
            STATE_TATAKRAMA: [
                CallbackQueryHandler(tatakrama_input_chosen, pattern="^(jset_|input_cancel)")
            ],
            STATE_TATAKRAMA_MANUAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, tatakrama_manual_received),
                CallbackQueryHandler(input_date_picked, pattern="^input_cancel$")
            ],
            STATE_CONFIRMATION: [
                CallbackQueryHandler(confirmation_handled, pattern="^(save_confirm|input_restart|input_cancel)")
            ]
        },
        fallbacks=[
            CommandHandler("start", start_command),
            CommandHandler("batal", start_command),
            CallbackQueryHandler(start_command, pattern="^menu_main$")
        ],
        per_message=False
    )

    # Conversation Handler untuk Cetak Laporan (Gambar / PDF)
    print_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(print_start, pattern="^menu_print$"),
            CallbackQueryHandler(print_date_chosen, pattern="^quick_print_"),
            CommandHandler("cetak", print_start)
        ],
        states={
            STATE_PRINT_DATE: [
                CallbackQueryHandler(print_date_chosen, pattern="^(sel_week_|quick_print_|print_date_manual|menu_main)")
            ],
            STATE_PRINT_MANUAL_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, print_manual_date_received),
                CallbackQueryHandler(print_date_chosen, pattern="^menu_main$")
            ],
            STATE_PRINT_SETTINGS: [
                CallbackQueryHandler(print_settings_action, pattern="^(set_ahadke_|toggle_pengajian|set_jijyah_|proceed_format|menu_print)")
            ],
            STATE_PRINT_MANUAL_JIJYAH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, print_manual_jijyah_received),
                CallbackQueryHandler(print_settings_action, pattern="^menu_print$")
            ],
            STATE_PRINT_FORMAT: [
                CallbackQueryHandler(print_format_chosen, pattern="^(fmt_|back_settings)")
            ]
        },
        fallbacks=[
            CommandHandler("start", start_command),
            CommandHandler("batal", start_command),
            CallbackQueryHandler(start_command, pattern="^menu_main$")
        ],
        per_message=False
    )

    # Conversation Handler untuk Pengelolaan Nama (Tambah Nama & Hapus Nama)
    name_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(start_add_name, pattern="^act_add_name$"),
            CallbackQueryHandler(start_del_name_menu, pattern="^act_del_name_menu$"),
        ],
        states={
            STATE_ADD_NAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name_added),
                CallbackQueryHandler(menu_callback_handler, pattern="^menu_switch_name$")
            ],
            STATE_DELETE_NAME: [
                CallbackQueryHandler(handle_name_deleted, pattern="^del_name_"),
                CallbackQueryHandler(menu_callback_handler, pattern="^menu_switch_name$")
            ]
        },
        fallbacks=[
            CommandHandler("start", start_command),
            CommandHandler("batal", start_command),
            CallbackQueryHandler(menu_callback_handler, pattern="^menu_switch_name$"),
            CallbackQueryHandler(start_command, pattern="^menu_main$")
        ],
        per_message=False
    )

    # Conversation Handler untuk Edit Data Inputan
    edit_conv = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(edit_start, pattern="^menu_edit$"),
            CommandHandler("edit", edit_start),
        ],
        states={
            STATE_EDIT_SELECT_DATE: [
                CallbackQueryHandler(edit_date_selected, pattern="^(editsel_|edit_date_custom|menu_main)"),
            ],
            STATE_EDIT_MANUAL_DATE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_manual_date_received),
                CallbackQueryHandler(edit_start, pattern="^edit_back_select$"),
                CallbackQueryHandler(start_command, pattern="^menu_main$"),
            ],
            STATE_EDIT_MENU: [
                CallbackQueryHandler(edit_menu_dispatcher, pattern="^(edit_act_|edit_back_select|menu_main)"),
            ],
            STATE_EDIT_SM_STATUS: [
                CallbackQueryHandler(edit_sm_status_chosen, pattern="^(editsm_ya|editsm_tidak|edit_dashboard_back)"),
            ],
            STATE_EDIT_SM_TIME: [
                CallbackQueryHandler(edit_sm_time_chosen, pattern="^(editsmtime_|edit_dashboard_back)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_sm_time_text),
            ],
            STATE_EDIT_SM_REASON: [
                CallbackQueryHandler(edit_sm_reason_chosen, pattern="^(editsmreason_|edit_dashboard_back)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_sm_reason_text),
            ],
            STATE_EDIT_DZIKIR: [
                CallbackQueryHandler(edit_dzikir_chosen, pattern="^(editdzikir_|edit_dashboard_back)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_dzikir_text),
            ],
            STATE_EDIT_DHUHA_STATUS: [
                CallbackQueryHandler(edit_dhuha_status_chosen, pattern="^(editdh_ya|editdh_tidak|edit_dashboard_back)"),
            ],
            STATE_EDIT_DHUHA_REASON: [
                CallbackQueryHandler(edit_dhuha_reason_chosen, pattern="^(editdhreason_|edit_dashboard_back)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_dhuha_reason_text),
            ],
            STATE_EDIT_PUASA_STATUS: [
                CallbackQueryHandler(edit_puasa_status_chosen, pattern="^(editp_ya|editp_tidak|edit_dashboard_back)"),
            ],
            STATE_EDIT_PUASA_REASON: [
                CallbackQueryHandler(edit_puasa_reason_chosen, pattern="^(editpreason_|edit_dashboard_back)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_puasa_reason_text),
            ],
            STATE_EDIT_ROWATIB: [
                CallbackQueryHandler(edit_rowatib_chosen, pattern="^(editrowatib_|edit_dashboard_back)"),
            ],
            STATE_EDIT_ROWATIB_REASON: [
                CallbackQueryHandler(edit_rowatib_reason_chosen, pattern="^(editrwreason_|edit_dashboard_back)"),
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_rowatib_reason_text),
            ],
            STATE_EDIT_AHAD_KE: [
                CallbackQueryHandler(edit_ahad_chosen, pattern="^(editahad_|edit_dashboard_back)"),
            ],
            STATE_EDIT_JIJYAH: [
                CallbackQueryHandler(edit_jijyah_chosen, pattern="^(editjset_|edit_dashboard_back)"),
            ],
            STATE_EDIT_JIJYAH_MANUAL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, edit_jijyah_manual_received),
                CallbackQueryHandler(edit_menu_dispatcher, pattern="^edit_dashboard_back$"),
            ],
            STATE_EDIT_DELETE_CONFIRM: [
                CallbackQueryHandler(edit_delete_confirmed, pattern="^(editdel_yes|edit_dashboard_back)"),
            ],
        },
        fallbacks=[
            CommandHandler("start", start_command),
            CommandHandler("batal", start_command),
            CommandHandler("menu", start_command),
            CallbackQueryHandler(start_command, pattern="^menu_main$"),
        ],
        per_message=False,
    )

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("menu", start_command))
    app.add_handler(CommandHandler("edit", edit_start))
    app.add_handler(input_conv)
    app.add_handler(edit_conv)
    app.add_handler(print_conv)
    app.add_handler(name_conv)
    app.add_handler(CallbackQueryHandler(menu_callback_handler))

    print("🤖 Bot Laporan Pelaksanaan Amanah sedang berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()
