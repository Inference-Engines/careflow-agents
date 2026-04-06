# ============================================================================
# openFDA Drug Labels API Client
# FDA 공인 약물 라벨 정보 — API 키 불필요, 실시간, 무료
# ============================================================================
# RxNav Interaction API가 2024-01에 deprecated(404)되면서 대체 소스로 도입.
# openFDA의 Drug Label 엔드포인트는 FDA 구조화 제품 라벨(SPL)을 그대로 노출하며,
# drug_interactions / warnings / contraindications / boxed_warning 섹션을 포함.
#
# Replacement for the deprecated RxNav Interaction API. openFDA exposes FDA
# Structured Product Labels (SPL) including drug_interactions, warnings,
# contraindications, and boxed_warning sections. No API key required.
#
# Endpoint:
#   GET https://api.fda.gov/drug/label.json?search=<query>&limit=1
# ============================================================================

from __future__ import annotations

import json
import logging
import ssl
import urllib.parse
import urllib.request
from functools import lru_cache

logger = logging.getLogger(__name__)

# 기업망/사설 인증서 환경에서도 동작하도록 SSL 검증 완화 (rxnorm_api와 동일 정책).
# Relaxed SSL context to tolerate corporate proxies / self-signed chains.
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

_BASE_URL = "https://api.fda.gov/drug/label.json"
_TIMEOUT = 8  # seconds — FDA 엔드포인트는 RxNav보다 약간 느릴 수 있음
_UA = "CareFlow/1.0 (+https://github.com/careflow)"


@lru_cache(maxsize=256)
def get_drug_label(drug_name: str) -> dict | None:
    """약물 라벨을 openFDA에서 조회하여 정규화된 dict로 반환.

    Fetch the FDA drug label for a given drug name and return a normalized dict.

    Returned fields:
        - brand_name, generic_name
        - drug_interactions:    list[str]
        - warnings:             list[str]
        - contraindications:    list[str]
        - boxed_warning:        list[str]  (black box warning, if any)
        - dosage_and_administration: list[str]

    Returns None when the drug is not found or the API is unreachable.
    결과는 프로세스 내 LRU 캐시로 보존된다.
    """
    name = (drug_name or "").strip()
    if not name:
        return None

    try:
        # brand_name / generic_name 양쪽 모두에서 검색 (대소문자 무관은 FDA 쪽 토큰화에 위임).
        # Search both brand_name and generic_name fields.
        query = (
            f'(openfda.brand_name:"{name}" OR openfda.generic_name:"{name}")'
        )
        url = f"{_BASE_URL}?search={urllib.parse.quote(query)}&limit=1"

        req = urllib.request.Request(
            url,
            headers={"User-Agent": _UA, "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=_TIMEOUT, context=_CTX) as resp:
            data = json.loads(resp.read())

        results = data.get("results", []) or []
        if not results:
            logger.debug("openfda.label_not_found: %s", name)
            return None

        label = results[0]
        openfda = label.get("openfda", {}) or {}

        return {
            "brand_name": (openfda.get("brand_name") or [name])[0],
            "generic_name": (openfda.get("generic_name") or [name])[0],
            "drug_interactions": label.get("drug_interactions", []) or [],
            "warnings": label.get("warnings", []) or [],
            "contraindications": label.get("contraindications", []) or [],
            "boxed_warning": label.get("boxed_warning", []) or [],
            "dosage_and_administration": label.get("dosage_and_administration", []) or [],
        }
    except Exception as e:  # noqa: BLE001
        logger.warning("openfda.get_drug_label failed for %r: %s", drug_name, e)
        return None


def check_drug_interactions_via_fda(
    new_drug: str,
    current_drugs: list[str],
) -> dict:
    """new_drug 라벨의 상호작용/경고/금기 섹션을 스캔하여 current_drugs 언급을 찾는다.

    Text-analysis over the new drug's FDA label:
      1. fetch the label for `new_drug`
      2. concatenate drug_interactions + warnings + contraindications
      3. for each drug in `current_drugs`, check if mentioned in the combined text
      4. infer severity from the section it appeared in
         (contraindications > warnings > drug_interactions)

    This is intentionally conservative — a substring hit in the label is treated
    as a candidate interaction that deserves clinician review. False positives
    are acceptable; false negatives are not.

    Returns:
        {
          "status": "checked" | "drug_not_found" | "no_interaction_data",
          "drug": <new_drug>,
          "source": "openfda",
          "interaction_count": int,
          "interactions": [ { drug_pair, severity, description, source }, ... ],
        }
    """
    label = get_drug_label(new_drug)
    if not label:
        return {"status": "drug_not_found", "drug": new_drug, "source": "openfda"}

    interactions_text = " ".join(label.get("drug_interactions", [])).lower()
    warnings_text = " ".join(label.get("warnings", [])).lower()
    contra_text = " ".join(label.get("contraindications", [])).lower()
    combined = f"{interactions_text} {warnings_text} {contra_text}"

    if not combined.strip():
        return {
            "status": "no_interaction_data",
            "drug": new_drug,
            "source": "openfda",
        }

    # 각 현재 복용 약물에 대해 섹션별로 언급 여부를 검사.
    # For each current drug, check mentions in the combined label sections.
    found_interactions: list[dict] = []
    for current_drug in current_drugs or []:
        current_lower = (current_drug or "").strip().lower()
        if not current_lower or current_lower not in combined:
            continue

        # 섹션별 우선순위로 severity 추론.
        # Infer severity from which section contained the mention
        # (contraindications is strictest, then warnings, then interactions).
        if current_lower in contra_text:
            severity = "CONTRAINDICATED"
        elif current_lower in warnings_text:
            severity = "HIGH"
        elif current_lower in interactions_text:
            severity = "MODERATE"
        else:
            severity = "UNKNOWN"

        # 주변 컨텍스트 추출 (best-effort) — 임상의 검토를 돕기 위한 발췌.
        # Extract surrounding context as best-effort excerpt for clinician review.
        idx = combined.find(current_lower)
        context = combined[max(0, idx - 150): idx + 200] if idx >= 0 else ""

        found_interactions.append({
            "drug_pair": [new_drug, current_drug],
            "severity": severity,
            "description": context.strip()[:400],
            "source": "openfda_drug_label",
        })

    return {
        "status": "checked",
        "drug": new_drug,
        "source": "openfda",
        "interaction_count": len(found_interactions),
        "interactions": found_interactions,
    }
