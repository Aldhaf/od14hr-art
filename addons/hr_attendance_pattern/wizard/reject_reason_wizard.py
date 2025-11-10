# -*- coding: utf-8 -*-
from odoo import models, fields, api

class RejectReasonWizard(models.TransientModel):
    """
    Model Transient (wizard) untuk pop-up input alasan penolakan.
    """
    _name = 'hr.shift.roster.reject.wizard'
    _description = 'Shift Roster Reject Reason Wizard'

    # Field untuk menampung input alasan dari manajer
    reason = fields.Text(string='Alasan Penolakan', required=True)

    def action_confirm_reject(self):
        """
        Dipanggil saat manajer menekan tombol "Konfirmasi Tolak" di wizard.
        """
        # Pastikan kita berada di konteks yang benar
        self.ensure_one()

        # Ambil ID record hr.shift.roster yang sedang dibuka (dikirim via context)
        active_id = self.env.context.get('active_id')
        if not active_id:
            return {'type': 'ir.actions.act_window_close'}  # Tutup wizard jika tidak ada ID

        # Cari record roster yang akan ditolak
        roster_record = self.env['hr.shift.roster'].browse(active_id)

        if roster_record.exists():
            # Panggil fungsi action_reject di record roster,
            # sambil mengirimkan alasan dari wizard
            roster_record.action_reject(reason=self.reason)

        # Tutup wizard pop-up
        return {'type': 'ir.actions.act_window_close'}