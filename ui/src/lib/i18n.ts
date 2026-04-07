/**
 * CareFlow i18n — Lightweight internationalization
 * 핵심 UI 텍스트 한국어/영어 전환
 */

export type Lang = 'en' | 'ko' | 'hi';

const translations: Record<string, Record<string, string>> = {
    // Home
    'greeting': { en: 'Namaste, Rajesh.', ko: '안녕하세요, 라제시님.', hi: 'नमस्ते, राजेश जी।' },
    'health_summary': { en: 'Here is your health summary for today.', ko: '오늘의 건강 요약입니다.', hi: 'यह रहा आज का आपका स्वास्थ्य सारांश।' },
    'blood_pressure': { en: 'Blood Pressure', ko: '혈압', hi: 'ब्लड प्रेशर (BP)' },
    'blood_glucose': { en: 'Blood Glucose', ko: '혈당', hi: 'ब्लड शुगर' },
    'elevated': { en: 'Elevated', ko: '주의', hi: 'बढ़ा हुआ' },
    'normal': { en: 'Normal', ko: '정상', hi: 'सामान्य' },
    'near_target': { en: 'Near Target', ko: '거의 정상', hi: 'लक्ष्य के करीब' },

    // Medications
    'next_medication': { en: 'Next Medication', ko: '다음 복용', hi: 'अगली दवाई' },
    'medications': { en: 'Medications', ko: '복용 약 목록', hi: 'दवाइयाँ' },
    'mark_taken': { en: 'Mark Taken', ko: '복용 완료', hi: 'दवा ली' },
    'taken': { en: 'Taken', ko: '복용함', hi: 'ले ली' },
    'scheduled': { en: 'Scheduled', ko: '예정', hi: 'निर्धारित' },

    // Safety
    'safety_info': { en: 'Safety Info', ko: '안전 정보', hi: 'सुरक्षा जानकारी' },
    'drug_alerts': { en: 'Drug Interaction Alerts', ko: '약물 충돌 주의', hi: 'दवाओं की टकराहट अलर्ट' },
    'interactions': { en: 'interactions', ko: '건의 약물 충돌', hi: 'दवाओं की टकराहट' },
    'tap_to_review': { en: 'Tap to review', ko: '탭하여 확인', hi: 'देखने के लिए टैप करें' },

    // Schedule
    'your_schedule': { en: 'Your Schedule', ko: '나의 일정', hi: 'आपकी समय-सारणी' },
    'upcoming_appointments': { en: 'Upcoming Appointments', ko: '예정된 진료', hi: 'आगामी अपॉइंटमेंट' },
    'past_appointments': { en: 'Past Appointments', ko: '지난 진료', hi: 'पिछली मुलाक़ातें' },
    'daily_medication_plan': { en: 'Daily Medication Plan', ko: '일일 복약 계획', hi: 'दैनिक दवा योजना' },
    'this_month': { en: 'This Month', ko: '이번 달', hi: 'इस महीने' },
    'cancel': { en: 'Cancel', ko: '취소', hi: 'रद्द करें' },
    'book_appointment': { en: 'Book Appointment', ko: '예약하기', hi: 'अपॉइंटमेंट बुक करें' },
    'next_visit': { en: 'Next Visit', ko: '다음 방문', hi: 'अगली मुलाक़ात' },
    'schedule': { en: 'Schedule', ko: '일정', hi: 'समय-सारणी' },
    'add_new': { en: '+ Add New', ko: '+ 새 예약', hi: '+ नया जोड़ें' },
    'fasting_required': { en: 'Fasting Required', ko: '검사 전 금식 필요', hi: 'खाली पेट आना ज़रूरी है' },
    'no_fasting': { en: 'No fasting needed', ko: '금식 안 하셔도 됩니다', hi: 'खाली पेट आने की ज़रूरत नहीं' },

    // Chat
    'ask_health': { en: 'Ask about your health', ko: '건강에 대해 물어보세요', hi: 'अपने स्वास्थ्य के बारे में पूछें' },
    'type_message': { en: 'Type a message...', ko: '메시지를 입력하세요...', hi: 'संदेश लिखें...' },
    'analyzing': { en: 'Let me look into that for you', ko: '확인하고 있어요', hi: 'मैं आपके लिए देख रहा हूँ...' },
    'send': { en: 'Send', ko: '전송', hi: 'भेजें' },
    'responding': { en: 'Responding...', ko: '응답 중...', hi: 'जवाब दे रहे हैं...' },
    'careflow_thinking': { en: 'CareFlow is thinking...', ko: 'CareFlow가 생각 중...', hi: 'CareFlow सोच रहा है...' },

    // Prompts
    'prompt_1': { en: 'How am I doing today?', ko: '오늘 건강 상태는 어때요?', hi: 'आज मेरी सेहत कैसी है?' },
    'prompt_2': { en: 'Check my blood pressure trend', ko: '혈압 추세를 확인해주세요', hi: 'मेरा BP ट्रेंड देखें' },
    'prompt_3': { en: 'What should I eat for lunch?', ko: '점심에 뭘 먹으면 좋을까요?', hi: 'दोपहर में क्या खाना चाहिए?' },
    'prompt_4': { en: 'When is my next appointment?', ko: '다음 예약이 언제예요?', hi: 'मेरी अगली अपॉइंटमेंट कब है?' },

    // Doctor View
    'doctor_summary': { en: "Doctor's Pre-Visit Summary", ko: '진료 전 요약', hi: "डॉक्टर का प्री-विज़िट सारांश" },
    'adherence_report': { en: 'Adherence Report', ko: '약 복용 현황', hi: 'दवा पालन रिपोर्ट' },
    'health_insights': { en: 'Health Insights', ko: '건강 인사이트', hi: 'स्वास्थ्य जानकारी' },
    'consult_topics': { en: 'Consult Topics', ko: '상담 주제', hi: 'परामर्श विषय' },
    'start_consult': { en: 'Start Consult', ko: '상담 시작', hi: 'परामर्श शुरू करें' },
    'full_history': { en: 'Full History', ko: '전체 기록', hi: 'पूरा इतिहास' },
    'add_topic': { en: 'Add Custom Topic', ko: '상담 주제 추가', hi: 'अपना विषय जोड़ें' },

    // Visit Summary
    'visit_summary': { en: 'Visit Summary', ko: '방문 요약', hi: 'मुलाक़ात सारांश' },
    'medication_change': { en: 'Medication Change', ko: '약 변경 사항', hi: 'दवाई में बदलाव' },
    'caregiver_notification': { en: 'Caregiver Notification', ko: '보호자 알림', hi: 'परिवारजन को सूचना' },
    'download_report': { en: 'Download Report (PDF)', ko: '보고서 다운로드 (PDF)', hi: 'रिपोर्ट डाउनलोड करें (PDF)' },
    'ask_careflow': { en: 'Ask CareFlow', ko: 'CareFlow에게 질문', hi: 'CareFlow से पूछें' },

    // Navigation
    'home': { en: 'Home', ko: '홈', hi: 'होम' },
    'doctor_view': { en: 'Doctor View', ko: '의사 화면', hi: 'डॉक्टर पेज' },
    'my_visits': { en: 'My Visits', ko: '방문 기록', hi: 'मेरी मुलाक़ातें' },

    // Settings
    'settings': { en: 'Settings', ko: '설정', hi: 'सेटिंग्स' },
    'language': { en: 'Language', ko: '언어', hi: 'भाषा' },
    'support': { en: 'Support', ko: '고객 지원', hi: 'सहायता' },

    // Dietary
    'dietary_update': { en: 'Dietary Update', ko: '식사 안내', hi: 'खान-पान अपडेट' },
    'sodium_limit': { en: 'Sodium limit: 2,300mg/day', ko: '소금(나트륨) 제한: 하루 2,300mg', hi: 'नमक (सोडियम) सीमा: 2,300mg प्रतिदिन' },

    // Agent Activity
    'agent_analyzing': { en: 'CareFlow AI is analyzing...', ko: 'CareFlow AI가 분석 중...', hi: 'CareFlow AI जाँच कर रहा है...' },
    'analysis_complete': { en: 'Analysis complete', ko: '분석 완료', hi: 'जाँच पूरी हुई' },
    'routing': { en: 'Routing your question', ko: '질문을 분석하는 중', hi: 'आपका सवाल भेज रहे हैं' },
    'checking_meds': { en: 'Checking your medications', ko: '약물을 확인하는 중', hi: 'आपकी दवाइयाँ जाँच रहे हैं' },
    'analyzing_health': { en: 'Analyzing health data', ko: '건강 데이터를 분석하는 중', hi: 'स्वास्थ्य जानकारी जाँच रहे हैं' },
    'consulting_records': { en: 'Consulting medical records', ko: '의료 기록을 조회하는 중', hi: 'मेडिकल रिकॉर्ड देख रहे हैं' },
    'checking_interactions': { en: 'Checking drug interactions', ko: '약물 충돌 여부를 확인하는 중', hi: 'दवाओं की टकराहट जाँच रहे हैं' },
    'preparing_response': { en: 'Preparing response', ko: '응답을 준비하는 중', hi: 'जवाब तैयार कर रहे हैं' },

    // Health Tips (patient-facing)
    'tip_walking': { en: 'Did you know? Walking 30 min daily lowers BP by 5-8 mmHg.', ko: '알고 계셨나요? 매일 30분 걸으시면 혈압이 5~8 mmHg 낮아져요.', hi: 'क्या आप जानते हैं? रोज़ 30 मिनट टहलने से ब्लड प्रेशर 5-8 mmHg कम होता है।' },
    'tip_metformin': { en: 'Tip: Take Metformin with meals to reduce stomach upset.', ko: '안내: Metformin은 식사와 함께 드시면 속이 편해요.', hi: 'सुझाव: पेट की तकलीफ़ कम करने के लिए मेटफ़ॉर्मिन खाने के साथ लें।' },
    'tip_dash': { en: 'Fact: A DASH diet can lower BP as much as medication.', ko: '참고: DASH 식단은 약만큼 혈압을 낮출 수 있어요.', hi: 'तथ्य: DASH डाइट दवाई जितना ब्लड प्रेशर कम कर सकती है।' },
    'tip_sleep': { en: 'Sleep tip: 7-8 hours of sleep helps regulate blood sugar.', ko: '수면 안내: 7~8시간 주무시면 혈당 조절에 도움이 돼요.', hi: 'नींद का सुझाव: 7-8 घंटे की नींद ब्लड शुगर नियंत्रित रखती है।' },
    'tip_checkup': { en: 'Reminder: Regular check-ups catch problems early.', ko: '알림: 정기 검진을 받으시면 문제를 일찍 발견할 수 있어요.', hi: 'याद रखें: नियमित जाँच से समस्याएँ जल्दी पकड़ में आती हैं।' },

    // Date labels
    'today': { en: 'Today', ko: '오늘', hi: 'आज' },
    'tomorrow': { en: 'Tomorrow', ko: '내일', hi: 'कल' },
    'in_n_days': { en: 'In {n} Days', ko: '{n}일 후', hi: '{n} दिन बाद' },

    // Typing messages
    'typing_1': { en: 'Checking your health summary for today...', ko: '오늘의 건강 요약을 확인하고 있어요...', hi: 'आज का स्वास्थ्य सारांश देख रहे हैं...' },
    'typing_2': { en: 'Your blood pressure is being monitored.', ko: '혈압을 모니터링하고 있습니다.', hi: 'आपका BP जाँचा जा रहा है।' },
    'typing_3': { en: 'Reviewing your medication schedule...', ko: '복용 일정을 검토하고 있어요...', hi: 'आपकी दवाई का शेड्यूल देख रहे हैं...' },
    'typing_4': { en: 'Keeping track of your upcoming appointments.', ko: '다가오는 예약을 확인하고 있습니다.', hi: 'आपकी आगामी अपॉइंटमेंट पर नज़र रख रहे हैं।' },
    'typing_5': { en: 'Your care team is staying informed.', ko: '담당 의료팀이 최신 정보를 확인하고 있습니다.', hi: 'आपकी केयर टीम को जानकारी मिल रही है।' },

    // TopBar / Emergency / Sidebar extras
    'notifications': { en: 'Notifications', ko: '알림', hi: 'सूचनाएँ' },
    'call_emergency': { en: 'Call Emergency', ko: '응급 전화', hi: 'इमरजेंसी कॉल करें' },
    'dark_mode': { en: 'Dark Mode', ko: '다크 모드', hi: 'डार्क मोड' },
    'text_size': { en: 'Text Size', ko: '글자 크기', hi: 'अक्षर का आकार' },
    'color_vision': { en: 'Color Vision', ko: '색각 모드', hi: 'रंग दृष्टि' },
    'close': { en: 'Close', ko: '닫기', hi: 'बंद करें' },
    'care_partner': { en: 'Your Care Partner', ko: '나의 건강 파트너', hi: 'आपका देखभाल साथी' },
    'powered_by': { en: 'Powered by CareFlow AI', ko: 'CareFlow AI 기반', hi: 'CareFlow AI द्वारा संचालित' },

    // Misc UI
    'done': { en: 'Done', ko: '완료', hi: 'हो गया' },
    'no_issues': { en: 'No issues', ko: '문제 없음', hi: 'कोई समस्या नहीं' },
    'all_clear': { en: 'All clear', ko: '이상 없음', hi: 'सब ठीक है' },
    'loading': { en: 'Loading...', ko: '로딩 중...', hi: 'लोड हो रहा है...' },
    'agents': { en: 'agents', ko: '에이전트', hi: 'एजेंट' },
};

let currentLang: Lang = 'en';

export function setLang(lang: Lang) { currentLang = lang; }
export function getLang(): Lang { return currentLang; }
export function t(key: string): string {
    return translations[key]?.[currentLang] || translations[key]?.['en'] || key;
}
