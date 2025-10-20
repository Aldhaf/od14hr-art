# -*- coding: utf-8 -*-

import requests
import json
import logging

from odoo import models, fields
from odoo.exceptions import UserError

# Import library baru dari Google
try:
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request
except ImportError:
    logging.getLogger(__name__).warning(
        "Google Auth libraries not installed. pip install google-auth google-auth-oauthlib")

_logger = logging.getLogger(__name__)


class HrNotification(models.Model):
    _name = 'hr.notification'
    _description = 'HR Employee Notification'
    _order = 'create_date desc'

    name = fields.Char(string='Title', required=True)
    body = fields.Text(string='Body')
    is_read = fields.Boolean(string='Is Read', default=False)

    type = fields.Selection([
        ('announcement', 'Announcement'),
        ('leave_approval', 'Leave Approval'),
        ('checkin_reminder', 'Check-in Reminder')
    ], string='Type', default='announcement', required=True)

    user_id = fields.Many2one(
        'res.users',
        string='Recipient User',
        required=True,
        ondelete='cascade'
    )

    related_id = fields.Char(string='Related Document ID')

    def _get_fcm_access_token(self):
        """
        Membuat access token OAuth 2.0 dari service account JSON.
        Token ini hanya berlaku selama 1 jam.
        """
        sa_json_str = self.env['ir.config_parameter'].sudo().get_param('hr_notifications.fcm_service_account_json')
        if not sa_json_str:
            _logger.error(
                "FCM Service Account JSON not found in System Parameters (hr_notifications.fcm_service_account_json)")
            return None, None

        try:
            sa_info = json.loads(sa_json_str)
            project_id = sa_info.get('project_id')

            # Tentukan scope yang diperlukan untuk FCM
            scopes = ['https://www.googleapis.com/auth/firebase.messaging']

            creds = service_account.Credentials.from_service_account_info(sa_info, scopes=scopes)

            # Refresh token jika sudah kedaluwarsa
            if not creds.valid:
                creds.refresh(Request())

            _logger.info("Successfully generated FCM access token.")
            return creds.token, project_id

        except Exception as e:
            _logger.error(f"Failed to create credentials or token from service account JSON: {e}")
            return None, None

    def _send_fcm_notification(self, fcm_token, data_payload=None):
        """
        Method ini mengirimkan notifikasi menggunakan FCM API V1.
        """
        self.ensure_one()

        access_token, project_id = self._get_fcm_access_token()
        if not access_token or not project_id:
            return False

        fcm_url = f'https://fcm.googleapis.com/v1/projects/{project_id}/messages:send'

        headers = {
            'Authorization': 'Bearer ' + access_token,
            'Content-Type': 'application/json',
        }

        # Struktur payload untuk API V1 sedikit berbeda
        payload = {
            'message': {
                'token': fcm_token,
                'notification': {
                    'title': self.name,
                    'body': self.body,
                },
                'data': data_payload or {}
            }
        }

        try:
            _logger.info(f"Sending FCM v1 notification to {fcm_token}")
            response = requests.post(fcm_url, data=json.dumps(payload), headers=headers, timeout=10)
            response.raise_for_status()

            _logger.info(f"FCM v1 response: {response.json()}")
            return True

        except requests.exceptions.Timeout:
            _logger.error("FCM v1 request timed out.")
            return False
        except requests.exceptions.RequestException as e:
            _logger.error(f"FCM v1 request failed: {e}")
            _logger.error(f"FCM v1 response body: {e.response.text if e.response else 'No response'}")
            return False

    def write(self, vals):
        # Cek: apakah pengguna hanya mencoba mengubah status 'is_read'?
        is_marking_as_read = 'is_read' in vals and len(vals) == 1

        # Jika ya, berikan izin khusus
        if is_marking_as_read:
            # Lakukan operasi 'write' dengan hak akses superuser (sudo)
            # Ini aman karena kita sudah membatasi operasinya hanya untuk 'is_read'
            return super(HrNotification, self.sudo()).write(vals)

        # Jika tidak, jalankan fungsi 'write' standar dengan aturan keamanan normal
        return super(HrNotification, self).write(vals)

    def unlink(self):
        """
        Override method 'unlink' untuk mengizinkan pengguna
        menghapus notifikasi miliknya sendiri.
        """
        for notification in self:
            # Jika pengguna yang mencoba menghapus bukan pemilik notifikasi dan bukan superuser
            if notification.user_id.id != self.env.uid and not self.env.is_superuser():
                # Tolak aksi penghapusan
                raise UserError("You are not allowed to delete this notification.")

        # Jika semua pemeriksaan lolos, lanjutkan dengan proses penghapusan standar
        return super(HrNotification, self).unlink()