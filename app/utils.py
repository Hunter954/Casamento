from datetime import datetime
from pathlib import Path
from uuid import uuid4
from flask import current_app
from werkzeug.utils import secure_filename


def format_currency(value):
    return f'R$ {value:,.2f}'.replace(',', 'X').replace('.', ',').replace('X', '.')


def save_upload(file_storage):
    if not file_storage or not file_storage.filename:
        return ''
    extension = Path(secure_filename(file_storage.filename)).suffix
    filename = f'{uuid4().hex}{extension}'
    destination = Path(current_app.config['UPLOAD_DIR']) / filename
    file_storage.save(destination)
    return f'uploads/{filename}'


def parse_datetime(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%dT%H:%M')
    except ValueError:
        return None
