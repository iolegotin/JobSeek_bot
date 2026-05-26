import httpx


class HHAsyncClient:
    """Асинхронный клиент для работы с API HeadHunter."""

    def __init__(self, base_url="https://api.hh.ru"):
        self.base_url = base_url

    async def fetch_vacancies(self, keyword):
        """
        Делает асинхронный запрос к API HH.ru и возвращает сырые данные вакансий.
        
        :param keyword: Строка для поиска (текст вакансии)
        :return: Сырой JSON-ответ (словарь)
        """
        params = {
            "text": keyword, 
            "order_by": "relevance",
            "per_page": 10
        }

        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/vacancies", 
                params=params
            )

            if response.status_code != 200:
                raise Exception(f"API Error: {response.status_code}")
            
            return response.json()


# Пример использования (если запускать напрямую):
if __name__ == "__main__":
    import asyncio
    
    async def main():
        client = HHAsyncClient()
        try:
            data = await client.fetch_vacancies("python")
            print(f"Найдено вакансий: {data.get('count', 0)}")
        except Exception as e:
            print(f"Ошибка: {e}")

    asyncio.run(main())
