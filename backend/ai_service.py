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

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

DEEPSEEK_URL = "https://api.deepseek.com/chat/completions"
OPENAI_URL = "https://api.openai.com/v1/chat/completions"

def _get_session():
    """Создает сессию с повторными попытками и прокси."""
    session = requests.Session()
    
    # Настройка повторов (Retries)
    retry_strategy = Retry(
        total=3, # Количество повторов
        backoff_factor=1, # Ожидание между повторами: 1s, 2s, 4s
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    
    # Настройка прокси
    proxies = {}
    if settings.HTTP_PROXY: proxies["http"] = settings.HTTP_PROXY
    if settings.HTTPS_PROXY: proxies["https"] = settings.HTTPS_PROXY
    if proxies:
        session.proxies.update(proxies)
        
    return session

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
        session = _get_session()
        response = session.post(url, json=payload, headers=headers, timeout=120)
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

def merge_extracted_data(base: Dict[str, Any], new_data: Dict[str, Any]) -> Dict[str, Any]:
    """Умно объединяет два набора данных, предотвращая затирание найденных полей пустыми значениями."""
    for key, val in new_data.items():
        # Если новое значение пустое — игнорируем его, сохраняя то, что было в base
        if val is None or val == "" or val == 0 or str(val).lower() == "null":
            continue
            
        # Если в базе еще нет значения или оно пустое — записываем новое
        if key not in base or base[key] is None or base[key] == "" or base[key] == 0:
            base[key] = val
        else:
            # Специальная логика для списков (например, potential_inns)
            if isinstance(base[key], list) and isinstance(val, list):
                base[key] = list(set(base[key] + val))
            # Специальная логика для строк-списков (адреса лифтов)
            elif key == "elevator_addresses" and isinstance(val, str):
                old_addrs = set(a.strip() for a in base[key].split("\n") if a.strip())
                new_addrs = set(a.strip() for a in val.split("\n") if a.strip())
                base[key] = "\n".join(sorted(list(old_addrs | new_addrs)))
            # Для остальных полей: если значения разные, оставляем более длинное (актуально для названий и адресов)
            elif isinstance(val, str) and isinstance(base[key], str):
                if len(val) > len(base[key]):
                    base[key] = val
    return base

def extract_contract_data(contract_text: str) -> Dict[str, Any]:
    """Анализирует текст договора, используя поэтапный анализ и умное слияние результатов."""
    if not contract_text:
        return {"error": "Пустой текст"}

    # 1. Готовим фрагменты (Начало, Контекст, Конец)
    head = contract_text[:40000]
    tail = contract_text[-40000:] if len(contract_text) > 40000 else ""
    keywords_context = get_smart_chunks(contract_text)
    
    chunks = [
        {"name": "Преамбула", "text": head},
        {"name": "Ключевые фрагменты", "text": keywords_context},
        {"name": "Реквизиты", "text": tail}
    ]
    
    final_data = {
        "doc_type": "ДОГ", "company": None, "customer": None, "customer_inn": None,
        "work_type": None, "work_address": None, "elevator_addresses": "",
        "elevator_count": 0, "contract_cost": 0, "monthly_cost": 0,
        "potential_inns": []
    }

    # 2. Опрашиваем ИИ по каждому чанку
    for chunk in chunks:
        if not chunk["text"] or len(chunk["text"]) < 100:
            continue
            
        prompt = f"""
        ### ЗАДАЧА: АНАЛИЗ ФРАГМЕНТА ДОГОВОРА ({chunk['name']}).
        Извлеки данные в формате JSON. Если данных нет, пиши null.
        
        JSON FORMAT:
        - doc_type: (ДОГ | ДС | АКТ | КС-2 | КС-3)
        - company: (ТОР-ЛИФТ | Противовес | Противовес-Т | null)
        - customer: Название заказчика
        - customer_inn: ИНН заказчика (10 или 12 цифр)
        - customer_ogrn: ОГРН заказчика
        - customer_ceo: ФИО директора
        - customer_legal_address: Юр. адрес
        - customer_contact_info: Телефоны, email
        - customer_bank_details: Реквизиты банка
        - work_type: (ТО | МОНТАЖ | СТРОЙКА | ПРОЕКТИРОВАНИЕ | КАПИТАЛЬНЫЕ РАБОТЫ)
        - work_address: Адрес объекта
        - elevator_addresses: Список адресов лифтов (через \\n)
        - elevator_count: количество лифтов (число)
        - contract_cost: общая сумма (число)
        - monthly_cost: сумма в месяц (число)
        - conclusion_date: YYYY-MM-DD
        - start_date: YYYY-MM-DD
        - end_date: YYYY-MM-DD
        - ultra_short_summary: Суть (1 фраза)
        - potential_inns: [список всех ИНН, найденных в этом куске]

        ТЕКСТ ДЛЯ АНАЛИЗА:
        {chunk['text']}
        """
        
        response_text = _call_ai(prompt, json_mode=True)
        if response_text:
            try:
                chunk_data = json.loads(response_text)
                final_data = merge_extracted_data(final_data, chunk_data)
            except:
                continue

    # 3. Валидация и обогащение ИНН через DaData
    candidates = final_data.get("potential_inns", [])
    if final_data.get("customer_inn"): 
        candidates.insert(0, final_data["customer_inn"])
    
    valid_inn = None
    for cand in candidates:
        clean = re.sub(r'\D', '', str(cand))
        if validate_inn(clean) and clean not in ["7718725359", "7724451010", "7714492210"]: # Исключаем свои ИНН
            valid_inn = clean
            break
    
    if valid_inn:
        final_data["customer_inn"] = valid_inn
        official = fetch_data_from_dadata(valid_inn)
        if official:
            final_data = merge_extracted_data(final_data, official)
    
    # 4. Финальная чистка типов данных
    for f in ["contract_cost", "monthly_cost", "elevator_count"]:
        if final_data.get(f) is not None:
            if isinstance(final_data[f], str):
                val = re.sub(r'[^\d.]', '', final_data[f])
                final_data[f] = float(val) if val else 0
    
    return final_data

def summarize_contract(contract_text: str) -> Optional[str]:
    smart_text = get_smart_chunks(contract_text)
    prompt = f"Напиши развернутое резюме договора на русском языке:\n{smart_text}"
    return _call_ai(prompt, json_mode=False)
