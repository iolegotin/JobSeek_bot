import aiogram


class AlertService:
    """Сервис для централизованной отправки алертов администратору через Telegram."""
    
    def __init__(self, admin_tg_id: int):
        self.admin_tg_id = admin_tg_id
        
    async def send_alert(self, severity: str, error_type: str, traceback: str = ""):
        """Отправка форматированного алерта админу."""
        message = f"🚨 {severity}\nТип: {error_type}\nTraceback:\n{traceback}"
        try:
            bot = aiogram.Bot("YOUR_TG_BOT_TOKEN")
            await bot.send_message(
                self.admin_tg_id,
                message,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Не удалось отправить алерт админу: {e}")


# Пример использования
async def main():
    alert_svc = AlertService(admin_tg_id=-123456789)
    await alert_svc.send_alert(
        severity="CRITICAL", 
        error_type="Database Connection Refused"
    )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
