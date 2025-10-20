# hr_notifications/models/hr_notification_cron.py

import logging
from odoo import models, api
from odoo.fields import Datetime
from collections import defaultdict

_logger = logging.getLogger(__name__)


class HrNotificationCron(models.Model):
    _name = 'hr.notification.cron'
    _description = 'Scheduled Actions for HR Notifications'

    @api.model
    def _execute_auto_checkout(self):
        _logger.info("--- CRON JOB START: AUTO CHECKOUT ---")

        # 1. Cari semua record absensi yang belum checkout dari hari-hari sebelumnya
        # Kita cari yang check_in-nya lebih dari 12 jam yang lalu untuk amannya
        twelve_hours_ago = Datetime.subtract(Datetime.now(), hours=12)

        attendances_to_fix = self.env['hr.attendance'].search([
            ('check_in', '<=', twelve_hours_ago),
            ('check_out', '=', False)  # Cari yang check_out-nya masih kosong
        ])

        if not attendances_to_fix:
            _logger.info("Tidak ditemukan absensi yang perlu di-checkout otomatis.")
            _logger.info("--- CRON JOB END: AUTO CHECKOUT ---")
            return

        _logger.info(f"Ditemukan {len(attendances_to_fix)} absensi yang akan di-checkout otomatis.")

        # 2. Iterasi melalui setiap record dan tentukan jam checkout-nya
        for attendance in attendances_to_fix:
            employee = attendance.employee_id
            work_pattern = employee.work_pattern_id  # Ambil pola kerja karyawan

            if not work_pattern:
                _logger.warning(f"Karyawan {employee.name} tidak memiliki Pola Kerja, auto checkout dilewati.")
                continue

            # 3. Tentukan waktu auto checkout berdasarkan Pola Kerja
            check_in_date = attendance.check_in.date()

            # Ubah jam float (misal: 17.0) menjadi Datetime
            work_to_hour = int(work_pattern.work_to)
            work_to_minute = int((work_pattern.work_to - work_to_hour) * 60)

            # Gabungkan tanggal check-in dengan jam selesai kerja
            auto_checkout_time = Datetime.now().replace(
                year=check_in_date.year,
                month=check_in_date.month,
                day=check_in_date.day,
                hour=work_to_hour,
                minute=work_to_minute,
                second=0,
                microsecond=0
            )

            # 4. Update record absensi dengan waktu checkout yang baru
            try:
                attendance.write({
                    'check_out': auto_checkout_time
                })
                _logger.info(f"Berhasil: Auto checkout untuk {employee.name} pada {auto_checkout_time}.")
            except Exception as e:
                _logger.error(f"Gagal: Auto checkout untuk {employee.name}. Error: {e}")

        _logger.info("--- CRON JOB END: AUTO CHECKOUT ---")

    def _send_reminder(self, reminder_type):
        """
        Fungsi generik yang sudah diperbaiki untuk mengirim pengingat
        TANPA menyimpan record di history.
        """
        if reminder_type == 'check_in':
            title = 'Jangan Lupa Check-in!'
            body = 'Selamat pagi! Jangan lupa untuk melakukan check-in hari ini.'
            log_msg = "check-in"
        else:  # 'check_out'
            title = 'Waktunya Check-out'
            body = 'Waktu kerja akan segera berakhir. Jangan lupa untuk melakukan check-out.'
            log_msg = "check-out"

        _logger.info(f"--- CRON JOB START: PENGINGAT {log_msg.upper()} ---")

        # 1. Ambil semua pengguna aktif yang memiliki token.
        users_with_token = self.env['res.users'].search([
            ('share', '=', False),
            ('fcm_token', '!=', False)
        ])

        if not users_with_token:
            _logger.warning("CRON JOB ABORTED: Tidak ada pengguna dengan FCM token.")
            return

        _logger.info(f"Ditemukan {len(users_with_token)} pengguna dengan token. Mengelompokkan token unik...")

        # 2. Kelompokkan pengguna berdasarkan FCM token mereka untuk menghindari duplikasi.
        tokens_to_users = defaultdict(list)
        for user in users_with_token:
            tokens_to_users[user.fcm_token].append(user.name)

        _logger.info(f"Ditemukan {len(tokens_to_users)} token UNIK. Memulai pengiriman...")

        # --- PERUBAHAN UTAMA DI SINI ---
        # Buat satu instance notifikasi sementara (transient) untuk mengirim pesan.
        # Ini TIDAK akan disimpan ke database.
        Notification = self.env['hr.notification']

        # 3. Iterasi melalui setiap token unik dan kirim notifikasi.
        for token, user_names in tokens_to_users.items():
            _logger.info(f"Mengirim ke Token: {token[:15]}... (Untuk pengguna: {user_names})")

            # Buat record 'virtual' di dalam memori, JANGAN di-create di database
            transient_notification = Notification.new({
                'name': title,
                'body': body,
            })

            try:
                # Panggil fungsi pengiriman dari record virtual ini
                transient_notification._send_fcm_notification(token)
                _logger.info(f"  -> SUKSES terkirim untuk {user_names}")
            except Exception as e:
                _logger.error(f"  -> GAGAL terkirim untuk {user_names}: {e}")

        _logger.info(f"--- CRON JOB END: PENGINGAT {log_msg.upper()} ---")

    @api.model
    def _send_check_in_reminder(self):
        self._send_reminder('check_in')

    @api.model
    def _send_check_out_reminder(self):
        self._send_reminder('check_out')