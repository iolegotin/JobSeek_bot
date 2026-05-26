from app.core.services.tg_deduplicator import TGDeduplicator


class TGChannelHandler:
    """Обработчик сообщений из телеграм-каналов с логикой исключения дублей."""

    def __init__(self):
        self.deduplicator = TGDeduplicator()
        self.last_max_id = 0  # Для инкрементальной обработки

    async def process_message(self, text_post: str, channel_id: int):
        """
        Обрабатывает сообщение из TG-канала, проверяет на дубликаты и сохраняет в ORM.
        
        :param text_post: Текст сообщения
        :param channel_id: ID телеграм-канала
        """
        if await self.deduplicator.is_duplicate(text_post, channel_id):
            print(f"Duplicate detected for channel {channel_id}, ignoring.")
            return None
        
        # Логика сохранения в ORM (например, через SQLAlchemy или Tortoise)
        # vacancy = VacancyModel(text=text_post, source="tg", channel_id=channel_id)
        # await vacancy.save()

    async def fetch_incremental(self):
        """Формирование инкрементальных пакетов данных для снижения нагрузки на сеть."""
        # Пример получения новых сообщений начиная с last_max_id
        pass
