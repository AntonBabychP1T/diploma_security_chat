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
        model_usage = {}

        for meta in meta_list:
            if not meta:
                continue
            latency = meta.get("latency")
            if isinstance(latency, (int, float)):
                latencies.append(latency)
            if meta.get("masked_used"):
                masked_count += 1
            
            # Track model usage
            model = meta.get("model", "unknown")
            model_usage[model] = model_usage.get(model, 0) + 1

        avg_latency = sum(latencies) / len(latencies) if latencies else 0.0

        return {
            "total_messages": total_messages or 0,
            "recent_avg_latency": avg_latency,
            "recent_masked_count": masked_count,
            "sample_size": len(meta_list),
            "model_usage": model_usage
        }

    async def get_model_leaderboard(self):
        """Aggregate votes from message metadata to show model performance."""
        # Fetch all messages with 'vote' in metadata
        # In a real DB we'd use JSON operators. Here we fetch assistant messages and filter in python.
        result = await self.db.execute(
            select(Message.meta_data).where(Message.role == "assistant")
        )
        meta_list = result.scalars().all()
        
        leaderboard = {}
        
        for meta in meta_list:
            if not meta: continue
            
            model = meta.get("model", "unknown")
            vote = meta.get("vote")
            
            if model not in leaderboard:
                leaderboard[model] = {"votes": 0, "wins": 0, "losses": 0, "ties": 0}
                
            if vote:
                leaderboard[model]["votes"] += 1
                if vote == "better":
                    leaderboard[model]["wins"] += 1
                elif vote == "worse":
                    leaderboard[model]["losses"] += 1
                elif vote == "tie":
                    leaderboard[model]["ties"] += 1
                    
        # Calculate win rate
        stats = []
        for model, data in leaderboard.items():
            total_votes = data["votes"]
            if total_votes > 0:
                win_rate = (data["wins"] / total_votes) * 100
                stats.append({
                    "model": model,
                    "win_rate": round(win_rate, 1),
                    "votes": total_votes,
                    "wins": data["wins"]
                })
                
        # Sort by win rate desc
        stats.sort(key=lambda x: x["win_rate"], reverse=True)
        return stats
