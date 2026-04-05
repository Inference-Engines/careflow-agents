# CareFlow — AlloyDB Setup Guide

> 한국어 + English bilingual guide for provisioning the CareFlow database layer.
> 본 문서는 CareFlow 의 데이터베이스 계층(Google Cloud AlloyDB for PostgreSQL)을
> 프로비저닝하고, 스키마를 적용하고, Rajesh Sharma 페르소나 시드 데이터를
> 적재하고, MCP Toolbox for Databases 를 연결하는 전 과정을 설명합니다.

---

## 0. Prerequisites / 사전 준비

| 항목 | 설명 |
|---|---|
| `gcloud` CLI | 최신 버전, `gcloud auth login` 완료 |
| GCP 프로젝트 | Billing 활성화, AlloyDB API / Service Networking API 활성화 |
| Region | 본 가이드는 `asia-south1` (Mumbai) 기준 — 페르소나가 인도 거주 |
| 로컬 도구 | `psql` (>=15), Python 3.11+ (옵션, `generate_seed.py` 용) |

```bash
# Enable required APIs / 필수 API 활성화
gcloud services enable \
    alloydb.googleapis.com \
    servicenetworking.googleapis.com \
    compute.googleapis.com
```

---

## 1. AlloyDB 인스턴스 생성 / Provision AlloyDB

AlloyDB 는 VPC Peering 을 사용하므로 먼저 Service Networking 을 구성해야 합니다.
AlloyDB requires a private services connection before the cluster can be created.

```bash
# 1) 환경 변수 / Environment variables
export PROJECT_ID="your-gcp-project"
export REGION="asia-south1"
export CLUSTER="careflow-cluster"
export INSTANCE="careflow-primary"
export NETWORK="default"
export DB_NAME="careflow"
export DB_USER="careflow_app"
export DB_PASS="$(openssl rand -base64 24)"   # 안전하게 보관 / store in Secret Manager

gcloud config set project "$PROJECT_ID"

# 2) Private Services Access 구성 (최초 1회) / one-time VPC setup
gcloud compute addresses create google-managed-services-default \
    --global --purpose=VPC_PEERING --prefix-length=16 \
    --network="projects/${PROJECT_ID}/global/networks/${NETWORK}"

gcloud services vpc-peerings connect \
    --service=servicenetworking.googleapis.com \
    --ranges=google-managed-services-default \
    --network="${NETWORK}"

# 3) AlloyDB 클러스터 생성 / Create cluster
gcloud alloydb clusters create "$CLUSTER" \
    --region="$REGION" \
    --network="projects/${PROJECT_ID}/global/networks/${NETWORK}" \
    --password="$DB_PASS"

# 4) Primary 인스턴스 생성 / Create primary instance
gcloud alloydb instances create "$INSTANCE" \
    --cluster="$CLUSTER" \
    --region="$REGION" \
    --instance-type=PRIMARY \
    --cpu-count=2 \
    --database-flags=google_ml_integration.enable_model_support=on
    # ^ Gemini / Vertex AI embedding 연동 시 필요
    #   Required if you later call Vertex AI embeddings from inside AlloyDB.
```

> **Tip.** AlloyDB 는 `vector` / `pgcrypto` 확장을 기본 제공하므로 별도 설치가
> 필요 없습니다. AlloyDB ships with `pgvector` and `pgcrypto` preinstalled.

---

## 2. DB / 사용자 생성 / Create database and app user

AlloyDB 는 IAM 인증과 PW 인증 둘 다 지원합니다. 여기서는 PW 인증 예시.

```bash
# AlloyDB Auth Proxy 로 터널링 (로컬에서 psql 접속용)
# Tunnel via the AlloyDB Auth Proxy so psql can reach the instance locally.
alloydb-auth-proxy \
    "projects/${PROJECT_ID}/locations/${REGION}/clusters/${CLUSTER}/instances/${INSTANCE}" \
    --port 5432 &

# 관리자(postgres)로 접속 후 DB/계정 생성
PGPASSWORD="$DB_PASS" psql -h 127.0.0.1 -U postgres -d postgres <<SQL
CREATE DATABASE ${DB_NAME};
CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';
GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};
SQL
```

---

## 3. 스키마 적용 / Apply schema

```bash
PGPASSWORD="$DB_PASS" psql \
    -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" \
    -f ./schema.sql
```

확인 / Verify:

```sql
\dt           -- 10개 테이블 + pgvector 인덱스 확인
-- Expected tables:
--   caregivers, patients, medications, medication_changes,
--   appointments, visit_records, tasks, notifications,
--   health_metrics, health_insights

\di idx_visit_embedding    -- ivfflat 인덱스 존재 확인
```

---

## 4. Rajesh Sharma 시드 데이터 삽입 / Load seed data

```bash
PGPASSWORD="$DB_PASS" psql \
    -h 127.0.0.1 -U "$DB_USER" -d "$DB_NAME" \
    -f ./seed_rajesh.sql
```

검증 / Sanity checks:

```sql
-- 환자 1명, 보호자 1명
SELECT name, age, conditions FROM patients;
--  Rajesh Sharma | 63 | {diabetes,hypertension}

-- 약물 5개
SELECT COUNT(*) FROM medications WHERE status = 'active';   -- 5

-- health_metrics = 4 metric_types x 90 days = 360
SELECT metric_type, COUNT(*)
FROM   health_metrics
WHERE  patient_id = '11111111-1111-1111-1111-111111111111'
GROUP BY metric_type;
--  blood_pressure | 90
--  blood_glucose  | 90
--  weight         | 90
--  heart_rate     | 90
```

> **Re-running.** `seed_rajesh.sql` 는 고정 UUID 기반으로 시작 부분에서 기존
> 데이터를 DELETE 하므로 **여러 번 재실행해도 안전**합니다 (idempotent).

### 4.1 (Optional) Python 제너레이터 / Python generator

`seed_rajesh.sql` 의 시계열 블록은 PostgreSQL `generate_series()` 로 직접
만들지만, SQL 을 미리 렌더링해 두고 싶거나 트렌드/노이즈 공식을 튜닝하려면
`generate_seed.py` 를 사용할 수 있습니다.

```bash
python generate_seed.py > health_metrics_inline.sql
# 필요하면 seed_rajesh.sql 의 generate_series 블록과 바꿔치기.
```

### 4.2 Embedding 채우기 / Populating vector embeddings

`visit_records.embedding` 은 시드에서 `NULL` 로 남겨 둡니다. 별도 ingestion
job 이 Gemini `text-embedding-004` (768-dim) 로 채우는 것을 권장합니다.
Leaving embeddings NULL keeps the seed deterministic and offline-friendly.

---

## 5. MCP Toolbox for Databases 설정 / Setup

CareFlow 에이전트들은 AlloyDB 를 MCP Toolbox for Databases 를 통해 조회/쓰기
합니다. MCP Toolbox 는 `tools.yaml` 에 정의된 쿼리만 노출하므로 SQL injection
공격면(attack surface) 이 좁습니다.

### 5.1 설치 / Install

```bash
# macOS / Linux — 바이너리 다운로드
curl -L https://github.com/googleapis/genai-toolbox/releases/latest/download/toolbox-linux-amd64 \
    -o toolbox && chmod +x toolbox
```

### 5.2 `tools.yaml` 예시

```yaml
sources:
  careflow-alloydb:
    kind: postgres
    host: 127.0.0.1          # Auth Proxy 로 터널링된 주소
    port: 5432
    database: careflow
    user: careflow_app
    password: ${CAREFLOW_DB_PASS}   # env var from Secret Manager

tools:
  get_active_medications:
    kind: postgres-sql
    source: careflow-alloydb
    description: "Return all ACTIVE medications for a given patient."
    parameters:
      - name: patient_id
        type: string
        description: "UUID of the patient"
    statement: |
      SELECT name, dosage, frequency, timing, notes
      FROM medications
      WHERE patient_id = $1 AND status = 'active'
      ORDER BY name;

  get_recent_health_metrics:
    kind: postgres-sql
    source: careflow-alloydb
    description: "Return last N days of a given metric_type for a patient."
    parameters:
      - name: patient_id
        type: string
      - name: metric_type
        type: string
      - name: days
        type: integer
    statement: |
      SELECT measured_at, value_primary, value_secondary, unit
      FROM health_metrics
      WHERE patient_id = $1
        AND metric_type = $2
        AND measured_at >= NOW() - ($3 || ' days')::interval
      ORDER BY measured_at ASC;

  search_visit_records:
    kind: postgres-sql
    source: careflow-alloydb
    description: "Vector similarity search over past visit records (pgvector)."
    parameters:
      - name: patient_id
        type: string
      - name: query_embedding
        type: string           # stringified vector literal, e.g. '[0.01,...]'
      - name: top_k
        type: integer
    statement: |
      SELECT id, visit_date, doctor_name, structured_summary,
             1 - (embedding <=> $2::vector) AS similarity
      FROM visit_records
      WHERE patient_id = $1 AND embedding IS NOT NULL
      ORDER BY embedding <=> $2::vector
      LIMIT $3;
```

### 5.3 실행 / Run

```bash
export CAREFLOW_DB_PASS="$DB_PASS"
./toolbox --tools-file ./tools.yaml --port 5000
```

ADK / Claude 에이전트에서는 `http://localhost:5000` 을 MCP 엔드포인트로
등록하면 위의 3개 도구를 tool-call 로 호출할 수 있습니다.
Register `http://localhost:5000` as the MCP endpoint in your ADK / Claude
agent and the three tools above become callable.

---

## 6. Teardown / 정리

```bash
gcloud alloydb instances delete "$INSTANCE" --cluster="$CLUSTER" --region="$REGION" --quiet
gcloud alloydb clusters  delete "$CLUSTER"  --region="$REGION" --quiet
```

---

## 7. 파일 구성 / Files in this directory

| 파일 | 설명 |
|---|---|
| `schema.sql`        | 10 tables + pgvector + ivfflat index — 전체 스키마 DDL |
| `seed_rajesh.sql`   | Rajesh Sharma 페르소나 결정론적 시드 (90일 시계열 포함) |
| `generate_seed.py`  | (옵션) 시계열 INSERT 문을 파이썬으로 재생성 |
| `README.md`         | 본 문서 / this file |
