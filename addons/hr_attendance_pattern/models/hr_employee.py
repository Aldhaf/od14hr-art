# -*- coding: utf-8 -*-
from odoo import models, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    work_pattern_id = fields.Many2one(
        'hr.work.pattern',
        string='Work Pattern',
        help="Assigns the employee to a specific work schedule."
    )
    store_location_id = fields.Many2one(
        'hr.store.location',
        string='Store Location',
        help="Assigns SPG/SPB to a specific store."
    )