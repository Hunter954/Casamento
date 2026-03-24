from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, current_app
from app import db
from app.models import RSVP, GuestbookMessage, SiteSettings, GiftItem, GiftPurchase
from app.services.message_ai import generate_loving_message
from app.services.mercado_pago import MercadoPagoService, MercadoPagoError

public_bp = Blueprint('public', __name__)


@public_bp.route('/')
def home():
    settings = SiteSettings.query.first()
    approved_messages = GuestbookMessage.query.filter_by(approved=True).order_by(GuestbookMessage.created_at.desc()).limit(6).all()
    gifts = GiftItem.query.filter_by(active=True).order_by(GiftItem.created_at.desc()).limit(6).all()
    return render_template('public/home.html', settings=settings, approved_messages=approved_messages, gifts=gifts)


@public_bp.route('/confirmar-presenca', methods=['POST'])
def confirm_presence():
    rsvp = RSVP(
        guest_name=request.form.get('guest_name', '').strip(),
        phone=request.form.get('phone', '').strip(),
        email=request.form.get('email', '').strip(),
        guests_count=int(request.form.get('guests_count', 1) or 1),
        attendance=request.form.get('attendance', 'yes'),
        message=request.form.get('message', '').strip(),
    )
    db.session.add(rsvp)
    db.session.commit()
    flash('Presença registrada com carinho! 💖', 'success')
    return redirect(url_for('public.home'))


@public_bp.route('/mural', methods=['GET', 'POST'])
def guestbook():
    settings = SiteSettings.query.first()
    if settings and not settings.allow_guestbook:
        flash('O mural está desativado no momento.', 'warning')
        return redirect(url_for('public.home'))

    if request.method == 'POST':
        message = GuestbookMessage(
            author_name=request.form.get('author_name', '').strip(),
            message=request.form.get('message', '').strip(),
            approved=False if settings and settings.require_guestbook_approval else True,
        )
        db.session.add(message)
        db.session.commit()
        flash('Recado enviado com sucesso! Ele aparecerá em breve. ✨', 'success')
        return redirect(url_for('public.guestbook'))

    messages = GuestbookMessage.query.filter_by(approved=True).order_by(GuestbookMessage.created_at.desc()).all()
    return render_template('public/guestbook.html', messages=messages, settings=settings)


@public_bp.route('/presentes')
def gifts():
    settings = SiteSettings.query.first()
    items = GiftItem.query.order_by(GiftItem.created_at.desc()).all()
    return render_template('public/gifts.html', items=items, settings=settings)


@public_bp.route('/presentes/<int:gift_id>/checkout', methods=['GET', 'POST'])
def gift_checkout(gift_id):
    gift = GiftItem.query.get_or_404(gift_id)
    settings = SiteSettings.query.first()

    if not gift.is_available:
        flash('Este presente não está mais disponível.', 'warning')
        return redirect(url_for('public.gifts'))

    if request.method == 'POST':
        purchase = GiftPurchase(
            gift_id=gift.id,
            buyer_name=request.form.get('buyer_name', '').strip(),
            buyer_email=request.form.get('buyer_email', '').strip(),
            buyer_phone=request.form.get('buyer_phone', '').strip(),
            confirmed_presence=request.form.get('confirmed_presence') == 'on',
            message=request.form.get('message', '').strip(),
            amount=gift.price,
            status='pending',
        )
        db.session.add(purchase)
        db.session.commit()

        try:
            pref = MercadoPagoService.create_preference(
                purchase=purchase,
                gift_title=gift.title,
                success_url=url_for('public.checkout_result', status='success', _external=True),
                pending_url=url_for('public.checkout_result', status='pending', _external=True),
                failure_url=url_for('public.checkout_result', status='failure', _external=True),
                notification_url=url_for('api.mercado_pago_webhook', _external=True),
            )
            purchase.mercado_pago_preference_id = pref['reference']
            db.session.commit()
        except MercadoPagoError as exc:
            db.session.rollback()
            purchase.status = 'payment_error'
            db.session.add(purchase)
            db.session.commit()
            current_app.logger.exception('Falha ao criar checkout do Mercado Pago para a compra %s', purchase.id)
            flash(f'Não foi possível iniciar o pagamento no Mercado Pago. Detalhe: {exc.message}', 'danger')
            return redirect(url_for('public.gift_checkout', gift_id=gift.id))
        except Exception:
            db.session.rollback()
            purchase.status = 'payment_error'
            db.session.add(purchase)
            db.session.commit()
            current_app.logger.exception('Erro inesperado ao iniciar checkout do Mercado Pago para a compra %s', purchase.id)
            flash('Ocorreu um erro interno ao iniciar o pagamento. Tente novamente em instantes.', 'danger')
            return redirect(url_for('public.gift_checkout', gift_id=gift.id))

        if pref['enabled']:
            return redirect(pref['sandbox_url'])
        flash('Checkout em modo local. Configure o token do Mercado Pago para ativar o pagamento real.', 'warning')
        return redirect(url_for('public.checkout_result', status='pending'))

    initial_message = generate_loving_message(settings.couple_names if settings else 'Darlon & Julia')
    return render_template('public/checkout.html', gift=gift, initial_message=initial_message)


@public_bp.route('/checkout/<status>')
def checkout_result(status):
    return render_template('public/checkout_result.html', status=status)


@public_bp.route('/gerar-mensagem')
def generate_message():
    settings = SiteSettings.query.first()
    return jsonify({'message': generate_loving_message(settings.couple_names if settings else 'Darlon & Julia')})
