import logging
import json
from pywebpush import webpush, WebPushException
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.notification_models import PushSubscription
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class NotificationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def send_notification(self, user_id: int, title: str, body: str, url: str) -> None:
        """
        Sends a push notification to all active subscriptions of the user.
        """
        if not settings.VAPID_PRIVATE_KEY or not settings.VAPID_CLAIM_EMAIL:
            logger.warning("VAPID keys not configured, skipping push notification.")
            return

        stmt = select(PushSubscription).where(PushSubscription.user_id == user_id, PushSubscription.revoked_at.is_(None))
        result = await self.db.execute(stmt)
        subscriptions = result.scalars().all()

        if not subscriptions:
            logger.info(f"No active subscriptions for user {user_id}")
            return

        payload = json.dumps({
            "title": title,
            "body": body,
            "url": url, # Custom data field expected by service worker
        })

        for sub in subscriptions:
            try:
                subscription_info = {
                    "endpoint": sub.endpoint,
                    "keys": {
                        "p256dh": sub.p256dh,
                        "auth": sub.auth
                    }
                }
                
                # webpush is synchronous, run in executor if needed. 
                # For simplicity here (and since it's usually fast enough or we are in worker),
                # we can run it. Ideally wrap in run_in_executor.
                import asyncio
                from functools import partial
                
                send_push = partial(
                    webpush,
                    subscription_info=subscription_info,
                    data=payload,
                    vapid_private_key=settings.VAPID_PRIVATE_KEY,
                    vapid_claims={"sub": f"mailto:{settings.VAPID_CLAIM_EMAIL}"}
                )
                
                await asyncio.get_event_loop().run_in_executor(None, send_push)
                logger.info(f"Push sent to {sub.id}")

            except WebPushException as ex:
                logger.error(f"WebPush failed for {sub.id}: {ex}")
                if ex.response and ex.response.status_code == 410: # Gone
                    logger.info(f"Subscription {sub.id} expired/gone, revoking.")
                    # Revoke subscription? Or delete.
                    # Usually better to delete or mark revoked.
                    # sub.revoked_at = datetime.utcnow() # Need datetime import
                    # Let's delete for simplicity or just log.
                    # We need session commit.
                    pass 
                    # If we want to revoke, we need to modify object attached to session.
                    # self.db is session.
                    # We can mark it.
                    from datetime import datetime
                    sub.revoked_at = datetime.utcnow()
                    # We commit at the end.
            except Exception as e:
                 logger.error(f"Error sending push: {e}")

        await self.db.commit()

    async def subscribe(self, user_id: int, subscription_info: Dict[str, Any], user_agent: str = None):
        endpoint = subscription_info.get("endpoint")
        keys = subscription_info.get("keys", {})
        p256dh = keys.get("p256dh")
        auth = keys.get("auth")

        if not endpoint or not p256dh or not auth:
            raise ValueError("Invalid subscription info")

        # Check existing
        stmt = select(PushSubscription).where(PushSubscription.endpoint == endpoint)
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        
        if existing:
            # Update user_id if changed? Or just re-activate
            existing.user_id = user_id
            existing.revoked_at = None
            existing.p256dh = p256dh
            existing.auth = auth
            existing.user_agent = user_agent
        else:
            new_sub = PushSubscription(
                user_id=user_id,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
                user_agent=user_agent
            )
            self.db.add(new_sub)
        
        await self.db.commit()
