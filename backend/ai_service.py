import json
import requests
import re
from typing import Dict, Any, Optional, List
from datetime import date, datetime
from config import settings
try:
    from utils import validate_inn
except ImportError:
    from .utils import validate_inn

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

def _call_ai(prompt: str, json_mode: bool = False, system_msg: str = None) -> Optional[str]:
    """Универсальный вызов ИИ."""
    api_to_use = "OpenAI" if settings.OPENAI_API_KEY else "DeepSeek"
    url = OPENAI_URL if settings.OPENAI_API_KEY else DEEPSEEK_URL
    key = settings.OPENAI_API_KEY if settings.OPENAI_API_KEY else settings.DEEPSEEK_API_KEY
    model = "gpt-4o" if settings.OPENAI_API_KEY else "deepseek-chat"

    if not key: return None

    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {key}"}
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_msg or "You are a professional legal analyst."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 3000
    }
    if json_mode: payload["response_format"] = {"type": "json_object"}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=150)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling {api_to_use}: {e}")
        return None

def get_smart_chunks(text: str) -> str:
    """Глубокое извлечение фрагментов для больших документов."""
    if not text: return ""
    head, tail = text[:35000], text[-35000:] if len(text) > 35000 else ""
    keywords = ["ИНН", "ремонт", "замена", "техническое обслуживание", "лифт", "стоимость", "срок", "адрес", "ОГРН", "банк"]
    context = ""
    for word in keywords:
        for match in re.finditer(re.escape(word), text, re.IGNORECASE):
            start, end = max(0, match.start() - 1000), min(len(text), match.end() + 1500)
            chunk = text[start:end]
            if not any(chunk[:50] in existing for existing in context.split("---")):
                context += f"\n--- ФРАГМЕНТ С '{word}' ---\n{chunk}\n"
            if len(context) > 80000: break
    return f"--- ПРЕАМБУЛА ---\n{head}\n\n{context}\n\n--- РЕКВИЗИТЫ ---\n{tail}"

def fetch_data_from_dadata(inn: str) -> Dict[str, Any]:
    if not settings.DADATA_API_KEY: return {}
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Authorization": f"Token {settings.DADATA_API_KEY}"}
    try:
        res = requests.post(url, json={"query": inn}, headers=headers, timeout=10)
        data = res.json()
        if data.get("suggestions"):
            p = data["suggestions"][0]["data"]
            return {
                "customer": data["suggestions"][0]["value"], "customer_inn": inn,
                "customer_ogrn": p.get("ogrn"), "customer_ceo": p.get("management", {}).get("name"),
                "customer_legal_address": p.get("address", {}).get("value"),
                "customer_bank_details": p.get("bank_details")
            }
    except: pass
    return {}

def extract_contract_data(contract_text: str) -> Dict[str, Any]:
    smart_text = get_smart_chunks(contract_text)
    
    prompt = f"""
    ### ЗАДАЧА: ПОЛНЫЙ АНАЛИЗ ДОГОВОРА.
    Извлеки ВСЕ данные. Если данные не найдены, пиши null.
    
    ИНСТРУКЦИЯ ПО ИНН: Найди ИНН заказчика. Если видишь несколько похожих чисел, верни их списком в potential_inns.
    
    JSON FORMAT:
    - doc_type: (ДОГ | ДС | АКТ | КС-2 | КС-3)
    - company: (ТОР-ЛИФТ | Противовес | Противовес-Т | null)
    - customer: Название заказчика
    - customer_inn: Основной найденный ИНН
    - potential_inns: [все найденные варианты ИНН]
    - work_type: (ТО | МОНТАЖ | СТРОЙКА | ПРОЕКТИРОВАНИЕ | КАПИТАЛЬНЫЕ РАБОТЫ)
    - work_address: Адрес объекта
    - elevator_addresses: Список адресов лифтов (через \\n)
    - elevator_count: количество лифтов (число)
    - contract_cost: общая сумма (число)
    - monthly_cost: сумма в месяц для ТО (число)
    - conclusion_date: YYYY-MM-DD
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - ultra_short_summary: Суть (1 фраза)

    ТЕКСТ:
    {smart_text}
    """
    
    response_text = _call_ai(prompt, json_mode=True)
    if not response_text: return {"error": "No AI response"}
    
    try:
        data = json.loads(response_text)
        
        # ЛОГИКА ВАЛИДАЦИИ ИНН (не блокирующая)
        candidates = data.get("potential_inns", [])
        if data.get("customer_inn"): candidates.insert(0, data["customer_inn"])
        
        valid_inn = None
        for cand in candidates:
            clean = re.sub(r'\D', '', str(cand))
            if validate_inn(clean) and clean not in ["7718725359"]: # ТОР-ЛИФТ
                valid_inn = clean
                break
        
        if valid_inn:
            data["customer_inn"] = valid_inn
            official = fetch_data_from_dadata(valid_inn)
            if official: data.update(official)
        
        # Финальная очистка
        if isinstance(data.get("elevator_addresses"), list): data["elevator_addresses"] = "\n".join(data["elevator_addresses"])
        for f in ["contract_cost", "monthly_cost", "elevator_count"]:
            if data.get(f) is not None:
                if isinstance(data[f], str): data[f] = float(re.sub(r'[^\d.]', '', data[f])) if re.sub(r'[^\d.]', '', data[f]) else 0
        
        return data
    except Exception as e:
        return {"error": str(e)}

def summarize_contract(contract_text: str) -> Optional[str]:
    smart_text = get_smart_chunks(contract_text)
    prompt = f"Напиши развернутое резюме договора на русском языке:\n{smart_text}"
    return _call_ai(prompt, json_mode=False)
