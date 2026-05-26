import litellm
from typing import Dict, Any


def build_system_prompt(query_text: str, weights_config: dict) -> str:
    """Сборка динамического системного промпта."""
    return f"""You are a helpful assistant analyzing job vacancies.

Query Text: {query_text}
Weights Config: {weights_config}

Please analyze the vacancy and provide a JSON response with the following structure:
{{
  "score": float (0.0 to 1.0),
  "reasons": ["string", ...],
  "updated_weights_suggestion": {{}}
}}
"""


async def get_vacancy_score(query_text: str, weights_config: dict) -> Dict[str, Any]:
    """Асинхронная обёртка для вызова модели через LiteLLM."""
    system_prompt = build_system_prompt(query_text, weights_config)

    # Вызов модели (здесь нужно замокать в тестах)
    response = await litellm.completion(
        model="gpt-3.5-turbo",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": query_text}],
        timeout=10,
    )

    # Валидация JSON ответа
    try:
        result = response.choices[0].message.content

        import json
        parsed_data = json.loads(result)

        # Проверка структуры
        if not isinstance(parsed_data.get("score"), (int, float)):
            raise ValueError("Score must be a number.")
        if not 0.0 <= parsed_data["score"] <= 1.0:
            raise ValueError("Score must be between 0.0 and 1.0.")

        if not isinstance(parsed_data.get("reasons"), list):
            raise ValueError("Reasons must be a list of strings.")

        if not isinstance(parsed_data.get("updated_weights_suggestion"), dict):
            raise ValueError("Updated weights suggestion must be a dictionary.")

        return parsed_data

    except json.JSONDecodeError:
        raise ValueError("Model returned invalid JSON structure.")


# ...
