import json
import requests
from typing import Dict, Any, Optional
from config import settings

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

def _call_deepseek(prompt: str, json_mode: bool = False) -> Optional[str]:
    if not settings.DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY not configured.")
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
    - doc_type: (ДОГ | ДС | АКТ | КС-2 | КС-3)
    - company: (ТОР-ЛИФТ | Противовес | Противовес-Т | null)
    - customer: Полное наименование заказчика (строка | null)
    - customer_inn: ИНН заказчика (строка из 10 или 12 цифр | null)
    - customer_ogrn: ОГРН или ОГРНИП заказчика (строка | null)
    - customer_ceo: ФИО руководителя / Ген. директора (строка | null)
    - customer_legal_address: Юридический адрес заказчика (строка | null)
    - customer_contacts: Контактные данные (телефон, email) (строка | null)
    - customer_bank_details: Банковские реквизиты (р/с, БИК, банк) (строка | null)
    - work_type: (ТО | МОНТАЖ | СТРОЙКА | ПРОЕКТИРОВАНИЕ | КАПИТАЛЬНЫЕ РАБОТЫ | null)
    - work_address: Адрес выполнения работ / Объект (строка | null)
    - elevator_addresses: Адреса установки лифтов (если несколько, через запятую) (строка | null)
    - contract_cost: Общая стоимость договора (число | null)
    - conclusion_date: Дата заключения договора (YYYY-MM-DD | null)
    - monthly_cost: Ежемесячная стоимость ТО (число | null)
    - start_date: Дата начала работ (YYYY-MM-DD | null)
    - end_date: Дата окончания работ (YYYY-MM-DD | null)
    - stages_info: Информация об этапах работ (строка | null)
    - ultra_short_summary: Сверхкраткое описание ОДНИМ предложением (Суть + Адрес объекта). Пример: "ТО 50 лифтов, Комсомольский проспект" (строка | null)
    
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
            return {"error": "Failed to parse AI response."}
    return {"error": "No response from AI."}

def summarize_contract(contract_text: str) -> Optional[str]:
    prompt = f"""
    Напиши краткое резюме договора на РУССКОМ ЯЗЫКЕ. 
    
    КАТЕГОРИЧЕСКИ ЗАПРЕЩЕНО:
    1. Использовать формат JSON или любой другой программный код.
    2. Использовать символы разметки: *, #, _, [, ].
    3. Выравнивать текст по центру.

    ТРЕБОВАНИЯ:
    1. Только простой текст, выровненный ПО ЛЕВОМУ КРАЮ.
    2. Используй только переносы строк для разделения логических блоков.
    3. Соблюдай план: Стороны, Предмет, Финансовые условия, Сроки, Прочее.

    Текст договора:
    {contract_text}
    """
    return _call_deepseek(prompt, json_mode=False)

def generate_ultra_short_summary(work_type: str, address: str, full_summary: str) -> str:
    prompt = f"""
    На основе данных договора сформируй ОДНУ очень короткую фразу для таблицы.
    Фраза должна содержать: Вид работ + Краткую суть (кол-во лифтов, если есть) + Адрес (улица).
    Пример: "ТО 50 лифтов, Комсомольский проспект" или "Монтаж 2 лифтов, ул. Ленина".
    
    ДАННЫЕ:
    Вид работ: {work_type}
    Адрес: {address}
    Описание: {full_summary}
    
    Результат (только фраза, без кавычек и лишних слов):
    """
    res = _call_deepseek(prompt, json_mode=False)
    return res.strip() if res else f"{work_type} по адресу {address}"
