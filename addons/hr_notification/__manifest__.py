# -*- coding: utf-8 -*-
{
    'name': "HR Notifications",
    'summary': "Module to manage and send notifications to HR mobile app.",
    'description': "Adds a new model hr.notification to store user-specific notifications.",
    'author': "Aldhaf",
    'website': "http://www.yourcompany.com",
    'category': 'Human Resources',
    'version': '14.0.1.0.0',

    # Modul 'hr' diperlukan karena kita akan menautkan notifikasi ke karyawan/pengguna HR
    'depends': ['base', 'hr'],

    # Selalu muat file security terlebih dahulu
    'data': [
        'security/ir.model.access.csv',
        # 'security/hr_notification_security.xml',
        'views/hr_notification_views.xml',
        'views/res_users_views.xml', # <-- Pastikan ini ada
        'data/ir_cron_data.xml',
        'data/hr_attendance_cron_data.xml',
    ],
    'installable': True,
    'application': True,
    'external_dependencies': {
        'python': [
            'requests',
            'google-auth',
            'google-auth-oauthlib'
        ]
    }
}