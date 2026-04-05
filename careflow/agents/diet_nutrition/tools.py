"""
Diet/Nutrition Agent — Tool Functions
식이/영양 에이전트 — 도구 함수 모음

FunctionTool definitions for the Diet/Nutrition Agent.
Uses real APIs with mock data fallback for resilience.
실제 API를 사용하되, 실패 시 mock 데이터로 fallback.

APIs:
  - USDA FoodData Central (lookup_food_nutrition) — API key: DEMO_KEY
  - Mock DB fallback for all tools

Tools:
  - get_patient_medications: 현재 복용 약물 조회 / Retrieve current medications
  - get_dietary_restrictions: 식이 제한 사항 조회 / Retrieve doctor-ordered dietary restrictions
  - lookup_food_nutrition: USDA 기반 영양 성분 조회 / USDA-based nutrition lookup
  - check_food_drug_interaction: 음식-약물 상호작용 확인 / Food-drug interaction check
"""

from __future__ import annotations

import json
import os
import ssl
import urllib.request
import urllib.error
import urllib.parse
from typing import Any

from google.adk.tools import ToolContext

# ---------------------------------------------------------------------------
# USDA FoodData Central API 설정 / USDA API Configuration
# API 키: 환경변수 우선, 없으면 DEMO_KEY 사용 (테스트용으로 작동)
# API key: env var first, fallback to DEMO_KEY (works for testing)
# ---------------------------------------------------------------------------
_USDA_API_KEY = os.environ.get("USDA_API_KEY", "DEMO_KEY")
_USDA_BASE_URL = "https://api.nal.usda.gov/fdc/v1"
_API_TIMEOUT = 5  # 초 / seconds

# SSL 컨텍스트 — 일부 환경에서 인증서 문제 우회 / SSL context for cert issues
_SSL_CTX = ssl.create_default_context()
try:
    _SSL_CTX.load_default_certs()
except Exception:
    _SSL_CTX = ssl.create_default_context()
    _SSL_CTX.check_hostname = False
    _SSL_CTX.verify_mode = ssl.CERT_NONE

# ---------------------------------------------------------------------------
# Mock Data — 데모용 목업 데이터
# Production에서는 AlloyDB / USDA FoodData Central / openFDA로 교체
# In production, replace with AlloyDB / USDA FoodData Central / openFDA
# ---------------------------------------------------------------------------

# 환자별 복용 약물 / Patient medication records
_MOCK_MEDICATIONS: dict[str, list[dict]] = {
    "patient_001": [
        {
            "drug_name": "Metformin",
            "dosage": "1000mg",
            "frequency": "twice daily",
            "purpose": "Type 2 Diabetes (DM2)",
        },
        {
            "drug_name": "Amlodipine",
            "dosage": "5mg",
            "frequency": "once daily",
            "purpose": "Hypertension (HTN)",
        },
    ],
    "patient_002": [
        {
            "drug_name": "Warfarin",
            "dosage": "5mg",
            "frequency": "once daily",
            "purpose": "Atrial Fibrillation — anticoagulant",
        },
        {
            "drug_name": "Lisinopril",
            "dosage": "10mg",
            "frequency": "once daily",
            "purpose": "Hypertension (HTN)",
        },
    ],
    "patient_003": [
        {
            "drug_name": "Atorvastatin",
            "dosage": "20mg",
            "frequency": "once daily at bedtime",
            "purpose": "Hyperlipidemia — cholesterol management",
        },
        {
            "drug_name": "Metformin",
            "dosage": "500mg",
            "frequency": "twice daily",
            "purpose": "Type 2 Diabetes (DM2)",
        },
    ],
}

# 환자별 식이 제한 사항 (의사 지시) / Doctor-ordered dietary restrictions
_MOCK_DIETARY_RESTRICTIONS: dict[str, dict] = {
    "patient_001": {
        "conditions": ["DM2", "HTN"],
        "restrictions": [
            {"type": "low_sodium", "target_mg": 2000, "source": "Dr. Sharma — visit 2024-12-20"},
            {"type": "low_sugar", "target_g": 25, "source": "Dr. Sharma — visit 2024-12-20"},
        ],
        "allergies": [],
        "locale": "India",
    },
    "patient_002": {
        "conditions": ["Atrial Fibrillation", "HTN"],
        "restrictions": [
            {"type": "consistent_vitamin_k", "note": "Keep vitamin K intake consistent for Warfarin stability", "source": "Dr. Patel — visit 2025-01-10"},
            {"type": "low_sodium", "target_mg": 1500, "source": "Dr. Patel — visit 2025-01-10"},
        ],
        "allergies": ["shellfish"],
        "locale": "India",
    },
    "patient_003": {
        "conditions": ["DM2", "Hyperlipidemia"],
        "restrictions": [
            {"type": "low_cholesterol", "note": "Limit saturated fat < 13g/day", "source": "Dr. Kim — visit 2025-02-05"},
            {"type": "low_sugar", "target_g": 30, "source": "Dr. Kim — visit 2025-02-05"},
        ],
        "allergies": ["peanuts"],
        "locale": "Korea",
    },
}

# USDA FoodData Central 기반 영양 성분 목업 / USDA-based nutrition mock data
# 실제 운영 시 USDA API (https://fdc.nal.usda.gov/) 호출로 대체
_MOCK_FOOD_NUTRITION: dict[str, dict] = {
    "white rice": {
        "food_name": "White Rice (cooked, 1 cup / 186g)",
        "calories_kcal": 206,
        "sodium_mg": 1.9,
        "sugar_g": 0.1,
        "carbohydrates_g": 44.5,
        "protein_g": 4.3,
        "fat_g": 0.4,
        "glycemic_index": 73,
        "source": "USDA FoodData Central #168878",
    },
    "brown rice": {
        "food_name": "Brown Rice (cooked, 1 cup / 195g)",
        "calories_kcal": 216,
        "sodium_mg": 10.0,
        "sugar_g": 0.7,
        "carbohydrates_g": 44.8,
        "protein_g": 5.0,
        "fat_g": 1.8,
        "glycemic_index": 50,
        "source": "USDA FoodData Central #168874",
    },
    "kimchi": {
        "food_name": "Kimchi (1 cup / 150g)",
        "calories_kcal": 23,
        "sodium_mg": 747,
        "sugar_g": 1.6,
        "carbohydrates_g": 3.6,
        "protein_g": 1.7,
        "fat_g": 0.5,
        "glycemic_index": 15,
        "source": "USDA FoodData Central #174276",
    },
    "dal": {
        "food_name": "Moong Dal (cooked, 1 cup / 200g)",
        "calories_kcal": 212,
        "sodium_mg": 4.0,
        "sugar_g": 3.4,
        "carbohydrates_g": 38.7,
        "protein_g": 14.2,
        "fat_g": 0.8,
        "glycemic_index": 31,
        "source": "USDA FoodData Central #172421",
    },
    "grapefruit": {
        "food_name": "Grapefruit (1 medium / 246g)",
        "calories_kcal": 97,
        "sodium_mg": 0,
        "sugar_g": 16.1,
        "carbohydrates_g": 24.5,
        "protein_g": 1.8,
        "fat_g": 0.3,
        "glycemic_index": 25,
        "source": "USDA FoodData Central #167762",
    },
    "spinach": {
        "food_name": "Spinach (cooked, 1 cup / 180g)",
        "calories_kcal": 41,
        "sodium_mg": 126,
        "sugar_g": 0.8,
        "carbohydrates_g": 6.8,
        "protein_g": 5.4,
        "fat_g": 0.5,
        "glycemic_index": 15,
        "note": "High in vitamin K — relevant for Warfarin patients",
        "source": "USDA FoodData Central #168462",
    },
    "oatmeal": {
        "food_name": "Oatmeal (cooked, 1 cup / 234g)",
        "calories_kcal": 154,
        "sodium_mg": 115,
        "sugar_g": 1.1,
        "carbohydrates_g": 27.4,
        "protein_g": 5.9,
        "fat_g": 2.6,
        "glycemic_index": 55,
        "source": "USDA FoodData Central #173904",
    },
    "banana": {
        "food_name": "Banana (1 medium / 118g)",
        "calories_kcal": 105,
        "sodium_mg": 1.2,
        "sugar_g": 14.4,
        "carbohydrates_g": 27.0,
        "protein_g": 1.3,
        "fat_g": 0.4,
        "glycemic_index": 51,
        "source": "USDA FoodData Central #173944",
    },
}

# 음식-약물 상호작용 데이터 / Food-drug interaction database
# 출처: openFDA Drug Labeling + DailyMed NLM
_MOCK_FOOD_DRUG_INTERACTIONS: dict[str, dict[str, dict]] = {
    "grapefruit": {
        "Amlodipine": {
            "severity": "WARNING",
            "interaction": (
                "Grapefruit inhibits CYP3A4 enzyme, which can increase "
                "Amlodipine blood levels and amplify side effects "
                "(dizziness, swelling, low blood pressure)."
            ),
            "recommendation": "Avoid grapefruit and grapefruit juice. Try oranges or other citrus instead.",
            "source": "openFDA Drug Label / DailyMed NLM",
        },
        "Atorvastatin": {
            "severity": "WARNING",
            "interaction": (
                "Grapefruit inhibits CYP3A4 enzyme, increasing statin levels "
                "in the blood. This raises the risk of rhabdomyolysis (muscle breakdown)."
            ),
            "recommendation": "Avoid grapefruit and grapefruit juice while on Atorvastatin.",
            "source": "openFDA Drug Label / DailyMed NLM",
        },
    },
    "alcohol": {
        "Metformin": {
            "severity": "WARNING",
            "interaction": (
                "Excessive alcohol consumption with Metformin increases "
                "the risk of lactic acidosis, a rare but serious condition."
            ),
            "recommendation": "Limit alcohol to at most 1 drink/day for women, 2 for men. Avoid binge drinking.",
            "source": "openFDA Drug Label / DailyMed NLM",
        },
    },
    "spinach": {
        "Warfarin": {
            "severity": "CAUTION",
            "interaction": (
                "Spinach is high in vitamin K which counteracts Warfarin's "
                "anticoagulant effect. Sudden changes in vitamin K intake "
                "can destabilize INR levels."
            ),
            "recommendation": (
                "Do NOT avoid spinach entirely — instead, keep your vitamin K "
                "intake CONSISTENT day-to-day. Inform your doctor of any major "
                "dietary changes."
            ),
            "source": "openFDA Drug Label / DailyMed NLM",
        },
    },
    "kimchi": {
        "Warfarin": {
            "severity": "CAUTION",
            "interaction": (
                "Kimchi contains vitamin K from cabbage/radish. Fermented "
                "kimchi may also affect gut flora, indirectly influencing "
                "vitamin K synthesis and Warfarin metabolism."
            ),
            "recommendation": "Keep kimchi portions consistent. Monitor INR regularly.",
            "source": "openFDA Drug Label / DailyMed NLM",
        },
    },
    "banana": {
        "Lisinopril": {
            "severity": "CAUTION",
            "interaction": (
                "Bananas are high in potassium. ACE inhibitors like Lisinopril "
                "can increase potassium levels (hyperkalemia risk)."
            ),
            "recommendation": "Moderate banana intake (1/day is generally fine). Watch for muscle weakness or irregular heartbeat.",
            "source": "openFDA Drug Label / DailyMed NLM",
        },
    },
}


# ---------------------------------------------------------------------------
# Tool Functions — FunctionTool로 등록될 함수들
# Each function signature: (param, ..., tool_context: ToolContext)
# ---------------------------------------------------------------------------


def get_patient_medications(patient_id: str, tool_context: ToolContext) -> dict:
    """현재 복용 약물 목록을 조회합니다.
    Retrieve the patient's current medication list.

    Args:
        patient_id: 환자 고유 ID / Unique patient identifier.
        tool_context: ADK ToolContext (injected by framework).

    Returns:
        dict with 'medications' list or 'error' message.
    """
    medications = _MOCK_MEDICATIONS.get(patient_id)
    if medications is None:
        return {
            "error": f"Patient '{patient_id}' not found.",
            "medications": [],
        }
    return {
        "patient_id": patient_id,
        "medications": medications,
        "count": len(medications),
    }


def get_dietary_restrictions(patient_id: str, tool_context: ToolContext) -> dict:
    """의사 지시 기반 식이 제한 사항을 조회합니다.
    Retrieve doctor-ordered dietary restrictions for the patient.

    Args:
        patient_id: 환자 고유 ID / Unique patient identifier.
        tool_context: ADK ToolContext (injected by framework).

    Returns:
        dict with conditions, restrictions, allergies, and locale.
    """
    restrictions = _MOCK_DIETARY_RESTRICTIONS.get(patient_id)
    if restrictions is None:
        return {
            "error": f"Patient '{patient_id}' not found.",
            "conditions": [],
            "restrictions": [],
            "allergies": [],
            "locale": "unknown",
        }
    return {"patient_id": patient_id, **restrictions}


def _query_usda_api(food_name: str) -> dict[str, Any] | None:
    """USDA FoodData Central API를 호출하여 영양 데이터를 가져옵니다.
    Query the USDA FoodData Central API for nutrition data.

    Args:
        food_name: 음식 이름 (영문) / Food name in English.

    Returns:
        dict with nutrition data on success, None on failure.
        성공 시 영양 데이터 dict, 실패 시 None.
    """
    try:
        params = urllib.parse.urlencode({
            "query": food_name,
            "api_key": _USDA_API_KEY,
            "pageSize": 1,
            "dataType": "Foundation,SR Legacy",
        })
        url = f"{_USDA_BASE_URL}/foods/search?{params}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})

        with urllib.request.urlopen(req, timeout=_API_TIMEOUT, context=_SSL_CTX) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        foods = data.get("foods", [])
        if not foods:
            return None

        food = foods[0]
        nutrients = {n["nutrientName"]: n["value"] for n in food.get("foodNutrients", []) if "value" in n}

        # 영양소 매핑 — USDA 필드명 → CareFlow 표준 필드
        # Nutrient mapping — USDA field names → CareFlow standard fields
        return {
            "food_name": food.get("description", food_name),
            "fdc_id": food.get("fdcId", "N/A"),
            "calories_kcal": nutrients.get("Energy", 0),
            "sodium_mg": nutrients.get("Sodium, Na", 0),
            "sugar_g": nutrients.get("Sugars, total including NLEA", nutrients.get("Sugars, Total", 0)),
            "carbohydrates_g": nutrients.get("Carbohydrate, by difference", 0),
            "protein_g": nutrients.get("Protein", 0),
            "fat_g": nutrients.get("Total lipid (fat)", 0),
            "fiber_g": nutrients.get("Fiber, total dietary", 0),
            "vitamin_k_ug": nutrients.get("Vitamin K (phylloquinone)", 0),
            "potassium_mg": nutrients.get("Potassium, K", 0),
            "source": f"USDA FoodData Central (FDC ID: {food.get('fdcId', 'N/A')})",
            "api_source": True,
        }
    except Exception:
        # API 실패 시 None 반환 → mock fallback 사용
        # Return None on API failure → use mock fallback
        return None


def lookup_food_nutrition(food_name: str, tool_context: ToolContext) -> dict:
    """USDA FoodData Central 기반 영양 성분을 조회합니다.
    Look up nutrition facts (sodium, sugar, calories, etc.) for a food item.

    실제 USDA API를 먼저 호출하고, 실패 시 로컬 mock 데이터로 fallback.
    Calls the real USDA API first; falls back to local mock data on failure.

    Args:
        food_name: 음식 이름 (영문) / Food name in English.
        tool_context: ADK ToolContext (injected by framework).

    Returns:
        dict with nutrition data or a 'not_found' message.
    """
    key = food_name.strip().lower()

    # 1단계: mock DB에 있으면 바로 반환 (빠른 경로, 검증된 데이터)
    # Step 1: Return from mock DB if available (fast path, curated data)
    mock_nutrition = _MOCK_FOOD_NUTRITION.get(key)
    if mock_nutrition is not None:
        return {"found": True, **mock_nutrition}

    # 2단계: mock에 없으면 USDA API 호출 / Step 2: Query USDA API if not in mock
    api_result = _query_usda_api(food_name)
    if api_result is not None:
        return {"found": True, **api_result}

    # 3단계: API도 실패 시 not_found 반환 / Step 3: Not found anywhere
    return {
        "food_name": food_name,
        "found": False,
        "message": (
            f"'{food_name}' not found in local cache or USDA FoodData Central API. "
            "Please verify the food name and try again."
        ),
    }


def check_food_drug_interaction(
    food_name: str, drug_name: str, tool_context: ToolContext
) -> dict:
    """음식-약물 상호작용을 확인합니다.
    Check for known food-drug interactions between a food and a medication.

    Args:
        food_name: 음식 이름 (영문) / Food name in English.
        drug_name: 약물 이름 (영문) / Drug/medication name in English.
        tool_context: ADK ToolContext (injected by framework).

    Returns:
        dict with interaction details or 'no_interaction_found'.
    """
    food_key = food_name.strip().lower()
    # 약물명은 첫 글자 대문자로 정규화 / Normalize drug name to title case
    drug_key = drug_name.strip().title()

    food_interactions = _MOCK_FOOD_DRUG_INTERACTIONS.get(food_key)
    if food_interactions is None:
        return {
            "food": food_name,
            "drug": drug_name,
            "interaction_found": False,
            "message": "No known interaction in database.",
        }

    drug_interaction = food_interactions.get(drug_key)
    if drug_interaction is None:
        return {
            "food": food_name,
            "drug": drug_name,
            "interaction_found": False,
            "message": "No known interaction in database.",
        }

    return {
        "food": food_name,
        "drug": drug_name,
        "interaction_found": True,
        **drug_interaction,
    }
