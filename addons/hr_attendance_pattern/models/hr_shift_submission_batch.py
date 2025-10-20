# hr_attendance_pattern/models/hr_shift_submission_batch.py
from odoo import models, fields

class HrShiftSubmissionBatch(models.Model):
    _name = 'hr.shift.submission.batch'
    _description = 'Shift Submission Batch'
    _order = 'create_date desc'

    employee_id = fields.Many2one('hr.employee', string='Employee', required=True)
    submission_month = fields.Char(string='Submission Month') # Contoh: "Oktober 2025"
    state = fields.Selection([
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='requested', required=True)

    # Ini adalah relasi yang menghubungkan "paket" ini ke detail jadwalnya
    roster_ids = fields.One2many('hr.shift.roster', 'batch_id', string='Roster Details')

    # --- FUNGSI UNTUK PERSETUJUAN MASSAL ---
    def action_approve_batch(self):
        for batch in self:
            batch.roster_ids.action_approve() # Panggil fungsi approve di setiap roster
            batch.write({'state': 'approved'})
        return True

    def action_reject_batch(self):
        # (Logika untuk reject bisa ditambahkan di sini)
        self.write({'state': 'rejected'})
        return True