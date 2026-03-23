import requests
from flask import current_app


class MercadoPagoService:
    API_URL = 'https://api.mercadopago.com/checkout/preferences'

    @classmethod
    def is_enabled(cls):
        return bool(current_app.config.get('MERCADO_PAGO_ACCESS_TOKEN'))

    @classmethod
    def create_preference(cls, purchase, gift_title, success_url, pending_url, failure_url, notification_url):
        if not cls.is_enabled():
            return {
                'enabled': False,
                'sandbox_url': '#',
                'reference': f'LOCAL-{purchase.id}',
            }

        payload = {
            'items': [{
                'title': gift_title,
                'quantity': 1,
                'currency_id': 'BRL',
                'unit_price': float(purchase.amount),
            }],
            'payer': {
                'name': purchase.buyer_name,
                'email': purchase.buyer_email,
            },
            'back_urls': {
                'success': success_url,
                'pending': pending_url,
                'failure': failure_url,
            },
            'auto_return': 'approved',
            'external_reference': str(purchase.id),
            'notification_url': notification_url,
        }
        headers = {
            'Authorization': f"Bearer {current_app.config['MERCADO_PAGO_ACCESS_TOKEN']}",
            'Content-Type': 'application/json',
        }
        response = requests.post(cls.API_URL, json=payload, headers=headers, timeout=20)
        response.raise_for_status()
        data = response.json()
        return {
            'enabled': True,
            'sandbox_url': data.get('init_point') or data.get('sandbox_init_point'),
            'reference': data.get('id', ''),
        }
