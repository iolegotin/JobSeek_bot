import hashlib
import aioredis


class TGDeduplicator:
    """Сервис для проверки дубликатов сообщений из TG-каналов."""

    def __init__(self, redis_url="redis://localhost"):
        self.redis = aioredis.Redis.from_url(redis_url)

    async def is_duplicate(self, text_post: str, channel_id: int) -> bool:
        """
        Вычисляет хэш текста поста + ID канала и проверяет наличие в Redis.
        
        :param text_post: Текст сообщения
        :param channel_id: ID телеграм-канала
        :return: True если дубль найден, False иначе
        """
        hash_key = hashlib.md5(f"{text_post}{channel_id}".encode()).hexdigest()
        exists = await self.redis.exists(hash_key)
        if exists:
            return True
        
        # Устанавливаем хэш с EXPIRE 7 дней (604800 секунд)
        await self.redis.setex(hash_key, time=604800, value="1")
        return False
