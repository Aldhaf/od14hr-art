# -*- coding: utf-8 -*-
from odoo import models, fields

class HrWorkPattern(models.Model):
    _name = 'hr.work.pattern'
    _description = 'Employee Work Pattern'

    name = fields.Char(string='Pattern Name', required=True, help="e.g., Office Hours, SPG Shift Pagi")

    store_location_id = fields.Many2one(
        'hr.store.location',
        string='Store Location',
        required=True,
        ondelete='cascade'
    )

    work_from = fields.Float(string='Work From', required=True,
                             help="Start time in 24-hour format, e.g., 8.0 for 08:00, 14.5 for 14:30")
    work_to = fields.Float(string='Work To', required=True, help="End time in 24-hour format, e.g., 17.0 for 17:00")

    duration = fields.Float(string='Work Duration (Hours)', compute='_compute_duration', readonly=True)

    def _compute_duration(self):
        for record in self:
            record.duration = record.work_to - record.work_from