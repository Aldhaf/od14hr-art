# -*- coding: utf-8 -*-

import logging
from odoo import models, api

_logger = logging.getLogger(__name__)

class HrLeave(models.Model):
    _inherit = 'hr.leave'

    def action_approve(self):
        # Jalankan dulu fungsi asli 'action_approve'
        res = super(HrLeave, self).action_approve()

        # Setelah cuti disetujui, jalankan logika notifikasi kita
        for leave in self:
            user = leave.user_id
            # Pastikan user ada dan memiliki token
            if user and user.fcm_token:
                _logger.info(f"Leave approved for {user.name}. Preparing to send notification.")

                # 1. Buat record notifikasi di database kita untuk history
                notification_vals = {
                    'name': 'Pengajuan Cuti Disetujui',
                    'body': f'Pengajuan cuti Anda untuk "{leave.name}" telah disetujui.',
                    'user_id': user.id,
                    'type': 'leave_approval',
                    'related_id': str(leave.id) # Simpan ID cuti untuk navigasi di app
                }
                new_notification = self.env['hr.notification'].create(notification_vals)

                # 2. Panggil fungsi pengirim notifikasi dari record yg baru dibuat
                try:
                    _logger.info(f"Sending notification {new_notification.id} to token {user.fcm_token[:10]}...")
                    new_notification._send_fcm_notification(user.fcm_token, data_payload={
                        'type': 'leave_approval',
                        'id': str(leave.id)
                    })
                except Exception as e:
                    _logger.error(f"Failed to send notification for leave {leave.id}: {e}")

        return res