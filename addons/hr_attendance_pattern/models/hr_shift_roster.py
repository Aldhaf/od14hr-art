# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import ValidationError
import logging
from firebase_admin import messaging

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
        index=True
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

    def action_open_reject_wizard(self):
        """
        Dipanggil oleh tombol "Reject" di form view.
        Fungsi ini mengembalikan aksi untuk membuka wizard pop-up.
        """
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Alasan Penolakan',
            'res_model': 'hr.shift.roster.reject.wizard',
            'view_mode': 'form',
            'view_id': self.env.ref('hr_attendance_pattern.hr_shift_roster_reject_wizard_view_form').id,
            'target': 'new',
            'context': {
                'default_active_id': self.id,  # Kirim ID roster saat ini ke wizard
            }
        }

    def _send_schedule_update_notification(self):
        self.ensure_one()
        employee = self.employee_id
        user = employee.user_id

        if not user or not hasattr(user, 'fcm_token') or not user.fcm_token:
            _logger.warning(f"Cannot send FCM: User {user.name if user else 'N/A'} (Employee: {employee.name}) has no FCM token or fcm_token field is missing.")
            return

        target_token = user.fcm_token
        _logger.info(f"Attempting to send VISUAL FCM schedule update for roster {self.id} (status: {self.state}) to token {target_token[:10]}...")

        # Tentukan judul dan isi notifikasi berdasarkan status
        notif_title = ""
        notif_body = ""
        if self.state == 'approved':
            notif_title = "Jadwal Disetujui"
            notif_body = f"Pengajuan jadwal Anda untuk tanggal {self.date.strftime('%d %b %Y')} telah disetujui."
        elif self.state == 'rejected':
            notif_title = "Jadwal Ditolak"
            notif_body = f"Pengajuan jadwal Anda untuk tanggal {self.date.strftime('%d %b %Y')} ditolak."
            # alasan jika ada
            if self.rejection_reason:
                notif_body += f" Alasan: {self.rejection_reason}"
        else:
            _logger.warning(f"Not sending notification for roster {self.id} with state {self.state}")
            return # Jangan kirim jika statusnya bukan approved/rejected

        # Siapkan payload data (opsional, tapi bagus untuk deep linking saat notifikasi ditekan)
        data_payload = {
            'type': 'schedule_status_change',
            'roster_id': str(self.id),
            'status': self.state,
            'date': str(self.date)
        }

        # Buat pesan FCM dengan payload NOTIFICATION
        message = messaging.Message(
            notification=messaging.Notification(
                title=notif_title,
                body=notif_body,
            ),
            # --- DATA PAYLOAD ---
            data=data_payload,
            token=target_token,
            # --- KONFIGURASI PLATFORM ---
            android=messaging.AndroidConfig(
                priority='high', # Prioritas tinggi untuk notifikasi visual
                notification=messaging.AndroidNotification(
                    # (Opsional) Atur channel ID jika Anda punya channel notifikasi custom
                    # channel_id='schedule_updates_channel',
                    # (Opsional) Atur ikon notifikasi custom
                    icon='@drawable/ic_notification'
                )
            ),
            apns=messaging.APNSConfig(
                headers={'apns-priority': '10'}, # Prioritas 10 untuk notifikasi visual
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(
                        # content_available=False, # Tidak perlu lagi untuk notifikasi visual
                        sound='default', # Mainkan suara default
                        # badge=1 # (Opsional) Atur badge number jika perlu
                    )
                )
            )
        )

        # Kirim pesan
        try:
            response = messaging.send(message)
            _logger.info(f"Successfully sent VISUAL FCM to {user.name}: {response}")
        except Exception as e:
            _logger.error(f"Failed to send VISUAL FCM to {user.name}: {e}")

    def action_submit(self):
        self.write({'state': 'requested'})

    def action_approve(self):
        # perubahan state dan approver
        self.write({
            'state': 'approved',
            'approver_id': self.env.user.id
        })

        # Memanggil fungsi helper baru untuk mengirim notifikasi
        for roster in self:
            try:
                 _logger.info(f"Roster {roster.id} approved. Triggering FCM.")
                 roster._send_schedule_update_notification()
            except Exception as e:
                 _logger.error(f"Error triggering FCM notification after approval for roster {roster.id}: {e}")

        return True

    def action_reject(self, reason=''):
        # perubahan state, approver, dan alasan
        self.write({
            'state': 'rejected',
            'approver_id': self.env.user.id,
            'rejection_reason': reason
        })

        # Memanggil fungsi helper baru untuk mengirim notifikasi
        for roster in self:
             try:
                 _logger.info(f"Roster {roster.id} rejected. Triggering FCM.")
                 roster._send_schedule_update_notification()
             except Exception as e:
                 _logger.error(f"Error triggering FCM notification after rejection for roster {roster.id}: {e}")

    def action_reset_to_draft(self):
        self.write({
            'state': 'draft',
            'approver_id': False,
            'rejection_reason': False
        })