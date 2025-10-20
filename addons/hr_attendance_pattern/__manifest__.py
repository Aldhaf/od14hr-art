# -*- coding: utf-8 -*-
{
    'name': "HR Attendance Pattern",
    'summary': "Manages dynamic work patterns for employees (shifts, office hours).",
    'description': "Adds models for Work Patterns and Store Locations for dynamic attendance calculation.",
    'author': "Aldhaf",
    'category': 'Human Resources',
    'version': '14.0.1.0.0',
    'depends': ['base', 'hr', 'hr_notification'], # Bergantung pada modul HR bawaan
    'data': [
        'security/ir.model.access.csv',
        'security/hr_shift_security.xml',
        'views/hr_work_pattern_views.xml',
        'views/hr_store_location_views.xml',
        'views/hr_employee_views.xml',
        'views/hr_shift_roster_views.xml',
        'views/hr_shift_submission_batch_views.xml',
    ],
    'installable': True,
    'application': True,
}