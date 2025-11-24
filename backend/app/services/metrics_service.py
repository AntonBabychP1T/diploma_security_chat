from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.models.chat import Message
from app.models.user import User

class MetricsService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_global_stats(self):
        # Total Users
        user_count = await self.db.scalar(select(func.count(User.id)))
        
        # Total Messages
        message_count = await self.db.scalar(select(func.count(Message.id)))
        
        # Messages with Masking
        # This is tricky with JSON field in SQLite/SQLAlchemy async
        # We'll fetch all messages with metadata and process in python for MVP simplicity
        # For production, use Postgres JSONB operators
        
        result = await self.db.execute(select(Message.meta_data).where(Message.role == 'assistant'))
        meta_datas = result.scalars().all()
        
        masked_count = 0
        total_tokens = 0
        model_usage = {}
        
        for meta in meta_datas:
            if not meta: continue
            
            if meta.get("masked_used"):
                masked_count += 1
                
            usage = meta.get("usage", {})
            total_tokens += usage.get("total_tokens", 0)
            
            model = meta.get("model", "unknown")
            model_usage[model] = model_usage.get(model, 0) + 1
            
        return {
            "total_users": user_count,
            "total_messages": message_count,
            "masked_messages": masked_count,
            "total_tokens": total_tokens,
            "model_usage": model_usage
        }

    async def get_recent_metrics(self, sample_size: int = 100):
        """Return metrics over the most recent assistant messages."""
        # Total messages in system (all roles)
        total_messages = await self.db.scalar(select(func.count(Message.id)))

        # Recent assistant messages for latency/masking stats
        result = await self.db.execute(
            select(Message.meta_data)
            .where(Message.role == "assistant")
            .order_by(Message.created_at.desc())
            .limit(sample_size)
        )
        meta_list = result.scalars().all()

        latencies = []
        masked_count = 0

        for meta in meta_list:
            if not meta:
                continue
            latency = meta.get("latency")
            if isinstance(latency, (int, float)):
                latencies.append(latency)
            if meta.get("masked_used"):
                masked_count += 1

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        return {
            "total_messages": total_messages or 0,
            "recent_avg_latency": avg_latency,
            "recent_masked_count": masked_count,
            "sample_size": len(meta_list)
        }
