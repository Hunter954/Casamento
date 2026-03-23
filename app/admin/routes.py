from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import AdminUser, SiteSettings, RSVP, GuestbookMessage, GiftItem, GiftPurchase, ContactLead, WhatsAppCampaign
from app.utils import save_upload, parse_datetime
from app.services.whatsapp import send_campaign_messages

admin_bp = Blueprint('admin', __name__)


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
    stats = {
        'rsvps': RSVP.query.count(),
        'approved_messages': GuestbookMessage.query.filter_by(approved=True).count(),
        'gifts': GiftItem.query.count(),
        'paid': GiftPurchase.query.filter_by(status='approved').count(),
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

        hero = request.files.get('hero_image')
        banner = request.files.get('gift_banner_image')
        hero_path = save_upload(hero)
        banner_path = save_upload(banner)
        if hero_path:
            settings.hero_image = hero_path
        if banner_path:
            settings.gift_banner_image = banner_path

        db.session.commit()
        flash('Configurações atualizadas.', 'success')
        return redirect(url_for('admin.settings'))
    return render_template('admin/settings.html', settings=settings)


@admin_bp.route('/presentes', methods=['GET', 'POST'])
@login_required
def manage_gifts():
    if request.method == 'POST':
        gift = GiftItem(
            title=request.form.get('title', ''),
            description=request.form.get('description', ''),
            price=float(request.form.get('price', 0) or 0),
            image_url='',
            active=request.form.get('active') == 'on',
        )
        image_file = request.files.get('image_file')
        image_path = save_upload(image_file)
        if image_path:
            gift.image_url = image_path
        db.session.add(gift)
        db.session.commit()
        flash('Presente cadastrado.', 'success')
        return redirect(url_for('admin.manage_gifts'))
    gifts = GiftItem.query.order_by(GiftItem.created_at.desc()).all()
    return render_template('admin/gifts.html', gifts=gifts)


@admin_bp.route('/presentes/<int:gift_id>/toggle')
@login_required
def toggle_gift(gift_id):
    gift = GiftItem.query.get_or_404(gift_id)
    gift.active = not gift.active
    db.session.commit()
    flash('Status do presente atualizado.', 'success')
    return redirect(url_for('admin.manage_gifts'))


@admin_bp.route('/rsvps')
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


@admin_bp.route('/compras')
@login_required
def purchases():
    purchases = GiftPurchase.query.order_by(GiftPurchase.created_at.desc()).all()
    return render_template('admin/purchases.html', purchases=purchases)


@admin_bp.route('/contatos', methods=['GET', 'POST'])
@login_required
def contacts():
    if request.method == 'POST':
        contact = ContactLead(
            name=request.form.get('name', ''),
            phone=request.form.get('phone', ''),
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
            title=request.form.get('title', ''),
            message=request.form.get('message', ''),
            active=True,
        )
        db.session.add(campaign)
        db.session.commit()
        flash('Campanha criada.', 'success')
        return redirect(url_for('admin.campaigns'))
    campaigns = WhatsAppCampaign.query.order_by(WhatsAppCampaign.created_at.desc()).all()
    contacts = ContactLead.query.all()
    return render_template('admin/campaigns.html', campaigns=campaigns, contacts=contacts)


@admin_bp.route('/campanhas/<int:campaign_id>/disparar', methods=['POST'])
@login_required
def trigger_campaign(campaign_id):
    campaign = WhatsAppCampaign.query.get_or_404(campaign_id)
    contacts = ContactLead.query.all()
    results = send_campaign_messages(campaign, contacts)
    sent = len([r for r in results if r[1] == 'sent'])
    skipped = len([r for r in results if r[1] == 'skipped'])
    flash(f'Campanha processada. Enviados: {sent} | Ignorados: {skipped}.', 'success')
    return redirect(url_for('admin.campaigns'))
