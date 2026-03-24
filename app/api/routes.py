from flask import Blueprint, request, jsonify
from app import db
from app.models import GiftPurchase
from app.services.mercado_pago import MercadoPagoService

api_bp = Blueprint('api', __name__)


@api_bp.route('/mercado-pago/webhook', methods=['POST'])
def mercado_pago_webhook():
    data = request.get_json(silent=True) or {}
    payment_id = None
    external_reference = request.args.get('external_reference')
    payment_status = None

    if data.get('data') and isinstance(data['data'], dict):
        payment_id = data['data'].get('id')
        external_reference = external_reference or data['data'].get('external_reference')

    payment_id = payment_id or data.get('id') or request.args.get('data.id') or request.args.get('id')

    if payment_id:
        try:
            payment_data = MercadoPagoService.fetch_payment(payment_id)
            external_reference = external_reference or str(payment_data.get('external_reference') or '')
            payment_status = payment_data.get('status')
        except Exception:
            payment_status = None

    if external_reference and str(external_reference).isdigit():
        purchase = GiftPurchase.query.get(int(external_reference))
        if purchase:
            purchase.mercado_pago_payment_id = str(payment_id or purchase.mercado_pago_payment_id or '')
            if payment_status == 'approved' or not payment_id:
                purchase.status = 'approved'
            elif payment_status:
                purchase.status = payment_status
            db.session.commit()

    return jsonify({'ok': True})
