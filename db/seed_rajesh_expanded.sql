-- =============================================================================
-- CareFlow EXPANDED Seed Data — Rajesh Sharma: 47 Additional Visit Records
-- =============================================================================
-- This file adds 47 new visit_records (IDs 04–50) spanning 18 months
-- (2024-10-01 to 2026-03-31) plus quarterly lab metrics (HbA1c, eGFR,
-- urine ACR, LDL).
--
-- DOES NOT duplicate existing visits: 2026-01-10, 2026-02-20, 2026-03-18
-- (IDs 01–03 in seed_rajesh.sql).
--
-- Key clinical events inserted:
--   - Oct 2024: Initial DM2+HTN diagnosis
--   - Jan 2025: HbA1c 7.4%, Aspirin + Atorvastatin added
--   - Jun 2025: Annual eye exam (no retinopathy)
--   - Sep 2025: Microalbuminuria discovered (ACR 45), Lisinopril initiated
--   - Nov 2025: Hypoglycemia episode
--   - Mar 2026: Hypertensive urgency ER visit (BP 182/110)
--
-- Safe to run alongside seed_rajesh.sql — uses ON CONFLICT DO NOTHING.
-- =============================================================================

BEGIN;

-- =============================================================================
-- VISIT RECORDS (47 new records, IDs 04–50)
-- =============================================================================

INSERT INTO visit_records
    (id, patient_id, visit_date, raw_input, structured_summary,
     doctor_name, hospital_name, key_findings, embedding)
VALUES

-- ---------------------------------------------------------------------------
-- #04 — 2024-10-01 — Initial DM2+HTN diagnosis (Routine follow-up)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000004',
 '11111111-1111-1111-1111-111111111111',
 '2024-10-01',
 'I went to see Dr. Mehta because I was feeling very tired and thirsty all the time. He did some tests and told me I have diabetes and high blood pressure. He gave me Metformin 500mg and a BP tablet called Amlodipine.',
 'New patient evaluation. Presenting complaint: polyuria, polydipsia, fatigue x 3 months. Random blood glucose 248 mg/dL. BP 152/96 mmHg (repeated: 148/94). BMI 27.2. Diagnosed with Type 2 Diabetes Mellitus and Essential Hypertension. Started on Metformin 500mg BD with meals and Amlodipine 5mg OD morning. Ordered baseline labs: HbA1c, fasting lipid panel, renal panel, urine routine. Counseled on dietary modification and 30-min daily walk.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"random_glucose":248,"bp_systolic":152,"bp_diastolic":96,"bmi":27.2,"diagnosis":["type_2_diabetes","essential_hypertension"],"meds_started":["metformin_500mg_bd","amlodipine_5mg_od"],"advice":["diet_modification","daily_walk_30min"]}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #05 — 2024-10-08 — Pharmacy/medication counseling
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000005',
 '11111111-1111-1111-1111-111111111111',
 '2024-10-08',
 'The pharmacist at Apollo explained how to take Metformin with food so my stomach does not get upset. She also showed me how to use the BP machine at home.',
 'Pharmacy counseling session. Reviewed Metformin administration: take with meals to minimize GI side effects. Demonstrated home BP monitor usage (Omron HEM-7120). Advised patient to maintain a BP diary. Discussed common side effects of Amlodipine (ankle edema, flushing).',
 'Pharmacist Joshi', 'Apollo Clinic, Mumbai',
 '{"counseling_topics":["metformin_gi_precautions","home_bp_monitoring","amlodipine_side_effects"],"device":"omron_hem_7120"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #06 — 2024-10-15 — Lab test visit (baseline)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000006',
 '11111111-1111-1111-1111-111111111111',
 '2024-10-15',
 'I went to SRL lab early morning without eating breakfast. They took a lot of blood samples and also asked for a urine sample.',
 'Baseline laboratory workup (fasting). HbA1c 7.8%. Fasting glucose 168 mg/dL. Fasting lipid panel: TC 242, LDL 148, HDL 38, TG 210. Renal panel: creatinine 1.0 mg/dL, eGFR 78 mL/min/1.73m2, BUN 18. Urine routine: no proteinuria. CBC within normal limits. LFT: ALT 32, AST 28.',
 'Lab Technician', 'SRL Diagnostics, Mumbai',
 '{"hba1c":7.8,"fasting_glucose":168,"total_cholesterol":242,"ldl":148,"hdl":38,"triglycerides":210,"creatinine":1.0,"egfr":78,"bun":18,"alt":32,"ast":28}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #07 — 2024-10-22 — Routine DM2+HTN follow-up (lab review)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000007',
 '11111111-1111-1111-1111-111111111111',
 '2024-10-22',
 'Dr. Mehta reviewed all my reports. He said sugar is high and cholesterol is also very high. He wants me to focus on diet first and recheck in 3 months before adding more medicines.',
 'Follow-up to review baseline labs. HbA1c 7.8% — moderate hyperglycemia. Dyslipidemia noted: LDL 148, TG 210, HDL 38. Renal function preserved (eGFR 78). Plan: continue Metformin 500mg BD + Amlodipine 5mg OD. Aggressive lifestyle modification: low glycemic index diet, reduce fried foods, increase fiber. Recheck HbA1c + lipids in 3 months. If targets not met, will add statin + aspirin.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"hba1c":7.8,"ldl":148,"bp_systolic":144,"bp_diastolic":92,"plan":"lifestyle_modification_3mo_recheck","targets":{"hba1c":"<7.0","ldl":"<100","bp":"<140/90"}}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #08 — 2024-11-05 — Dietitian consultation #1
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000008',
 '11111111-1111-1111-1111-111111111111',
 '2024-11-05',
 'I went to see the dietitian at Apollo. She gave me a proper meal plan. She said I should eat more dal, vegetables and reduce rice portions. No more fried snacks with chai.',
 'Dietitian consultation. Current diet assessment: high carbohydrate intake (estimated 300g/day), frequent fried snacks, 3-4 cups chai with sugar daily. Weight 73.5 kg, BMI 27.2. Prescribed 1800 kcal diabetic diet plan: 50% complex carbs, 25% protein, 25% fat. Specific recommendations: replace white rice with brown rice (half portions), increase dal and vegetable intake, switch to stevia for chai, avoid fried items. Target: 2-3 kg weight loss over 3 months.',
 'Dt. Priya Kapoor', 'Apollo Clinic, Mumbai',
 '{"weight":73.5,"bmi":27.2,"daily_calories_target":1800,"carb_grams_current":300,"dietary_changes":["reduce_rice","increase_dal_vegetables","no_fried_snacks","stevia_for_chai"],"weight_target":71}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #09 — 2024-11-20 — Telehealth check-in #1
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000009',
 '11111111-1111-1111-1111-111111111111',
 '2024-11-20',
 'Had a video call with Dr. Mehta. I showed him my BP diary. Readings have been mostly 138-142 over 88-92. He said the diet changes will take time to show effect.',
 'Telehealth follow-up (video). Patient reports compliance with Metformin and Amlodipine. Home BP diary reviewed: average 140/90 over past 2 weeks (range 136-144/86-94). No hypoglycemia episodes. Mild GI discomfort with Metformin — advised to take strictly with meals. Dietary compliance partial — still consuming white rice. Encouraged continued lifestyle modification. Next in-person visit Jan 2025.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai (Telehealth)',
 '{"bp_systolic_avg":140,"bp_diastolic_avg":90,"medication_compliance":"good","gi_side_effects":"mild","dietary_compliance":"partial"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #10 — 2024-12-10 — Flu shot (Miscellaneous)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000010',
 '11111111-1111-1111-1111-111111111111',
 '2024-12-10',
 'Doctor suggested I get a flu shot since I have diabetes and my immunity may be lower. Got it at Apollo, just a small prick in the arm.',
 'Influenza vaccination administered. Quadrivalent inactivated influenza vaccine (Fluarix) 0.5 mL IM left deltoid. Patient is in high-risk category due to DM2 and age >60. No immediate adverse reaction observed (monitored 15 min). Also counseled on pneumococcal vaccination — scheduled for next visit.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"vaccine":"influenza_quadrivalent","route":"IM_left_deltoid","adverse_reaction":"none","counseling":"pneumococcal_vaccine_next"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #11 — 2024-12-20 — Podiatry/foot exam #1
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000011',
 '11111111-1111-1111-1111-111111111111',
 '2024-12-20',
 'Dr. Mehta sent me to the foot doctor to check my feet since diabetic patients can have foot problems. The doctor checked sensation in my feet with a thin wire and said everything is normal for now.',
 'Diabetic foot examination (baseline). Comprehensive foot assessment: skin intact, no calluses or deformities. Peripheral pulses: dorsalis pedis and posterior tibial bilaterally palpable. 10g monofilament test: sensation intact at all 10 sites bilaterally. Vibration perception (128 Hz tuning fork): normal at great toe bilaterally. No evidence of peripheral neuropathy. Advised daily foot inspection, proper footwear, moisturizing cream.',
 'Dr. Sunil Patil', 'Apollo Clinic, Mumbai',
 '{"monofilament_test":"normal_all_sites","vibration_sense":"normal","peripheral_pulses":"palpable_bilateral","skin":"intact","neuropathy":"absent","advice":["daily_foot_inspection","proper_footwear"]}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #12 — 2025-01-10 — Routine DM2+HTN follow-up (quarterly)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000012',
 '11111111-1111-1111-1111-111111111111',
 '2025-01-10',
 'Went for my 3-month checkup. Doctor was happy that sugar came down a little but said cholesterol is still high. He added two more tablets — one for cholesterol and a small aspirin for my heart.',
 'Quarterly DM2+HTN review. BP 136/88. Weight 72.8 kg (down 0.7 kg). HbA1c 7.4% (improved from 7.8%). Fasting glucose 142 mg/dL. LDL 142 mg/dL (inadequately controlled despite diet). CV risk assessment: 10-year ASCVD risk >10% (age, DM2, dyslipidemia). Added Atorvastatin 20mg OD at bedtime and Aspirin 75mg OD after dinner for primary CV prevention. Continue Metformin 500mg BD + Amlodipine 5mg OD.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"hba1c":7.4,"fasting_glucose":142,"ldl":142,"bp_systolic":136,"bp_diastolic":88,"weight":72.8,"meds_added":["atorvastatin_20mg_od","aspirin_75mg_od"],"ascvd_risk":">10%"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #13 — 2025-01-20 — Lab test visit (post-statin baseline)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000013',
 '11111111-1111-1111-1111-111111111111',
 '2025-01-20',
 'Doctor asked me to get blood tests done again so he has a fresh baseline after starting the new cholesterol medicine. Fasting blood test at SRL.',
 'Fasting laboratory panel (post-statin initiation baseline). HbA1c 7.4%. Fasting glucose 138 mg/dL. Lipid panel: TC 228, LDL 142, HDL 40, TG 198. Renal: creatinine 1.0, eGFR 77, BUN 17. LFT: ALT 30, AST 26. CK 120 U/L (baseline for statin myopathy monitoring). Urine ACR 22 mg/g (normal, <30).',
 'Lab Technician', 'SRL Diagnostics, Mumbai',
 '{"hba1c":7.4,"fasting_glucose":138,"ldl":142,"hdl":40,"triglycerides":198,"creatinine":1.0,"egfr":77,"alt":30,"ck":120,"urine_acr":22}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #14 — 2025-02-05 — Pharmacy/medication counseling #2
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000014',
 '11111111-1111-1111-1111-111111111111',
 '2025-02-05',
 'Went to the pharmacy to pick up my new medicines. The pharmacist explained that Atorvastatin should be taken at bedtime and told me about muscle pain side effects I should watch for.',
 'Pharmacy counseling — new medications. Reviewed Atorvastatin 20mg: take at bedtime, report any unexplained muscle pain/tenderness or dark urine (rhabdomyolysis warning signs). Reviewed Aspirin 75mg: take after dinner, avoid on empty stomach, watch for GI bleeding signs (black stools, unusual bruising). Pill organizer provided for 5-medication regimen. Medication reconciliation confirmed: Metformin 500mg BD, Amlodipine 5mg OD, Atorvastatin 20mg OD, Aspirin 75mg OD.',
 'Pharmacist Joshi', 'Apollo Clinic, Mumbai',
 '{"counseling_topics":["atorvastatin_bedtime_dosing","myopathy_warning_signs","aspirin_gi_precautions","pill_organizer"],"total_medications":4}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #15 — 2025-02-18 — Cardiology referral #1 (ECG)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000015',
 '11111111-1111-1111-1111-111111111111',
 '2025-02-18',
 'Dr. Mehta referred me to a heart specialist Dr. Desai because of my diabetes and high cholesterol. They did an ECG test where they attached wires to my chest. Dr. Desai said it looks fine.',
 'Cardiology consultation (CV risk stratification). History reviewed: 63M with DM2, HTN, dyslipidemia. Non-smoker. No chest pain, dyspnea, or palpitations. Exam: S1 S2 normal, no murmurs. JVP normal. Pedal edema absent. 12-lead ECG: normal sinus rhythm, rate 76 bpm, normal axis, no ST-T changes, no LVH criteria met. Impression: low-intermediate CV risk currently. Recommend: continue statin + aspirin, stress test in 3-4 months for comprehensive risk assessment, maintain BP <140/90.',
 'Dr. Desai', 'Apollo Hospital, Mumbai',
 '{"ecg":"normal_sinus_rhythm","heart_rate":76,"axis":"normal","st_changes":"none","lvh":"absent","murmurs":"none","cv_risk":"low_intermediate","plan":"stress_test_3_4_months"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #16 — 2025-03-05 — Telehealth check-in #2
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000016',
 '11111111-1111-1111-1111-111111111111',
 '2025-03-05',
 'Video call with Dr. Mehta. I told him the new medicines are going well, no muscle pain from cholesterol tablet. BP at home is around 134-138 over 86-88. He seems satisfied.',
 'Telehealth follow-up. Patient reports good tolerance to Atorvastatin — no myalgia or GI symptoms. Home BP diary: average 136/87 (range 132-140/84-90) — better controlled. Fasting glucose self-monitoring: 130-145 mg/dL range. Weight 72.5 kg. Dietary adherence improving — reduced rice portions, fewer fried items. Continue all medications. Next in-person visit April 2025 for quarterly review.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai (Telehealth)',
 '{"bp_systolic_avg":136,"bp_diastolic_avg":87,"fasting_glucose_range":"130-145","weight":72.5,"statin_tolerance":"good","dietary_compliance":"improving"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #17 — 2025-03-25 — Dental checkup (Miscellaneous)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000017',
 '11111111-1111-1111-1111-111111111111',
 '2025-03-25',
 'Went for dental checkup. The dentist said diabetic patients are more prone to gum disease. My gums were slightly swollen but no cavities. He cleaned my teeth and told me to floss daily.',
 'Dental examination. Patient informed dentist of DM2 history. Oral exam: mild gingivitis noted (gingival index 1.2), no caries, no periodontal pockets >3mm. Scaling and polishing performed. Advised: twice daily brushing with soft bristle, daily flossing, use chlorhexidine mouthwash for 2 weeks. Follow-up in 6 months. HbA1c communicated to dentist for surgical risk awareness.',
 'Dr. Raghav (Dentist)', 'Apollo Clinic, Mumbai',
 '{"gingivitis":"mild","caries":"none","periodontal_pockets":"normal","procedure":"scaling_polishing","advice":["daily_flossing","chlorhexidine_mouthwash"]}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #18 — 2025-04-08 — Routine DM2+HTN follow-up (quarterly)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000018',
 '11111111-1111-1111-1111-111111111111',
 '2025-04-08',
 'Quarterly visit with Dr. Mehta. He checked my BP and weight. Said everything is going in the right direction. Sugar coming down slowly. Cholesterol will need lab recheck next month.',
 'Quarterly DM2+HTN review. BP 134/86. Weight 72.2 kg (cumulative loss 1.3 kg). Home glucose diary: fasting 128-140 mg/dL. Patient reports improved dietary habits. No medication side effects. Plan: continue current regimen (Metformin 500mg BD, Amlodipine 5mg, Atorvastatin 20mg, Aspirin 75mg). Order labs in 6 weeks: HbA1c, fasting lipids, renal panel, LFT, CK.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"bp_systolic":134,"bp_diastolic":86,"weight":72.2,"fasting_glucose_range":"128-140","plan":"continue_regimen","labs_ordered_6wk":["hba1c","lipid_panel","renal_panel","lft","ck"]}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #19 — 2025-04-22 — Dietitian consultation #2
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000019',
 '11111111-1111-1111-1111-111111111111',
 '2025-04-22',
 'Follow-up with the dietitian. I lost about 1.3 kg in 6 months which she said is good but slow. She adjusted my meal plan to include more protein and gave me a list of low GI snacks.',
 'Dietitian follow-up consultation. Weight 72.2 kg (from 73.5 kg baseline — 1.3 kg loss over 5.5 months). Dietary recall: improved compliance, reduced white rice, some fried snack lapses on weekends. Revised plan: increase protein to 30% (add paneer, sprouts, eggs), introduce low-GI snack options (roasted chana, mixed nuts, fruit with nut butter), restrict evening carbs. Recommended 150 min/week moderate exercise (brisk walking). Next review in 3 months.',
 'Dt. Priya Kapoor', 'Apollo Clinic, Mumbai',
 '{"weight":72.2,"weight_loss_total":1.3,"protein_target":"30%","exercise_target":"150min_per_week","dietary_changes":["increase_protein","low_gi_snacks","restrict_evening_carbs"]}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #20 — 2025-05-20 — Lab test visit (6-month labs)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000020',
 '11111111-1111-1111-1111-111111111111',
 '2025-05-20',
 'Went for my 6-monthly blood tests at SRL. They took blood and urine both. Had to fast from last night so I was very hungry by the time it was done.',
 'Fasting laboratory panel (6-month review). HbA1c 7.1% (improving trend: 7.8 → 7.4 → 7.1). Fasting glucose 126 mg/dL. Lipid panel: TC 198, LDL 108, HDL 42, TG 178. Renal: creatinine 1.1, eGFR 74, BUN 19. LFT: ALT 34, AST 30. CK 115. Urine ACR 28 mg/g (normal, <30 — but trending up from 22). Urine routine: no glycosuria.',
 'Lab Technician', 'SRL Diagnostics, Mumbai',
 '{"hba1c":7.1,"fasting_glucose":126,"ldl":108,"hdl":42,"triglycerides":178,"creatinine":1.1,"egfr":74,"alt":34,"ck":115,"urine_acr":28}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #21 — 2025-05-28 — Routine follow-up (lab review)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000021',
 '11111111-1111-1111-1111-111111111111',
 '2025-05-28',
 'Dr. Mehta reviewed my lab reports. He was happy about HbA1c coming down to 7.1. Cholesterol has also improved a lot. He mentioned kidney test is still fine but wants to keep watching it closely.',
 'Lab review follow-up. HbA1c 7.1% — excellent response to lifestyle + Metformin. LDL 108 (improved from 148 but still above target <100). eGFR 74 — stable. Urine ACR 28 — still normal but trending upward from 22 (6 months prior). Will monitor ACR closely given DM2 nephropathy risk. Plan: continue all medications unchanged. LDL not yet at target — reinforce dietary fat restriction. Recheck labs including ACR in 3-4 months.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"hba1c":7.1,"ldl":108,"egfr":74,"urine_acr":28,"acr_trend":"upward","bp_systolic":132,"bp_diastolic":84,"plan":"continue_monitor_acr"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #22 — 2025-06-10 — Cardiology referral #2 (stress test)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000022',
 '11111111-1111-1111-1111-111111111111',
 '2025-06-10',
 'Dr. Desai the heart doctor did a treadmill stress test. I had to walk fast on a treadmill while they watched my heart on a monitor. I was very tired after but he said the test results are good.',
 'Cardiac stress test (treadmill exercise test — Bruce protocol). Resting HR 74, BP 134/84. Achieved 7.2 METs (85% of age-predicted max HR). Peak HR 134, peak BP 178/88. ECG during exercise: no significant ST depression or arrhythmia. No chest pain or dyspnea limiting exercise. Recovery: HR and BP normalized within 5 minutes. Impression: negative for inducible ischemia at moderate workload. Adequate exercise capacity for age. Continue current CV prevention strategy.',
 'Dr. Desai', 'Apollo Hospital, Mumbai',
 '{"test":"treadmill_stress_bruce","resting_hr":74,"peak_hr":134,"mets":7.2,"resting_bp":"134/84","peak_bp":"178/88","st_changes":"none","ischemia":"negative","exercise_capacity":"adequate"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #23 — 2025-06-18 — Ophthalmology (annual diabetic retinopathy screen)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000023',
 '11111111-1111-1111-1111-111111111111',
 '2025-06-18',
 'Doctor checked my eyes today. They put drops to make my pupils big and then shone a bright light to look inside. My eyes were blurry for a few hours afterwards. He said no diabetes damage to my eyes so far.',
 'Annual diabetic retinopathy screening. Visual acuity: OD 6/9, OS 6/9 (corrected). IOP: OD 16, OS 15 mmHg. Dilated fundoscopic examination: no microaneurysms, no hemorrhages, no exudates, no neovascularization bilaterally. Macula: normal foveal reflex bilateral. Optic disc: healthy cup-to-disc ratio 0.3 bilateral. Impression: no diabetic retinopathy. No hypertensive retinopathy. Recommend annual screening. Advised UV-protection sunglasses.',
 'Dr. Kulkarni', 'Sankara Nethralaya, Mumbai',
 '{"visual_acuity_od":"6/9","visual_acuity_os":"6/9","iop_od":16,"iop_os":15,"diabetic_retinopathy":"absent","hypertensive_retinopathy":"absent","cup_disc_ratio":0.3,"plan":"annual_screening"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #24 — 2025-06-30 — Podiatry/foot exam #2
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000024',
 '11111111-1111-1111-1111-111111111111',
 '2025-06-30',
 'Had my six-monthly foot checkup. The doctor tested my feet again with the thin wire and also checked blood flow. Everything still normal. He reminded me to never walk barefoot.',
 'Diabetic foot examination (6-month follow-up). Skin: intact, mild dryness on heels — recommended urea-based moisturizer. No calluses, ulcers, or fungal infection. Monofilament (10g): protective sensation intact all sites bilaterally. Vibration perception: normal. ABI (ankle-brachial index): 1.05 right, 1.08 left — normal. Pedal pulses: palpable bilateral. No neuropathy progression. Advised: daily foot inspection, never walk barefoot, moisturize heels, proper diabetic footwear.',
 'Dr. Sunil Patil', 'Apollo Clinic, Mumbai',
 '{"monofilament_test":"normal","vibration_sense":"normal","abi_right":1.05,"abi_left":1.08,"skin":"mild_heel_dryness","neuropathy":"absent","advice":["moisturize_heels","diabetic_footwear","no_barefoot"]}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #25 — 2025-07-10 — Routine DM2+HTN follow-up (quarterly)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000025',
 '11111111-1111-1111-1111-111111111111',
 '2025-07-10',
 'Quarterly visit. BP was 130/84 today which doctor said is good. Weight is stable. He said let us keep going with same medicines and recheck blood in September.',
 'Quarterly DM2+HTN review. BP 130/84 — well controlled. HR 72. Weight 71.8 kg. Home glucose diary: fasting 118-132 mg/dL (improved range). No hypoglycemia. No medication side effects. Eye exam and stress test both negative — reassuring. Plan: continue Metformin 500mg BD, Amlodipine 5mg, Atorvastatin 20mg, Aspirin 75mg. Next labs (including ACR recheck) in September.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"bp_systolic":130,"bp_diastolic":84,"weight":71.8,"heart_rate":72,"fasting_glucose_range":"118-132","plan":"continue_regimen_labs_september"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #26 — 2025-07-22 — Telehealth check-in #3
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000026',
 '11111111-1111-1111-1111-111111111111',
 '2025-07-22',
 'Quick video call with Dr. Mehta. I told him I am feeling much better now, more energy, less thirsty. Home BP has been around 128-134 range. He said to continue everything as is.',
 'Telehealth follow-up. Patient reports subjective improvement — less polyuria, improved energy levels. Home BP: average 131/83 (range 126-136/80-86). Self-monitored fasting glucose: 120-130 mg/dL. Good medication compliance. Walking 20-30 min daily. Continue current regimen. No concerns.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai (Telehealth)',
 '{"bp_systolic_avg":131,"bp_diastolic_avg":83,"fasting_glucose_range":"120-130","symptoms":"improved_energy_less_polyuria","medication_compliance":"good","exercise":"walking_20_30min_daily"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #27 — 2025-08-12 — Pharmacy/medication counseling #3
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000027',
 '11111111-1111-1111-1111-111111111111',
 '2025-08-12',
 'Went to refill all my medicines. Pharmacist checked if I have any side effects and asked if I am taking everything on time. She reminded me about taking statin at bedtime.',
 'Pharmacy medication review and refill. 4-medication regimen reviewed: Metformin 500mg BD (good compliance), Amlodipine 5mg OD AM (good compliance), Atorvastatin 20mg OD bedtime (occasionally missing — reinforced timing), Aspirin 75mg OD post-dinner (good compliance). No reported adverse effects. 3-month supply dispensed. Reminder: Atorvastatin most effective at bedtime due to nocturnal cholesterol synthesis peak.',
 'Pharmacist Joshi', 'Apollo Clinic, Mumbai',
 '{"medications_dispensed":4,"supply_duration":"3_months","compliance":"good_except_occasional_statin_miss","counseling":"statin_bedtime_reinforcement"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #28 — 2025-09-08 — Lab test visit (quarterly + ACR recheck)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000028',
 '11111111-1111-1111-1111-111111111111',
 '2025-09-08',
 'Went for my quarterly blood and urine tests. Doctor had specifically asked for the kidney urine test to be repeated this time.',
 'Fasting laboratory panel (quarterly). HbA1c 7.1% (stable). Fasting glucose 122 mg/dL. Lipid panel: TC 188, LDL 96, HDL 44, TG 168. Renal: creatinine 1.1, eGFR 72 mL/min/1.73m2 (slight decline from 77), BUN 20. LFT: ALT 32, AST 28. CK 110. Urine ACR: 45 mg/g — MODERATELY INCREASED (previously 28). Flags: new-onset microalbuminuria (ACR 30-300 mg/g range). eGFR 72 consistent with CKD Stage 2.',
 'Lab Technician', 'SRL Diagnostics, Mumbai',
 '{"hba1c":7.1,"fasting_glucose":122,"ldl":96,"hdl":44,"triglycerides":168,"creatinine":1.1,"egfr":72,"urine_acr":45,"acr_category":"moderately_increased","ckd_stage":2,"alt":32,"ck":110}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #29 — 2025-09-20 — Routine follow-up: MICROALBUMINURIA DISCOVERY + LISINOPRIL
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000029',
 '11111111-1111-1111-1111-111111111111',
 '2025-09-20',
 'Dr. Mehta looked very serious when reviewing my reports. He said my kidney urine test shows early signs of kidney stress from diabetes. He added a new tablet called Lisinopril to protect my kidneys. He said this is very important and I must not miss this medicine.',
 'Critical lab review: new-onset microalbuminuria. Urine ACR 45 mg/g (moderately increased, A2 category). eGFR 72 mL/min/1.73m2 (CKD Stage G2A2). Trend: ACR 22 → 28 → 45 over 8 months — progressive increase. HbA1c 7.1%, LDL 96 — both improved. BP 132/86. Assessment: early diabetic nephropathy. INITIATED Lisinopril 10mg OD morning for renoprotection (ACE inhibitor — first-line for diabetic nephropathy with microalbuminuria). Counseled on importance of strict medication adherence. Check potassium and creatinine in 2 weeks. Target ACR reduction >30% at 3 months. Recheck ACR quarterly.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"urine_acr":45,"egfr":72,"ckd_stage":"G2A2","acr_trend":[22,28,45],"bp_systolic":132,"bp_diastolic":86,"hba1c":7.1,"ldl":96,"new_med":"lisinopril_10mg_od","indication":"renoprotection_microalbuminuria","target":"acr_reduction_30pct_3months","followup":"potassium_creatinine_2weeks"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #30 — 2025-10-04 — Lab test (2-week post-Lisinopril safety check)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000030',
 '11111111-1111-1111-1111-111111111111',
 '2025-10-04',
 'Had to go for a quick blood test two weeks after starting the new kidney medicine. Doctor wanted to check if the medicine is affecting my potassium levels.',
 'Post-ACE inhibitor safety labs (2 weeks after Lisinopril initiation). Serum potassium 4.4 mEq/L (normal 3.5-5.0). Creatinine 1.1 mg/dL (stable, no rise >30% — safe to continue). eGFR 72. BUN 19. No hyperkalemia. Safe to continue Lisinopril 10mg. Patient reports no dry cough or angioedema.',
 'Lab Technician', 'SRL Diagnostics, Mumbai',
 '{"potassium":4.4,"creatinine":1.1,"egfr":72,"bun":19,"lisinopril_safety":"confirmed","side_effects":"none"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #31 — 2025-10-15 — Telehealth check-in #4
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000031',
 '11111111-1111-1111-1111-111111111111',
 '2025-10-15',
 'Video call with Dr. Mehta. He asked if I am having any cough from the new kidney medicine. I said no. My BP at home has actually come down a bit since starting Lisinopril, around 126-130 range. He was happy about that.',
 'Telehealth follow-up — 4 weeks post-Lisinopril initiation. No ACE inhibitor side effects reported: no dry cough, no angioedema, no dizziness. Home BP: average 128/82 (range 124-132/78-84) — improved with addition of Lisinopril. Fasting glucose: 118-128 mg/dL. Good compliance with all 5 medications. Patient understanding of kidney protection importance confirmed. Next in-person visit November.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai (Telehealth)',
 '{"bp_systolic_avg":128,"bp_diastolic_avg":82,"fasting_glucose_range":"118-128","lisinopril_side_effects":"none","medication_compliance":"good","total_medications":5}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #32 — 2025-10-28 — Dietitian consultation #3
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000032',
 '11111111-1111-1111-1111-111111111111',
 '2025-10-28',
 'Saw the dietitian again. Since they found the kidney issue, she said I need to also watch my protein intake — not too much. She adjusted my meal plan. She also said to reduce salt even more.',
 'Dietitian consultation — adjusted for early diabetic nephropathy. Weight 71.5 kg. Given microalbuminuria (ACR 45), dietary protein capped at 0.8 g/kg/day (approximately 57 g/day) per KDOQI guidelines. Sodium restriction reinforced: target <2 g/day (currently estimated 3-4 g/day). Potassium-rich foods counseled (bananas, spinach) but cautioned about excess given ACE inhibitor use. Revised meal plan distributed. Patient counseled on reading food labels for sodium content.',
 'Dt. Priya Kapoor', 'Apollo Clinic, Mumbai',
 '{"weight":71.5,"protein_target_g_per_day":57,"protein_restriction":"0.8g_per_kg","sodium_target":"<2g_per_day","potassium_counseling":"moderate_intake","plan":"renal_diabetic_diet"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #33 — 2025-11-12 — HYPOGLYCEMIA ER VISIT
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000033',
 '11111111-1111-1111-1111-111111111111',
 '2025-11-12',
 'I had a very scary episode. I took my morning Metformin but then could not eat breakfast because Priya called and I got busy on the phone. Around 11am I started sweating, shaking, and feeling very dizzy. My neighbor brought me to the hospital emergency.',
 'ER visit — hypoglycemia episode. Patient brought in by neighbor with symptoms of diaphoresis, tremor, dizziness, and confusion. Onset approximately 3 hours after Metformin 500mg ingestion without food. Capillary blood glucose at presentation: 54 mg/dL. BP 118/76. HR 96 (tachycardic). No LOC. GCS 14/15 (slightly confused). Management: IV dextrose 25% 50mL bolus → glucose rose to 112 mg/dL within 15 minutes. Symptoms resolved. Monitored for 2 hours — glucose stable at 118 mg/dL. Discharged with counseling: NEVER take Metformin without a meal. Keep glucose tablets/candy accessible. Educated on hypoglycemia warning signs. Follow-up with Dr. Mehta in 1 week.',
 'Dr. Nair', 'Apollo Hospital ER, Mumbai',
 '{"presenting_glucose":54,"bp_systolic":118,"bp_diastolic":76,"heart_rate":96,"gcs":14,"symptoms":["diaphoresis","tremor","dizziness","confusion"],"cause":"metformin_without_meal","treatment":"iv_dextrose_25pct_50ml","glucose_post_treatment":112,"discharge_glucose":118,"disposition":"discharged","counseling":["never_skip_meals_with_metformin","carry_glucose_tablets"]}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #34 — 2025-11-19 — Follow-up after hypoglycemia
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000034',
 '11111111-1111-1111-1111-111111111111',
 '2025-11-19',
 'Went to see Dr. Mehta after my hospital scare. He scolded me gently for skipping breakfast. He said the medicine is fine, I just must always eat before taking it. He checked my sugar and BP, both okay now.',
 'Post-hypoglycemia follow-up (1 week after ER visit). Patient stable, no recurrent hypoglycemia. Has been carrying glucose tablets since the episode. Fasting glucose today: 126 mg/dL. BP 130/84. Reinforced: Metformin must always be taken with meals — if meal is delayed, delay the dose. Not a contraindication to Metformin itself — medication-induced hypoglycemia with Metformin monotherapy is rare; this was precipitated by prolonged fasting after dosing. Continue Metformin 500mg BD. No dose adjustment needed.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"fasting_glucose":126,"bp_systolic":130,"bp_diastolic":84,"hypoglycemia_recurrence":"none","carries_glucose_tablets":"yes","metformin_dose":"unchanged_500mg_bd","counseling":"meal_timing_with_metformin"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #35 — 2025-11-28 — Pharmacy/medication counseling #4
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000035',
 '11111111-1111-1111-1111-111111111111',
 '2025-11-28',
 'Pharmacist called me after hearing about my low sugar episode. She gave me a proper schedule chart for all my 5 medicines showing which meal to take each one with.',
 'Pharmacy counseling — post-hypoglycemia medication timing review. Created detailed medication administration schedule: (1) Morning with breakfast: Metformin 500mg + Amlodipine 5mg + Lisinopril 10mg. (2) Evening with dinner: Metformin 500mg + Aspirin 75mg. (3) Bedtime: Atorvastatin 20mg. Emphasized: if breakfast delayed, delay morning Metformin. Provided laminated schedule card for refrigerator. Dispensed glucose tablets (10 tabs) for emergency hypoglycemia management.',
 'Pharmacist Joshi', 'Apollo Clinic, Mumbai',
 '{"counseling":"medication_timing_schedule","schedule":{"morning_with_breakfast":["metformin_500mg","amlodipine_5mg","lisinopril_10mg"],"evening_with_dinner":["metformin_500mg","aspirin_75mg"],"bedtime":["atorvastatin_20mg"]},"glucose_tablets_dispensed":10}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #36 — 2025-12-08 — Lab test visit (quarterly + ACR)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000036',
 '11111111-1111-1111-1111-111111111111',
 '2025-12-08',
 'Quarterly blood tests again. Doctor specifically wants to see if the Lisinopril is helping my kidney numbers.',
 'Fasting laboratory panel (quarterly, 3 months post-Lisinopril). HbA1c 7.2% (stable). Fasting glucose 124 mg/dL. Lipid panel: TC 182, LDL 92, HDL 45, TG 158. Renal: creatinine 1.1, eGFR 73 (stable). Potassium 4.3 mEq/L. Urine ACR: 34 mg/g — IMPROVED from 45 (24% reduction with Lisinopril). LFT normal. CK 108.',
 'Lab Technician', 'SRL Diagnostics, Mumbai',
 '{"hba1c":7.2,"fasting_glucose":124,"ldl":92,"hdl":45,"triglycerides":158,"creatinine":1.1,"egfr":73,"potassium":4.3,"urine_acr":34,"acr_change":"-24pct_from_45","alt":30,"ck":108}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #37 — 2025-12-18 — Routine DM2+HTN follow-up (quarterly review)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000037',
 '11111111-1111-1111-1111-111111111111',
 '2025-12-18',
 'Dr. Mehta reviewed my reports. He was pleased the kidney medicine is working — the urine protein has gone down. But he said HbA1c has gone up slightly to 7.2 and he is watching it. He reminded me about the festival season and not to eat too many sweets.',
 'Quarterly DM2+HTN review. HbA1c 7.2% (slight uptick from 7.1% — likely Diwali dietary indiscretion). LDL 92 (at target <100 — excellent statin response). ACR 34 (improved from 45 — 24% reduction, target was >30%). eGFR 73 (stable). BP 128/82. Weight 72.0 kg. Assessment: Lisinopril renoprotection effective but ACR still above normal. Continue all 5 medications. Counseled on festive diet discipline. Warned that if HbA1c rises further, Metformin dose increase may be needed. Next labs and visit in January 2026.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"hba1c":7.2,"ldl":92,"urine_acr":34,"egfr":73,"bp_systolic":128,"bp_diastolic":82,"weight":72.0,"lisinopril_response":"acr_reduced_24pct","concern":"hba1c_slight_uptick","plan":"monitor_hba1c_continue_meds"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #38 — 2025-12-28 — Ophthalmology follow-up (6-month from annual)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000038',
 '11111111-1111-1111-1111-111111111111',
 '2025-12-28',
 'Went for a follow-up eye check since my kidneys are affected. The eye doctor wanted to make sure diabetes is not also harming my eyes. All good this time too.',
 'Ophthalmology follow-up (6 months post-annual, prompted by new microalbuminuria). Given new diabetic nephropathy, early repeat retinal screening warranted. Visual acuity: OD 6/9, OS 6/9. IOP: OD 15, OS 16. Dilated fundoscopy: no microaneurysms, no hemorrhages, no macular edema bilaterally. Impression: no diabetic retinopathy. No progression. Continue annual screening (next June 2026). Good correlation with HbA1c control.',
 'Dr. Kulkarni', 'Sankara Nethralaya, Mumbai',
 '{"visual_acuity_od":"6/9","visual_acuity_os":"6/9","iop_od":15,"iop_os":16,"diabetic_retinopathy":"absent","macular_edema":"absent","reason":"early_rescreen_given_nephropathy","next_screening":"June 2026"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #39 — 2025-12-30 — General checkup / annual health review (Miscellaneous)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000039',
 '11111111-1111-1111-1111-111111111111',
 '2025-12-30',
 'End of year general checkup. Doctor did a full physical exam. Checked my heart, lungs, stomach, everything. Said I am managing well for someone with diabetes and BP issues.',
 'Annual comprehensive health review. General: well-appearing, alert. Vitals: BP 130/84, HR 74, RR 16, SpO2 98%, Temp 36.6C. Weight 72.0 kg. HEENT: normal. CVS: S1 S2 normal, no murmurs. Chest: bilateral clear air entry, no wheeze. Abdomen: soft, non-tender, no organomegaly. Extremities: no edema, pedal pulses palpable. Neuro: grossly intact. Review of systems: no new complaints. Year summary: DM2 improved (HbA1c 7.8→7.2), HTN controlled, dyslipidemia at target, microalbuminuria responding to ACE-I. One hypoglycemia event (resolved). Overall: satisfactory chronic disease management.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"bp_systolic":130,"bp_diastolic":84,"heart_rate":74,"spo2":98,"weight":72.0,"annual_summary":{"hba1c_trend":"7.8_to_7.2","htn":"controlled","ldl":"at_target","acr":"improving_on_lisinopril","retinopathy":"absent","neuropathy":"absent"},"overall":"satisfactory"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #40 — 2025-12-15 — Pharmacy/medication counseling #5
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000040',
 '11111111-1111-1111-1111-111111111111',
 '2025-12-15',
 'Picked up my medicines for the next 3 months. The pharmacist also reminded me to get my pneumonia vaccine which I have been putting off.',
 'Pharmacy refill and counseling. 5-medication regimen dispensed (3-month supply): Metformin 500mg, Amlodipine 5mg, Atorvastatin 20mg, Aspirin 75mg, Lisinopril 10mg. Compliance review: patient using laminated schedule card — no missed doses in past month. Reminded about pending pneumococcal vaccination (PPSV23 — recommended for DM2 patients >60 years). Patient agreed to schedule for next clinic visit.',
 'Pharmacist Joshi', 'Apollo Clinic, Mumbai',
 '{"medications_dispensed":5,"supply_duration":"3_months","compliance":"excellent","pending_vaccine":"pneumococcal_ppsv23"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #41 — 2026-01-05 — Lab test (pre-visit labs for Jan 10 appointment)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000041',
 '11111111-1111-1111-1111-111111111111',
 '2026-01-05',
 'Got blood tests done before my January appointment with Dr. Mehta. Had to fast overnight again.',
 'Fasting laboratory panel (pre-visit for quarterly review). HbA1c 8.1% — SIGNIFICANT INCREASE from 7.2%. Fasting glucose 156 mg/dL. Lipid panel: TC 186, LDL 94, HDL 44, TG 162. Renal: creatinine 1.1, eGFR 71. Potassium 4.2. Urine ACR: 32 mg/g (continues to improve). LFT and CK normal.',
 'Lab Technician', 'SRL Diagnostics, Mumbai',
 '{"hba1c":8.1,"fasting_glucose":156,"ldl":94,"hdl":44,"triglycerides":162,"creatinine":1.1,"egfr":71,"potassium":4.2,"urine_acr":32}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- (Existing #01 = 2026-01-10, #02 = 2026-02-20, #03 = 2026-03-18 — SKIPPED)
-- ---------------------------------------------------------------------------

-- ---------------------------------------------------------------------------
-- #42 — 2026-01-22 — Ophthalmology follow-up
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000042',
 '11111111-1111-1111-1111-111111111111',
 '2026-01-22',
 'Went for another eye check because my sugar went high again. Dr. Kulkarni checked carefully and said still no damage, but I need to control sugar quickly or it could start.',
 'Ophthalmology follow-up (prompted by HbA1c spike to 8.1%). Dilated fundoscopy: no new microaneurysms or hemorrhages. No macular edema. OCT macula: normal retinal thickness OU. Impression: no diabetic retinopathy despite glycemic deterioration. Counseled patient that sustained hyperglycemia significantly increases retinopathy risk. Urged strict glycemic control. Next: rescreen in 6 months or sooner if HbA1c remains >8%.',
 'Dr. Kulkarni', 'Sankara Nethralaya, Mumbai',
 '{"diabetic_retinopathy":"absent","oct_macula":"normal","context":"hba1c_8.1_spike","counseling":"glycemic_control_urgent","next_screening":"6_months_or_sooner"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #43 — 2026-01-30 — Podiatry/foot exam #3
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000043',
 '11111111-1111-1111-1111-111111111111',
 '2026-01-30',
 'Annual foot exam. The doctor noticed my feet are a bit more dry than before and asked me to use a special cream. The nerve test was still normal though.',
 'Diabetic foot examination (annual). Skin: increased dryness bilateral, early fissuring on right heel — prescribed urea 20% cream BD. No ulcers, calluses, or fungal infection. Monofilament (10g): protective sensation intact all 10 sites bilateral. Vibration: intact. Pedal pulses: palpable bilateral. ABI: 1.02 right, 1.05 left (normal). No neuropathy. Advised moisturize feet twice daily, inspect daily, avoid hot water soaks. Follow-up in 6 months.',
 'Dr. Sunil Patil', 'Apollo Clinic, Mumbai',
 '{"monofilament_test":"normal","vibration_sense":"normal","abi_right":1.02,"abi_left":1.05,"skin":"increased_dryness_right_heel_fissuring","treatment":"urea_20pct_cream","neuropathy":"absent"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #44 — 2026-02-10 — Lab test (1-month post Metformin uptitration)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000044',
 '11111111-1111-1111-1111-111111111111',
 '2026-02-10',
 'Quick blood test to check if the higher Metformin dose is helping. Just fasting sugar and kidney test this time.',
 'Interim labs (1 month post Metformin uptitration 500→1000mg BD). Fasting glucose 138 mg/dL (improving from 156). Renal: creatinine 1.1, eGFR 71 (stable). Potassium 4.3. No lactic acidosis concern. Metformin uptitration appears to be having early effect.',
 'Lab Technician', 'SRL Diagnostics, Mumbai',
 '{"fasting_glucose":138,"creatinine":1.1,"egfr":71,"potassium":4.3,"lactic_acidosis":"no_concern","metformin_response":"early_improvement"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #45 — 2026-02-28 — Ophthalmology (dilated exam — 6mo follow-up)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000045',
 '11111111-1111-1111-1111-111111111111',
 '2026-02-28',
 'Another eye check. Dr. Kulkarni said everything is still clear. He wants to see me again in June for the annual screening.',
 'Ophthalmology follow-up. Visual acuity: OD 6/9, OS 6/12 (slight decline OS — refraction recommended). IOP: OD 15, OS 16. Dilated fundoscopy: no diabetic retinopathy OU. No macular edema. Impression: stable, no retinopathy. Left eye acuity slightly reduced — likely refractive, not diabetic. Ordered refraction. Next annual screening June 2026.',
 'Dr. Kulkarni', 'Sankara Nethralaya, Mumbai',
 '{"visual_acuity_od":"6/9","visual_acuity_os":"6/12","iop_od":15,"iop_os":16,"diabetic_retinopathy":"absent","note":"os_refraction_recommended","next_screening":"June_2026"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #46 — 2026-03-05 — Routine DM2+HTN follow-up
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000046',
 '11111111-1111-1111-1111-111111111111',
 '2026-03-05',
 'Saw Dr. Mehta for regular checkup. Fasting sugar has come down since he increased the Metformin dose. But BP is slowly creeping up again — 138/88 today. He wants me to do more walking.',
 'Quarterly DM2+HTN review. BP 138/88 — trending up from well-controlled range. HR 76. Weight 72.4 kg. Fasting glucose (home): 130-140 mg/dL (improved from 150+ range post-uptitration). Current regimen: Metformin 1000mg BD, Amlodipine 5mg, Lisinopril 10mg, Atorvastatin 20mg, Aspirin 75mg. BP not at target despite dual antihypertensive therapy. Dietary sodium assessment: estimated 3g/day (above 2g target). Plan: strict sodium restriction, increase physical activity to 30 min/day, recheck in 2 weeks. If BP persists >140/90, consider uptitrating Amlodipine to 10mg or adding HCTZ.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"bp_systolic":138,"bp_diastolic":88,"heart_rate":76,"weight":72.4,"fasting_glucose_range":"130-140","sodium_intake_estimated":"3g","plan":"strict_sodium_restriction_increase_exercise","escalation_plan":"amlodipine_uptitration_or_add_hctz"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #47 — 2026-03-10 — Miscellaneous (pneumococcal vaccine)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000047',
 '11111111-1111-1111-1111-111111111111',
 '2026-03-10',
 'Finally got the pneumonia vaccine that the pharmacist had been reminding me about. Small injection in the arm, bit sore afterwards but nothing major.',
 'Pneumococcal vaccination administered. PPSV23 (Pneumovax 23) 0.5 mL IM right deltoid. Indicated for DM2 patient >60 years per ACIP/IAP guidelines. No immediate adverse reactions (monitored 15 minutes). Mild local tenderness expected. No further pneumococcal vaccination needed for 5 years. Updated vaccination record.',
 'Dr. Mehta', 'Apollo Clinic, Mumbai',
 '{"vaccine":"pneumococcal_ppsv23","route":"IM_right_deltoid","adverse_reaction":"none","next_due":"5_years"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #48 — 2026-03-15 — Lab test (pre-visit)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000048',
 '11111111-1111-1111-1111-111111111111',
 '2026-03-15',
 'Blood and urine tests before my next visit with Dr. Mehta. Hoping the kidney numbers are still getting better.',
 'Fasting laboratory panel (quarterly). HbA1c 7.6% (improving from 8.1% — Metformin uptitration effective). Fasting glucose 132 mg/dL. Lipid panel: TC 180, LDL 90, HDL 46, TG 152. Renal: creatinine 1.1, eGFR 71. Potassium 4.4. Urine ACR: 30 mg/g (continues improving from 45 → 34 → 32 → 30). LFT normal.',
 'Lab Technician', 'SRL Diagnostics, Mumbai',
 '{"hba1c":7.6,"fasting_glucose":132,"ldl":90,"hdl":46,"triglycerides":152,"creatinine":1.1,"egfr":71,"potassium":4.4,"urine_acr":30}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #49 — 2026-03-22 — Miscellaneous (general BP trending check)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000049',
 '11111111-1111-1111-1111-111111111111',
 '2026-03-22',
 'Just a quick BP check at the clinic since my home readings have been on the higher side. The nurse took it three times. It was 144/92 average. Doctor said we may need to increase one of the BP medicines.',
 'Walk-in BP assessment. Serial BP measurements: 146/94, 142/90, 144/92 (average 144/92). Consistently above target (<140/90) on dual therapy (Amlodipine 5mg + Lisinopril 10mg). No headache, visual changes, or chest pain. Weight 72.6 kg. Plan: scheduled formal follow-up for medication adjustment consideration. Reinforced sodium restriction and stress management.',
 'Nurse Sharma', 'Apollo Clinic, Mumbai',
 '{"bp_readings":[{"systolic":146,"diastolic":94},{"systolic":142,"diastolic":90},{"systolic":144,"diastolic":92}],"bp_average":"144/92","symptoms":"none","plan":"schedule_followup_for_med_adjustment"}'::jsonb,
 NULL),

-- ---------------------------------------------------------------------------
-- #50 — 2026-03-28 — ER VISIT: HYPERTENSIVE URGENCY (BP 182/110)
-- ---------------------------------------------------------------------------
('ccccccc1-0000-0000-0000-000000000050',
 '11111111-1111-1111-1111-111111111111',
 '2026-03-28',
 'I had a very bad headache and felt like my heart was pounding. Priya was visiting and she checked my BP at home — it was 182/110. She panicked and took me to Apollo emergency. They gave me medicine through IV to bring the BP down. I was kept for observation for 6 hours.',
 'ER visit — hypertensive urgency. Presenting complaint: severe occipital headache, palpitations, anxiety. Home BP reading 182/110 (taken by daughter). ER triage: BP 178/108 (confirmed), HR 92, RR 20, SpO2 97%. No focal neurological deficits. No chest pain. Fundoscopy: no papilledema. ECG: sinus tachycardia, no acute ST changes. Troponin I: <0.01 (negative). Creatinine 1.2 (mildly up from baseline 1.1). Urine dipstick: trace protein. Management: IV Labetalol 20mg bolus → BP reduced to 158/96 at 30 min → repeat Labetalol 40mg → BP 142/88 at 1 hour. Transitioned to oral medications. Observed 6 hours — BP stabilized at 138/86. Discharge plan: continue current medications, add Amlodipine uptitration from 5mg to 10mg (per Dr. Mehta phone consultation), urgent follow-up with Dr. Mehta within 48 hours, daily home BP monitoring, avoid stress and excess salt.',
 'Dr. Nair', 'Apollo Hospital ER, Mumbai',
 '{"presenting_bp":"182/110","er_bp":"178/108","heart_rate":92,"spo2":97,"headache":"severe_occipital","neuro_deficits":"none","papilledema":"absent","ecg":"sinus_tachycardia_no_st_changes","troponin":"<0.01","creatinine":1.2,"treatment":[{"drug":"labetalol_iv","dose":"20mg_then_40mg"}],"bp_30min":"158/96","bp_1hr":"142/88","bp_discharge":"138/86","disposition":"discharged_after_6hr","plan":["amlodipine_uptitrate_5_to_10mg","urgent_followup_48hr","daily_home_bp"]}'::jsonb,
 NULL)

ON CONFLICT (id) DO NOTHING;


-- =============================================================================
-- HEALTH METRICS — Quarterly lab values (HbA1c, eGFR, Urine ACR, LDL)
-- =============================================================================
-- These complement the existing 90-day time-series in seed_rajesh.sql and
-- extend lab tracking back to Oct 2024.

-- HbA1c (quarterly)
INSERT INTO health_metrics (patient_id, metric_type, value_primary, value_secondary, unit, measured_at, source)
VALUES
('11111111-1111-1111-1111-111111111111', 'hba1c', 7.8, NULL, '%', '2024-10-15 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'hba1c', 7.4, NULL, '%', '2025-01-20 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'hba1c', 7.1, NULL, '%', '2025-05-20 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'hba1c', 7.1, NULL, '%', '2025-09-08 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'hba1c', 7.2, NULL, '%', '2025-12-08 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'hba1c', 8.1, NULL, '%', '2026-01-05 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'hba1c', 7.6, NULL, '%', '2026-03-15 09:00:00', 'lab')
ON CONFLICT DO NOTHING;

-- eGFR (quarterly)
INSERT INTO health_metrics (patient_id, metric_type, value_primary, value_secondary, unit, measured_at, source)
VALUES
('11111111-1111-1111-1111-111111111111', 'egfr', 78, NULL, 'mL/min/1.73m2', '2024-10-15 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'egfr', 77, NULL, 'mL/min/1.73m2', '2025-01-20 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'egfr', 74, NULL, 'mL/min/1.73m2', '2025-05-20 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'egfr', 72, NULL, 'mL/min/1.73m2', '2025-09-08 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'egfr', 73, NULL, 'mL/min/1.73m2', '2025-12-08 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'egfr', 71, NULL, 'mL/min/1.73m2', '2026-01-05 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'egfr', 71, NULL, 'mL/min/1.73m2', '2026-03-15 09:00:00', 'lab')
ON CONFLICT DO NOTHING;

-- Urine ACR (quarterly — tracking microalbuminuria)
INSERT INTO health_metrics (patient_id, metric_type, value_primary, value_secondary, unit, measured_at, source)
VALUES
('11111111-1111-1111-1111-111111111111', 'urine_acr', 22, NULL, 'mg/g', '2025-01-20 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'urine_acr', 28, NULL, 'mg/g', '2025-05-20 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'urine_acr', 45, NULL, 'mg/g', '2025-09-08 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'urine_acr', 34, NULL, 'mg/g', '2025-12-08 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'urine_acr', 32, NULL, 'mg/g', '2026-01-05 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'urine_acr', 30, NULL, 'mg/g', '2026-03-15 09:00:00', 'lab')
ON CONFLICT DO NOTHING;

-- LDL cholesterol (quarterly)
INSERT INTO health_metrics (patient_id, metric_type, value_primary, value_secondary, unit, measured_at, source)
VALUES
('11111111-1111-1111-1111-111111111111', 'ldl', 148, NULL, 'mg/dL', '2024-10-15 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'ldl', 142, NULL, 'mg/dL', '2025-01-20 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'ldl', 108, NULL, 'mg/dL', '2025-05-20 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'ldl', 96, NULL, 'mg/dL', '2025-09-08 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'ldl', 92, NULL, 'mg/dL', '2025-12-08 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'ldl', 94, NULL, 'mg/dL', '2026-01-05 09:00:00', 'lab'),
('11111111-1111-1111-1111-111111111111', 'ldl', 90, NULL, 'mg/dL', '2026-03-15 09:00:00', 'lab')
ON CONFLICT DO NOTHING;

COMMIT;

-- =============================================================================
-- Verification queries (optional — run manually)
-- =============================================================================
-- SELECT COUNT(*) FROM visit_records WHERE patient_id = '11111111-1111-1111-1111-111111111111';
-- -- Expected: 50 (3 original + 47 new)
--
-- SELECT visit_date, doctor_name, hospital_name FROM visit_records
--   WHERE patient_id = '11111111-1111-1111-1111-111111111111'
--   ORDER BY visit_date;
--
-- SELECT metric_type, COUNT(*), MIN(measured_at), MAX(measured_at)
--   FROM health_metrics
--   WHERE patient_id = '11111111-1111-1111-1111-111111111111'
--     AND metric_type IN ('hba1c','egfr','urine_acr','ldl')
--   GROUP BY metric_type;
-- =============================================================================
-- End of seed_rajesh_expanded.sql
-- =============================================================================
