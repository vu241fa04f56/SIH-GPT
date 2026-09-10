"""
alert_service.py
────────────────
Firebase Cloud Messaging (FCM) push alert service.

Sends disaster alerts to subscribed devices whenever
the disaster model predicts high-risk conditions.

Requires:
  - FIREBASE_CREDENTIALS_PATH env var pointing to your service account JSON
  - pip install firebase-admin
"""

from __future__ import annotations

import os
from dataclasses import dataclass

from loguru import logger

# ── Firebase init (lazy — only if credentials exist) ─────────────────────────
_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    creds_path = os.getenv("FIREBASE_CREDENTIALS_PATH", "")
    if not creds_path or not os.path.exists(creds_path):
        logger.warning("Firebase credentials not found. Push alerts will be logged only.")
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials
        cred = credentials.Certificate(creds_path)
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("Firebase app initialised.")
    except Exception as exc:
        logger.error(f"Firebase init failed: {exc}")

    return _firebase_app


@dataclass
class DisasterAlert:
    city_name: str
    disaster_type: str
    severity: str
    risk_score: float
    lead_hours: float
    recommended_action: str
    language: str = "en"


async def send_alert_to_token(fcm_token: str, alert: DisasterAlert) -> bool:
    """
    Send a push notification to a single FCM token.

    Returns True if sent successfully (or logged in stub mode).
    """
    app = _get_firebase_app()

    title = f"⚠️ {alert.disaster_type.replace('_', ' ').title()} Alert — {alert.city_name}"
    body = (
        f"Risk: {alert.severity.upper()} ({alert.risk_score:.0%}) | "
        f"Expected in ~{alert.lead_hours:.0f} hours. {alert.recommended_action}"
    )

    if app is None:
        # Stub mode — log instead of sending
        logger.info(f"[STUB ALERT → {fcm_token[:20]}...] {title}: {body}")
        return True

    try:
        from firebase_admin import messaging
        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={
                "city": alert.city_name,
                "disaster_type": alert.disaster_type,
                "severity": alert.severity,
                "risk_score": str(alert.risk_score),
                "lead_hours": str(alert.lead_hours),
            },
            token=fcm_token,
        )
        messaging.send(message)
        logger.info(f"FCM alert sent to {fcm_token[:20]}...")
        return True
    except Exception as exc:
        logger.error(f"FCM send failed: {exc}")
        return False


async def broadcast_disaster_alert(
    subscriptions: list,
    city_name: str,
    disaster_type: str,
    severity: str,
    risk_score: float,
    lead_hours: float = 3.0,
) -> int:
    """
    Send alert to all subscriptions. Returns count of successful sends.
    """
    action_map = {
        "cyclone": "Move to higher ground. Stay indoors. Avoid coastal areas.",
        "flood": "Move to elevated areas. Avoid flooded roads. Listen to IMD alerts.",
        "heavy_rain": "Avoid low-lying areas. Do not drive in flooded streets.",
        "lightning": "Stay indoors. Avoid open fields and tall trees.",
        "earthquake": "Drop, cover, hold on. Move away from buildings after shaking stops.",
        "landslide": "Evacuate slopes immediately. Move to flat ground.",
        "typhoon": "Evacuate if advised. Secure loose objects. Stay away from windows.",
        "severe_wind": "Secure outdoor items. Avoid travel during peak gusts.",
    }
    recommended = action_map.get(disaster_type, "Follow local authority instructions.")

    sent = 0
    for sub in subscriptions:
        alert = DisasterAlert(
            city_name=city_name,
            disaster_type=disaster_type,
            severity=severity,
            risk_score=risk_score,
            lead_hours=lead_hours,
            recommended_action=recommended,
            language=getattr(sub, "language", "en"),
        )
        ok = await send_alert_to_token(sub.fcm_token, alert)
        if ok:
            sent += 1

    logger.info(f"Alerts sent: {sent}/{len(subscriptions)}")
    return sent
