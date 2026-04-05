-- =============================================================================
-- CareFlow Database Schema (AlloyDB / PostgreSQL 15+)
-- =============================================================================
-- 목적 (Purpose):
--   만성질환 (당뇨 + 고혈압) 환자의 방문 후 케어(post-visit care)를 위한
--   멀티 에이전트 시스템 CareFlow 의 핵심 데이터 저장소 스키마.
--   Primary data store for the CareFlow multi-agent post-visit care system
--   targeting chronic disease patients (DM2 + HTN).
--
-- 대상 DB (Target DB):
--   Google Cloud AlloyDB for PostgreSQL (with pgvector preinstalled)
--   Compatible with vanilla PostgreSQL >= 15 + pgvector >= 0.5.0
--
-- 설계 원칙 (Design Principles):
--   1) 모든 PK 는 UUID (gen_random_uuid) — 분산 환경/에이전트 병렬 INSERT 안전
--      All PKs are UUIDs — safe for distributed / parallel agent inserts.
--   2) visit_records 는 RAG 용 vector(768) 임베딩을 포함 (text-embedding-004).
--      visit_records carries a 768-dim embedding for RAG (text-embedding-004).
--   3) health_metrics 는 시계열(time-series) 최적화 복합 인덱스 사용.
--      health_metrics uses a composite index tuned for time-series queries.
--   4) 외래키는 ON DELETE CASCADE 로 환자 탈퇴(GDPR/DPDP) 대응.
--      FKs use ON DELETE CASCADE to support right-to-erasure workflows.
-- =============================================================================

-- -----------------------------------------------------------------------------
-- Extensions
-- -----------------------------------------------------------------------------
-- pgvector : 벡터 유사도 검색 (visit_records RAG)
-- pgcrypto : gen_random_uuid() 를 위해 필요 (AlloyDB 에는 기본 포함)
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pgcrypto;

-- =============================================================================
-- 1) caregivers  —  보호자 정보 / Caregiver information
-- =============================================================================
-- patients 가 caregiver_id 를 참조하므로 caregivers 를 먼저 생성.
-- Must be created before `patients` because of the FK direction.
CREATE TABLE IF NOT EXISTS caregivers (
    id                       UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name                     VARCHAR(100)  NOT NULL,
    email                    VARCHAR(255)  NOT NULL,   -- Gmail MCP 발송 주소
    phone                    VARCHAR(30),
    relationship             VARCHAR(50),              -- daughter | son | spouse | ...
    location                 VARCHAR(100),             -- e.g., 'Bangalore, IN'
    notification_preferences JSONB         DEFAULT '{}'::jsonb,
                                                        -- { "frequency": "daily",
                                                        --   "channels": ["email"],
                                                        --   "quiet_hours": "22:00-07:00" }
    created_at               TIMESTAMP     DEFAULT NOW()
);

COMMENT ON TABLE  caregivers IS 'Family caregivers who receive CareFlow notifications (Gmail MCP target).';
COMMENT ON COLUMN caregivers.notification_preferences IS 'JSONB: frequency/channels/quiet_hours etc.';

-- =============================================================================
-- 2) patients  —  환자 기본 정보 / Patient master
-- =============================================================================
CREATE TABLE IF NOT EXISTS patients (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(100) NOT NULL,
    age             INTEGER       CHECK (age BETWEEN 0 AND 130),
    gender          VARCHAR(10),                        -- male | female | other
    conditions      TEXT[]        NOT NULL DEFAULT '{}',-- {'diabetes','hypertension'}
    language        VARCHAR(10)   DEFAULT 'en',         -- i18n for voice UX
    phone           VARCHAR(30),
    caregiver_id    UUID          REFERENCES caregivers(id) ON DELETE SET NULL,
    created_at      TIMESTAMP     DEFAULT NOW(),
    updated_at      TIMESTAMP     DEFAULT NOW()
);

COMMENT ON COLUMN patients.conditions IS 'Array of ICD-ish condition tags, e.g. {diabetes, hypertension}.';
CREATE INDEX IF NOT EXISTS idx_patients_caregiver ON patients(caregiver_id);

-- =============================================================================
-- 3) medications  —  약물 처방 / Current & historical medications
-- =============================================================================
CREATE TABLE IF NOT EXISTS medications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    name            VARCHAR(200) NOT NULL,             -- e.g., 'Metformin'
    dosage          VARCHAR(100),                      -- e.g., '1000mg'
    frequency       VARCHAR(100),                      -- e.g., 'twice_daily'
    timing          VARCHAR(100),                      -- e.g., 'with_meals'
    route           VARCHAR(30)  DEFAULT 'oral',       -- oral | injection | topical
    status          VARCHAR(20)  DEFAULT 'active'
                    CHECK (status IN ('active','discontinued','modified','paused')),
    prescribed_date DATE,
    end_date        DATE,
    notes           TEXT,
    created_at      TIMESTAMP    DEFAULT NOW(),
    updated_at      TIMESTAMP    DEFAULT NOW()
);

-- 자주 쓰는 조회: "이 환자의 현재(active) 복용 약물 전체"
-- Hot path: "list all ACTIVE medications for patient X"
CREATE INDEX IF NOT EXISTS idx_medications_patient ON medications(patient_id, status);

-- =============================================================================
-- 4) medication_changes  —  약물 변경 이력 / Medication change log
-- =============================================================================
-- 약물이 추가/변경/중단될 때마다 한 행씩 append-only 로 기록.
-- Append-only audit log for every medication change event.
CREATE TABLE IF NOT EXISTS medication_changes (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    medication_id   UUID REFERENCES medications(id) ON DELETE CASCADE,
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    change_type     VARCHAR(20) NOT NULL
                    CHECK (change_type IN ('new','dosage_change','frequency_change',
                                           'discontinued','resumed')),
    previous_dosage VARCHAR(100),
    new_dosage      VARCHAR(100),
    reason          TEXT,                              -- 의사 메모 / doctor's reasoning
    changed_by      VARCHAR(100),                      -- e.g., 'Dr. Mehta'
    changed_at      TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_medication_changes_patient
    ON medication_changes(patient_id, changed_at DESC);

-- =============================================================================
-- 5) appointments  —  예약 / Appointments
-- =============================================================================
CREATE TABLE IF NOT EXISTS appointments (
    id                UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id        UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    type              VARCHAR(50),                     -- follow_up | lab_test | specialist
    title             VARCHAR(200),
    scheduled_date    TIMESTAMP NOT NULL,
    location          VARCHAR(200),
    notes             TEXT,
    fasting_required  BOOLEAN   DEFAULT FALSE,
    calendar_event_id VARCHAR(200),                    -- Google Calendar event id (MCP)
    status            VARCHAR(20) DEFAULT 'scheduled'
                      CHECK (status IN ('scheduled','completed','cancelled','no_show')),
    created_at        TIMESTAMP  DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id, scheduled_date);

-- =============================================================================
-- 6) visit_records  —  방문 기록 (+ vector embedding for RAG)
-- =============================================================================
-- Medical Info Agent 가 RAG 검색의 source-of-truth 로 사용.
-- embedding 은 Gemini text-embedding-004 (768 dim).
CREATE TABLE IF NOT EXISTS visit_records (
    id                 UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id         UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    visit_date         DATE NOT NULL,
    raw_input          TEXT,                           -- 원본 음성/텍스트 입력
    structured_summary TEXT,                           -- LLM 이 정리한 요약
    doctor_name        VARCHAR(100),
    hospital_name      VARCHAR(200),
    key_findings       JSONB,                          -- { "bp":"high", "hba1c":8.2 ... }
    embedding          vector(768),                    -- text-embedding-004
    created_at         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_visit_records_patient
    ON visit_records(patient_id, visit_date DESC);

-- pgvector ivfflat 인덱스 — 코사인 유사도 기준.
-- NOTE: ivfflat 는 테이블에 데이터가 어느 정도 쌓인 후(최소 ~1000행 권장)에
--        ANALYZE 를 다시 돌리면 리콜이 개선됨.
-- NOTE: Re-run ANALYZE once you have ~1k+ rows for better ivfflat recall.
CREATE INDEX IF NOT EXISTS idx_visit_embedding
    ON visit_records USING ivfflat (embedding vector_cosine_ops)
    WITH (lists = 100);

-- =============================================================================
-- 7) tasks  —  할 일 / Action items
-- =============================================================================
CREATE TABLE IF NOT EXISTS tasks (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id       UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    description      TEXT NOT NULL,
    due_date         DATE,
    priority         VARCHAR(10) DEFAULT 'medium'
                     CHECK (priority IN ('low','medium','high','urgent')),
    status           VARCHAR(20) DEFAULT 'pending'
                     CHECK (status IN ('pending','in_progress','completed','overdue','cancelled')),
    created_by_agent VARCHAR(50),                     -- e.g., 'medical_info_agent'
    related_visit_id UUID REFERENCES visit_records(id) ON DELETE SET NULL,
    created_at       TIMESTAMP DEFAULT NOW(),
    completed_at     TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tasks_patient_status ON tasks(patient_id, status);

-- =============================================================================
-- 8) notifications  —  알림 로그 / Notification delivery log
-- =============================================================================
CREATE TABLE IF NOT EXISTS notifications (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID REFERENCES patients(id) ON DELETE CASCADE,
    caregiver_id    UUID REFERENCES caregivers(id) ON DELETE SET NULL,
    type            VARCHAR(30),                      -- visit_update | weekly_digest | alert | insight
    content         JSONB,                            -- { "subject": "...", "body": "..." }
    delivery_method VARCHAR(20),                      -- email | push | sms
    status          VARCHAR(20) DEFAULT 'sent'
                    CHECK (status IN ('pending','sent','failed','bounced')),
    error_message   TEXT,
    sent_at         TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_notifications_patient ON notifications(patient_id, sent_at DESC);

-- =============================================================================
-- 9) health_metrics  —  건강 지표 시계열 / Health metrics time-series
-- =============================================================================
-- Health Insight Agent 가 트렌드/상관관계 분석에 사용.
-- Used by Health Insight Agent for trend & correlation analysis.
CREATE TABLE IF NOT EXISTS health_metrics (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id      UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    metric_type     VARCHAR(50) NOT NULL,             -- blood_pressure | blood_glucose | weight | heart_rate
    value_primary   DECIMAL(10,2),                    -- systolic BP | fasting glucose | kg | bpm
    value_secondary DECIMAL(10,2),                    -- diastolic BP (nullable)
    unit            VARCHAR(20),                      -- mmHg | mg/dL | kg | bpm
    measured_at     TIMESTAMP NOT NULL,
    source          VARCHAR(50),                      -- visit | self_report | device
    notes           TEXT,
    created_at      TIMESTAMP DEFAULT NOW()
);

-- 시계열 최적화 복합 인덱스:
-- "환자 X 의 혈압을 최근 90일 범위로 시간순 조회" 쿼리 패턴을 커버.
-- Composite index tuned for: "all metrics of type M for patient P
--                              within [start, end] ORDER BY measured_at".
CREATE INDEX IF NOT EXISTS idx_health_metrics_patient
    ON health_metrics(patient_id, metric_type, measured_at DESC);

-- =============================================================================
-- 10) health_insights  —  AI 생성 인사이트 / AI-generated insights
-- =============================================================================
CREATE TABLE IF NOT EXISTS health_insights (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    patient_id       UUID NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    insight_type     VARCHAR(30),                     -- trend_alert | correlation |
                                                       -- pre_visit_summary | recommendation
    severity         VARCHAR(10) DEFAULT 'info'
                     CHECK (severity IN ('info','warning','urgent')),
    title            VARCHAR(200),
    content          TEXT NOT NULL,
    data_range_start DATE,
    data_range_end   DATE,
    supporting_data  JSONB,                           -- raw data points used
    acknowledged     BOOLEAN DEFAULT FALSE,
    acknowledged_by  VARCHAR(100),
    acknowledged_at  TIMESTAMP,
    created_at       TIMESTAMP DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_health_insights_patient
    ON health_insights(patient_id, insight_type, created_at DESC);

-- =============================================================================
-- End of schema.sql
-- =============================================================================
