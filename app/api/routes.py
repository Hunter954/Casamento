from flask import Blueprint, request, jsonify
from app import db
from app.models import GiftPurchase

api_bp = Blueprint('api', __name__)


@api_bp.route('/mercado-pago/webhook', methods=['POST'])
def mercado_pago_webhook():
    data = request.get_json(silent=True) or {}
    external_reference = None
    if data.get('data') and isinstance(data['data'], dict):
        external_reference = data['data'].get('external_reference')
    external_reference = external_reference or request.args.get('external_reference')

    if external_reference and external_reference.isdigit():
        purchase = GiftPurchase.query.get(int(external_reference))
        if purchase:
            purchase.status = 'approved'
            purchase.mercado_pago_payment_id = str(data.get('id', ''))
            db.session.commit()
    return jsonify({'ok': True})
