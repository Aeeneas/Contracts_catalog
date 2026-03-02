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
        system_msg = "You are a specialized legal assistant. Your primary mission is to find the INN and critical DATES (conclusion, start, end) in the contract text."

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
    """Извлечение фрагментов с фокусом на ИНН и ДАТЫ."""
    if not text: return ""
    head = text[:35000]
    tail = text[-35000:] if len(text) > 35000 else ""
    
    date_context = ""
    date_keywords = [
        r"\d{2}\.\d{2}\.20\d{2}", 
        r"январ", r"феврал", r"март", r"апрел", r"ма(?:я|й)", r"июн", 
        r"июл", r"август", r"сентябр", r"октябр", r"ноябр", r"декабр",
        r"действует до", r"срок действия", r"в течение", r"календарных дней"
    ]
    
    for pattern in date_keywords:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            start = max(0, match.start() - 800)
            end = min(len(text), match.end() + 1200)
            chunk = text[start:end]
            if not any(chunk[:50] in existing for existing in date_context.split("---")):
                date_context += f"\n--- ФРАГМЕНТ С ДАТОЙ/СРОКОМ ---\n{chunk}\n"
            if len(date_context) > 40000: break
            
    inn_context = ""
    inn_matches = list(re.finditer(r'(?i)(ИНН|IНН|ИHH|77\d{8}|\d{10}|\d{12})', text))
    for match in inn_matches[:5]:
        start = max(0, match.start() - 500)
        end = min(len(text), match.end() + 500)
        inn_context += f"\n--- ФРАГМЕНТ С ИНН ---\n{text[start:end]}\n"

    combined_text = f"--- НАЧАЛО ---\n{head}\n\n{date_context}\n\n{inn_context}\n\n--- КОНЕЦ ---\n{tail}"
    return combined_text[:130000]

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
    """Математический расчет ежемесячной стоимости на основе дат и общей суммы."""
    try:
        if not data.get("contract_cost") or not data.get("start_date") or not data.get("end_date"):
            return None
        
        # Только для договоров ТО (Техническое Обслуживание)
        if data.get("work_type") != "ТО":
            return None

        start = datetime.strptime(data["start_date"], "%Y-%m-%d").date()
        end = datetime.strptime(data["end_date"], "%Y-%m-%d").date()
        
        # Считаем количество месяцев (включая неполные как полные для ТО)
        months = (end.year - start.year) * 12 + (end.month - start.month) + 1
        
        if months > 0:
            calc_cost = float(data["contract_cost"]) / months
            return round(calc_cost, 2)
    except:
        pass
    return None

def extract_contract_data(contract_text: str) -> Dict[str, Any]:
    smart_text = get_smart_chunks(contract_text)
    
    prompt = f"""
    ### ЗАДАЧА: ИЗВЛЕЧЬ ИНН И ДАТЫ.
    1. conclusion_date: Дата заключения (начало договора).
    2. start_date: Дата начала работ.
    3. end_date: Дата окончания работ или срок действия.
    
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
    - elevator_addresses: Адреса лифтов
    - contract_cost: Общая сумма (число)
    - monthly_cost: Сумма в месяц (число)
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
            
            # Очистка ИНН и Dadata
            if data.get("customer_inn"):
                inn = re.sub(r'\D', '', str(data["customer_inn"]))
                if len(inn) in [10, 12]:
                    data["customer_inn"] = inn
                    official = fetch_data_from_dadata(inn)
                    for k in ["customer", "customer_ogrn", "customer_ceo", "customer_legal_address"]:
                        if official.get(k): data[k] = official[k]
                else: data["customer_inn"] = None

            # Очистка стоимости от ИИ
            for field in ["contract_cost", "monthly_cost"]:
                if data.get(field) and isinstance(data[field], str):
                    clean_val = re.sub(r'[^\d.]', '', data[field])
                    data[field] = float(clean_val) if clean_val else None

            # МАТЕМАТИЧЕСКИЙ ПЕРЕРАСЧЕТ (СТРАХОВКА)
            if data.get("work_type") == "ТО" and not data.get("monthly_cost"):
                calc_val = calculate_monthly_cost_fallback(data)
                if calc_val:
                    data["monthly_cost"] = calc_val

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
