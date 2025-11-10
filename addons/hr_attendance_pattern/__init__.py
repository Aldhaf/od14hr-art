import logging
import firebase_admin
from firebase_admin import credentials
from odoo import api, SUPERUSER_ID

_logger = logging.getLogger(__name__)

# Ganti dengan path ke file JSON kunci akun layanan Anda
SERVICE_ACCOUNT_KEY_PATH = 'C:/OdooConfig/serviceAccountKey.json'

try:
    cred = credentials.Certificate(SERVICE_ACCOUNT_KEY_PATH)
    firebase_admin.initialize_app(cred)
    _logger.info("Firebase Admin SDK initialized successfully.")
except Exception as e:
    _logger.error(f"Failed to initialize Firebase Admin SDK: {e}")

from . import controllers
from . import models
from . import wizard