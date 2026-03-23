from datetime import datetime
from app import db
from app.models import WhatsAppDispatch


def send_campaign_messages(campaign, contacts):
    results = []
    for contact in contacts:
        existing = WhatsAppDispatch.query.filter_by(campaign_id=campaign.id, contact_id=contact.id).first()
        if existing and existing.status == 'sent':
            results.append((contact.phone, 'skipped'))
            continue
        if not existing:
            existing = WhatsAppDispatch(campaign_id=campaign.id, contact_id=contact.id)
            db.session.add(existing)
        existing.status = 'sent'
        existing.sent_at = datetime.utcnow()
        results.append((contact.phone, 'sent'))
    db.session.commit()
    return results
