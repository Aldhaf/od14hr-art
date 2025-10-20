# -*- coding: utf-8 -*-
from odoo import models, fields

class HrStoreLocation(models.Model):
    _name = 'hr.store.location'
    _description = 'Store Location for SPG/SPB'

    name = fields.Char(string='Store Name', required=True)
    address = fields.Text(string='Address')
    gps_latitude = fields.Float(string='GPS Latitude', digits=(10, 7))
    gps_longitude = fields.Float(string='GPS Longitude', digits=(10, 7))

    geofence_radius = fields.Integer(
        string='Geofence Radius (meters)',
        default=150,
        help="Jarak toleransi absensi dari titik koordinat toko dalam meter."
    )