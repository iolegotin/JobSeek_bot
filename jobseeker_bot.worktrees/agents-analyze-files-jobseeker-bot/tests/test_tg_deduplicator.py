import unittest
from unittest.mock import patch


class TestTGDeduplicator(unittest.TestCase):
    @patch('app.core.services.tg_deduplicator.aioredis')
    def test_is_duplicate_existing_hash(self, mock_aioredis_module):
        """Тест проверяет, что существующий хэш в Redis возвращает True."""
        # Настраиваем мок для экземпляра Redis
        mock_redis_instance = unittest.mock.MagicMock()
        mock_aioredis_module.Redis.from_url.return_value = mock_redis_instance

        from app.core.services.tg_deduplicator import TGDeduplicator
        dedup = TGDeduplicator(redis_url="redis://fake")

        # При вызове exists() возвращаем 1 (хэш есть)
        mock_redis_instance.exists.return_value = 1 

        result = dedup.is_duplicate("some text", 123)
        self.assertTrue(result)

    @patch('app.core.services.tg_deduplicator.aioredis')
    def test_is_duplicate_new_hash(self, mock_aioredis_module):
        """Тест проверяет, что новый хэш устанавливается в Redis и возвращает False."""
        # Настраиваем мок для экземпляра Redis
        mock_redis_instance = unittest.mock.MagicMock()
        mock_aioredis_module.Redis.from_url.return_value = mock_redis_instance

        from app.core.services.tg_deduplicator import TGDeduplicator
        dedup = TGDeduplicator(redis_url="redis://fake")

        # При вызове exists() возвращаем 0 (хэша нет)
        mock_redis_instance.exists.return_value = 0 

        result = dedup.is_duplicate("some text", 123)
        self.assertFalse(result)
        
        # Проверяем, что setex был вызван с правильными параметрами
        mock_redis_instance.setex.assert_called_once()
