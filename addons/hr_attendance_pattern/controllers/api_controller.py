# -*- coding: utf-8 -*-
from datetime import timedelta
from odoo import http, fields
from odoo.http import request
import logging

_logger = logging.getLogger(__name__)

class WorkPatternApiController(http.Controller):

    @http.route('/api/submit_monthly_roster', type='json', auth='user', methods=['POST'], csrf=False)
    def submit_monthly_roster(self, schedules=None, month_name=None, **kwargs):
        employee = self._get_employee()
        if not employee or not schedules:
            return {'error': 'Data tidak lengkap.'}

        Batch = request.env['hr.shift.submission.batch'].sudo()
        Roster = request.env['hr.shift.roster'].sudo()

        try:
            # 1. Buat "Paket" (Batch) nya terlebih dahulu
            new_batch = Batch.create({
                'employee_id': employee.id,
                'submission_month': month_name,  # Contoh: "Oktober 2025"
            })

            # 2. Buat setiap detail jadwal dan hubungkan ke batch
            for schedule in schedules:
                Roster.create({
                    'employee_id': employee.id,
                    'date': schedule.get('date'),
                    'work_pattern_id': schedule.get('work_pattern_id'),
                    'state': 'requested',
                    'batch_id': new_batch.id,  # <-- Menghubungkan ke paket
                })

            return {'success': True, 'message': 'Pengajuan bulanan berhasil dikirim.'}
        except Exception as e:
            request.env.cr.rollback()
            return {'error': str(e)}

    @http.route('/api/get_booked_dates', type='json', auth='user', methods=['POST'], csrf=False)
    def get_booked_dates(self, start_date=None, end_date=None, **kwargs):
        employee = self._get_employee()
        if not employee:
            return {'error': 'Karyawan tidak ditemukan.'}

        if not start_date or not end_date:
            return {'error': 'Rentang tanggal dibutuhkan.'}

        _logger.info(f"API Call: /api/get_booked_dates for {employee.name} from {start_date} to {end_date}")

        # Cari semua jadwal yang statusnya BUKAN 'rejected' atau 'draft'
        domain = [
            ('employee_id', '=', employee.id),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('state', 'in', ['requested', 'approved'])
        ]

        booked_rosters = request.env['hr.shift.roster'].search_read(domain, fields=['date', 'state'])

        # Format data agar mudah dibaca oleh Flutter
        for roster in booked_rosters:
            # Ubah objek tanggal menjadi string
            if roster.get('date'):
                roster['date'] = roster['date'].strftime('%Y-%m-%d')

        return {'booked_dates': booked_rosters}

    @http.route('/api/cancel_shift_request', type='json', auth='user', methods=['POST'], csrf=False)
    def cancel_shift_request(self, roster_id=None, **kwargs):
        if not roster_id:
            return {'error': 'Roster ID tidak ditemukan.'}

        employee = self._get_employee()
        if not employee:
            return {'error': 'Karyawan tidak ditemukan.'}

        _logger.info(f"User {employee.name} mencoba membatalkan Roster ID: {roster_id}")

        # Cari record jadwal yang dimaksud
        roster_to_cancel = request.env['hr.shift.roster'].sudo().search([
            ('id', '=', roster_id),
            ('employee_id', '=', employee.id)  # Pastikan APC hanya bisa membatalkan jadwal miliknya sendiri
        ])

        if not roster_to_cancel:
            return {'error': 'Jadwal tidak ditemukan atau Anda tidak memiliki akses.'}

        # Validasi utama: hanya izinkan pembatalan jika statusnya 'requested'
        if roster_to_cancel.state != 'requested':
            _logger.warning(
                f"Gagal membatalkan: Jadwal ID {roster_id} sudah diproses (status: {roster_to_cancel.state}).")
            return {'error': f'Tidak bisa membatalkan jadwal yang sudah berstatus "{roster_to_cancel.state}".'}

        # Hapus record jadwal
        try:
            roster_to_cancel.unlink()
            _logger.info(f"Berhasil: Jadwal ID {roster_id} telah dibatalkan oleh {employee.name}.")
            return {'success': True, 'message': 'Pengajuan jadwal berhasil dibatalkan.'}
        except Exception as e:
            _logger.error(f"Gagal menghapus record jadwal ID {roster_id}: {e}")
            return {'error': 'Terjadi kesalahan di server saat mencoba membatalkan.'}

    # Helper method untuk mendapatkan employee dari user yang login
    def _get_employee(self):
        user = request.env.user
        employee = request.env['hr.employee'].search([('user_id', '=', user.id)], limit=1)
        if not employee:
            _logger.warning(f"API Call Failed: Employee data not found for user: {user.name}")
            return None
        return employee

    @http.route('/api/get_work_profile', type='json', auth='user', methods=['POST'], csrf=False)
    def get_work_profile(self, **kwargs):
        employee = self._get_employee()
        if not employee:
            return {'error': 'Employee data not found for this user.'}

        today_str = fields.Date.context_today(employee)
        _logger.info(f"API Call: /api/get_work_profile for user: {employee.user_id.name}")

        domain = [
            ('employee_id', '=', employee.id),
            ('date', '=', today_str),
            ('state', '=', 'approved')
        ]
        approved_roster = request.env['hr.shift.roster'].search(domain, limit=1)

        work_pattern_to_use = approved_roster.work_pattern_id if approved_roster else employee.work_pattern_id

        if approved_roster:
            _logger.info(f"Dynamic roster found for {employee.name} today. Using shift: {work_pattern_to_use.name}")
        else:
            _logger.info(
                f"No dynamic roster for {employee.name} today. Using default schedule: {work_pattern_to_use.name if work_pattern_to_use else 'None'}")

        store_location = employee.store_location_id
        job_title_value = employee.job_id.name if employee.job_id else False

        response_data = {
            'employee_name': employee.name,
            'job_title': job_title_value,
            'work_pattern': {
                'name': work_pattern_to_use.name if work_pattern_to_use else False,
                'work_from': work_pattern_to_use.work_from if work_pattern_to_use else False,
                'work_to': work_pattern_to_use.work_to if work_pattern_to_use else False,
            },
            'store_location': {
                'name': store_location.name if store_location else False,
                'latitude': store_location.gps_latitude if store_location else False,
                'longitude': store_location.gps_longitude if store_location else False,
            }
        }
        _logger.info(f"API Response Sent: {response_data}")
        return response_data

    @http.route('/api/get_available_shifts', type='json', auth='user', methods=['POST'], csrf=False)
    def get_available_shifts(self, **kwargs):
        employee = self._get_employee()

        if not employee or not employee.store_location_id:
            _logger.warning(
                f"API Call Failed for {employee.user_id.name if employee else 'Unknown User'}: Employee or store location not found.")
            return {'error': 'Lokasi toko Anda tidak terdaftar. Hubungi Admin.'}

        store_location_id = employee.store_location_id.id
        _logger.info(f"API Call: /api/get_available_shifts for {employee.name} at store ID {store_location_id}")

        # Cari semua pola kerja yang terhubung dengan lokasi toko karyawan
        shifts = request.env['hr.work.pattern'].search_read(
            [('store_location_id', '=', store_location_id)],
            fields=['id', 'name', 'work_from', 'work_to']
        )

        return {'shifts': shifts}

    # --- ENDPOINT BARU 1: UNTUK MENGAJUKAN JADWAL ---
    @http.route('/api/submit_shift_request', type='json', auth='user', methods=['POST'], csrf=False)
    # Ubah signature untuk secara eksplisit menerima 'schedules'
    def submit_shift_request(self, schedules=None, **kwargs):
        employee = self._get_employee()
        if not employee:
            return {'error': 'Employee not found.'}

        # Pindahkan pengecekan ke sini
        if not schedules:
            _logger.warning(f"API Call Failed: User {employee.user_id.name} submitted with no schedules.")
            return {'error': 'No schedules provided.'}

        # Tambahkan log PENTING ini untuk debugging
        _logger.info(f"User {employee.user_id.name} submitting {len(schedules)} shift requests. Data: {schedules}")

        Roster = request.env['hr.shift.roster']
        created_ids = []
        try:
            for schedule in schedules:
                vals = {
                    'employee_id': employee.id,
                    'date': schedule.get('date'),
                    'work_pattern_id': schedule.get('work_pattern_id'),
                    'state': 'requested',
                }
                new_roster = Roster.sudo().create(vals)
                created_ids.append(new_roster.id)

            _logger.info(f"Successfully created {len(created_ids)} roster records for {employee.user_id.name}.")
            return {'success': True, 'created_ids': created_ids}
        except Exception as e:
            _logger.error(f"Failed to create roster records for {employee.user_id.name}. Error: {e}")
            # Batalkan transaksi jika ada error
            request.env.cr.rollback()
            return {'error': str(e)}

    # --- ENDPOINT BARU 2: UNTUK MENGAMBIL RIWAYAT ROSTER ---
    @http.route('/api/get_my_roster', type='json', auth='user', methods=['POST'], csrf=False)
    def get_my_roster(self, **kwargs):
        employee = self._get_employee()
        if not employee:
            return {'error': 'Employee not found.'}

        # 'search_read' akan mengambil data dari database
        rosters_data = request.env['hr.shift.roster'].search_read(
            [('employee_id', '=', employee.id)],
            fields=[
                'id',
                'date',
                'work_pattern_id',
                'state',
                'rejection_reason',
                'create_date'
            ],
            order='date desc'
        )

        # Loop untuk memproses data sebelum dikirim
        for roster in rosters_data:
            if roster.get('work_pattern_id'):
                pattern_id = roster['work_pattern_id'][0]
                # Ambil record work.pattern untuk mendapatkan jamnya
                pattern = request.env['hr.work.pattern'].browse(pattern_id)
                roster['work_pattern_name'] = pattern.name
                roster['work_from'] = pattern.work_from
                roster['work_to'] = pattern.work_to

        _logger.info(f"User {employee.user_id.name} fetched {len(rosters_data)} roster records.")

        return {'rosters': rosters_data}

    @http.route('/api/get_daily_hours', type='json', auth='user', methods=['POST'], csrf=False)
    def get_daily_worked_hours(self, start_date=None, end_date=None, **kwargs):
        _logger.info(f"API Call: /api/get_daily_hours from {start_date} to {end_date}")

        employee = self._get_employee()
        if not employee:
            return {'error': 'Employee not found'}

        start_date_obj = fields.Date.from_string(start_date)
        end_date_obj = fields.Date.from_string(end_date)

        # Ambil semua data absensi dalam rentang tanggal
        domain = [
            ('employee_id', '=', employee.id),
            ('check_in', '>=', f'{start_date} 00:00:00'),
            ('check_in', '<=', f'{end_date} 23:59:59'),
        ]
        attendances = request.env['hr.attendance'].search(domain)

        # Ambil semua data jadwal yang disetujui dalam rentang tanggal
        roster_domain = [
            ('employee_id', '=', employee.id),
            ('date', '>=', start_date),
            ('date', '<=', end_date),
            ('state', '=', 'approved')
        ]
        approved_rosters = request.env['hr.shift.roster'].search(roster_domain)
        roster_map = {roster.date: roster for roster in approved_rosters}

        # Inisialisasi variabel
        total_hours = 0.0
        total_overtime = 0.0
        details = []

        # Iterasi setiap hari dalam rentang tanggal yang diminta
        current_date = start_date_obj
        while current_date <= end_date_obj:
            date_str = current_date.strftime('%Y-%m-%d')

            # Cari absensi untuk hari ini
            day_attendances = [att for att in attendances if att.check_in.date() == current_date]
            day_worked_hours = sum(att.worked_hours for att in day_attendances)

            # Tentukan status hari ini
            status = 'absent'
            standard_hours = 8.0  # Standar jam kerja default

            if day_worked_hours > 0:
                status = 'worked'
                total_hours += day_worked_hours

                # Cek jadwal untuk hari ini untuk menghitung lembur
                if current_date in roster_map:
                    roster = roster_map[current_date]
                    if roster.work_pattern_id:
                        standard_hours = roster.work_pattern_id.duration

                overtime = max(0, day_worked_hours - standard_hours)
                total_overtime += overtime

            # Anda bisa menambahkan logika untuk 'holiday' di sini jika ada modelnya

            details.append({
                'date': date_str,
                'hours': day_worked_hours,
                'status': status
            })

            current_date += timedelta(days=1)

        response_data = {
            'total_hours': total_hours,
            'overtime': total_overtime,
            'details': details
        }

        _logger.info(f"API Response being sent: {response_data}")
        return response_data