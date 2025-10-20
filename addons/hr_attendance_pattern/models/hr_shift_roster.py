# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging

_logger = logging.getLogger(__name__)

class HrShiftRoster(models.Model):
    _name = 'hr.shift.roster'
    _description = 'Employee Shift Roster'
    _order = 'date desc, employee_id'
    batch_id = fields.Many2one('hr.shift.submission.batch', string='Submission Batch', ondelete='cascade')

    employee_id = fields.Many2one(
        'hr.employee',
        string='Employee',
        required=True,
        index=True  # Tambahkan index untuk pencarian lebih cepat
    )

    date = fields.Date(
        string='Date',
        required=True,
        index=True
    )

    work_pattern_id = fields.Many2one(
        'hr.work.pattern',
        string='Work Pattern (Shift)',
        required=True
    )

    # Field state ini adalah KUNCI dari sistem persetujuan kita.
    # default='draft' memastikan setiap jadwal baru dimulai sebagai draf.
    state = fields.Selection([
        ('draft', 'Draft'),
        ('requested', 'Requested'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ], string='Status', default='draft', required=True, index=True, copy=False)

    # Field ini akan membantu supervisor memberikan alasan jika menolak pengajuan
    rejection_reason = fields.Text(string='Rejection Reason', readonly=True, copy=False)

    # Kita simpan siapa yang menyetujui/menolak untuk audit
    approver_id = fields.Many2one('res.users', string='Approved/Rejected by', readonly=True, copy=False)

    # Memastikan tidak ada jadwal ganda untuk karyawan yang sama di tanggal yang sama
    _sql_constraints = [
        ('employee_date_uniq', 'unique(employee_id, date)', 'A schedule for this employee on this date already exists!')
    ]

    # --- Tambahkan method untuk mengubah state ---

    def action_submit(self):
        self.write({'state': 'requested'})

    def action_approve(self):
        # Langsung tulis perubahan state ke 'approved'
        self.write({
            'state': 'approved',
            'approver_id': self.env.user.id
        })

        # --- LOGIKA TRIGGER NOTIFIKASI (TETAP DIPERTAHANKAN) ---
        for roster in self:
            user = roster.employee_id.user_id
            if user and user.fcm_token:
                _logger.info(f"Jadwal disetujui untuk {user.name}. Menyiapkan notifikasi trigger.")

                Notification = self.env['hr.notification']

                transient_notification = Notification.new({
                    'name': 'Jadwal Disetujui',
                    'body': 'Jadwal Anda telah diperbarui.',
                })

                try:
                    _logger.info(f"Mengirim trigger 'schedule_update' ke token {user.fcm_token[:10]}...")
                    transient_notification._send_fcm_notification(user.fcm_token, data_payload={
                        'type': 'schedule_update',
                        'message': 'Your schedule has been updated. Please refresh.'
                    })
                except Exception as e:
                    _logger.error(f"Gagal mengirim trigger notifikasi untuk jadwal {roster.id}: {e}")

        # Karena ini adalah aksi tombol, kita bisa return True
        return True

    def action_reject(self, reason=''):
        self.write({
            'state': 'rejected',
            'approver_id': self.env.user.id,
            'rejection_reason': reason
        })

    def action_reset_to_draft(self):
        self.write({
            'state': 'draft',
            'approver_id': False,
            'rejection_reason': False
        })