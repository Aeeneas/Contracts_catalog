import json
import requests
from typing import Dict, Any, Optional
from config import settings

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

def _call_deepseek(prompt: str, json_mode: bool = False) -> Optional[str]:
    """Внутренняя функция для вызова DeepSeek API."""
    if not settings.DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY is not configured.")
        return None

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": "You are a helpful assistant that extracts data from contracts."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 2000
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        response = requests.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=60)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling DeepSeek API: {e}")
        return None

def extract_contract_data(contract_text: str) -> Dict[str, Any]:
    """
    Извлекает структурированные данные из договора с помощью DeepSeek.
    """
    prompt = f"""
    Извлеки следующую информацию из текста договора и верни JSON.
    Если не найдено, используй null.
    
    Поля JSON:
    - company: (одно из: ТОР-ЛИФТ, Противовес, Противовес-Т)
    - customer: Полное наименование заказчика
    - work_type: (одно из: ТО, МОНТАЖ, СТРОЙКА, ПРОЕКТИРОВАНИЕ, КАПИТАЛЬНЫЕ РАБОТЫ)
    - contract_cost: Общая стоимость (число)
    - conclusion_date: Дата заключения (YYYY-MM-DD)
    - monthly_cost: Ежемесячная стоимость (число или null)
    - start_date: Дата начала (YYYY-MM-DD)
    - end_date: Дата окончания (YYYY-MM-DD)
    - stages_info: Информация об этапах (строка или null)
    
    Текст договора:
    {contract_text}
    """
    
    response_text = _call_deepseek(prompt, json_mode=True)
    if response_text:
        try:
            return json.loads(response_text)
        except Exception as e:
            print(f"Error parsing JSON: {e}")
            return {"error": "Failed to parse AI response."}
    return {"error": "No response from AI."}

def summarize_contract(contract_text: str) -> Optional[str]:
    """Создает резюме договора."""
    prompt = f"Напиши краткое и информативное резюме договора (стороны, предмет, цена, сроки): {contract_text}"
    return _call_deepseek(prompt)
