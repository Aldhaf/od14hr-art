# File: hr_attendance_api/__manifest__.py
{
    'name': 'HR Attendance API Security',
    'version': '14.0.1.0.0',
    'summary': 'Menambahkan API untuk check-in aman via mobile',
    'author': 'Aldhaf',
    'depends': [
        'hr_attendance', # Penting! Modul kita bergantung pada modul absensi standar
    ],
    'data': [
        'views/hr_attendance_view.xml',
        'data/hr_attendance_config_data.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}