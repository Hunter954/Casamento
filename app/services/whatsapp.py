import json
import re
from datetime import datetime
from typing import Iterable

import requests
from flask import current_app

from app import db
from app.models import SiteSettings, WhatsAppDispatch


class WhatsAppConfigError(Exception):
    pass


class WhatsAppSendError(Exception):
    pass


def _settings():
    return SiteSettings.query.first()


def normalize_whatsapp_phone(value: str) -> str:
    digits = ''.join(char for char in str(value or '') if char.isdigit())
    if not digits:
        return ''
    if digits.startswith('55') and len(digits) in {12, 13}:
        return digits
    if len(digits) in {10, 11}:
        return f'55{digits}'
    return digits


def sanitize_zapi_base_url(value: str | None) -> str:
    raw = (value or '').strip().rstrip('/')
    if not raw:
        return 'https://api.z-api.io'
    if '/instances/' in raw:
        raw = raw.split('/instances/')[0].rstrip('/')
    if raw.endswith('/send-text'):
        raw = raw[:-10].rstrip('/')
    return raw or 'https://api.z-api.io'


def get_whatsapp_config():
    settings = _settings()
    instance_id = (getattr(settings, 'zapi_instance_id', '') or current_app.config.get('ZAPI_INSTANCE_ID', '')).strip()
    token = (getattr(settings, 'zapi_token', '') or current_app.config.get('ZAPI_TOKEN', '')).strip()
    client_token = (getattr(settings, 'zapi_client_token', '') or current_app.config.get('ZAPI_CLIENT_TOKEN', '')).strip()
    base_url = sanitize_zapi_base_url((getattr(settings, 'zapi_base_url', '') or current_app.config.get('ZAPI_BASE_URL', 'https://api.z-api.io')))
    sender_number = (getattr(settings, 'zapi_sender_number', '') or current_app.config.get('WHATSAPP_SENDER_NUMBER', '')).strip()
    enabled = bool(getattr(settings, 'zapi_enabled', False) or current_app.config.get('ZAPI_ENABLED') == '1')
    delay_seconds = int(getattr(settings, 'zapi_delay_seconds', 4) or 4)

    return {
        'enabled': enabled,
        'instance_id': instance_id,
        'token': token,
        'client_token': client_token,
        'base_url': base_url,
        'sender_number': sender_number,
        'delay_seconds': max(1, min(delay_seconds, 15)),
    }


def validate_whatsapp_config(config=None):
    config = config or get_whatsapp_config()
    missing = []
    if not config['enabled']:
        missing.append('integração ativada')
    if not config['instance_id']:
        missing.append('instance id')
    if not config['token']:
        missing.append('token')
    if not config['client_token']:
        missing.append('client-token')
    if missing:
        raise WhatsAppConfigError('Preencha a configuração da Z-API: ' + ', '.join(missing) + '.')
    return config


def _post_send_text(phone: str, message: str, delay_seconds: int | None = None):
    config = validate_whatsapp_config()
    normalized_phone = normalize_whatsapp_phone(phone)
    if not normalized_phone:
        raise WhatsAppSendError('Telefone inválido para envio.')
    endpoint = f"{config['base_url']}/instances/{config['instance_id']}/token/{config['token']}/send-text"
    payload = {
        'phone': normalized_phone,
        'message': message,
        'delayMessage': delay_seconds or config['delay_seconds'],
    }
    headers = {
        'Client-Token': config['client_token'],
        'Content-Type': 'application/json',
    }
    response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
    response_data = {}
    try:
        response_data = response.json()
    except ValueError:
        response_data = {'raw': response.text}

    if response.ok:
        return {
            'ok': True,
            'phone': normalized_phone,
            'response': response_data,
            'message_id': response_data.get('zaapId') or response_data.get('messageId') or response_data.get('id') or '',
        }

    error_message = (
        response_data.get('value')
        or response_data.get('message')
        or response_data.get('error')
        or response.text
        or 'Falha ao enviar pela Z-API.'
    )
    raise WhatsAppSendError(error_message)


def send_test_message(phone: str, message: str):
    return _post_send_text(phone=phone, message=message)


def render_campaign_message(template: str, contact, settings=None, site_url: str = '') -> str:
    settings = settings or _settings()
    content = str(template or '').strip()
    if not content:
        return ''

    wedding_date = ''
    if settings and getattr(settings, 'wedding_date', None):
        wedding_date = settings.wedding_date.strftime('%d/%m/%Y')

    replacements = {
        '%contato%': (getattr(contact, 'name', '') or '').strip(),
        '%nome_noivos%': (getattr(settings, 'couple_names', '') or '').strip() if settings else '',
        '%data_casamento%': wedding_date,
        '%horario_casamento%': (getattr(settings, 'wedding_time', '') or '').strip() if settings else '',
        '%local_casamento%': (getattr(settings, 'wedding_location_name', '') or '').strip() if settings else '',
        '%endereco_casamento%': (getattr(settings, 'wedding_address', '') or '').strip() if settings else '',
        '%cidade_casamento%': (getattr(settings, 'wedding_city', '') or '').strip() if settings else '',
        '%rota_url%': (getattr(settings, 'route_url', '') or '').strip() if settings else '',
        '%site_url%': (site_url or '').strip(),
    }
    for key, value in replacements.items():
        content = content.replace(key, value)

    content = re.sub(r'\n{3,}', '\n\n', content).strip()
    return content


def _dispatch_response_text(data: dict) -> str:
    return serialize_payload(data)


def send_campaign_messages(campaign, contacts: Iterable, tag_filter: str | None = None, send_scope: str = 'unsent', settings=None, site_url: str = ''):
    validate_whatsapp_config()
    results = []
    settings = settings or _settings()

    for contact in contacts:
        if tag_filter and tag_filter != 'todos' and (contact.tag or '').strip().lower() != tag_filter.strip().lower():
            results.append({'contact': contact, 'status': 'skipped', 'reason': 'tag'})
            continue

        existing = WhatsAppDispatch.query.filter_by(campaign_id=campaign.id, contact_id=contact.id).first()
        if send_scope == 'unsent' and existing:
            results.append({'contact': contact, 'status': 'skipped', 'reason': 'already_processed'})
            continue
        if send_scope == 'errors' and (not existing or existing.status != 'error'):
            results.append({'contact': contact, 'status': 'skipped', 'reason': 'not_error'})
            continue
        if send_scope == 'all' and existing and existing.status == 'sent':
            results.append({'contact': contact, 'status': 'skipped', 'reason': 'already_sent'})
            continue

        if not existing:
            existing = WhatsAppDispatch(campaign_id=campaign.id, contact_id=contact.id)
            db.session.add(existing)

        existing.phone_sent = normalize_whatsapp_phone(contact.phone)
        personalized_message = render_campaign_message(campaign.message, contact=contact, settings=settings, site_url=site_url)
        try:
            response = _post_send_text(phone=contact.phone, message=personalized_message)
            existing.status = 'queued'
            existing.sent_at = None
            existing.provider_message_id = response.get('message_id', '')
            existing.response_body = _dispatch_response_text(response.get('response'))
            existing.error_message = ''
            results.append({'contact': contact, 'status': 'queued'})
        except Exception as exc:
            existing.status = 'error'
            existing.error_message = str(exc)
            existing.response_body = ''
            results.append({'contact': contact, 'status': 'error', 'reason': str(exc)})

    db.session.commit()
    return results



def serialize_payload(data):
    try:
        return json.dumps(data or {}, ensure_ascii=False)
    except Exception:
        return str(data or '')


def extract_message_id(data):
    if not isinstance(data, dict):
        return ''
    for key in ('zaapId', 'messageId', 'id', 'message_id'):
        value = data.get(key)
        if value:
            return str(value)
    nested = data.get('data')
    if isinstance(nested, dict):
        return extract_message_id(nested)
    return ''
