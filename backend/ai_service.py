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
        system_msg = "You are a specialized legal assistant. Your primary mission is to find the INN, critical DATES, and the EXACT NUMBER of elevators mentioned for maintenance or installation."

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
    """Извлечение фрагментов с фокусом на ИНН, ДАТЫ и КОЛИЧЕСТВО ЛИФТОВ."""
    if not text: return ""
    head = text[:35000]
    tail = text[-35000:] if len(text) > 35000 else ""
    
    # Контекст для дат и лифтов
    context = ""
    keywords = [
        r"\d{2}\.\d{2}\.20\d{2}", 
        r"январ", r"феврал", r"март", r"апрел", r"ма(?:я|й)", r"июн", 
        r"июл", r"август", r"сентябр", r"октябр", r"ноябр", r"декабр",
        r"действует до", r"срок действия", r"количество лифтов", r"единиц",
        r"\d+\s*шт", r"\d+\s*\(.*\)\s*лифт", r"перечень оборудования"
    ]
    
    for pattern in keywords:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 1000)
            end = min(len(text), match.end() + 1500)
            chunk = text[start:end]
            if not any(chunk[:50] in existing for existing in context.split("---")):
                context += f"\n--- ФРАГМЕНТ ДЛЯ АНАЛИЗА ---\n{chunk}\n"
            if len(context) > 50000: break
            
    inn_matches = list(re.finditer(r'(?i)(ИНН|IНН|ИHH|77\d{8}|\d{10}|\d{12})', text))
    inn_context = ""
    for match in inn_matches[:5]:
        start = max(0, match.start() - 500)
        end = min(len(text), match.end() + 500)
        inn_context += f"\n--- ИНН КОНТЕКСТ ---\n{text[start:end]}\n"

    combined_text = f"--- НАЧАЛО ---\n{head}\n\n{context}\n\n{inn_context}\n\n--- КОНЕЦ ---\n{tail}"
    return combined_text[:135000]

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
    ### ЗАДАЧА: ИЗВЛЕЧЬ ИНН, ДАТЫ И КОЛИЧЕСТВО ЛИФТОВ.
    
    ИНСТРУКЦИЯ ПО ЛИФТАМ:
    Найди в тексте количество лифтов, которые принимаются на обслуживание или подлежат монтажу. 
    Обычно это фразы: "количество лифтов: 5", "5 (пять) лифтов", "монтаж 2-х лифтов".
    Если есть список адресов, посчитай количество уникальных адресов/лифтов.

    JSON FORMAT:
    - doc_type: (ДОГ | ДС | АКТ | КС-2 | КС-3)
    - company: (ТОР-ЛИФТ | Противовес | Противовес-Т | null)
    - customer: Название заказчика
    - customer_inn: ИНН
    - customer_ogrn: ОГРН
    - customer_ceo: Директор
    - customer_legal_address: Юр. адрес
    - customer_contacts: Тел/Email
    - customer_bank_details: р/с, БИК, Банк
    - work_type: (ТО | МОНТАЖ | СТРОЙКА | ПРОЕКТИРОВАНИЕ | КАПИТАЛЬНЫЕ РАБОТЫ | null)
    - work_address: Адрес объекта
    - elevator_addresses: Список адресов лифтов (строго каждый с новой строки)
    - elevator_count: ОБЩЕЕ КОЛИЧЕСТВО ЛИФТОВ (число)
    - contract_cost: Сумма (число)
    - monthly_cost: В месяц (число)
    - conclusion_date: YYYY-MM-DD
    - start_date: YYYY-MM-DD
    - end_date: YYYY-MM-DD
    - stages_info: Этапы
    - ultra_short_summary: Суть

    ТЕКСТ:
    {smart_text}
    """
    
    response_text = _call_deepseek(prompt, json_mode=True)
    if response_text:
        try:
            data = json.loads(response_text)
            
            if data.get("customer_inn"):
                inn = re.sub(r'\D', '', str(data["customer_inn"]))
                if len(inn) in [10, 12]:
                    data["customer_inn"] = inn
                    official = fetch_data_from_dadata(inn)
                    for k in ["customer", "customer_ogrn", "customer_ceo", "customer_legal_address"]:
                        if official.get(k): data[k] = official[k]
                else: data["customer_inn"] = None

            for field in ["contract_cost", "monthly_cost"]:
                if data.get(field) and isinstance(data[field], str):
                    clean_val = re.sub(r'[^\d.]', '', data[field])
                    data[field] = float(clean_val) if clean_val else None

            if data.get("work_type") == "ТО" and not data.get("monthly_cost"):
                calc_val = calculate_monthly_cost_fallback(data)
                if calc_val: data["monthly_cost"] = calc_val

            # Если ИИ не вернул число в count, попробуем посчитать по списку адресов
            if not data.get("elevator_count") and data.get("elevator_addresses"):
                addrs = [s for s in data["elevator_addresses"].split('\n') if s.strip()]
                data["elevator_count"] = len(addrs)

            return data
        except: return {"error": "JSON error"}
    return {"error": "No response"}

def summarize_contract(contract_text: str) -> Optional[str]:
    smart_text = get_smart_chunks(contract_text)
    prompt = f"Напиши резюме договора (Стороны, Предмет, Деньги, Сроки) на основе текста:\n{smart_text}"
    return _call_deepseek(prompt, json_mode=False)

def generate_ultra_short_summary(work_type: str, address: str, full_summary: str) -> str:
    prompt = f"Короткая фраза (Вид работ + Адрес): {work_type}, {address}, {full_summary[:300]}"
    res = _call_deepseek(prompt, json_mode=False)
    return res.strip() if res else f"{work_type} по адресу {address}"
