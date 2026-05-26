import aioredis
from typing import Optional


class StateManager:
    """Синглтон для управления глобальным статусом системы."""
    
    _instance = None
    
    def __init__(self, redis_url="redis://localhost"):
        self.redis = aioredis.Redis.from_url(redis_url)
        self._state_key = "system_state"
        
    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = StateManager()
        return cls._instance
        
    async def set_stop(self, reason: str = ""):
        """Устанавливает глобальный флаг STOP."""
        await self.redis.set(self._state_key, "STOP")
        
    async def reset_state(self):
        """Сбрасывает состояние системы в нормальное."""
        await self.redis.delete(self._state_key)
        
    async def is_stopped(self) -> bool:
        """Проверяет, находится ли система в режиме STOP."""
        state = await self.redis.get(self._state_key)
        return state == b"STOP"
    
    def get_degradation_message(self) -> str:
        """Возвращает вежливый текст заглушки для пользователей."""
        return "За последние 24 часа новых вакансий не найдено..."


# Пример использования
async def main():
    sm = StateManager.get_instance()
    await sm.set_stop("Database connection failed")
    
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
