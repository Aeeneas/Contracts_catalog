import json
import requests
import re
from typing import Dict, Any, Optional
from datetime import date, datetime
from config import settings

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"

def _call_deepseek(prompt: str, json_mode: bool = False, system_msg: str = None) -> Optional[str]:
    if not settings.DEEPSEEK_API_KEY:
        print("Error: DEEPSEEK_API_KEY not configured.")
        return None

    if system_msg is None:
        system_msg = "You are a professional legal expert specializing in elevator industry contracts. Your task is to accurately classify works and extract data."

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {settings.DEEPSEEK_API_KEY}"
    }

    payload = {
        "model": "deepseek-chat",
        "messages": [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.0,
        "max_tokens": 3000
    }

    if json_mode:
        payload["response_format"] = {"type": "json_object"}

    try:
        response = requests.post(DEEPSEEK_URL, json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        return response.json()['choices'][0]['message']['content']
    except Exception as e:
        print(f"Error calling DeepSeek API: {e}")
        return None

def get_smart_chunks(text: str) -> str:
    """Извлечение фрагментов с фокусом на ИНН, ДАТЫ и КЛАССИФИКАЦИЮ РАБОТ."""
    if not text: return ""
    head = text[:35000]
    tail = text[-35000:] if len(text) > 35000 else ""
    
    context = ""
    keywords = [
        r"ремонт", r"замена", r"модернизация", r"капитальный", 
        r"дефектная ведомость", r"техническое обслуживание", r"монтаж",
        r"пусконаладочные", r"экспертиза", r"периодический", r"ежемесячно",
        r"количество лифтов", r"стоимость", r"ИНН"
    ]
    
    for pattern in keywords:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 1000)
            end = min(len(text), match.end() + 1500)
            chunk = text[start:end]
            if not any(chunk[:50] in existing for existing in context.split("---")):
                context += f"\n--- ФРАГМЕНТ ДЛЯ АНАЛИЗА ---\n{chunk}\n"
            if len(context) > 60000: break
            
    combined_text = f"--- НАЧАЛО ---\n{head}\n\n{context}\n\n--- КОНЕЦ ---\n{tail}"
    return combined_text[:140000]

def fetch_data_from_dadata(inn: str) -> Dict[str, Any]:
    if not settings.DADATA_API_KEY: return {}
    url = "https://suggestions.dadata.ru/suggestions/api/4_1/rs/findById/party"
    headers = {"Content-Type": "application/json", "Accept": "application/json", "Authorization": f"Token {settings.DADATA_API_KEY}"}
    try:
        response = requests.post(url, json={"query": inn}, headers=headers, timeout=10)
        data = response.json()
        if data.get("suggestions"):
            p = data["suggestions"][0]["data"]
            return {
                "customer": data["suggestions"][0]["value"],
                "customer_inn": inn,
                "customer_ogrn": p.get("ogrn"),
                "customer_ceo": p.get("management", {}).get("name"),
                "customer_legal_address": p.get("address", {}).get("value"),
            }
    except: pass
    return {}

def calculate_monthly_cost_fallback(data: Dict[str, Any]) -> Optional[float]:
    try:
        if not data.get("contract_cost") or not data.get("start_date") or not data.get("end_date"):
            return None
        if data.get("work_type") != "ТО":
            return None
        start = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
        months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        if months > 0:
            return round(float(data["contract_cost"]) / months, 2)
    except: pass
    return None

def extract_contract_data(contract_text: str) -> Dict[str, Any]:
    smart_text = get_smart_chunks(contract_text)
    
    prompt = f"""
    ### ЗАДАЧА: КЛАССИФИКАЦИЯ РАБОТ И ИЗВЛЕЧЕНИЕ ДАННЫХ.
    
    ИНСТРУКЦИЯ ПО ТИПАМ РАБОТ (work_type):
    1. 'ТО' — регулярное ежемесячное ТО.
    2. 'КАПИТАЛЬНЫЕ РАБОТЫ' — РЕМОНТ, ЗАМЕНА узлов, МОДЕРНИЗАЦИЯ.
    3. 'МОНТАЖ' — установка нового лифта.
    
    JSON FORMAT:
    - doc_type: (ДОГ | ДС | АКТ | КС-2 | КС-3)
    - company: (ТОР-ЛИФТ | Противовес | Противовес-Т | null)
    - customer: Название заказчика
    - customer_inn: ИНН
    - work_type: (ТО | МОНТАЖ | СТРОЙКА | ПРОЕКТИРОВАНИЕ | КАПИТАЛЬНЫЕ РАБОТЫ)
    - work_address: Адрес объекта
    - elevator_addresses: Список адресов лифтов (строго каждый с новой строки)
    - elevator_count: ОБЩЕЕ КОЛИЧЕСТВО ЛИФТОВ (число)
    - contract_cost: Общая сумма (число)
    - monthly_cost: В месяц (число)
    - conclusion_date: YYYY-MM-DD
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - ultra_short_summary: Суть ОДНОЙ ФРАЗОЙ

    ТЕКСТ:
    {smart_text}
    """
    
    response_text = _call_deepseek(prompt, json_mode=True)
    if response_text:
        try:
            data = json.loads(response_text)
            
            # 1. ОБРАБОТКА ИНН И DADATA
            if data.get("customer_inn"):
                inn = re.sub(r'\D', '', str(data["customer_inn"]))
                if len(inn) in [10, 12]:
                    data["customer_inn"] = inn
                    official = fetch_data_from_dadata(inn)
                    for k in ["customer", "customer_ogrn", "customer_ceo", "customer_legal_address"]:
                        if official.get(k): data[k] = official[k]
                else: data["customer_inn"] = None

            # 2. ОЧИСТКА СПИСКА АДРЕСОВ (Конвертация из списка в строку, если нужно)
            if isinstance(data.get("elevator_addresses"), list):
                data["elevator_addresses"] = "\n".join(data["elevator_addresses"])

            # 3. ОЧИСТКА ЧИСЕЛ
            for field in ["contract_cost", "monthly_cost", "elevator_count"]:
                if data.get(field) is not None:
                    if isinstance(data[field], str):
                        clean_val = re.sub(r'[^\d.]', '', data[field])
                        data[field] = float(clean_val) if clean_val else 0
                    if field == "elevator_count": data[field] = int(data[field])

            # 4. МАТЕМАТИЧЕСКИЙ ПЕРЕРАСЧЕТ
            if data.get("work_type") == "ТО" and not data.get("monthly_cost"):
                calc_val = calculate_monthly_cost_fallback(data)
                if calc_val: data["monthly_cost"] = calc_val
            
            if data.get("work_type") == "КАПИТАЛЬНЫЕ РАБОТЫ":
                data["monthly_cost"] = None

            # 5. ПОДСЧЕТ ЛИФТОВ, ЕСЛИ ИИ НЕ ВЕРНУЛ ЧИСЛО
            if not data.get("elevator_count") and data.get("elevator_addresses"):
                addrs = [s for s in str(data["elevator_addresses"]).split('\n') if s.strip()]
                data["elevator_count"] = len(addrs)

            return data
        except Exception as e:
            print(f"Error processing AI response: {e}")
            return {"error": str(e)}
    return {"error": "No response"}

def summarize_contract(contract_text: str) -> Optional[str]:
    smart_text = get_smart_chunks(contract_text)
    prompt = f"Напиши резюме договора (Стороны, Предмет, Деньги, Сроки) на основе текста:\n{smart_text}"
    return _call_deepseek(prompt, json_mode=False)
