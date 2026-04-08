import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Icon } from '@iconify/react';
import BentoCard from './BentoCard';
import EmergencyBanner from './EmergencyBanner';
import DrugInteractionAlert from './DrugInteractionAlert';
import ChatTrendChart from './ChatTrendChart';
import AgentActivityFeed from './AgentActivityFeed';
import { cn } from '../lib/utils';
import ReactMarkdown from 'react-markdown';
import { t } from '../lib/i18n';
import type { UseAgentChatReturn } from '../lib/useAgentChat';
import { fetchLatestMetric, fetchMetricTrend, fetchActiveMedications, fetchAppointments, markMedicationTaken, fetchDrugInteractions } from '../lib/api';
import type { MetricLatest, Medication, Appointment as ApiAppointment, DrugInteraction } from '../lib/api';

interface PatientDashboardViewProps {
    agentChat: UseAgentChatReturn;
    onViewChange?: (view: string) => void;
}

// Hardcoded fallback values
const FALLBACK_BP: VitalData = { value: '140/90', unit: 'mmHg', badgeKey: 'elevated', badgeColor: 'text-error bg-error-container', barWidth: '84%', barColor: 'bg-error' };
const FALLBACK_GLUCOSE: VitalData = { value: '128', unit: 'mg/dL', badgeKey: 'near_target', badgeColor: 'text-warning bg-warning/10', barWidth: '58%', barColor: 'bg-warning' };

interface VitalData { value: string; unit: string; badgeKey: string; badgeColor: string; barWidth: string; barColor: string; }
const FALLBACK_MEDS: { name: string; dose: string; status?: string; time?: string; active?: boolean; dimmed?: boolean; id?: string }[] = [
    { name: 'Metformin', dose: '1000mg · After Breakfast', status: 'taken', time: '08:30 AM' },
    { name: 'Aspirin', dose: '75mg · After Breakfast', status: 'taken', time: '08:30 AM' },
    { name: 'Amlodipine', dose: '5mg · Before Lunch', active: true },
    { name: 'Lisinopril', dose: '10mg · After Lunch', time: 'Scheduled: 01:30 PM', dimmed: true },
    { name: 'Atorvastatin', dose: '20mg · Before Bed', time: 'Scheduled: 09:00 PM', dimmed: true },
];
const FALLBACK_APPT = { title: 'HbA1c Test', date: 'Wednesday, April 17', time: '08:00 AM', location: 'Apollo Clinic, Mumbai', note: 'Fasting required', daysUntil: 'In 10 Days' as string };

const SUGGESTED_PROMPTS = [
    { textKey: 'prompt_1', icon: "solar:heart-pulse-linear" },
    { textKey: 'prompt_2', icon: "solar:graph-up-linear" },
    { textKey: 'prompt_3', icon: "solar:chef-hat-linear" },
    { textKey: 'prompt_4', icon: "solar:calendar-linear" },
];

const TYPING_MESSAGES_KEYS = ['typing_1', 'typing_2', 'typing_3', 'typing_4', 'typing_5'];

/* -- JSON Response Fallback Parser ---------------------------------------- */
/**
 * Parses agent responses that may come back as JSON (from after_model callbacks
 * or edge cases) and extracts human-readable text.
 */
function parseAgentResponse(raw: string): string {
    const trimmed = raw.trim();

    // Strip markdown code fences
    let jsonStr = trimmed;
    if (jsonStr.startsWith('```')) {
        const lines = jsonStr.split('\n');
        lines.shift(); // remove ```json
        if (lines[lines.length - 1]?.trim() === '```') lines.pop();
        jsonStr = lines.join('\n');
    }

    // Try JSON parse
    if (jsonStr.startsWith('{') || jsonStr.startsWith('[')) {
        try {
            const parsed = JSON.parse(jsonStr);
            if (typeof parsed === 'object' && parsed !== null) {
                // Extract readable fields
                const textFields = ['message', 'text', 'answer', 'recommendation', 'response', 'summary', 'description'];
                for (const field of textFields) {
                    if (typeof parsed[field] === 'string' && parsed[field].length > 10) {
                        let result: string = parsed[field];
                        // Append warnings if present
                        if (parsed.food_drug_warnings?.length) {
                            result += '\n\n\u26A0\uFE0F Drug-Food Warnings:\n' + parsed.food_drug_warnings.map((w: any) => `\u2022 ${w.medication}: Avoid ${w.avoid_food} \u2014 ${w.reason}`).join('\n');
                        }
                        if (parsed.warnings?.length) {
                            result += '\n\n\u26A0\uFE0F Warnings:\n' + parsed.warnings.map((w: any) => typeof w === 'string' ? `\u2022 ${w}` : `\u2022 ${JSON.stringify(w)}`).join('\n');
                        }
                        // Append disclaimer if present
                        if (parsed.disclaimer) {
                            result += '\n\n\uD83D\uDCCB ' + parsed.disclaimer;
                        }
                        return result;
                    }
                }

                // For structured data like meal plans, format nicely
                if (parsed.sample_meals) {
                    let result = '';
                    if (parsed.recommended_foods) result += '\u2705 Recommended: ' + parsed.recommended_foods.join(', ') + '\n\n';
                    if (parsed.avoid_foods) result += '\u274C Avoid: ' + parsed.avoid_foods.join(', ') + '\n\n';
                    if (parsed.sample_meals) {
                        result += '\uD83C\uDF7D\uFE0F Sample Meals:\n';
                        for (const [meal, desc] of Object.entries(parsed.sample_meals)) {
                            result += `\u2022 ${meal.charAt(0).toUpperCase() + meal.slice(1)}: ${desc}\n`;
                        }
                    }
                    if (parsed.disclaimer) result += '\n\uD83D\uDCCB ' + parsed.disclaimer;
                    return result;
                }

                // For options arrays
                if (parsed.options?.length) {
                    let result = parsed.options.map((o: string, i: number) => `${i + 1}. ${o}`).join('\n');
                    if (parsed.notes) result += '\n\n\uD83D\uDCDD ' + parsed.notes;
                    if (parsed.disclaimer) result += '\n\n\uD83D\uDCCB ' + parsed.disclaimer;
                    return result;
                }

                // Fallback: stringify nicely but remove technical fields
                const { disclaimer, confidence, recommendation_type, constraints_applied, ...rest } = parsed;
                return JSON.stringify(rest, null, 2);
            }
        } catch {
            // Not valid JSON, return as-is
        }
    }

    return raw;
}

/* -- Typing Animation Component ------------------------------------------ */
const TypingAnimation: React.FC<{ texts: string[] }> = ({ texts }) => {
    const [currentTextIndex, setCurrentTextIndex] = useState(0);
    const [displayText, setDisplayText] = useState('');
    const [isDeleting, setIsDeleting] = useState(false);

    useEffect(() => {
        const currentFullText = texts[currentTextIndex];
        let timeout: ReturnType<typeof setTimeout>;

        if (!isDeleting && displayText === currentFullText) {
            // Pause before deleting
            timeout = setTimeout(() => setIsDeleting(true), 2000);
        } else if (isDeleting && displayText === '') {
            // Move to next text
            setIsDeleting(false);
            setCurrentTextIndex((prev) => (prev + 1) % texts.length);
        } else if (isDeleting) {
            // Erase character by character
            timeout = setTimeout(() => {
                setDisplayText(currentFullText.substring(0, displayText.length - 1));
            }, 20);
        } else {
            // Type character by character
            timeout = setTimeout(() => {
                setDisplayText(currentFullText.substring(0, displayText.length + 1));
            }, 35);
        }

        return () => clearTimeout(timeout);
    }, [displayText, isDeleting, currentTextIndex, texts]);

    return (
        <p className="text-slate-500 mt-2 text-base font-medium h-7">
            <span className="cursor-blink">{displayText}</span>
        </p>
    );
};

/* -- Health Tips Cycling Component ---------------------------------------- */
const HEALTH_TIP_KEYS = ['tip_walking', 'tip_metformin', 'tip_dash', 'tip_sleep', 'tip_checkup'];
const HEALTH_TIP_ICONS = ['\u{1F4A1}', '\u{1F48A}', '\u{1F957}', '\u{1F4A4}', '\u{1F3E5}'];

const HealthTipsCycler: React.FC = () => {
    const [tipIndex, setTipIndex] = useState(0);
    const [fade, setFade] = useState(true);

    useEffect(() => {
        const interval = setInterval(() => {
            setFade(false);
            setTimeout(() => {
                setTipIndex((prev) => (prev + 1) % HEALTH_TIP_KEYS.length);
                setFade(true);
            }, 300);
        }, 4000);
        return () => clearInterval(interval);
    }, []);

    return (
        <p
            className="text-xs text-slate-400 mt-2 transition-opacity duration-300"
            style={{ opacity: fade ? 1 : 0 }}
        >
            {HEALTH_TIP_ICONS[tipIndex]} {t(HEALTH_TIP_KEYS[tipIndex])}
        </p>
    );
};

/* -- Skeleton Component -------------------------------------------------- */
const Skeleton = ({ className }: { className?: string }) => (
    <div className={cn("animate-pulse skeleton-shimmer rounded-lg", className)} />
);

const PatientDashboardView: React.FC<PatientDashboardViewProps> = ({ agentChat, onViewChange }) => {
    const { messages, status, sendMessage, agentActivities } = agentChat;
    const [inputText, setInputText] = useState('');
    const [takenMeds, setTakenMeds] = useState<Set<string>>(new Set());
    const [drugAlertsExpanded, setDrugAlertsExpanded] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // API-driven state with hardcoded fallbacks
    const [bpData, setBpData] = useState<VitalData>(FALLBACK_BP);
    const [glucoseData, setGlucoseData] = useState<VitalData>(FALLBACK_GLUCOSE);
    const [medsData, setMedsData] = useState(FALLBACK_MEDS);
    const [apptData, setApptData] = useState(FALLBACK_APPT);
    const [loading, setLoading] = useState(true);
    const [emergencyAlerts, setEmergencyAlerts] = useState<
        { type: 'hypertensive_crisis' | 'hypoglycemia' | 'hyperglycemia'; message: string; value: string }[]
    >([]);

    // Drug interaction alerts — fetched from the API (openFDA with fallback)
    const [drugInteractionAlerts, setDrugInteractionAlerts] = useState<DrugInteraction[]>([]);

    // Proactive Alert — AI가 먼저 위험 감지 / AI proactively detects risks
    const [proactiveAlert, setProactiveAlert] = useState<{type: string; message: string; severity: 'warning' | 'urgent'} | null>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Fetch live data on mount
    useEffect(() => {
        let mounted = true;

        async function loadData() {
            const [bp, glucose, meds, appts, drugInteractions] = await Promise.all([
                fetchLatestMetric('blood_pressure'),
                fetchLatestMetric('blood_glucose'),
                fetchActiveMedications(),
                fetchAppointments(),
                fetchDrugInteractions(),
            ]);

            if (!mounted) return;

            if (bp?.value) {
                const parts = bp.value.split('/');
                const systolic = Math.round(parseFloat(parts[0] || '0'));
                const diastolic = Math.round(parseFloat(parts[1] || '0'));
                const cleanValue = `${systolic}/${diastolic}`;
                const isElevated = systolic >= 130;
                setBpData({
                    value: cleanValue,
                    unit: bp.unit || 'mmHg',
                    badgeKey: isElevated ? 'elevated' as const : 'normal' as const,
                    badgeColor: isElevated ? 'text-error bg-error-container' : 'text-secondary bg-secondary-container',
                    barWidth: `${Math.min(100, Math.round((systolic / 180) * 100))}%`,
                    barColor: isElevated ? 'bg-error' : 'bg-secondary',
                });
            }

            if (glucose?.value) {
                const gVal = Math.round(parseFloat(glucose.value));
                const isOptimal = gVal <= 100;
                const isNearTarget = gVal > 100 && gVal <= 140;
                setGlucoseData({
                    value: String(gVal),
                    unit: glucose.unit || 'mg/dL',
                    badgeKey: isOptimal ? 'normal' as const : isNearTarget ? 'near_target' as const : 'elevated' as const,
                    badgeColor: isOptimal ? 'text-secondary bg-secondary-container' : isNearTarget ? 'text-amber-600 bg-amber-50' : 'text-error bg-error-container',
                    barWidth: `${Math.min(100, Math.round((gVal / 250) * 100))}%`,
                    barColor: isOptimal ? 'bg-secondary' : isNearTarget ? 'bg-amber-400' : 'bg-error',
                });
            }

            if (meds?.length) {
                setMedsData(meds.map((m) => ({
                    id: m.id,
                    name: m.name,
                    dose: m.dose + (m.schedule ? ` · ${m.schedule}` : ''),
                    status: m.taken_today ? 'taken' : undefined,
                    time: m.taken_today ? 'today' : undefined,
                    active: !m.taken_today,
                    dimmed: false,
                })));
            }

            if (appts?.length) {
                const next = appts[0];
                const apptDate = new Date(next.date);
                const now = new Date();
                const diffDays = Math.ceil((apptDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
                const daysLabel = diffDays === 0 ? t('today') : diffDays === 1 ? t('tomorrow') : `In ${diffDays} Days`;
                setApptData({
                    title: next.title,
                    date: next.date,
                    time: next.time,
                    location: next.location,
                    note: next.note || '',
                    daysUntil: daysLabel,
                });
            }

            if (drugInteractions?.length) {
                setDrugInteractionAlerts(drugInteractions);
            }

            // Check emergency thresholds
            if (mounted) {
                const alerts: typeof emergencyAlerts = [];

                if (bp?.value) {
                    const systolic = parseInt(bp.value.split('/')[0] || '0', 10);
                    const diastolic = parseInt(bp.value.split('/')[1] || '0', 10);
                    if (systolic > 180 || diastolic > 120) {
                        alerts.push({
                            type: 'hypertensive_crisis',
                            message: 'Blood pressure is dangerously high. Seek immediate medical attention.',
                            value: bp.value + ' mmHg',
                        });
                    }
                }

                if (glucose?.value) {
                    const gVal = parseInt(glucose.value, 10);
                    if (gVal < 70) {
                        alerts.push({
                            type: 'hypoglycemia',
                            message: 'Blood glucose is critically low. Consume fast-acting sugar immediately.',
                            value: glucose.value + ' mg/dL',
                        });
                    } else if (gVal > 400) {
                        alerts.push({
                            type: 'hyperglycemia',
                            message: 'Blood glucose is dangerously high. Seek immediate medical attention.',
                            value: glucose.value + ' mg/dL',
                        });
                    }
                }

                setEmergencyAlerts(alerts);

                // Proactive Health Alert — 7-day trend analysis
                let didSetAlert = false;
                try {
                    const recentBP = await fetchMetricTrend('blood_pressure', 7);
                    if (recentBP?.length >= 3) {
                        const values = recentBP.map((p: any) => parseFloat(p.systolic || p.value?.toString().split('/')[0] || '0'));
                        const avg = values.reduce((a: number, b: number) => a + b, 0) / values.length;
                        const latest = values[values.length - 1];
                        const earliest = values[0];
                        const trend = latest - earliest;

                        if (avg > 140) {
                            setProactiveAlert({
                                type: 'bp_elevated',
                                message: `Your blood pressure has averaged ${Math.round(avg)} mmHg over the past week, which is above the recommended 140 mmHg. Consider reducing sodium intake and discuss medication adjustment with Dr. Mehta at your next visit.`,
                                severity: 'urgent'
                            });
                            didSetAlert = true;
                        } else if (trend > 5) {
                            setProactiveAlert({
                                type: 'bp_rising',
                                message: `Your blood pressure shows an upward trend over the past 7 days (${Math.round(earliest)} → ${Math.round(latest)} mmHg). This is worth monitoring. Try the DASH diet and ensure you're taking Amlodipine regularly.`,
                                severity: 'warning'
                            });
                            didSetAlert = true;
                        }
                    }

                    // Also check glucose if no BP alert
                    if (!didSetAlert) {
                        const recentGlucose = await fetchMetricTrend('blood_glucose', 7);
                        if (recentGlucose?.length >= 3) {
                            const gValues = recentGlucose.map((p: any) => parseFloat(p.value || '0'));
                            const gAvg = gValues.reduce((a: number, b: number) => a + b, 0) / gValues.length;
                            if (gAvg > 140) {
                                setProactiveAlert({
                                    type: 'glucose_elevated',
                                    message: `Your blood glucose has averaged ${Math.round(gAvg)} mg/dL this week, above the 140 mg/dL target. Make sure to take Metformin with meals and limit sugary foods.`,
                                    severity: 'warning'
                                });
                            }
                        }
                    }
                } catch {
                    // Trend fetch failed — skip proactive alert silently
                }

                setLoading(false);
            }
        }

        loadData();
        return () => { mounted = false; };
    }, []);

    const handleSend = async (text?: string) => {
        const msg = (text || inputText).trim();
        if (!msg || status === 'streaming') return;
        setInputText('');
        await sendMessage(msg);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const hasMessages = messages.length > 0;
    const isStreaming = status === 'streaming';

    const activeMedCount = medsData.length;
    const alertCount = drugInteractionAlerts.length;

    return (
        <div className={cn('lg:ml-72 pb-28 px-6 md:px-10 min-h-dvh', emergencyAlerts.length > 0 ? 'pt-28' : 'pt-16')}>

            {/* -- Emergency Banners ---------------------------------------- */}
            {emergencyAlerts.map((alert, i) => (
                <EmergencyBanner
                    key={`${alert.type}-${i}`}
                    type={alert.type}
                    message={alert.message}
                    value={alert.value}
                />
            ))}

            {/* -- Row 1: Welcome + Typing Animation ----------------------- */}
            <div className="mb-6 animate-reveal">
                <h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 tracking-tight">
                    {t('greeting')}
                </h1>
                <TypingAnimation texts={TYPING_MESSAGES_KEYS.map(k => t(k))} />
            </div>

            {/* -- Proactive Health Alert Banner ----------------------------- */}
            {proactiveAlert && (
                <div className={cn(
                    'mb-5 rounded-2xl animate-reveal overflow-hidden shadow-card',
                    proactiveAlert.severity === 'urgent'
                        ? 'bg-gradient-to-r from-error/5 via-white to-white'
                        : 'bg-gradient-to-r from-amber-50 via-white to-white'
                )}>
                    <div className="p-4">
                        <div className="flex items-start gap-3">
                            <div className={cn(
                                'w-10 h-10 rounded-2xl flex items-center justify-center shrink-0 shadow-sm',
                                proactiveAlert.severity === 'urgent'
                                    ? 'bg-error text-white'
                                    : 'bg-gradient-to-br from-amber-400 to-amber-500 text-white'
                            )}>
                                <Icon
                                    icon={proactiveAlert.severity === 'urgent' ? 'solar:danger-triangle-bold' : 'solar:lightbulb-bolt-bold'}
                                    width={20}
                                />
                            </div>
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 mb-1.5">
                                    <span className={cn(
                                        'text-xs font-bold tracking-tight',
                                        proactiveAlert.severity === 'urgent' ? 'text-error' : 'text-amber-700'
                                    )}>
                                        {proactiveAlert.severity === 'urgent' ? 'Proactive Alert' : 'Health Insight'}
                                    </span>
                                    <span className="text-[10px] text-slate-300">AI-detected</span>
                                </div>
                                <p className="text-sm text-slate-600 leading-relaxed">{proactiveAlert.message}</p>
                            </div>
                            <button
                                onClick={() => setProactiveAlert(null)}
                                className="shrink-0 text-slate-300 hover:text-slate-500 transition-colors"
                            >
                                <Icon icon="solar:close-circle-linear" width={18} />
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* -- Row 2: Compact Vitals Chips (horizontal scroll) --------- */}
            <div className="flex gap-3 overflow-x-auto pb-4 no-scrollbar animate-reveal stagger-1">
                <VitalChip
                    icon="solar:heart-pulse-bold"
                    iconColor="text-red-500"
                    label={t('blood_pressure')}
                    value={loading ? '...' : bpData.value}
                    badge={loading ? undefined : t(bpData.badgeKey)}
                    badgeColor={bpData.badgeKey === 'elevated' ? 'text-red-600 bg-red-50' : 'text-secondary bg-secondary-container'}
                />
                <VitalChip
                    icon="solar:water-bold"
                    iconColor="text-blue-500"
                    label={t('blood_glucose')}
                    value={loading ? '...' : `${glucoseData.value} ${glucoseData.unit}`}
                    badge={loading ? undefined : t(glucoseData.badgeKey)}
                    badgeColor={glucoseData.badgeKey === 'elevated' ? 'text-red-600 bg-red-50' : glucoseData.badgeKey === 'near_target' ? 'text-amber-600 bg-amber-50' : 'text-secondary bg-secondary-container'}
                />
                <VitalChip
                    icon="solar:pill-bold"
                    iconColor="text-primary"
                    label="Next"
                    value={loading ? '...' : (() => {
                        const nextMed = medsData.find(m => m.active || (!m.status && !m.time));
                        return nextMed ? `${nextMed.name} ${nextMed.time || ''}`.trim() : 'All taken';
                    })()}
                />
                <VitalChip
                    icon="solar:calendar-bold"
                    iconColor="text-violet-500"
                    label={apptData.title}
                    value={loading ? '...' : apptData.daysUntil.toLowerCase()}
                />
            </div>

            {/* -- Row 3: Contextual Action Cards (grid, above chat) ------- */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-5 animate-reveal stagger-2">
                <ContextCard
                    icon="solar:pill-bold"
                    iconColor="bg-primary/10 text-primary"
                    title={t('next_medication')}
                    detail={loading ? t('loading') : `${medsData.find(m => m.active)?.name || 'All taken'}`}
                    sub={loading ? '' : medsData.find(m => m.active)?.dose || 'Great job today'}
                    onClick={() => onViewChange?.('schedule')}
                />
                <ContextCard
                    icon="solar:shield-check-bold"
                    iconColor="bg-amber-50 text-amber-600"
                    title={t('safety_info')}
                    detail={alertCount > 0 ? `${alertCount} ${t('interactions')}` : t('no_issues')}
                    sub={alertCount > 0 ? t('tap_to_review') : t('all_clear')}
                    onClick={() => setDrugAlertsExpanded(!drugAlertsExpanded)}
                    highlight={alertCount > 0}
                />
                <ContextCard
                    icon="solar:calendar-bold"
                    iconColor="bg-violet-50 text-violet-600"
                    title={t('next_visit')}
                    detail={loading ? t('loading') : apptData.title}
                    sub={loading ? '' : apptData.daysUntil}
                    onClick={() => onViewChange?.('schedule')}
                />
            </div>

            {/* -- Row 4: CHAT (Main Focus) -------------------------------- */}
            <div className="animate-reveal stagger-3 mb-5">
                <BentoCard
                    className="hover-lift"
                    innerClassName="flex flex-col p-0 overflow-hidden"
                    noReveal
                >
                    <div className="p-6 flex flex-col">
                        {/* Suggested prompt chips */}
                        <div className="flex gap-2.5 overflow-x-auto pb-4 px-1 no-scrollbar">
                            {SUGGESTED_PROMPTS.map(prompt => (
                                <button
                                    key={prompt.textKey}
                                    onClick={() => handleSend(t(prompt.textKey))}
                                    disabled={isStreaming}
                                    className="prompt-chip shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-full bg-primary/5 text-primary text-sm font-semibold
                                               border border-primary/12 min-h-[44px]
                                               disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]"
                                >
                                    <Icon icon={prompt.icon} width={16} className="shrink-0 opacity-70" />
                                    {t(prompt.textKey)}
                                </button>
                            ))}
                        </div>

                        {/* Messages area */}
                        <div className={cn(
                            'flex-1 overflow-y-auto space-y-4 pr-1 transition-all duration-500',
                            hasMessages ? 'max-h-[70vh] mb-4' : 'max-h-0',
                        )}>
                            {messages.map((msg) => (
                                <div
                                    key={msg.id}
                                    className={cn(
                                        'flex gap-2.5',
                                        msg.role === 'user' ? 'flex-row-reverse' : 'flex-row',
                                    )}
                                >
                                    {/* Avatar */}
                                    <div
                                        className={cn(
                                            'w-7 h-7 rounded-full flex items-center justify-center shrink-0 mt-1',
                                            msg.role === 'user'
                                                ? 'bg-primary text-white'
                                                : 'bg-primary/10 text-primary',
                                        )}
                                    >
                                        <Icon
                                            icon={msg.role === 'user'
                                                ? 'solar:user-bold'
                                                : 'solar:stars-bold'}
                                            width={13}
                                        />
                                    </div>

                                    {/* Bubble */}
                                    <div
                                        className={cn(
                                            'max-w-[80%] rounded-2xl px-4 py-3 text-base leading-relaxed',
                                            msg.role === 'user'
                                                ? 'bg-primary text-white rounded-tr-sm'
                                                : 'bg-surface-container-low text-slate-800 rounded-tl-sm',
                                        )}
                                    >
                                        {msg.role === 'assistant' ? (
                                            <div className="prose prose-sm prose-slate max-w-none">
                                                {msg.content ? (
                                                    <>
                                                        <ReactMarkdown>{parseAgentResponse(msg.content)}</ReactMarkdown>
                                                        {/* Auto-detect trend responses and show inline chart */}
                                                        {/blood pressure|BP trend|systolic|diastolic/i.test(msg.content) && (
                                                            <ChatTrendChart metricType="blood_pressure" />
                                                        )}
                                                        {/blood glucose|blood sugar|glucose trend|HbA1c/i.test(msg.content) && (
                                                            <ChatTrendChart metricType="blood_glucose" />
                                                        )}
                                                        {/weight|body weight|kg trend|BMI/i.test(msg.content) && (
                                                            <ChatTrendChart metricType="weight" />
                                                        )}
                                                        {/heart rate|pulse|bpm|resting heart|HR trend/i.test(msg.content) && (
                                                            <ChatTrendChart metricType="heart_rate" />
                                                        )}
                                                    </>
                                                ) : (
                                                    <div className="flex flex-col gap-1">
                                                        <div className="flex items-center gap-2">
                                                            <span className="text-sm text-slate-500">{t('analyzing')}</span>
                                                            <span className="flex items-center gap-1">
                                                                <span className="h-2 w-2 animate-bounce rounded-full bg-primary" style={{ animationDelay: '0ms' }} />
                                                                <span className="h-2 w-2 animate-bounce rounded-full bg-secondary" style={{ animationDelay: '150ms' }} />
                                                                <span className="h-2 w-2 animate-bounce rounded-full bg-primary/60" style={{ animationDelay: '300ms' }} />
                                                            </span>
                                                        </div>
                                                        <HealthTipsCycler />
                                                    </div>
                                                )}
                                            </div>
                                        ) : (
                                            msg.content
                                        )}
                                        {msg.role === 'assistant' &&
                                            isStreaming &&
                                            msg === messages[messages.length - 1] && (
                                                <span className="inline-block w-1.5 h-4 bg-primary/60 ml-0.5 animate-pulse rounded-sm align-middle" />
                                            )}
                                    </div>
                                </div>
                            ))}

                            {/* Typing indicator */}
                            {isStreaming && (!messages.length || messages[messages.length - 1]?.role === 'user') && (
                                <div className="flex items-center gap-1.5 px-4 py-3">
                                    <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{animationDelay: '0ms'}} />
                                    <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{animationDelay: '150ms'}} />
                                    <div className="w-2 h-2 rounded-full bg-primary animate-bounce" style={{animationDelay: '300ms'}} />
                                    <span className="text-sm text-slate-400 ml-2">{t('careflow_thinking')}</span>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Agent Activity Feed — inside chat, between messages and input */}
                        {(isStreaming || agentActivities.length > 0) && (
                            <div className="mb-3">
                                <AgentActivityFeed events={agentActivities} visible={true} />
                                {agentActivities.length > 0 && agentActivities.every((e) => e.status === 'done') && (
                                    <div className="flex items-center gap-2 text-xs text-secondary bg-secondary/5 border border-secondary/10 rounded-xl px-3 py-1.5 mt-2">
                                        <Icon icon="solar:check-circle-bold" width={14} className="text-secondary shrink-0" />
                                        <span>{t('analysis_complete')}</span>
                                    </div>
                                )}
                            </div>
                        )}

                        {/* Input area — clean flex row */}
                        <div className="flex items-center gap-2 bg-surface-container-low rounded-2xl p-2">
                            <textarea
                                ref={textareaRef}
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                onKeyDown={handleKeyDown}
                                disabled={isStreaming}
                                rows={1}
                                className="flex-1 bg-transparent px-3 py-2 text-base focus:outline-none resize-none placeholder:text-slate-300 disabled:opacity-60"
                                placeholder={isStreaming ? t('responding') : t('type_message')}
                            />
                            <button
                                className="w-9 h-9 rounded-full bg-primary/10 text-primary flex items-center justify-center hover:bg-primary/20 transition-colors shrink-0"
                                aria-label="Voice input"
                                onClick={() => {
                                    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
                                    if (!SR) return;
                                    const r = new SR(); r.lang = 'en-IN';
                                    r.onresult = (e: any) => { const t = e.results[0][0].transcript; if (t) handleSend(t); };
                                    r.start();
                                }}
                            >
                                <Icon icon="solar:microphone-bold" width={16} />
                            </button>
                            <button
                                onClick={() => handleSend()}
                                disabled={isStreaming || !inputText.trim()}
                                className="w-9 h-9 rounded-full bg-primary text-white flex items-center justify-center hover:bg-primary/90 transition-colors shrink-0 disabled:opacity-30"
                                aria-label="Send"
                            >
                                <Icon icon="solar:arrow-up-bold" width={16} />
                            </button>
                        </div>
                    </div>
                </BentoCard>
            </div>

            {/* -- Drug Interaction Alerts (collapsible) -------------------- */}
            {drugAlertsExpanded && drugInteractionAlerts.length > 0 && (
                <div className="mt-4 animate-reveal">
                    <div className="flex items-center gap-2.5 mb-3">
                        <Icon icon="solar:shield-warning-bold" width={18} className="text-amber-600" />
                        <h3 className="text-base font-bold text-slate-900 tracking-tight">{t('drug_alerts')}</h3>
                        <span className="text-sm font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
                            {drugInteractionAlerts.length} found
                        </span>
                        <button
                            onClick={() => setDrugAlertsExpanded(false)}
                            className="ml-auto text-sm text-slate-400 hover:text-slate-600 spring"
                        >
                            <Icon icon="solar:close-circle-linear" width={18} />
                        </button>
                    </div>
                    <DrugInteractionAlert alerts={drugInteractionAlerts} />
                </div>
            )}
        </div>
    );
};

/* -- Sub-components ------------------------------------------------------- */

/** Compact vital stat chip for Row 2 */
const VitalChip: React.FC<{
    icon: string;
    iconColor: string;
    label: string;
    value: string;
    badge?: string;
    badgeColor?: string;
}> = ({ icon, iconColor, label, value, badge, badgeColor }) => (
    <div className="shrink-0 flex items-center gap-2.5 px-4 py-2.5 rounded-2xl bg-white border border-slate-100 shadow-[0_2px_8px_-2px_rgba(0,0,0,0.06)] hover-lift">
        <Icon icon={icon} width={18} className={iconColor} />
        <div className="flex items-center gap-2">
            <span className="text-sm font-bold text-slate-800 whitespace-nowrap">{label} {value}</span>
            {badge && (
                <span className={cn('text-sm font-bold px-2 py-0.5 rounded-full whitespace-nowrap', badgeColor)}>
                    {badge}
                </span>
            )}
        </div>
    </div>
);

/** Contextual action card — shows real data, not just a label */
const ContextCard: React.FC<{
    icon: string;
    iconColor: string;
    title: string;
    detail: string;
    sub?: string;
    onClick?: () => void;
    highlight?: boolean;
}> = ({ icon, iconColor, title, detail, sub, onClick, highlight }) => (
    <button
        onClick={onClick}
        className={cn(
            'flex flex-col items-start gap-2 p-4 rounded-2xl bg-white border',
            'shadow-[0_2px_8px_-2px_rgba(0,0,0,0.06)] hover-lift active:scale-[0.98]',
            'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] h-[120px]',
            highlight ? 'border-amber-200 bg-amber-50/30' : 'border-slate-100',
        )}
    >
        <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center', iconColor)}>
            <Icon icon={icon} width={18} />
        </div>
        <div className="text-left">
            <p className="text-sm font-semibold text-slate-400 uppercase tracking-wide">{title}</p>
            <p className="text-base font-bold text-slate-800 leading-snug mt-0.5">{detail}</p>
            {sub && <p className="text-sm text-slate-500 mt-0.5">{sub}</p>}
        </div>
    </button>
);

export default PatientDashboardView;
