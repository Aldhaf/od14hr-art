from odoo import models, fields, api


class ResUsers(models.Model):
    _inherit = 'res.users'

    fcm_token = fields.Char(string="FCM Token", help="Firebase Cloud Messaging Token for mobile push notifications.")

    def write(self, vals):
        is_updating_fcm_only = 'fcm_token' in vals and len(vals) == 1
        is_updating_own_profile = all(user.id == self.env.user.id for user in self.sudo())

        if is_updating_fcm_only and is_updating_own_profile:
            return super(ResUsers, self.sudo()).write(vals)

        return super(ResUsers, self).write(vals)