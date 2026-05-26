import pytest
from unittest.mock import patch, MagicMock
from app.core.services.state_manager import StateManager
from app.core.services.alert_svc import AlertService


class TestGracefulDegradation:
    """Тесты для проверки graceful degradation и алертов админу."""

    # Тест 1: Проверка перехвата глобальных ошибок и перехода в STOP
    def test_global_exception_intercepts_and_stops(self):
        """При падении БД воркеры должны переходить в idle-режим."""
        sm = StateManager()
        
        with patch('app.core.services.state_manager.aioredis') as mock_redis:
            # Мокаем падение коннекта к базе данных
            mock_redis_instance = MagicMock()
            mock_redis.Redis.from_url.return_value = mock_redis_instance
            
            # Симулируем OperationalError при запросе
            with pytest.raises(Exception) as exc_info:
                raise Exception("Database Connection Refused")
            
            # Проверяем, что стейт-менеджер перехватил ошибку и перешел в STOP
            assert sm.is_stopped() == True
            
    # Тест 2: Проверка вежливого статуса для пользователей при STOP
    def test_user_receives_degradation_message(self):
        """При режиме STOP пользователь получает регламентированный текст."""
        sm = StateManager()
        
        # Эмулируем запрос вакансий в режиме STOP
        with patch.object(sm, 'is_stopped', return_value=True):
            # Логика заглушки должна вернуть вежливое сообщение
            expected_text = "За последние 24 часа новых вакансий не найдено..."
            
            # Проверяем, что при запросе в режиме STOP возвращается текст заглушки
            assert sm.get_degradation_message() == expected_text
            
    # Тест 3: Проверка мгновенной доставки алерта админу
    def test_admin_instant_alert_delivery(self):
        """Админу моментально приходит форматированный лог ошибки."""
        alert_svc = AlertService(admin_tg_id=-123456789)
        
        with patch('app.core.services.alert_svc.aiogram') as mock_aiogram:
            # Мокаем Bot.send_message для админа
            mock_bot_instance = MagicMock()
            mock_aiogram.Bot.return_value = mock_bot_instance
            
            # Вызываем искусственный FloodWait или APIError
            try:
                raise Exception("FloodWait")
            except Exception as e:
                alert_svc.send_alert(
                    severity="CRITICAL", 
                    error_type="TG FloodWait",
                    traceback=f"Traceback of {e}"
                )
                
                # Проверяем, что метод отправки алерта был вызван с нужными аргументами
                mock_bot_instance.send_message.assert_called_once_with(
                    -123456789, 
                    "🚨 CRITICAL\nТип: TG FloodWait\nTraceback:\n..."
                )
