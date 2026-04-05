-- =============================================================================
-- CareFlow Seed Data — Rajesh Sharma Persona
-- =============================================================================
-- 페르소나 (Persona):
--   Rajesh Sharma, 63세 남성, 인도 Mumbai 거주.
--   진단: Type 2 Diabetes (DM2) + Hypertension (HTN).
--   주 보호자(primary caregiver): 딸 Priya Sharma, Bangalore 거주.
--
-- Persona:
--   Rajesh Sharma, 63, male, lives in Mumbai, India.
--   Diagnosis: Type 2 diabetes + hypertension.
--   Primary caregiver: daughter Priya Sharma in Bangalore.
--
-- 이 파일은 결정론적(deterministic) 시드:
--   고정 UUID 사용 → 테스트/CI 에서 assert 가능, 멱등적으로 재실행 가능.
--   Uses fixed UUIDs so tests can assert against them; safe to re-run with
--   a TRUNCATE beforehand.
--
-- 시계열 데이터(health_metrics) 는 generate_series() + 수식으로 생성하여
--   90일치 혈압/혈당/체중/심박수를 한 번의 INSERT 로 채워 넣는다.
-- Time-series data is generated via generate_series() so that 90 days of
-- BP / glucose / weight / heart rate are seeded in a single statement each.
-- =============================================================================

BEGIN;

-- -----------------------------------------------------------------------------
-- 멱등 재실행을 위한 정리 (Idempotent reset for Rajesh's data only)
-- -----------------------------------------------------------------------------
-- 고정 UUID 로만 지우므로 다른 시드 데이터와 충돌하지 않음.
DELETE FROM health_insights    WHERE patient_id   = '11111111-1111-1111-1111-111111111111';
DELETE FROM health_metrics     WHERE patient_id   = '11111111-1111-1111-1111-111111111111';
DELETE FROM notifications      WHERE patient_id   = '11111111-1111-1111-1111-111111111111';
DELETE FROM tasks              WHERE patient_id   = '11111111-1111-1111-1111-111111111111';
DELETE FROM visit_records      WHERE patient_id   = '11111111-1111-1111-1111-111111111111';
DELETE FROM appointments       WHERE patient_id   = '11111111-1111-1111-1111-111111111111';
DELETE FROM medication_changes WHERE patient_id   = '11111111-1111-1111-1111-111111111111';
DELETE FROM medications        WHERE patient_id   = '11111111-1111-1111-1111-111111111111';
DELETE FROM patients           WHERE id           = '11111111-1111-1111-1111-111111111111';
DELETE FROM caregivers         WHERE id           = '22222222-2222-2222-2222-222222222222';

-- =============================================================================
-- 1) caregivers — Priya Sharma (딸 / daughter)
-- =============================================================================
INSERT INTO caregivers (id, name, email, phone, relationship, location, notification_preferences)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    'Priya Sharma',
    'priya.sharma@example.com',
    '+91-98765-43210',
    'daughter',
    'Bangalore, IN',
    '{"frequency":"daily","channels":["email"],"quiet_hours":"22:00-07:00","language":"en"}'::jsonb
);

-- =============================================================================
-- 2) patients — Rajesh Sharma
-- =============================================================================
INSERT INTO patients (id, name, age, gender, conditions, language, phone, caregiver_id)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'Rajesh Sharma',
    63,
    'male',
    ARRAY['diabetes','hypertension'],
    'en',
    '+91-98111-22334',
    '22222222-2222-2222-2222-222222222222'
);

-- =============================================================================
-- 3) medications — 5개 / 5 active meds
-- =============================================================================
-- 고정 UUID 로 medication_changes FK 를 안정적으로 연결.
INSERT INTO medications (id, patient_id, name, dosage, frequency, timing, status, prescribed_date, notes)
VALUES
    ('aaaaaaa1-0000-0000-0000-000000000001', '11111111-1111-1111-1111-111111111111',
     'Metformin',    '1000mg', 'twice_daily', 'with_meals', 'active', '2024-06-15',
     'First-line DM2. Dosage increased from 500mg to 1000mg on 2026-01-10.'),
    ('aaaaaaa1-0000-0000-0000-000000000002', '11111111-1111-1111-1111-111111111111',
     'Amlodipine',   '5mg',    'once_daily',  'morning',    'active', '2024-06-15',
     'Calcium channel blocker for HTN.'),
    ('aaaaaaa1-0000-0000-0000-000000000003', '11111111-1111-1111-1111-111111111111',
     'Aspirin',      '75mg',   'once_daily',  'after_dinner','active','2024-06-15',
     'Low-dose cardioprotective.'),
    ('aaaaaaa1-0000-0000-0000-000000000004', '11111111-1111-1111-1111-111111111111',
     'Atorvastatin', '20mg',   'once_daily',  'bedtime',    'active', '2024-06-15',
     'For dyslipidemia. LDL target <100 mg/dL.'),
    ('aaaaaaa1-0000-0000-0000-000000000005', '11111111-1111-1111-1111-111111111111',
     'Lisinopril',   '10mg',   'once_daily',  'morning',    'active', '2025-09-20',
     'ACE inhibitor added for renoprotection.');

-- 약물 변경 이력: Metformin 증량 이벤트
INSERT INTO medication_changes
    (medication_id, patient_id, change_type, previous_dosage, new_dosage, reason, changed_by, changed_at)
VALUES
    ('aaaaaaa1-0000-0000-0000-000000000001',
     '11111111-1111-1111-1111-111111111111',
     'dosage_change', '500mg', '1000mg',
     'Fasting glucose trending above 140 mg/dL over 4 weeks; HbA1c 8.1%.',
     'Dr. Mehta', '2026-01-10 10:30:00'),
    ('aaaaaaa1-0000-0000-0000-000000000005',
     '11111111-1111-1111-1111-111111111111',
     'new', NULL, '10mg',
     'Added Lisinopril for renoprotection given microalbuminuria.',
     'Dr. Mehta', '2025-09-20 11:15:00');

-- =============================================================================
-- 4) appointments — 과거 2 완료 + 미래 2 예정
-- =============================================================================
INSERT INTO appointments
    (id, patient_id, type, title, scheduled_date, location, notes, fasting_required, status)
VALUES
    -- 과거 완료 / past completed
    ('bbbbbbb1-0000-0000-0000-000000000001',
     '11111111-1111-1111-1111-111111111111',
     'follow_up', 'Routine diabetes follow-up',
     '2026-01-10 10:00:00', 'Apollo Clinic, Mumbai',
     'Quarterly DM2 + HTN review. Metformin uptitrated.',
     FALSE, 'completed'),
    ('bbbbbbb1-0000-0000-0000-000000000002',
     '11111111-1111-1111-1111-111111111111',
     'lab_test', 'Fasting lipid panel + HbA1c',
     '2026-02-14 08:00:00', 'SRL Diagnostics, Mumbai',
     'Fasting required. Results reviewed on 2026-02-20.',
     TRUE, 'completed'),
    -- 미래 예정 / upcoming
    ('bbbbbbb1-0000-0000-0000-000000000003',
     '11111111-1111-1111-1111-111111111111',
     'lab_test', 'HbA1c recheck (3-month)',
     '2026-04-18 08:00:00', 'SRL Diagnostics, Mumbai',
     'Fasting required. Post Metformin uptitration recheck.',
     TRUE, 'scheduled'),
    ('bbbbbbb1-0000-0000-0000-000000000004',
     '11111111-1111-1111-1111-111111111111',
     'follow_up', 'Endocrinology follow-up with Dr. Mehta',
     '2026-04-25 10:30:00', 'Apollo Clinic, Mumbai',
     'Review HbA1c, BP trend, med adherence.',
     FALSE, 'scheduled');

-- =============================================================================
-- 5) visit_records — 최근 3개월 방문 기록 3건 (embedding 은 NULL 로 두고
--    별도 ingestion job 이 text-embedding-004 로 채우는 것을 권장)
-- =============================================================================
INSERT INTO visit_records
    (id, patient_id, visit_date, raw_input, structured_summary,
     doctor_name, hospital_name, key_findings, embedding)
VALUES
    ('ccccccc1-0000-0000-0000-000000000001',
     '11111111-1111-1111-1111-111111111111',
     '2026-01-10',
     'Doctor said my sugar has been too high, he increased the metformin dose. Also asked me to reduce salt in my food.',
     'DM2 + HTN follow-up. HbA1c 8.1% (up from 7.4%). Metformin increased from 500mg BD to 1000mg BD. BP 138/88. Advised low-sodium diet (<2g/day) and daily home BP monitoring.',
     'Dr. Mehta', 'Apollo Clinic, Mumbai',
     '{"hba1c":8.1,"bp_systolic":138,"bp_diastolic":88,"advice":["low_sodium","daily_home_bp"],"med_changes":["metformin_500_to_1000"]}'::jsonb,
     NULL),
    ('ccccccc1-0000-0000-0000-000000000002',
     '11111111-1111-1111-1111-111111111111',
     '2026-02-20',
     'Got my blood test results. Doctor said cholesterol is okay but sugar still slightly high. Continue same medicines.',
     'Lab review visit. HbA1c 7.6% (improving). LDL 92 mg/dL (at target). Fasting glucose 132 mg/dL. Continue current regimen. Reinforced dietary counseling.',
     'Dr. Mehta', 'Apollo Clinic, Mumbai',
     '{"hba1c":7.6,"ldl":92,"fasting_glucose":132,"plan":"continue_regimen"}'::jsonb,
     NULL),
    ('ccccccc1-0000-0000-0000-000000000003',
     '11111111-1111-1111-1111-111111111111',
     '2026-03-18',
     'My blood pressure readings at home have been going up lately. Doctor checked and said to watch it closely.',
     'Interim visit for rising home BP readings. In-clinic BP 142/90. No new symptoms. Advised continued Amlodipine + Lisinopril, sodium <2g/day, re-evaluate in 4 weeks. Consider dose adjustment if trend persists.',
     'Dr. Mehta', 'Apollo Clinic, Mumbai',
     '{"bp_systolic":142,"bp_diastolic":90,"trend":"rising","action":"monitor_4_weeks"}'::jsonb,
     NULL);

-- =============================================================================
-- 6) tasks — 5개 / 5 action items
-- =============================================================================
INSERT INTO tasks
    (patient_id, description, due_date, priority, status, created_by_agent, related_visit_id)
VALUES
    ('11111111-1111-1111-1111-111111111111',
     'HbA1c 재검사 (fasting) — SRL Diagnostics / HbA1c recheck (fasting)',
     '2026-04-18', 'high', 'pending',
     'medical_info_agent', 'ccccccc1-0000-0000-0000-000000000002'),
    ('11111111-1111-1111-1111-111111111111',
     '일일 나트륨 섭취 2g 이하로 제한 / Limit daily sodium intake below 2g',
     '2026-04-30', 'high', 'in_progress',
     'diet_nutrition_agent', 'ccccccc1-0000-0000-0000-000000000001'),
    ('11111111-1111-1111-1111-111111111111',
     '매일 아침/저녁 가정 혈압 측정 및 기록 / Measure & log home BP twice daily',
     '2026-04-30', 'high', 'in_progress',
     'health_insight_agent', 'ccccccc1-0000-0000-0000-000000000003'),
    ('11111111-1111-1111-1111-111111111111',
     'Metformin 1000mg 식사와 함께 하루 2회 복용 / Take Metformin 1000mg twice daily with meals',
     '2026-04-30', 'urgent', 'in_progress',
     'task_agent', 'ccccccc1-0000-0000-0000-000000000001'),
    ('11111111-1111-1111-1111-111111111111',
     '주 3회 30분 산책 / 30-minute walk 3x per week',
     '2026-04-30', 'medium', 'pending',
     'diet_nutrition_agent', NULL);

-- =============================================================================
-- 7) health_metrics — 90일 시계열 / 90-day time-series
-- =============================================================================
-- 기준일: 2026-04-05 (today). 90일 전부터 오늘까지, 매일 1회 측정.
-- Day 0 = 2026-01-05, Day 89 = 2026-04-04.
--
-- 설계 의도 / Design intent:
--   blood_pressure  : 135/85 → 142/90 로 점진적 상승 (인사이트 트리거용)
--   blood_glucose   : 145 → 128 로 개선 (Metformin 증량 효과)
--   weight          : 72kg 근방 안정 (+/- 0.8kg 노이즈)
--   heart_rate      : 74bpm 근방 안정 (+/- 4bpm 노이즈)
--
-- 결정론적 노이즈: sin(day) 기반 — 재실행 시 동일한 값 보장.
-- Deterministic noise via sin(day) so reruns reproduce identical values.

-- 혈압 / Blood pressure (mmHg)
INSERT INTO health_metrics
    (patient_id, metric_type, value_primary, value_secondary, unit, measured_at, source)
SELECT
    '11111111-1111-1111-1111-111111111111',
    'blood_pressure',
    -- systolic: 135 → 142 linear + small oscillation
    ROUND( (135 + (day::numeric / 89) * 7 + 2 * SIN(day::numeric / 3))::numeric, 0 ),
    -- diastolic: 85 → 90 linear + small oscillation
    ROUND( (85  + (day::numeric / 89) * 5 + 1.5 * SIN(day::numeric / 4))::numeric, 0 ),
    'mmHg',
    ('2026-01-05 08:00:00'::timestamp + (day || ' days')::interval),
    'self_report'
FROM generate_series(0, 89) AS day;

-- 공복 혈당 / Fasting blood glucose (mg/dL)
INSERT INTO health_metrics
    (patient_id, metric_type, value_primary, value_secondary, unit, measured_at, source)
SELECT
    '11111111-1111-1111-1111-111111111111',
    'blood_glucose',
    -- 145 → 128 linear decline (Metformin uptitration effect) + noise
    ROUND( (145 - (day::numeric / 89) * 17 + 3 * SIN(day::numeric / 2.5))::numeric, 0 ),
    NULL,
    'mg/dL',
    ('2026-01-05 07:30:00'::timestamp + (day || ' days')::interval),
    'self_report'
FROM generate_series(0, 89) AS day;

-- 체중 / Weight (kg) — stable ~72kg
INSERT INTO health_metrics
    (patient_id, metric_type, value_primary, value_secondary, unit, measured_at, source)
SELECT
    '11111111-1111-1111-1111-111111111111',
    'weight',
    ROUND( (72 + 0.8 * SIN(day::numeric / 5))::numeric, 1 ),
    NULL,
    'kg',
    ('2026-01-05 07:00:00'::timestamp + (day || ' days')::interval),
    'self_report'
FROM generate_series(0, 89) AS day;

-- 심박수 / Resting heart rate (bpm) — stable ~74 bpm
INSERT INTO health_metrics
    (patient_id, metric_type, value_primary, value_secondary, unit, measured_at, source)
SELECT
    '11111111-1111-1111-1111-111111111111',
    'heart_rate',
    ROUND( (74 + 4 * SIN(day::numeric / 3.5))::numeric, 0 ),
    NULL,
    'bpm',
    ('2026-01-05 08:15:00'::timestamp + (day || ' days')::interval),
    'device'
FROM generate_series(0, 89) AS day;

-- =============================================================================
-- 검증 쿼리 (옵션) / Verification queries (optional)
-- =============================================================================
-- SELECT COUNT(*) FROM health_metrics WHERE patient_id = '11111111-1111-1111-1111-111111111111';
-- -- Expected: 360 (= 4 metric_types x 90 days)

COMMIT;

-- =============================================================================
-- End of seed_rajesh.sql
-- =============================================================================
