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
            {
                "role": "system", 
                "content": "You are a strict data extraction expert. Your task is to extract information from contracts with 100% accuracy. NEVER invent, guess, or assume information. If a field is not explicitly stated in the text, return null for that field. Do not provide explanations, only the JSON object."
            },
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
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
    ### ИНСТРУКЦИЯ:
    Извлеки данные из следующего текста договора. 
    ПРАВИЛА:
    1. Если точное значение поля отсутствует в тексте, ВСЕГДА возвращай null.
    2. НЕ ПРИДУМЫВАЙ, не догадывайся и не додумывай информацию.
    3. Для поля 'company' выбирай СТРОГО из: ТОР-ЛИФТ, Противовес, Противовес-Т. Если нет точного совпадения - null.
    4. Для поля 'work_type' выбирай СТРОГО из: ТО, МОНТАЖ, СТРОЙКА, ПРОЕКТИРОВАНИЕ, КАПИТАЛЬНЫЕ РАБОТЫ. Если нет точного совпадения - null.
    5. Формат JSON.

    Поля JSON:
    - doc_type: (ДОГ | ДС | АКТ | КС-2 | КС-3) - тип документа
    - company: (ТОР-ЛИФТ | Противовес | Противовес-Т | null)
    - customer: Полное наименование заказчика (строка | null)
    - work_type: (ТО | МОНТАЖ | СТРОЙКА | ПРОЕКТИРОВАНИЕ | КАПИТАЛЬНЫЕ РАБОТЫ | null)
    - contract_cost: Общая стоимость договора (число | null)
    - conclusion_date: Дата заключения договора (YYYY-MM-DD | null)
    - monthly_cost: Ежемесячная стоимость ТО (число | null)
    - start_date: Дата начала работ (YYYY-MM-DD | null)
    - end_date: Дата окончания работ (YYYY-MM-DD | null)
    - stages_info: Информация об этапах работ (строка | null)
    
    Текст договора:
    ---
    {contract_text}
    ---
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
    """Создает человекочитаемое резюме договора."""
    prompt = f"""
    Напиши краткое, но информативное резюме договора в виде связного текста с использованием маркированного списка. 
    Используй следующий план:
    1. Стороны договора (Заказчик и Исполнитель).
    2. Предмет договора (что именно нужно сделать).
    3. Цена и условия оплаты.
    4. Сроки выполнения работ.
    5. Особые условия или приложения (если есть).

    Текст должен быть на русском языке, профессиональным и легко читаемым. НЕ ИСПОЛЬЗУЙ JSON.
    
    Текст договора:
    {contract_text}
    """
    return _call_deepseek(prompt, json_mode=False)
