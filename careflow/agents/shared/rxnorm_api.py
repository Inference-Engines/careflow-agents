# ============================================================================
# NIH RxNav API Client  (Drug Name Normalization Only)
# 미국 국립의학도서관(NLM) RxNav — 무료, API 키 불필요
# ============================================================================
# RxNav는 여전히 약물명 정규화(RxCUI 조회)에는 유효한 권위 소스이다.
# 그러나 RxNav /interaction/list 엔드포인트는 2024-01에 deprecated되어 404를
# 반환하므로, 상호작용 검증은 openFDA Drug Labels(shared.openfda_api)로 이관.
#
# RxNav is still the authoritative source for drug-name -> RxCUI normalization.
# However the /interaction/list endpoint was DEPRECATED in Jan 2024 (returns
# 404), so interaction checking has been migrated to openFDA Drug Labels.
# See: careflow.agents.shared.openfda_api
#
# Endpoints still used:
#   GET /rxcui.json?name={drug}  — resolve drug name -> RxCUI
# Deprecated (kept for API compatibility, emits warning):
#   check_interaction_pair(), check_medication_list()
# ============================================================================

from __future__ import annotations

import json
import logging
import ssl
import urllib.parse
import urllib.request
import warnings
from functools import lru_cache
from itertools import combinations

logger = logging.getLogger(__name__)

# 일부 기업망/사설 인증서 환경에서도 동작하도록 SSL 검증을 완화.
# Relaxed SSL context to tolerate corporate proxies / self-signed chains.
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

_BASE_URL = "https://rxnav.nlm.nih.gov/REST"
_TIMEOUT = 5  # seconds
_UA = "CareFlow/1.0 (+https://github.com/careflow)"


def _http_get_json(url: str) -> dict:
    """단순 GET → JSON 파서. 공용 헬퍼.

    Minimal GET helper returning parsed JSON. Raises on network/parse error.
    """
    req = urllib.request.Request(
        url,
        headers={"User-Agent": _UA, "Accept": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=_TIMEOUT, context=_CTX) as resp:
        return json.loads(resp.read())


@lru_cache(maxsize=256)
def get_rxcui(drug_name: str) -> str | None:
    """약물명 → RxCUI(표준 식별자) 조회. 프로세스 내 캐시 유지.

    Resolve a drug name to its RxCUI. Results are cached per-process.
    Returns None if the drug is not found or the API is unreachable.
    """
    name = (drug_name or "").strip()
    if not name:
        return None
    try:
        url = f"{_BASE_URL}/rxcui.json?name={urllib.parse.quote(name.lower())}"
        data = _http_get_json(url)
        ids = data.get("idGroup", {}).get("rxnormId", []) or []
        return ids[0] if ids else None
    except Exception as e:  # noqa: BLE001
        logger.debug("rxnav.get_rxcui failed for %r: %s", drug_name, e)
        return None


@lru_cache(maxsize=256)
def normalize_drug_name(name: str) -> str:
    """약물명을 RxNorm 표준 이름으로 정규화 (brand → generic 매핑 포함).

    Normalize a drug name to its RxNorm standard name. This resolves brand
    names to their canonical form (e.g. "Tylenol" -> "acetaminophen") by
    round-tripping through RxCUI. If RxNav is unreachable or the drug is
    unknown, returns the input stripped/lowercased unchanged.

    Used by the openFDA interaction checker to improve label-match recall
    when the user provides a brand name but the label uses the generic
    (or vice-versa).
    """
    raw = (name or "").strip()
    if not raw:
        return raw

    rxcui = get_rxcui(raw)
    if not rxcui:
        return raw.lower()

    try:
        # /rxcui/{rxcui}/property.json?propName=RxNorm%20Name
        url = (
            f"{_BASE_URL}/rxcui/{urllib.parse.quote(rxcui)}"
            f"/property.json?propName=RxNorm%20Name"
        )
        data = _http_get_json(url)
        props = (
            data.get("propConceptGroup", {}).get("propConcept", []) or []
        )
        if props:
            normalized = (props[0].get("propValue") or "").strip()
            if normalized:
                return normalized.lower()
    except Exception as e:  # noqa: BLE001
        logger.debug("rxnav.normalize_drug_name failed for %r: %s", name, e)

    return raw.lower()


def check_interaction_pair(drug1: str, drug2: str) -> dict:
    """[DEPRECATED] 두 약물 간 상호작용 조회. RxNav /interaction/list는 2024-01 단종됨.

    .. deprecated::
        RxNav's /interaction/list endpoint was retired in January 2024 and now
        returns HTTP 404. Use
        ``careflow.agents.shared.openfda_api.check_drug_interactions_via_fda``
        instead. This stub is retained for backward-compatible imports and
        will always return ``status="deprecated"``.
    """
    warnings.warn(
        "rxnorm_api.check_interaction_pair is deprecated: RxNav /interaction/list "
        "was retired in Jan 2024. Use shared.openfda_api.check_drug_interactions_via_fda.",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.warning(
        "rxnav.check_interaction_pair is DEPRECATED (RxNav /interaction/list "
        "retired 2024-01). Caller should migrate to openfda_api."
    )
    return {
        "status": "deprecated",
        "drugs": [drug1, drug2],
        "source": "rxnav_deprecated",
        "message": (
            "RxNav /interaction/list was deprecated in 2024-01. "
            "Use shared.openfda_api.check_drug_interactions_via_fda."
        ),
    }


def _legacy_check_interaction_pair(drug1: str, drug2: str) -> dict:
    """[LEGACY, UNUSED] 원래 RxNav 호출 로직 — 참고용으로만 보존.

    Original implementation kept only for historical reference. Do not call.
    """
    rxcui1 = get_rxcui(drug1)
    rxcui2 = get_rxcui(drug2)
    if not rxcui1 or not rxcui2:
        return {
            "status": "unknown",
            "drugs": [drug1, drug2],
            "source": "rxnav_not_found",
            "missing_rxcui": [
                name for name, cui in ((drug1, rxcui1), (drug2, rxcui2)) if not cui
            ],
        }

    try:
        url = f"{_BASE_URL}/interaction/list.json?rxcuis={rxcui1}+{rxcui2}"
        data = _http_get_json(url)
    except Exception as e:  # noqa: BLE001
        logger.warning("rxnav.check_interaction_pair failed: %s", e)
        return {
            "status": "api_error",
            "drugs": [drug1, drug2],
            "error": str(e)[:100],
        }

    interactions: list[dict] = []
    for group in data.get("fullInteractionTypeGroup", []) or []:
        for itype in group.get("fullInteractionType", []) or []:
            for pair in itype.get("interactionPair", []) or []:
                interactions.append({
                    "severity": pair.get("severity", "N/A"),
                    "description": (pair.get("description", "") or "")[:300],
                    "source_drugbank": True,
                })

    if interactions:
        return {
            "status": "interactions_found",
            "drugs": [drug1, drug2],
            "source": "rxnav_drugbank",
            "interaction_count": len(interactions),
            "interactions": interactions,
        }
    return {
        "status": "no_interactions",
        "drugs": [drug1, drug2],
        "source": "rxnav_drugbank",
    }


def check_medication_list(medications: list[str]) -> dict:
    """[DEPRECATED] 복약 목록 전체 쌍 상호작용 스캔. RxNav 종단이 단종되어 사용 불가.

    .. deprecated::
        Depends on the retired RxNav /interaction/list endpoint. Use the
        openFDA-backed checker in ``careflow.agents.task.tools.check_drug_interactions``
        (which calls ``shared.openfda_api.check_drug_interactions_via_fda``).
    """
    warnings.warn(
        "rxnorm_api.check_medication_list is deprecated: RxNav /interaction/list "
        "was retired in Jan 2024. Use task.tools.check_drug_interactions.",
        DeprecationWarning,
        stacklevel=2,
    )
    logger.warning(
        "rxnav.check_medication_list is DEPRECATED — upstream endpoint retired."
    )
    # combinations는 단순 시그니처 호환 목적으로 참조만 해 둠.
    _ = combinations
    return {
        "status": "deprecated",
        "medications": medications or [],
        "source": "rxnav_deprecated",
        "message": (
            "RxNav /interaction/list was deprecated in 2024-01. "
            "Use task.tools.check_drug_interactions (openFDA-backed)."
        ),
    }
