import os
import unittest
import datetime
import database
import pdf_generator
import fitz

class TestAmanahBot(unittest.TestCase):
    def setUp(self):
        database.init_db()

    def test_dynamic_name_management(self):
        chat_id = 88888

        # 1. Pastikan nama default awal ada
        initial_names = database.get_all_names()
        self.assertIn("FIRHAN", initial_names)
        self.assertIn("INDRI", initial_names)

        # 2. Tambahkan beberapa nama baru
        self.assertTrue(database.add_name("AHMAD"))
        self.assertTrue(database.add_name("SITI"))
        self.assertTrue(database.add_name("RAHMAT"))

        # Pastikan nama-nama baru muncul di daftar
        all_names = database.get_all_names()
        self.assertIn("AHMAD", all_names)
        self.assertIn("SITI", all_names)
        self.assertIn("RAHMAT", all_names)

        # 3. Ganti user aktif ke salah satu nama baru
        database.set_user_setting(chat_id, "AHMAD")
        self.assertEqual(database.get_user_setting(chat_id), "AHMAD")

        database.set_user_setting(chat_id, "SITI")
        self.assertEqual(database.get_user_setting(chat_id), "SITI")

        # 4. Hapus nama
        self.assertTrue(database.delete_name("RAHMAT"))
        self.assertNotIn("RAHMAT", database.get_all_names())

    def test_week_calculation(self):
        target = datetime.date(2026, 9, 9) # Wednesday
        monday, sunday, ahad_ke, bulan_str = database.calculate_week_info(target)
        
        self.assertEqual(monday.strftime("%Y-%m-%d"), "2026-09-07")
        self.assertEqual(sunday.strftime("%Y-%m-%d"), "2026-09-13")
        self.assertEqual(ahad_ke, 2)
        self.assertEqual(bulan_str, "07 - 13 September 2026")

    def test_ahad_ke_selection_and_preservation(self):
        mon_dt = datetime.date(2026, 10, 26)
        mon_str = "2026-10-26"
        nama = "AHMAD"

        database.save_laporan({
            "chat_id": 12345,
            "nama": nama,
            "tanggal": "2026-10-26",
            "hari": "SENIN",
            "ahad_ke": 3,
            "monday_date": mon_str,
            "solat_malam_status": 1,
            "solat_malam_jam": "03:30 s/d 04:10",
            "solat_malam_alasan": "",
            "jumlah_dzikir": "10000",
            "dhuha_status": 1,
            "dhuha_alasan": "",
            "puasa_status": 1,
            "puasa_alasan": "",
            "rowatib": "5 waktu",
            "rowatib_alasan": ""
        })

        week_data = database.get_laporan_week(nama, mon_dt)
        self.assertEqual(week_data["ahad_ke"], 3, "Ahad ke harus sesuai pilihan user (3)!")

        database.save_pekan_ahad_ke(nama, mon_str, 4)
        week_data2 = database.get_laporan_week(nama, mon_dt)
        self.assertEqual(week_data2["ahad_ke"], 4, "Ahad ke harus terupdate menjadi 4!")

        test_pdf = "test_ahad_ke_dynamic.pdf"
        pdf_generator.generate_pdf_report(test_pdf, week_data2)
        doc = fitz.open(test_pdf)
        text = doc[0].get_text()
        self.assertIn("NAMA : AHMAD", text)
        self.assertIn("AHAD KE : 4", text)
        doc.close()
        os.remove(test_pdf)

    def test_jijyah_options_and_manual(self):
        nama = "SITI"
        mon_str = "2026-10-26"
        mon_dt = datetime.date(2026, 10, 26)

        # 1. Pilihan 2000
        database.save_pekan_jijyah(nama, mon_str, "2000")
        w1 = database.get_laporan_week(nama, mon_dt)
        self.assertEqual(w1["tata_krama_jijyah"], "2000")

        # 2. Pilihan 67000
        database.save_pekan_jijyah(nama, mon_str, "67000")
        w2 = database.get_laporan_week(nama, mon_dt)
        self.assertEqual(w2["tata_krama_jijyah"], "67000")

        # 3. Input Manual
        database.save_pekan_jijyah(nama, mon_str, "75000")
        w3 = database.get_laporan_week(nama, mon_dt)
        self.assertEqual(w3["tata_krama_jijyah"], "75000")

        test_pdf = "test_jijyah_dynamic.pdf"
        pdf_generator.generate_pdf_report(test_pdf, w3)
        doc = fitz.open(test_pdf)
        text = doc[0].get_text()
        self.assertIn("NAMA : SITI", text)
        self.assertIn("Jijyah : 75000", text)
        doc.close()
        os.remove(test_pdf)

    def test_report_bundle_pdf_and_image(self):
        test_pdf = "test_bundle_report.pdf"
        test_img = "test_bundle_report.png"
        target_dt = datetime.date(2026, 9, 7)
        
        database.save_pekan_info("FIRHAN", "2026-09-07", pengajian_status=1, tata_krama_nominal="", tata_krama_ahad="", tata_krama_jijyah="67000", ahad_ke=2)
        week_data = database.get_laporan_week("FIRHAN", target_dt)
        
        pdf_out, img_out = pdf_generator.generate_report_bundle(test_pdf, test_img, week_data)
        
        self.assertTrue(os.path.exists(pdf_out))
        self.assertTrue(os.path.exists(img_out))
        
        doc = fitz.open(pdf_out)
        text = doc[0].get_text()
        self.assertIn("AHAD KE : 2", text)
        self.assertIn("Hadir : ✓", text)
        self.assertIn("Tidak : ✓", text)
        self.assertIn("Jijyah : 67000", text)
        doc.close()
        
        os.remove(test_pdf)
        os.remove(test_img)

    def test_update_laporan_fields(self):
        nama = "TEST_USER_EDIT"
        tgl = "2026-10-27"
        mon_str = "2026-10-26"
        
        # Simpan laporan awal
        database.save_laporan({
            "chat_id": 99999,
            "nama": nama,
            "tanggal": tgl,
            "hari": "SELASA",
            "ahad_ke": 4,
            "monday_date": mon_str,
            "solat_malam_status": 1,
            "solat_malam_jam": "03:30 s/d 04:10",
            "solat_malam_alasan": "",
            "jumlah_dzikir": "10000",
            "dhuha_status": 1,
            "dhuha_alasan": "",
            "puasa_status": 0,
            "puasa_alasan": "Tidak Puasa",
            "rowatib": "5 waktu",
            "rowatib_alasan": ""
        })

        rec_initial = database.get_laporan_by_date(nama, tgl)
        self.assertIsNotNone(rec_initial)
        self.assertEqual(rec_initial["solat_malam_status"], 1)
        self.assertEqual(rec_initial["rowatib"], "5 waktu")

        # 1. Edit Solat Malam menjadi Tidak (alasan: Sakit)
        updated_sm = database.update_laporan(nama, tgl, {
            "solat_malam_status": 0,
            "solat_malam_jam": "-",
            "solat_malam_alasan": "Sakit",
            "jumlah_dzikir": "-"
        })
        self.assertTrue(updated_sm)
        rec_sm = database.get_laporan_by_date(nama, tgl)
        self.assertEqual(rec_sm["solat_malam_status"], 0)
        self.assertEqual(rec_sm["solat_malam_alasan"], "Sakit")
        self.assertEqual(rec_sm["solat_malam_jam"], "-")

        # 2. Edit Solat Dhuha menjadi Tidak (alasan: Uzur Syar'i)
        updated_dh = database.update_laporan(nama, tgl, {
            "dhuha_status": 0,
            "dhuha_alasan": "Uzur Syar'i"
        })
        self.assertTrue(updated_dh)
        rec_dh = database.get_laporan_by_date(nama, tgl)
        self.assertEqual(rec_dh["dhuha_status"], 0)
        self.assertEqual(rec_dh["dhuha_alasan"], "Uzur Syar'i")

        # 3. Edit Puasa menjadi Ya (1)
        updated_p = database.update_laporan(nama, tgl, {
            "puasa_status": 1,
            "puasa_alasan": ""
        })
        self.assertTrue(updated_p)
        rec_p = database.get_laporan_by_date(nama, tgl)
        self.assertEqual(rec_p["puasa_status"], 1)
        self.assertEqual(rec_p["puasa_alasan"], "")

        # 4. Edit Rowatib menjadi 3 waktu
        updated_rw = database.update_laporan(nama, tgl, {
            "rowatib": "3 waktu"
        })
        self.assertTrue(updated_rw)
        rec_rw = database.get_laporan_by_date(nama, tgl)
        self.assertEqual(rec_rw["rowatib"], "3 waktu")

        # 5. Edit Ahad Ke menjadi 5
        updated_ahad = database.update_laporan(nama, tgl, {
            "ahad_ke": 5
        })
        self.assertTrue(updated_ahad)
        rec_ahad = database.get_laporan_by_date(nama, tgl)
        self.assertEqual(rec_ahad["ahad_ke"], 5)

    def test_delete_laporan(self):
        nama = "TEST_USER_DEL"
        tgl = "2026-10-28"
        
        database.save_laporan({
            "chat_id": 99999,
            "nama": nama,
            "tanggal": tgl,
            "hari": "RABU",
            "ahad_ke": 4,
            "monday_date": "2026-10-26",
            "solat_malam_status": 1,
            "solat_malam_jam": "03:30 s/d 04:10",
            "solat_malam_alasan": "",
            "jumlah_dzikir": "10000",
            "dhuha_status": 1,
            "dhuha_alasan": "",
            "puasa_status": 0,
            "puasa_alasan": "",
            "rowatib": "5 waktu",
            "rowatib_alasan": ""
        })

        self.assertIsNotNone(database.get_laporan_by_date(nama, tgl))
        
        # Hapus laporan
        del_result = database.delete_laporan(nama, tgl)
        self.assertTrue(del_result)
        self.assertIsNone(database.get_laporan_by_date(nama, tgl))

        # Hapus tanggal yang tidak ada harus return False
        self.assertFalse(database.delete_laporan(nama, "2099-01-01"))

    def test_get_recent_laporan(self):
        nama = "TEST_USER_RECENT"
        dates = ["2026-10-20", "2026-10-21", "2026-10-22", "2026-10-23"]
        for d in dates:
            database.save_laporan({
                "chat_id": 99999,
                "nama": nama,
                "tanggal": d,
                "hari": "HARI",
                "ahad_ke": 3,
                "monday_date": "2026-10-19",
                "solat_malam_status": 1,
                "solat_malam_jam": "03:30 s/d 04:10",
                "solat_malam_alasan": "",
                "jumlah_dzikir": "10000",
                "dhuha_status": 1,
                "dhuha_alasan": "",
                "puasa_status": 0,
                "puasa_alasan": "",
                "rowatib": "5 waktu",
                "rowatib_alasan": ""
            })

        recent = database.get_recent_laporan(nama, limit=3)
        self.assertEqual(len(recent), 3)
        # Urutan harus tanggal terbaru di awal
        self.assertEqual(recent[0]["tanggal"], "2026-10-23")
        self.assertEqual(recent[1]["tanggal"], "2026-10-22")
        self.assertEqual(recent[2]["tanggal"], "2026-10-21")

    def test_edit_reflected_in_pdf_report(self):
        nama = "TEST_EDIT_PDF"
        mon_dt = datetime.date(2026, 10, 26)
        mon_str = "2026-10-26"

        # Simpan laporan awal
        database.save_laporan({
            "chat_id": 99999,
            "nama": nama,
            "tanggal": "2026-10-26",
            "hari": "SENIN",
            "ahad_ke": 4,
            "monday_date": mon_str,
            "solat_malam_status": 1,
            "solat_malam_jam": "03:30 s/d 04:10",
            "solat_malam_alasan": "",
            "jumlah_dzikir": "10000",
            "dhuha_status": 1,
            "dhuha_alasan": "",
            "puasa_status": 1,
            "puasa_alasan": "",
            "rowatib": "5 waktu",
            "rowatib_alasan": ""
        })

        # Edit laporan: ubah rowatib jadi "2 waktu" dan solat malam jadi tidak karena "Kesiangan"
        database.update_laporan(nama, "2026-10-26", {
            "solat_malam_status": 0,
            "solat_malam_jam": "-",
            "solat_malam_alasan": "Kesiangan",
            "jumlah_dzikir": "-",
            "rowatib": "2 waktu"
        })

        week_data = database.get_laporan_week(nama, mon_dt)
        self.assertEqual(week_data["days"]["SENIN"]["rowatib"], "2 waktu")
        self.assertEqual(week_data["days"]["SENIN"]["solat_malam"], "-")
        self.assertIn("SENIN: Kesiangan", week_data["keterangan_rows"]["solat_malam"])

        test_pdf = "test_edited_report.pdf"
        pdf_generator.generate_pdf_report(test_pdf, week_data)
        doc = fitz.open(test_pdf)
        text = doc[0].get_text()
        self.assertIn("2 waktu", text)
        self.assertIn("Kesiangan", text)
        doc.close()
        os.remove(test_pdf)

    def test_keterangan_diisi_ketika_tidak_menjalankan(self):
        nama = "TEST_ALASAN_KETERANGAN"
        mon_dt = datetime.date(2026, 11, 2)
        mon_str = "2026-11-02"

        # 1. SENIN: Puasa tidak jalan (Halangan)
        database.save_laporan({
            "chat_id": 77777,
            "nama": nama,
            "tanggal": "2026-11-02",
            "hari": "SENIN",
            "ahad_ke": 1,
            "monday_date": mon_str,
            "solat_malam_status": 1,
            "solat_malam_jam": "03:30 s/d 04:10",
            "solat_malam_alasan": "",
            "jumlah_dzikir": "10000",
            "dhuha_status": 1,
            "dhuha_alasan": "",
            "puasa_status": 0,
            "puasa_alasan": "Halangan",
            "rowatib": "5 waktu",
            "rowatib_alasan": ""
        })

        # 2. SELASA: Solat malam terlewat, Solat rawatib tidak full (Halangan)
        database.save_laporan({
            "chat_id": 77777,
            "nama": nama,
            "tanggal": "2026-11-03",
            "hari": "SELASA",
            "ahad_ke": 1,
            "monday_date": mon_str,
            "solat_malam_status": 0,
            "solat_malam_jam": "-",
            "solat_malam_alasan": "Terlewat",
            "jumlah_dzikir": "-",
            "dhuha_status": 1,
            "dhuha_alasan": "",
            "puasa_status": 0,
            "puasa_alasan": "",
            "rowatib": "3 waktu",
            "rowatib_alasan": "Halangan"
        })

        # 3. RABU: Dhuha terlewat, Rowatib 4 waktu (Ada Keperluan)
        database.save_laporan({
            "chat_id": 77777,
            "nama": nama,
            "tanggal": "2026-11-04",
            "hari": "RABU",
            "ahad_ke": 1,
            "monday_date": mon_str,
            "solat_malam_status": 1,
            "solat_malam_jam": "03:40 s/d 04:20",
            "solat_malam_alasan": "",
            "jumlah_dzikir": "20.000",
            "dhuha_status": 0,
            "dhuha_alasan": "Terlewat",
            "puasa_status": 0,
            "puasa_alasan": "",
            "rowatib": "4 waktu",
            "rowatib_alasan": "Ada Keperluan"
        })

        week_data = database.get_laporan_week(nama, mon_dt)

        # Verifikasi alasan tercatat di keterangan_rows
        self.assertIn("SELASA: Terlewat", week_data["keterangan_rows"]["solat_malam"])
        self.assertIn("SELASA: Halangan", week_data["keterangan_rows"]["rowatib"])
        self.assertIn("RABU: Ada Keperluan", week_data["keterangan_rows"]["rowatib"])
        self.assertIn("RABU: Terlewat", week_data["keterangan_rows"]["dhuha"])
        self.assertIn("SENIN: Halangan", week_data["keterangan_rows"]["puasa"])

        # Verifikasi hasil render PDF mencetak alasan tersebut
        test_pdf = "test_alasan_keterangan.pdf"
        pdf_generator.generate_pdf_report(test_pdf, week_data)
        doc = fitz.open(test_pdf)
        text = doc[0].get_text()

        self.assertIn("SELASA: Terlewat", text)
        self.assertIn("SELASA: Halangan", text)
        self.assertIn("RABU: Ada Keperluan", text)
        self.assertIn("RABU: Terlewat", text)
        self.assertIn("SENIN: Halangan", text)

        doc.close()
        os.remove(test_pdf)

    def test_edit_callback_patterns_and_operations(self):
        import re

        # Verifikasi pattern regex pada ConversationHandler edit
        patterns = {
            "STATE_EDIT_SELECT_DATE": r"^(editsel_|edit_date_custom|menu_main)",
            "STATE_EDIT_MENU": r"^(edit_act_|edit_back_select|menu_main)",
            "STATE_EDIT_SM_TIME": r"^(editsmtime_|edit_dashboard_back)",
            "STATE_EDIT_SM_REASON": r"^(editsmreason_|edit_dashboard_back)",
            "STATE_EDIT_DZIKIR": r"^(editdzikir_|edit_dashboard_back)",
            "STATE_EDIT_DHUHA_REASON": r"^(editdhreason_|edit_dashboard_back)",
            "STATE_EDIT_PUASA_REASON": r"^(editpreason_|edit_dashboard_back)",
            "STATE_EDIT_ROWATIB": r"^(editrowatib_|edit_dashboard_back)",
            "STATE_EDIT_ROWATIB_REASON": r"^(editrwreason_|edit_dashboard_back)",
            "STATE_EDIT_AHAD_KE": r"^(editahad_|edit_dashboard_back)",
            "STATE_EDIT_JIJYAH": r"^(editjset_|edit_dashboard_back)",
        }

        # Contoh callback data aktual dari inline button
        samples = [
            ("STATE_EDIT_SELECT_DATE", "editsel_2026-10-27"),
            ("STATE_EDIT_SELECT_DATE", "edit_date_custom"),
            ("STATE_EDIT_SELECT_DATE", "menu_main"),
            ("STATE_EDIT_MENU", "edit_act_sm"),
            ("STATE_EDIT_MENU", "edit_act_dhuha"),
            ("STATE_EDIT_MENU", "edit_act_puasa"),
            ("STATE_EDIT_MENU", "edit_act_rowatib"),
            ("STATE_EDIT_MENU", "edit_act_ahad"),
            ("STATE_EDIT_MENU", "edit_act_pengajian"),
            ("STATE_EDIT_MENU", "edit_act_jijyah"),
            ("STATE_EDIT_MENU", "edit_act_del"),
            ("STATE_EDIT_MENU", "edit_back_select"),
            ("STATE_EDIT_MENU", "menu_main"),
            ("STATE_EDIT_SM_TIME", "editsmtime_03:30 s/d 04:10"),
            ("STATE_EDIT_SM_TIME", "editsmtime_manual"),
            ("STATE_EDIT_SM_TIME", "edit_dashboard_back"),
            ("STATE_EDIT_SM_REASON", "editsmreason_Terlewat"),
            ("STATE_EDIT_SM_REASON", "editsmreason_Halangan"),
            ("STATE_EDIT_SM_REASON", "edit_dashboard_back"),
            ("STATE_EDIT_DZIKIR", "editdzikir_10000"),
            ("STATE_EDIT_DZIKIR", "editdzikir_20000"),
            ("STATE_EDIT_DZIKIR", "editdzikir_manual"),
            ("STATE_EDIT_DZIKIR", "edit_dashboard_back"),
            ("STATE_EDIT_DHUHA_REASON", "editdhreason_Terlewat"),
            ("STATE_EDIT_DHUHA_REASON", "editdhreason_Halangan"),
            ("STATE_EDIT_DHUHA_REASON", "edit_dashboard_back"),
            ("STATE_EDIT_PUASA_REASON", "editpreason_Halangan"),
            ("STATE_EDIT_PUASA_REASON", "editpreason_Terlewat"),
            ("STATE_EDIT_PUASA_REASON", "edit_dashboard_back"),
            ("STATE_EDIT_ROWATIB", "editrowatib_5 waktu"),
            ("STATE_EDIT_ROWATIB", "editrowatib_3 waktu"),
            ("STATE_EDIT_ROWATIB", "edit_dashboard_back"),
            ("STATE_EDIT_ROWATIB_REASON", "editrwreason_Halangan"),
            ("STATE_EDIT_ROWATIB_REASON", "editrwreason_Terlewat"),
            ("STATE_EDIT_ROWATIB_REASON", "edit_dashboard_back"),
            ("STATE_EDIT_AHAD_KE", "editahad_1"),
            ("STATE_EDIT_AHAD_KE", "editahad_4"),
            ("STATE_EDIT_AHAD_KE", "edit_dashboard_back"),
            ("STATE_EDIT_JIJYAH", "editjset_2000"),
            ("STATE_EDIT_JIJYAH", "editjset_67000"),
            ("STATE_EDIT_JIJYAH", "editjset_manual"),
            ("STATE_EDIT_JIJYAH", "edit_dashboard_back"),
        ]

        for state_name, callback_data in samples:
            pattern = patterns[state_name]
            self.assertTrue(
                bool(re.match(pattern, callback_data)),
                f"Pattern {pattern} pada state {state_name} harus mencocokkan '{callback_data}'!"
            )

        # Verifikasi operasi edit data di database
        nama = "FIRHAN"
        tgl = "2026-10-27"
        database.save_laporan({
            "chat_id": 99999,
            "nama": nama,
            "tanggal": tgl,
            "hari": "SELASA",
            "ahad_ke": 1,
            "monday_date": "2026-10-26",
            "solat_malam_status": 1,
            "solat_malam_jam": "03:30 s/d 04:10",
            "solat_malam_alasan": "",
            "jumlah_dzikir": "10000",
            "dhuha_status": 1,
            "dhuha_alasan": "",
            "puasa_status": 0,
            "puasa_alasan": "",
            "rowatib": "5 waktu",
            "rowatib_alasan": ""
        })

        # Update Solat Malam via edit
        database.update_laporan(nama, tgl, {
            "solat_malam_status": 0,
            "solat_malam_jam": "-",
            "solat_malam_alasan": "Terlewat",
            "jumlah_dzikir": "-"
        })
        rec = database.get_laporan_by_date(nama, tgl)
        self.assertEqual(rec["solat_malam_status"], 0)
        self.assertEqual(rec["solat_malam_alasan"], "Terlewat")

        # Update Rowatib via edit
        database.update_laporan(nama, tgl, {
            "rowatib": "3 waktu",
            "rowatib_alasan": "Halangan"
        })
        rec = database.get_laporan_by_date(nama, tgl)
        self.assertEqual(rec["rowatib"], "3 waktu")
        self.assertEqual(rec["rowatib_alasan"], "Halangan")

        # Hapus via edit delete
        self.assertTrue(database.delete_laporan(nama, tgl))
        self.assertIsNone(database.get_laporan_by_date(nama, tgl))

    def test_end_to_end_edit_handlers_flow(self):
        import asyncio
        from unittest.mock import AsyncMock, MagicMock
        import bot

        async def run_async_test():
            chat_id = 998877
            cur_name = "TEST_E2E"
            database.add_name(cur_name)
            database.set_user_setting(chat_id, cur_name)

            tgl = "2026-10-27"
            database.save_laporan({
                "chat_id": chat_id,
                "nama": cur_name,
                "tanggal": tgl,
                "hari": "SELASA",
                "ahad_ke": 1,
                "monday_date": "2026-10-26",
                "solat_malam_status": 1,
                "solat_malam_jam": "03:30 s/d 04:10",
                "solat_malam_alasan": "",
                "jumlah_dzikir": "10000",
                "dhuha_status": 1,
                "dhuha_alasan": "",
                "puasa_status": 0,
                "puasa_alasan": "",
                "rowatib": "5 waktu",
                "rowatib_alasan": ""
            })

            def make_update(callback_data=None, text=None):
                update = MagicMock()
                update.effective_chat.id = chat_id
                if callback_data:
                    query = MagicMock()
                    query.data = callback_data
                    query.answer = AsyncMock()
                    query.edit_message_text = AsyncMock()
                    update.callback_query = query
                else:
                    update.callback_query = None
                if text:
                    msg = MagicMock()
                    msg.text = text
                    msg.reply_text = AsyncMock()
                    update.message = msg
                else:
                    update.message = None
                return update

            context = MagicMock()
            context.user_data = {}

            # 1. Start menu edit
            s1 = await bot.edit_start(make_update(callback_data="menu_edit"), context)
            self.assertEqual(s1, bot.STATE_EDIT_SELECT_DATE)

            # 2. Pilih tanggal
            s2 = await bot.edit_date_selected(make_update(callback_data=f"editsel_{tgl}"), context)
            self.assertEqual(s2, bot.STATE_EDIT_MENU)
            self.assertEqual(context.user_data.get("edit_target_date"), tgl)

            # 3. Edit Solat Malam
            s3 = await bot.edit_menu_dispatcher(make_update(callback_data="edit_act_sm"), context)
            self.assertEqual(s3, bot.STATE_EDIT_SM_STATUS)
            s4 = await bot.edit_sm_status_chosen(make_update(callback_data="editsm_tidak"), context)
            self.assertEqual(s4, bot.STATE_EDIT_SM_REASON)
            s5 = await bot.edit_sm_reason_chosen(make_update(callback_data="editsmreason_Kesiangan"), context)
            self.assertEqual(s5, bot.STATE_EDIT_MENU)
            rec = database.get_laporan_by_date(cur_name, tgl)
            self.assertEqual(rec["solat_malam_status"], 0)
            self.assertEqual(rec["solat_malam_alasan"], "Kesiangan")

            # 4. Edit Dhuha
            await bot.edit_menu_dispatcher(make_update(callback_data="edit_act_dhuha"), context)
            await bot.edit_dhuha_status_chosen(make_update(callback_data="editdh_tidak"), context)
            await bot.edit_dhuha_reason_chosen(make_update(callback_data="editdhreason_Terlewat"), context)
            rec = database.get_laporan_by_date(cur_name, tgl)
            self.assertEqual(rec["dhuha_status"], 0)
            self.assertEqual(rec["dhuha_alasan"], "Terlewat")

            # 5. Edit Puasa
            await bot.edit_menu_dispatcher(make_update(callback_data="edit_act_puasa"), context)
            await bot.edit_puasa_status_chosen(make_update(callback_data="editp_ya"), context)
            rec = database.get_laporan_by_date(cur_name, tgl)
            self.assertEqual(rec["puasa_status"], 1)

            # 6. Edit Rowatib
            await bot.edit_menu_dispatcher(make_update(callback_data="edit_act_rowatib"), context)
            await bot.edit_rowatib_chosen(make_update(callback_data="editrowatib_3 waktu"), context)
            await bot.edit_rowatib_reason_chosen(make_update(callback_data="editrwreason_Halangan"), context)
            rec = database.get_laporan_by_date(cur_name, tgl)
            self.assertEqual(rec["rowatib"], "3 waktu")
            self.assertEqual(rec["rowatib_alasan"], "Halangan")

            # 7. Edit Ahad Ke
            await bot.edit_menu_dispatcher(make_update(callback_data="edit_act_ahad"), context)
            await bot.edit_ahad_chosen(make_update(callback_data="editahad_4"), context)
            rec = database.get_laporan_by_date(cur_name, tgl)
            self.assertEqual(rec["ahad_ke"], 4)

            # 8. Hapus Laporan
            await bot.edit_menu_dispatcher(make_update(callback_data="edit_act_del"), context)
            await bot.edit_delete_confirmed(make_update(callback_data="editdel_yes"), context)
            self.assertIsNone(database.get_laporan_by_date(cur_name, tgl))

            database.delete_name(cur_name)

        asyncio.run(run_async_test())

    def test_print_combined_all_and_active_mode(self):
        import asyncio
        from unittest.mock import AsyncMock, MagicMock
        import bot

        async def run_print_test():
            chat_id = 991122
            cur_name = "TEST_FIRHAN_PRINT"
            other_name = "TEST_INDRI_PRINT"
            database.add_name(cur_name)
            database.add_name(other_name)
            database.set_user_setting(chat_id, cur_name)

            mon_dt = datetime.date(2026, 11, 2)
            mon_str = "2026-11-02"

            database.save_laporan({
                "chat_id": chat_id,
                "nama": cur_name,
                "tanggal": "2026-11-03",
                "hari": "SELASA",
                "ahad_ke": 1,
                "monday_date": mon_str,
                "solat_malam_status": 0,
                "solat_malam_jam": "-",
                "solat_malam_alasan": "Terlewat",
                "jumlah_dzikir": "-",
                "dhuha_status": 1,
                "dhuha_alasan": "",
                "puasa_status": 0,
                "puasa_alasan": "",
                "rowatib": "3 waktu",
                "rowatib_alasan": "Halangan"
            })

            database.save_laporan({
                "chat_id": 999333,
                "nama": other_name,
                "tanggal": "2026-11-02",
                "hari": "SENIN",
                "ahad_ke": 1,
                "monday_date": mon_str,
                "solat_malam_status": 1,
                "solat_malam_jam": "03:30 s/d 04:10",
                "solat_malam_alasan": "",
                "jumlah_dzikir": "10000",
                "dhuha_status": 1,
                "dhuha_alasan": "",
                "puasa_status": 1,
                "puasa_alasan": "",
                "rowatib": "5 waktu",
                "rowatib_alasan": ""
            })

            # 1. Verifikasi Generator Gabungan PDF & Bundle
            all_data = [
                database.get_laporan_week(cur_name, mon_dt),
                database.get_laporan_week(other_name, mon_dt),
            ]
            week_meta = {
                "ahad_ke": 1,
                "bulan": all_data[0]["bulan"],
                "posko": "TANGKIL",
                "monday_date": mon_str
            }

            test_pdf = "test_unit_all.pdf"
            test_prefix = "test_unit_all_img"
            pdf_path, img_paths = pdf_generator.generate_combined_report_bundle(test_pdf, test_prefix, all_data, week_meta)

            self.assertTrue(os.path.exists(pdf_path))
            self.assertGreaterEqual(len(img_paths), 1)

            doc = fitz.open(pdf_path)
            full_pdf_text = "\n".join(page.get_text() for page in doc)
            self.assertIn("LAPORAN PELAKSANAAN AMANAH PER POSKO", full_pdf_text)
            self.assertIn("POSKO : TANGKIL", full_pdf_text)
            self.assertIn(f"NAMA : {cur_name}", full_pdf_text)
            self.assertIn(f"NAMA : {other_name}", full_pdf_text)
            # Pastikan detail jam solat malam, jumlah dzikir, rowatib, dan alasan tampil lengkap tanpa disingkat
            self.assertIn("03:30 s/d 04:10", full_pdf_text)
            self.assertIn("10000", full_pdf_text)
            self.assertIn("3 waktu", full_pdf_text)
            self.assertIn("5 waktu", full_pdf_text)
            self.assertIn("SELASA: Terlewat", full_pdf_text)
            self.assertIn("SELASA: Halangan", full_pdf_text)
            self.assertNotIn("/7 hr", full_pdf_text)

            doc.close()
            os.remove(pdf_path)
            for p in img_paths:
                os.remove(p)

            # Verifikasi format_detailed_person_report_text tidak menggunakan singkatan
            detail_txt_1 = bot.format_detailed_person_report_text(all_data[0])
            detail_txt_2 = bot.format_detailed_person_report_text(all_data[1])
            self.assertIn("Solat Malam:", detail_txt_1)
            self.assertIn("Jumlah Dzikir:", detail_txt_1)
            self.assertIn("Solat Dhuha:", detail_txt_1)
            self.assertIn("Puasa Senin & Kamis:", detail_txt_1)
            self.assertIn("Solat Rowatib:", detail_txt_1)
            self.assertIn("Jam 03:30 s/d 04:10", detail_txt_2)
            self.assertIn("10000", detail_txt_2)
            self.assertNotIn("SM:", detail_txt_2)
            self.assertNotIn("Dz:", detail_txt_2)

            # 2. Verifikasi Handler Bot
            def make_update(callback_data=None):
                u = MagicMock()
                u.effective_chat.id = chat_id
                q = MagicMock()
                q.data = callback_data
                q.answer = AsyncMock()
                q.edit_message_text = AsyncMock()
                u.callback_query = q
                return u

            ctx = MagicMock()
            ctx.user_data = {}
            ctx.bot.send_message = AsyncMock()
            ctx.bot.send_photo = AsyncMock()
            ctx.bot.send_document = AsyncMock()
            ctx.bot.send_media_group = AsyncMock()

            # Mulai cetak -> pilih target
            s1 = await bot.print_start(make_update("menu_print"), ctx)
            self.assertEqual(s1, bot.STATE_PRINT_TARGET)

            # Pilih target Keseluruhan
            s2 = await bot.print_target_chosen(make_update("ptarget_all"), ctx)
            self.assertEqual(s2, bot.STATE_PRINT_DATE)
            self.assertEqual(ctx.user_data["print_target_mode"], "all")

            # Pilih pekan -> langsung klik fmt_both dari STATE_PRINT_SETTINGS
            s3 = await bot.print_date_chosen(make_update(f"sel_week_{mon_str}"), ctx)
            self.assertEqual(s3, bot.STATE_PRINT_SETTINGS)

            s3_direct = await bot.print_settings_action(make_update("fmt_both"), ctx)
            self.assertEqual(s3_direct, bot.ConversationHandler.END)
            self.assertTrue(ctx.bot.send_document.called)
            self.assertTrue(ctx.bot.send_photo.called or ctx.bot.send_media_group.called)

            # Lanjut ke format via proceed_format
            ctx.user_data = {"print_target_mode": "all", "print_mon_str": mon_str}
            s4 = await bot.print_settings_action(make_update("proceed_format"), ctx)
            self.assertEqual(s4, bot.STATE_PRINT_FORMAT)

            # Pilih format PDF
            s5 = await bot.print_format_chosen(make_update("fmt_pdf"), ctx)
            self.assertEqual(s5, bot.ConversationHandler.END)
            self.assertTrue(ctx.bot.send_document.called)

            # Pilih format Gambar
            ctx.user_data = {"print_target_mode": "all", "print_mon_str": mon_str}
            s6 = await bot.print_format_chosen(make_update("fmt_img"), ctx)
            self.assertEqual(s6, bot.ConversationHandler.END)
            self.assertTrue(ctx.bot.send_media_group.called or ctx.bot.send_photo.called)

            # Pilih format Nama Aktif
            ctx.user_data = {"print_target_mode": "active", "print_mon_str": mon_str}
            s7 = await bot.print_format_chosen(make_update("fmt_both"), ctx)
            self.assertEqual(s7, bot.ConversationHandler.END)

            # Cleanup
            database.delete_name(cur_name)
            database.delete_name(other_name)
            database.delete_laporan(cur_name, "2026-11-03")
            database.delete_laporan(other_name, "2026-11-02")

        asyncio.run(run_print_test())

    def test_laporan_cetak_perposko_complete(self):
        """
        Pengujian komprehensif bahwa Laporan Cetak Per Posko:
        1. Menampilkan nama Posko ('TANGKIL' atau Posko kustom) pada Halaman Rekapitulasi Posko.
        2. Menampilkan nama Posko pada setiap Halaman Detail Individu Anggota Posko.
        3. Menampilkan Total Anggota Posko yang sesuai.
        4. Merangkum seluruh anggota posko beserta detail harian dan alasan keterangan ibadah.
        """
        posko_test = "TANGKIL"
        members = ["ANGGOTA_POSKO_1", "ANGGOTA_POSKO_2"]
        for m in members:
            database.add_name(m)

        mon_str = "2026-11-09"
        mon_dt = datetime.date(2026, 11, 9)

        # Anggota 1 posko: ada uzur solat malam
        database.save_laporan({
            "chat_id": 112233,
            "nama": members[0],
            "tanggal": "2026-11-10",
            "hari": "SELASA",
            "ahad_ke": 2,
            "monday_date": mon_str,
            "solat_malam_status": 0,
            "solat_malam_jam": "-",
            "solat_malam_alasan": "Terlewat",
            "jumlah_dzikir": "-",
            "dhuha_status": 1,
            "dhuha_alasan": "",
            "puasa_status": 0,
            "puasa_alasan": "",
            "rowatib": "5 waktu",
            "rowatib_alasan": ""
        })

        # Anggota 2 posko: ada uzur rowatib
        database.save_laporan({
            "chat_id": 445566,
            "nama": members[1],
            "tanggal": "2026-11-09",
            "hari": "SENIN",
            "ahad_ke": 2,
            "monday_date": mon_str,
            "solat_malam_status": 1,
            "solat_malam_jam": "03:30 s/d 04:10",
            "solat_malam_alasan": "",
            "jumlah_dzikir": "10000",
            "dhuha_status": 1,
            "dhuha_alasan": "",
            "puasa_status": 1,
            "puasa_alasan": "",
            "rowatib": "4 waktu",
            "rowatib_alasan": "Ada Keperluan"
        })

        all_data = [database.get_laporan_week(m, mon_dt) for m in members]
        week_meta = {
            "ahad_ke": 2,
            "bulan": all_data[0]["bulan"],
            "posko": posko_test,
            "monday_date": mon_str
        }

        test_pdf = "test_laporan_perposko.pdf"
        test_prefix = "test_laporan_perposko_img"
        pdf_path, img_paths = pdf_generator.generate_combined_report_bundle(
            test_pdf, test_prefix, all_data, week_meta
        )

        self.assertTrue(os.path.exists(pdf_path))
        self.assertEqual(len(img_paths), 1) # 2 anggota muat utuh dalam 1 halaman Landscape A4

        doc = fitz.open(pdf_path)
        self.assertEqual(len(doc), 1)

        page_text = doc[0].get_text()
        self.assertIn("LAPORAN PELAKSANAAN AMANAH PER POSKO", page_text)
        self.assertIn(f"POSKO : {posko_test}", page_text)
        self.assertIn("TOTAL ANGGOTA : 2 ORANG", page_text)
        self.assertIn("NAMA : ANGGOTA_POSKO_1", page_text)
        self.assertIn("NAMA : ANGGOTA_POSKO_2", page_text)
        self.assertIn("SOLAT MALAM", page_text)
        self.assertIn("JUMLAH DZIKIR", page_text)
        self.assertIn("PUASA SENIN & KAMIS", page_text)
        self.assertIn("SOLAT ROWATIB", page_text)
        self.assertIn("03:30 s/d 04:10", page_text)
        self.assertIn("10000", page_text)
        self.assertIn("4 waktu", page_text)
        self.assertIn("SELASA: Terlewat", page_text)
        self.assertIn("SENIN: Ada Keperluan", page_text)
        self.assertNotIn("/7 hr", page_text)

        doc.close()

        # Cleanup
        os.remove(pdf_path)
        for p in img_paths:
            os.remove(p)

        for m in members:
            database.delete_name(m)
        database.delete_laporan(members[0], "2026-11-10")
        database.delete_laporan(members[1], "2026-11-09")

if __name__ == "__main__":
    unittest.main()
