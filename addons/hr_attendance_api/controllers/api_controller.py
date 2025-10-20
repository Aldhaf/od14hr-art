# File: hr_attendance_api/controllers/api_controller.py

import base64
from datetime import datetime
from odoo import http, fields
from odoo.http import request, Response
import logging

# Pindahkan import ke luar try-except agar lebih jelas
from geopy.distance import geodesic

_logger = logging.getLogger(__name__)


class AttendanceApiController(http.Controller):

    @http.route('/api/hr_attendance/check_in', type='http', auth='user', methods=['POST'], csrf=False)
    def secure_check_in(self, **kw):
        try:
            employee_id = int(kw.get('employee_id'))
            latitude = float(kw.get('check_in_latitude'))
            longitude = float(kw.get('check_in_longitude'))
            photo_file = request.httprequest.files.get('check_in_photo')

            if not all([employee_id, latitude, longitude]):
                # 2. Perbaiki cara membuat respons error
                return Response('Data GPS atau Karyawan tidak lengkap.', status=400)

            employee = request.env['hr.employee'].sudo().browse(employee_id)
            if not employee:
                return Response('Data Karyawan tidak ditemukan.', status=400)

            # --- VALIDASI JADWAL YANG DISETUJUI ---
            today_str = fields.Date.context_today(employee)
            approved_schedule = request.env['hr.shift.roster'].sudo().search([
                ('employee_id', '=', employee.id),
                ('date', '=', today_str),
                ('state', '=', 'approved')
            ], limit=1)

            if not approved_schedule:
                _logger.warning(
                    f"Check-in DITOLAK untuk {employee.name} karena tidak ada jadwal yang disetujui hari ini.")
                return Response('Tidak ada jadwal kerja yang disetujui untuk Anda hari ini.', status=403)

            # --- LOGIKA GEOFENCING ---
            if not employee.store_location_id:
                return Response('Profil Anda tidak memiliki lokasi kerja yang terdaftar.', status=400)

            store_location = employee.store_location_id
            employee_coords = (latitude, longitude)
            store_coords = (store_location.gps_latitude, store_location.gps_longitude)

            distance = geodesic(employee_coords, store_coords).meters
            config_param = request.env['ir.config_parameter'].sudo()
            TOLERANCE_METERS = store_location.geofence_radius

            _logger.info(
                f"Validasi Geofence untuk {employee.name}: Jarak {distance:.2f} meter. Toleransi: {TOLERANCE_METERS} meter.")

            if distance > TOLERANCE_METERS:
                _logger.warning(
                    f"Check-in DITOLAK untuk {employee.name} karena di luar jangkauan ({distance:.2f} meter).")
                return Response(
                    f'Anda berada {int(distance)} meter dari lokasi kerja. Harap lakukan absensi di area yang ditentukan.',
                    status=403)

            photo_data = base64.b64encode(photo_file.read()) if photo_file else False

            request.env['hr.attendance'].sudo().create({
                'employee_id': employee_id,
                'check_in': datetime.now(),
                'x_check_in_latitude': latitude,
                'x_check_in_longitude': longitude,
                'x_check_in_photo': photo_data,
            })

            _logger.info(f"Check-in BERHASIL untuk {employee.name} (jarak: {distance:.2f} meter).")
            return Response('Check-in berhasil direkam.', status=200)

        except Exception as e:
            _logger.error(f"Terjadi error fatal pada API check_in: {e}", exc_info=True)
            # 3. Perbaiki cara membuat respons error 500
            return Response('Terjadi error di server: %s' % str(e), status=500)