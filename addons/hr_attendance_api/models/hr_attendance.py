# File: hr_attendance_api/models/hr_attendance.py
from odoo import models, fields

class HrAttendanceInherit(models.Model):
    _inherit = 'hr.attendance' # Mewarisi model hr.attendance

    # Menambahkan field-field baru.
    # Awalan 'x_' adalah praktik yang baik untuk field kustom.
    x_check_in_latitude = fields.Float(string='Latitude Check-in', digits=(10, 7))
    x_check_in_longitude = fields.Float(string='Longitude Check-in', digits=(10, 7))
    x_check_in_photo = fields.Binary(string='Foto Check-in', attachment=True)