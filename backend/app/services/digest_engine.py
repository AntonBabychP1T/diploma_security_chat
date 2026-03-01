import json
import logging
import re
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
from typing import Any, Dict, List, Literal, Optional
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.models.calendar_event_snapshot import CalendarEventSnapshot
from app.models.chat import Chat
from app.models.digest_models import (
    ActionProposal,
    ActionStatus,
    ActionType,
    DigestRun,
    EmailSnapshot,
    GmailSyncState,
)
from app.models.google_account import GoogleAccount
from app.schemas.chat import ChatCreate
from app.schemas.secretary import CalendarEvent, EmailMessage
from app.services.chat_service import ChatService
from app.services.gmail_sync import GmailSyncService
from app.services.google_auth_service import GoogleAuthService
from app.services.google_workspace import GoogleWorkspaceClient
from app.services.notification_service import NotificationService
from app.providers import ProviderFactory

logger = logging.getLogger(__name__)
settings = get_settings()


class DigestEngine:
    def __init__(self, db: AsyncSession, user_id: int):
        self.db = db
        self.user_id = user_id
        self.provider = ProviderFactory().get_provider("openai")
        self._push_dedup_keys: set[str] = set()

    async def run_digest(self, mode: Literal["poll", "morning", "evening"] = "poll") -> Dict[str, Any]:
        logger.info("Starting digest run for user=%s mode=%s", self.user_id, mode)
        google = await self._get_google_client()
        if not google:
            return {"status": "skipped", "reason": "no_google_account"}

        _, client = google
        sync_state = await self._get_or_create_sync_state()

        if mode == "poll":
            return await self._run_poll_mode(client, sync_state)
        if mode == "morning":
            return await self._run_morning_mode(client, sync_state)
        if mode == "evening":
            return await self._run_evening_mode(client, sync_state)

        return {"status": "failed", "error": f"Unsupported mode: {mode}"}

    async def _run_poll_mode(
        self,
        client: GoogleWorkspaceClient,
        sync_state: GmailSyncState,
    ) -> Dict[str, Any]:
        try:
            emails, start_history_id = await self._sync_emails(
                sync_state,
                access_token=client.access_token,
                lookback_days=1,
            )
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}

        await self._persist_email_snapshots(emails)
        classified_emails = await self._classify_emails(emails)
        important_emails = [item for item in classified_emails if item["important"]]
        calendar_changes = await self._monitor_calendar_changes(client)

        if not important_emails and not calendar_changes:
            return {
                "status": "success",
                "mode": "poll",
                "reason": "no_relevant_changes",
                "emails_scanned": len(emails),
            }

        digest_run = await self._create_digest_run(
            mode="poll",
            start_history_id_used=start_history_id,
            stats={
                "emails_scanned": len(emails),
                "important_emails": len(important_emails),
                "calendar_changes": len(calendar_changes),
            },
        )
        actions = await self._create_poll_actions(digest_run.id, client, classified_emails)
        summary_text = self._build_poll_summary(important_emails, calendar_changes)
        push_title = self._get_poll_push_title(important_emails, calendar_changes)
        await self._publish_digest(
            digest_run=digest_run,
            summary_text=summary_text,
            actions=actions,
            source="gmail_poll",
            push_title=push_title,
            dedup_key=f"digest:{digest_run.id}",
        )
        return {
            "status": "success",
            "mode": "poll",
            "digest_id": digest_run.id,
            "actions_count": len(actions),
            "important_emails": len(important_emails),
            "calendar_changes": len(calendar_changes),
        }

    async def _run_morning_mode(
        self,
        client: GoogleWorkspaceClient,
        sync_state: GmailSyncState,
    ) -> Dict[str, Any]:
        try:
            emails, start_history_id = await self._sync_emails(
                sync_state,
                access_token=client.access_token,
                lookback_days=1,
            )
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}

        await self._persist_email_snapshots(emails)
        classified_emails = await self._classify_emails(emails)
        important_emails = [item for item in classified_emails if item["important"]]
        today_start, today_end = self._local_day_window_utc(day_offset=0)
        events_today = await client.list_events(today_start, today_end, include_cancelled=False)

        digest_run = await self._create_digest_run(
            mode="morning",
            start_history_id_used=start_history_id,
            stats={
                "emails_scanned": len(emails),
                "important_emails": len(important_emails),
                "events_today": len(events_today),
            },
        )
        summary_text = self._build_morning_summary(important_emails, events_today)
        await self._publish_digest(
            digest_run=digest_run,
            summary_text=summary_text,
            actions=[],
            source="morning_plan",
            push_title="Ранковий план дня",
            dedup_key=f"digest:{digest_run.id}",
        )
        return {
            "status": "success",
            "mode": "morning",
            "digest_id": digest_run.id,
            "events_today": len(events_today),
            "important_emails": len(important_emails),
        }

    async def _run_evening_mode(
        self,
        client: GoogleWorkspaceClient,
        sync_state: GmailSyncState,
    ) -> Dict[str, Any]:
        try:
            emails, start_history_id = await self._sync_emails(
                sync_state,
                access_token=client.access_token,
                lookback_days=1,
            )
        except Exception as exc:
            return {"status": "failed", "error": str(exc)}

        await self._persist_email_snapshots(emails)
        classified_emails = await self._classify_emails(emails)
        important_emails = [item for item in classified_emails if item["important"]]
        today_start, today_end = self._local_day_window_utc(day_offset=0)
        tomorrow_start, tomorrow_end = self._local_day_window_utc(day_offset=1)
        events_today = await client.list_events(today_start, today_end, include_cancelled=False)
        events_tomorrow = await client.list_events(tomorrow_start, tomorrow_end, include_cancelled=False)
        pending_actions = await self._get_pending_actions()

        digest_run = await self._create_digest_run(
            mode="evening",
            start_history_id_used=start_history_id,
            stats={
                "emails_scanned": len(emails),
                "important_emails": len(important_emails),
                "events_today": len(events_today),
                "events_tomorrow": len(events_tomorrow),
                "pending_actions": len(pending_actions),
            },
        )
        summary_text = self._build_evening_summary(
            important_emails=important_emails,
            events_today=events_today,
            events_tomorrow=events_tomorrow,
            pending_actions=pending_actions,
        )
        await self._publish_digest(
            digest_run=digest_run,
            summary_text=summary_text,
            actions=[],
            source="evening_summary",
            push_title="Вечірній підсумок і план на завтра",
            dedup_key=f"digest:{digest_run.id}",
        )
        return {
            "status": "success",
            "mode": "evening",
            "digest_id": digest_run.id,
            "events_today": len(events_today),
            "events_tomorrow": len(events_tomorrow),
            "pending_actions": len(pending_actions),
        }

    async def _get_google_client(self) -> Optional[tuple[GoogleAccount, GoogleWorkspaceClient]]:
        stmt = select(GoogleAccount).where(GoogleAccount.user_id == self.user_id)
        account = (await self.db.execute(stmt)).scalar_one_or_none()
        if not account:
            return None

        access_token = account.access_token
        if account.refresh_token:
            token_info = await GoogleAuthService.refresh_access_token(account.refresh_token)
            access_token = token_info["access_token"]
            account.access_token = access_token
            await self.db.commit()

        if not access_token:
            return None
        return account, GoogleWorkspaceClient(access_token)

    async def _get_or_create_sync_state(self) -> GmailSyncState:
        stmt = select(GmailSyncState).where(GmailSyncState.user_id == self.user_id)
        sync_state = (await self.db.execute(stmt)).scalar_one_or_none()
        if sync_state:
            return sync_state

        sync_state = GmailSyncState(user_id=self.user_id, last_history_id=None)
        self.db.add(sync_state)
        await self.db.commit()
        await self.db.refresh(sync_state)
        return sync_state

    async def _sync_emails(
        self,
        sync_state: GmailSyncState,
        access_token: str,
        lookback_days: int,
    ) -> tuple[List[EmailMessage], Optional[int]]:
        sync_service = GmailSyncService(access_token)
        start_history_id_used = sync_state.last_history_id
        try:
            if sync_state.last_history_id:
                emails, new_history_id, expired = await sync_service.sync_incremental(sync_state.last_history_id)
                if expired:
                    emails, new_history_id = await sync_service.sync_full(lookback_days=lookback_days)
            else:
                emails, new_history_id = await sync_service.sync_full(lookback_days=lookback_days)

            sync_state.last_history_id = new_history_id
            sync_state.last_success_at = datetime.utcnow()
            sync_state.error_streak = 0
            sync_state.last_error = None
            await self.db.commit()
            return emails, start_history_id_used
        except Exception as exc:
            sync_state.error_streak += 1
            sync_state.last_error = str(exc)
            await self.db.commit()
            logger.error("Email sync failed for user=%s: %s", self.user_id, exc)
            raise

    async def _persist_email_snapshots(self, emails: List[EmailMessage]) -> None:
        if not emails:
            return

        message_ids = [email.id for email in emails]
        stmt_existing = select(EmailSnapshot.gmail_message_id).where(
            EmailSnapshot.user_id == self.user_id,
            EmailSnapshot.gmail_message_id.in_(message_ids),
        )
        existing_ids = set((await self.db.execute(stmt_existing)).scalars().all())

        for email in emails:
            if email.id in existing_ids:
                continue
            labels_set = set(email.label_ids or [])
            snapshot = EmailSnapshot(
                user_id=self.user_id,
                gmail_message_id=email.id,
                thread_id=email.thread_id,
                sender=email.sender,
                subject=email.subject,
                snippet=email.snippet,
                internal_date=int(self._to_utc_naive(email.date).timestamp() * 1000),
                label_ids=list(labels_set),
                category=self._email_category(labels_set),
            )
            self.db.add(snapshot)
        await self.db.commit()

    async def _classify_emails(self, emails: List[EmailMessage]) -> List[Dict[str, Any]]:
        classified: List[Dict[str, Any]] = []
        for email in emails:
            text = f"{email.subject} {email.snippet}".lower()
            labels = set(email.label_ids or [])
            important = bool(labels.intersection({"IMPORTANT", "STARRED", "CATEGORY_PERSONAL"})) or bool(
                re.search(r"\b(urgent|asap|deadline|important|action required)\b", text)
            )
            meeting_invite = bool(
                re.search(r"\b(meeting|invite|invitation|calendar|schedule|zoom|teams)\b", text)
            )
            classified.append(
                {
                    "email": email,
                    "important": important or meeting_invite,
                    "meeting_invite": meeting_invite,
                    "reason": "heuristic",
                }
            )

        llm_flags = await self._classify_with_llm(classified)
        for item in classified:
            llm_item = llm_flags.get(item["email"].id)
            if not llm_item:
                continue
            item["important"] = item["important"] or llm_item.get("important", False)
            item["meeting_invite"] = item["meeting_invite"] or llm_item.get("meeting_invite", False)
            if llm_item.get("reason"):
                item["reason"] = llm_item["reason"]
        return classified

    async def _classify_with_llm(self, classified_emails: List[Dict[str, Any]]) -> Dict[str, Dict[str, Any]]:
        if not classified_emails:
            return {}
        sample = []
        for item in classified_emails[:20]:
            email: EmailMessage = item["email"]
            sample.append(
                {
                    "id": email.id,
                    "sender": email.sender,
                    "subject": email.subject,
                    "snippet": email.snippet,
                }
            )
        prompt = (
            "Classify emails for notification urgency.\n"
            "Return strict JSON object: {'items':[{'id':'...','important':true/false,'meeting_invite':true/false,'reason':'...'}]}.\n"
            f"Emails: {json.dumps(sample, ensure_ascii=False)}"
        )
        try:
            response = await self.provider.generate(
                [{"role": "user", "content": prompt}],
                options={"model": "gpt-5-mini", "response_format": {"type": "json_object"}},
            )
            payload = json.loads(response.content or "{}")
            output: Dict[str, Dict[str, Any]] = {}
            for entry in payload.get("items", []):
                email_id = entry.get("id")
                if not email_id:
                    continue
                output[email_id] = {
                    "important": bool(entry.get("important")),
                    "meeting_invite": bool(entry.get("meeting_invite")),
                    "reason": entry.get("reason", ""),
                }
            return output
        except Exception as exc:
            logger.warning("LLM classification failed for user=%s: %s", self.user_id, exc)
            return {}

    async def _monitor_calendar_changes(self, client: GoogleWorkspaceClient) -> List[Dict[str, Any]]:
        now = datetime.utcnow()
        window_start = now - timedelta(hours=1)
        window_end = now + timedelta(hours=48)
        events = await client.list_events(window_start, window_end, include_cancelled=True)

        stmt = select(CalendarEventSnapshot).where(CalendarEventSnapshot.user_id == self.user_id)
        existing_rows = (await self.db.execute(stmt)).scalars().all()
        existing_map = {row.event_id: row for row in existing_rows}

        changes: List[Dict[str, Any]] = []
        for event in events:
            event_status = (event.status or "confirmed").lower()
            fingerprint = self._calendar_fingerprint(event)
            existing = existing_map.get(event.id)

            change_type: Optional[str] = None
            if existing is None:
                snapshot = CalendarEventSnapshot(
                    user_id=self.user_id,
                    event_id=event.id,
                    updated_fingerprint=fingerprint,
                    status=event_status,
                    last_seen_at=datetime.utcnow(),
                )
                self.db.add(snapshot)
                change_type = "cancelled" if event_status == "cancelled" else "created"
            else:
                if existing.updated_fingerprint != fingerprint or existing.status != event_status:
                    change_type = "cancelled" if event_status == "cancelled" else "updated"
                existing.updated_fingerprint = fingerprint
                existing.status = event_status
                existing.last_seen_at = datetime.utcnow()

            if change_type and self._is_important_calendar_change(event, change_type):
                changes.append({"change_type": change_type, "event": event})

        await self.db.commit()
        return changes

    def _is_important_calendar_change(self, event: CalendarEvent, change_type: str) -> bool:
        if change_type in {"created", "cancelled"}:
            return True
        start_dt = self._to_utc_naive(event.start)
        return start_dt <= datetime.utcnow() + timedelta(days=2)

    def _calendar_fingerprint(self, event: CalendarEvent) -> str:
        payload = {
            "summary": event.summary,
            "start": self._to_utc_naive(event.start).isoformat(),
            "end": self._to_utc_naive(event.end).isoformat(),
            "location": event.location or "",
            "description": event.description or "",
            "attendees": sorted(event.attendees or []),
            "status": event.status or "confirmed",
            "updated": self._to_utc_naive(event.updated).isoformat() if event.updated else "",
        }
        return sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    async def _create_poll_actions(
        self,
        digest_id: int,
        client: GoogleWorkspaceClient,
        classified_emails: List[Dict[str, Any]],
    ) -> List[ActionProposal]:
        actions: List[ActionProposal] = []
        invite_count = 0
        draft_count = 0
        for item in classified_emails:
            email: EmailMessage = item["email"]
            if item.get("meeting_invite") and invite_count < 3:
                slots = await self._suggest_slots(client)
                payload = {
                    "summary": f"Meeting: {email.subject}",
                    "source_message_id": email.id,
                    "attendees": self._extract_emails_from_text(f"{email.sender} {email.snippet}"),
                    "suggested_slots": slots,
                }
                if slots:
                    payload["proposed_start_time"] = slots[0]["start_time"]
                    payload["proposed_end_time"] = slots[0]["end_time"]
                    payload["start_time"] = slots[0]["start_time"]
                    payload["end_time"] = slots[0]["end_time"]
                proposal = ActionProposal(
                    digest_id=digest_id,
                    user_id=self.user_id,
                    type=ActionType.CREATE_EVENT.value,
                    payload_json=payload,
                    status=ActionStatus.PENDING.value,
                )
                self.db.add(proposal)
                actions.append(proposal)
                invite_count += 1
                continue

            if item.get("important") and draft_count < 2 and re.search(r"\b(reply|respond|feedback|confirm)\b", email.snippet.lower()):
                sender_candidates = self._extract_emails_from_text(email.sender)
                if not sender_candidates:
                    continue
                draft_payload = {
                    "to": sender_candidates,
                    "subject": f"Re: {email.subject}",
                    "body": "Дякую за лист. Повернуся з відповіддю найближчим часом.",
                    "source_message_id": email.id,
                }
                proposal = ActionProposal(
                    digest_id=digest_id,
                    user_id=self.user_id,
                    type=ActionType.CREATE_DRAFT.value,
                    payload_json=draft_payload,
                    status=ActionStatus.PENDING.value,
                )
                self.db.add(proposal)
                actions.append(proposal)
                draft_count += 1

        await self.db.commit()
        for action in actions:
            await self.db.refresh(action)
        return actions

    async def _suggest_slots(self, client: GoogleWorkspaceClient) -> List[Dict[str, str]]:
        window_start = datetime.utcnow()
        window_end = datetime.utcnow() + timedelta(days=2)
        slots = await client.find_free_slots(window_start, window_end, duration_minutes=30)
        suggestions = []
        for slot in slots[:3]:
            suggestions.append(
                {
                    "start_time": self._to_utc_naive(slot.start).isoformat(),
                    "end_time": self._to_utc_naive(slot.end).isoformat(),
                }
            )
        return suggestions

    async def _create_digest_run(
        self,
        mode: str,
        start_history_id_used: Optional[int],
        stats: Dict[str, int],
    ) -> DigestRun:
        now = datetime.utcnow()
        if mode == "poll":
            period_start = now - timedelta(hours=1)
        else:
            period_start = now - timedelta(hours=12)
        digest_run = DigestRun(
            user_id=self.user_id,
            period_start=period_start,
            period_end=now,
            start_history_id_used=start_history_id_used,
            stats={**stats, "mode": mode},  # type: ignore[arg-type]
            status="SUCCESS",
        )
        self.db.add(digest_run)
        await self.db.commit()
        await self.db.refresh(digest_run)
        return digest_run

    async def _publish_digest(
        self,
        digest_run: DigestRun,
        summary_text: str,
        actions: List[ActionProposal],
        source: str,
        push_title: str,
        dedup_key: str,
    ) -> None:
        chat = await self._get_or_create_digest_chat()
        chat_service = ChatService(self.db, self.user_id)

        metadata_actions = [
            {
                "id": action.id,
                "type": str(action.type),
                "payload": action.payload_json,
                "status": str(action.status),
            }
            for action in actions
        ]
        message = await chat_service.create_system_message(
            chat_id=chat.id,
            content=summary_text,
            source=source,
            metadata={
                "digest_id": digest_run.id,
                "actions": metadata_actions,
                "stats": digest_run.stats,
            },
        )

        digest_run.created_chat_id = chat.id
        digest_run.created_message_id = message.id
        await self.db.commit()

        body = summary_text.strip().splitlines()[0] if summary_text.strip() else "Є нові оновлення."
        await self._send_push_notification(
            title=push_title,
            body=body[:160],
            chat_id=chat.id,
            dedup_key=dedup_key,
        )

    async def _send_push_notification(self, title: str, body: str, chat_id: int, dedup_key: str) -> None:
        if dedup_key in self._push_dedup_keys:
            return
        self._push_dedup_keys.add(dedup_key)

        notification_service = NotificationService(self.db)
        url = f"{settings.FRONTEND_PUBLIC_URL.rstrip('/')}/chats/{chat_id}"
        await notification_service.send_notification(self.user_id, title, body, url)

    async def _get_or_create_digest_chat(self) -> Chat:
        stmt = select(Chat).where(Chat.user_id == self.user_id, Chat.title == "Inbox Digest (Google)")
        existing = (await self.db.execute(stmt)).scalar_one_or_none()
        if existing:
            return existing
        service = ChatService(self.db, self.user_id)
        return await service.create_chat(ChatCreate(title="Inbox Digest (Google)"))

    async def _get_pending_actions(self) -> List[ActionProposal]:
        stmt = select(ActionProposal).where(
            ActionProposal.user_id == self.user_id,
            ActionProposal.status == ActionStatus.PENDING.value,
        )
        return (await self.db.execute(stmt)).scalars().all()

    def _build_poll_summary(
        self,
        important_emails: List[Dict[str, Any]],
        calendar_changes: List[Dict[str, Any]],
    ) -> str:
        lines = ["Оновлення за останню перевірку:"]
        if important_emails:
            lines.append("")
            lines.append("Важливі листи:")
            for item in important_emails[:5]:
                email: EmailMessage = item["email"]
                marker = " (meeting invite)" if item.get("meeting_invite") else ""
                lines.append(f"- {email.subject} — {email.sender}{marker}")
        if calendar_changes:
            lines.append("")
            lines.append("Зміни в календарі:")
            for change in calendar_changes[:5]:
                event: CalendarEvent = change["event"]
                lines.append(f"- [{change['change_type']}] {event.summary} ({self._to_utc_naive(event.start).strftime('%Y-%m-%d %H:%M')} UTC)")
        return "\n".join(lines)

    def _build_morning_summary(self, important_emails: List[Dict[str, Any]], events_today: List[CalendarEvent]) -> str:
        lines = ["Ранковий план дня:"]
        if events_today:
            lines.append("")
            lines.append("Події на сьогодні:")
            for event in sorted(events_today, key=lambda ev: self._to_utc_naive(ev.start))[:8]:
                lines.append(f"- {event.summary} ({self._to_utc_naive(event.start).strftime('%H:%M')} UTC)")
        else:
            lines.append("- У календарі сьогодні подій не знайдено.")

        if important_emails:
            lines.append("")
            lines.append("Важливі листи:")
            for item in important_emails[:5]:
                email: EmailMessage = item["email"]
                lines.append(f"- {email.subject} — {email.sender}")
        else:
            lines.append("")
            lines.append("Немає нових важливих листів.")
        return "\n".join(lines)

    def _build_evening_summary(
        self,
        important_emails: List[Dict[str, Any]],
        events_today: List[CalendarEvent],
        events_tomorrow: List[CalendarEvent],
        pending_actions: List[ActionProposal],
    ) -> str:
        lines = ["Вечірній підсумок:"]
        lines.append(f"- Подій сьогодні: {len(events_today)}")
        lines.append(f"- Важливих листів за день: {len(important_emails)}")
        lines.append(f"- Невиконаних дій: {len(pending_actions)}")

        lines.append("")
        lines.append("План на завтра:")
        if events_tomorrow:
            for event in sorted(events_tomorrow, key=lambda ev: self._to_utc_naive(ev.start))[:8]:
                lines.append(f"- {event.summary} ({self._to_utc_naive(event.start).strftime('%H:%M')} UTC)")
        else:
            lines.append("- Наразі подій у календарі на завтра немає.")
        return "\n".join(lines)

    def _get_poll_push_title(
        self,
        important_emails: List[Dict[str, Any]],
        calendar_changes: List[Dict[str, Any]],
    ) -> str:
        if any(item.get("meeting_invite") for item in important_emails):
            return "Важливий лист із запрошенням"
        if important_emails:
            return "Новий важливий лист"
        if calendar_changes:
            return "Зміни у вашому календарі"
        return "Нові оновлення"

    def _email_category(self, labels_set: set[str]) -> str:
        if "CATEGORY_PROMOTIONS" in labels_set:
            return "PROMO"
        if labels_set.intersection({"IMPORTANT", "STARRED", "CATEGORY_PERSONAL"}):
            return "IMPORTANT"
        return "OTHER"

    def _extract_emails_from_text(self, text: str) -> List[str]:
        candidates = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text or "")
        return list(dict.fromkeys(candidates))

    def _local_day_window_utc(self, day_offset: int) -> tuple[datetime, datetime]:
        tz = ZoneInfo(settings.SCHEDULER_TIMEZONE)
        now_local = datetime.now(tz)
        target_date = now_local.date() + timedelta(days=day_offset)
        start_local = datetime.combine(target_date, time.min, tzinfo=tz)
        end_local = datetime.combine(target_date, time.max, tzinfo=tz)
        start_utc = start_local.astimezone(timezone.utc).replace(tzinfo=None)
        end_utc = end_local.astimezone(timezone.utc).replace(tzinfo=None)
        return start_utc, end_utc

    def _to_utc_naive(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value
        return value.astimezone(timezone.utc).replace(tzinfo=None)
