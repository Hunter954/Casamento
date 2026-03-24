from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user

from app import db
from app.models import (
    AdminUser,
    SiteSettings,
    RSVP,
    GuestbookMessage,
    GiftItem,
    GiftPurchase,
    ContactLead,
    WhatsAppCampaign,
    WhatsAppDispatch,
)
from app.utils import save_upload, parse_datetime, format_phone, normalize_phone_digits
from app.services.whatsapp import send_campaign_messages, send_test_message, WhatsAppConfigError

admin_bp = Blueprint('admin', __name__)


def _to_float(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _tag_options():
    tags = [tag for (tag,) in db.session.query(ContactLead.tag).distinct().order_by(ContactLead.tag.asc()).all() if tag]
    return ['todos'] + tags


@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('admin.dashboard'))
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        user = AdminUser.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('admin.dashboard'))
        flash('Credenciais inválidas.', 'danger')
    return render_template('admin/login.html')


@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sessão encerrada com sucesso.', 'success')
    return redirect(url_for('admin.login'))


@admin_bp.route('/')
@login_required
def dashboard():
    approved_purchases = GiftPurchase.query.filter_by(status='approved')
    stats = {
        'rsvps': RSVP.query.count(),
        'approved_messages': GuestbookMessage.query.filter_by(approved=True).count(),
        'gifts': GiftItem.query.count(),
        'paid': approved_purchases.count(),
        'paid_total': sum(item.amount or 0 for item in approved_purchases.all()),
        'contacts': ContactLead.query.count(),
        'campaigns': WhatsAppCampaign.query.count(),
        'dispatches_sent': WhatsAppDispatch.query.filter_by(status='sent').count(),
    }
    purchases = GiftPurchase.query.order_by(GiftPurchase.created_at.desc()).limit(8).all()
    return render_template('admin/dashboard.html', stats=stats, purchases=purchases)


@admin_bp.route('/configuracoes', methods=['GET', 'POST'])
@login_required
def settings():
    settings = SiteSettings.query.first()
    if not settings:
        settings = SiteSettings()
        db.session.add(settings)
        db.session.commit()
    if request.method == 'POST':
        settings.couple_names = request.form.get('couple_names', '')
        settings.hero_phrase = request.form.get('hero_phrase', '')
        settings.wedding_date = parse_datetime(request.form.get('wedding_date', ''))
        settings.wedding_location_name = request.form.get('wedding_location_name', '')
        settings.wedding_address = request.form.get('wedding_address', '')
        settings.wedding_city = request.form.get('wedding_city', '')
        settings.wedding_time = request.form.get('wedding_time', '')
        settings.map_embed_url = request.form.get('map_embed_url', '')
        settings.route_url = request.form.get('route_url', '')
        settings.gift_banner_title = request.form.get('gift_banner_title', '')
        settings.gift_button_label = request.form.get('gift_button_label', '')
        settings.final_message = request.form.get('final_message', '')
        settings.theme_primary = request.form.get('theme_primary', '#7a3144')
        settings.theme_secondary = request.form.get('theme_secondary', '#f7d7df')
        settings.theme_accent = request.form.get('theme_accent', '#f14d78')
        settings.allow_guestbook = request.form.get('allow_guestbook') == 'on'
        settings.require_guestbook_approval = request.form.get('require_guestbook_approval') == 'on'
        settings.whatsapp_message_template = request.form.get('whatsapp_message_template', '')
        settings.mercado_pago_enabled = request.form.get('mercado_pago_enabled') == 'on'
        settings.mercado_pago_access_token = request.form.get('mercado_pago_access_token', '').strip()
        settings.mercado_pago_public_key = request.form.get('mercado_pago_public_key', '').strip()
        settings.zapi_enabled = request.form.get('zapi_enabled') == 'on'
        settings.zapi_instance_id = request.form.get('zapi_instance_id', '').strip()
        settings.zapi_token = request.form.get('zapi_token', '').strip()
        settings.zapi_client_token = request.form.get('zapi_client_token', '').strip()
        settings.zapi_sender_number = normalize_phone_digits(request.form.get('zapi_sender_number', '').strip())
        settings.zapi_base_url = request.form.get('zapi_base_url', 'https://api.z-api.io').strip() or 'https://api.z-api.io'
        settings.zapi_delay_seconds = int(request.form.get('zapi_delay_seconds', 4) or 4)

        hero_upload = request.files.get('hero_image')
        gift_banner_upload = request.files.get('gift_banner_image')
        if hero_upload and hero_upload.filename:
            settings.hero_image = save_upload(hero_upload)
        if gift_banner_upload and gift_banner_upload.filename:
            settings.gift_banner_image = save_upload(gift_banner_upload)

        db.session.commit()
        flash('Configurações salvas com sucesso.', 'success')
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html', settings=settings)


@admin_bp.route('/configuracoes/whatsapp/testar', methods=['POST'])
@login_required
def test_whatsapp():
    phone = request.form.get('test_phone', '').strip()
    message = request.form.get('test_message', '').strip() or 'Teste de integração Z-API enviado pelo painel do site.'
    try:
        send_test_message(phone=phone, message=message)
        flash('Mensagem de teste enviada com sucesso.', 'success')
    except Exception as exc:
        flash(f'Falha no teste da Z-API: {exc}', 'danger')
    return redirect(url_for('admin.settings'))


@admin_bp.route('/presentes', methods=['GET', 'POST'])
@login_required
def manage_gifts():
    if request.method == 'POST':
        image_path = save_upload(request.files.get('image')) if request.files.get('image') else ''
        item = GiftItem(
            title=request.form.get('title', ''),
            description=request.form.get('description', ''),
            price=_to_float((request.form.get('price', '') or '').replace('.', '').replace(',', '.')),
            image_url=image_path,
            active=request.form.get('active') == 'on',
            allow_multiple_purchases=request.form.get('allow_multiple_purchases') == 'on',
        )
        db.session.add(item)
        db.session.commit()
        flash('Presente cadastrado com sucesso.', 'success')
        return redirect(url_for('admin.manage_gifts'))
    gifts = GiftItem.query.order_by(GiftItem.created_at.desc()).all()
    return render_template('admin/gifts.html', gifts=gifts)


@admin_bp.route('/presentes/<int:gift_id>/editar', methods=['POST'])
@login_required
def edit_gift(gift_id):
    gift = GiftItem.query.get_or_404(gift_id)
    gift.title = request.form.get('title', gift.title)
    gift.description = request.form.get('description', gift.description)
    gift.price = _to_float((request.form.get('price', gift.price) or '').replace('.', '').replace(',', '.'))
    gift.active = request.form.get('active') == 'on'
    gift.allow_multiple_purchases = request.form.get('allow_multiple_purchases') == 'on'
    image_upload = request.files.get('image')
    if image_upload and image_upload.filename:
        gift.image_url = save_upload(image_upload)
    db.session.commit()
    flash('Presente atualizado com sucesso.', 'success')
    return redirect(url_for('admin.manage_gifts'))


@admin_bp.route('/presentes/<int:gift_id>/excluir', methods=['POST'])
@login_required
def delete_gift(gift_id):
    gift = GiftItem.query.get_or_404(gift_id)
    db.session.delete(gift)
    db.session.commit()
    flash('Presente excluído.', 'success')
    return redirect(url_for('admin.manage_gifts'))


@admin_bp.route('/confirmacoes')
@login_required
def manage_rsvps():
    rsvps = RSVP.query.order_by(RSVP.created_at.desc()).all()
    return render_template('admin/rsvps.html', rsvps=rsvps)


@admin_bp.route('/mural')
@login_required
def manage_guestbook():
    messages = GuestbookMessage.query.order_by(GuestbookMessage.created_at.desc()).all()
    return render_template('admin/guestbook.html', messages=messages)


@admin_bp.route('/mural/<int:message_id>/aprovar')
@login_required
def approve_message(message_id):
    message = GuestbookMessage.query.get_or_404(message_id)
    message.approved = True
    db.session.commit()
    flash('Recado aprovado.', 'success')
    return redirect(url_for('admin.manage_guestbook'))


@admin_bp.route('/mural/<int:message_id>/desaprovar')
@login_required
def disapprove_message(message_id):
    message = GuestbookMessage.query.get_or_404(message_id)
    message.approved = False
    db.session.commit()
    flash('Recado movido para pendente.', 'success')
    return redirect(url_for('admin.manage_guestbook'))


@admin_bp.route('/mural/<int:message_id>/excluir', methods=['POST'])
@login_required
def delete_message(message_id):
    message = GuestbookMessage.query.get_or_404(message_id)
    db.session.delete(message)
    db.session.commit()
    flash('Recado excluído.', 'success')
    return redirect(url_for('admin.manage_guestbook'))


@admin_bp.route('/compras')
@login_required
def purchases():
    purchases = GiftPurchase.query.order_by(GiftPurchase.created_at.desc()).all()
    return render_template('admin/purchases.html', purchases=purchases)


@admin_bp.route('/compras/<int:purchase_id>/excluir', methods=['POST'])
@login_required
def delete_purchase(purchase_id):
    purchase = GiftPurchase.query.get_or_404(purchase_id)
    db.session.delete(purchase)
    db.session.commit()
    flash('Compra excluída com sucesso.', 'success')
    return redirect(url_for('admin.purchases'))


@admin_bp.route('/contatos', methods=['GET', 'POST'])
@login_required
def contacts():
    if request.method == 'POST':
        contact = ContactLead(
            name=request.form.get('name', ''),
            phone=normalize_phone_digits(request.form.get('phone', '')),
            email=request.form.get('email', ''),
            tag=request.form.get('tag', 'convidado'),
        )
        db.session.add(contact)
        db.session.commit()
        flash('Contato salvo.', 'success')
        return redirect(url_for('admin.contacts'))
    contacts = ContactLead.query.order_by(ContactLead.created_at.desc()).all()
    return render_template('admin/contacts.html', contacts=contacts)


@admin_bp.route('/campanhas', methods=['GET', 'POST'])
@login_required
def campaigns():
    if request.method == 'POST':
        campaign = WhatsAppCampaign(
            title=request.form.get('title', '').strip(),
            message=request.form.get('message', '').strip(),
            active=True,
            target_tag=request.form.get('target_tag', 'todos').strip() or 'todos',
        )
        db.session.add(campaign)
        db.session.commit()
        flash('Campanha criada.', 'success')
        return redirect(url_for('admin.campaigns'))

    campaigns = WhatsAppCampaign.query.order_by(WhatsAppCampaign.created_at.desc()).all()
    contacts = ContactLead.query.order_by(ContactLead.created_at.desc()).all()
    dispatches = WhatsAppDispatch.query.order_by(WhatsAppDispatch.created_at.desc()).limit(50).all()
    tags = _tag_options()
    settings = SiteSettings.query.first()
    return render_template(
        'admin/campaigns.html',
        campaigns=campaigns,
        contacts=contacts,
        dispatches=dispatches,
        tags=tags,
        settings=settings,
    )


@admin_bp.route('/campanhas/<int:campaign_id>/disparar', methods=['POST'])
@login_required
def trigger_campaign(campaign_id):
    campaign = WhatsAppCampaign.query.get_or_404(campaign_id)
    contacts = ContactLead.query.all()
    try:
        results = send_campaign_messages(campaign, contacts, tag_filter=campaign.target_tag)
        sent = len([r for r in results if r['status'] == 'sent'])
        skipped = len([r for r in results if r['status'] == 'skipped'])
        errors = len([r for r in results if r['status'] == 'error'])
        flash(f'Campanha processada. Enviados: {sent} | Ignorados: {skipped} | Erros: {errors}.', 'success' if errors == 0 else 'warning')
    except WhatsAppConfigError as exc:
        flash(str(exc), 'danger')
    return redirect(url_for('admin.campaigns'))


@admin_bp.route('/campanhas/<int:campaign_id>/excluir', methods=['POST'])
@login_required
def delete_campaign(campaign_id):
    campaign = WhatsAppCampaign.query.get_or_404(campaign_id)
    for dispatch in campaign.dispatches:
        db.session.delete(dispatch)
    db.session.delete(campaign)
    db.session.commit()
    flash('Campanha excluída.', 'success')
    return redirect(url_for('admin.campaigns'))
