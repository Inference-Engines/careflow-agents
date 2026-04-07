import React, { useState, useRef, useEffect, useCallback } from 'react';
import { Icon } from '@iconify/react';
import BentoCard from './BentoCard';
import EmergencyBanner from './EmergencyBanner';
import DrugInteractionAlert from './DrugInteractionAlert';
import AgentActivityFeed from './AgentActivityFeed';
import { cn } from '../lib/utils';
import ReactMarkdown from 'react-markdown';
import type { UseAgentChatReturn } from '../lib/useAgentChat';
import { fetchLatestMetric, fetchActiveMedications, fetchAppointments, markMedicationTaken } from '../lib/api';
import type { MetricLatest, Medication, Appointment as ApiAppointment } from '../lib/api';

interface PatientDashboardViewProps {
    agentChat: UseAgentChatReturn;
    onViewChange?: (view: string) => void;
}

// Hardcoded fallback values
const FALLBACK_BP = { value: '140/90', unit: 'mmHg', badge: 'Elevated', badgeColor: 'text-error bg-error-container', barWidth: '84%', barColor: 'bg-error' };
const FALLBACK_GLUCOSE = { value: '128', unit: 'mg/dL', badge: 'Near Target', badgeColor: 'text-warning bg-warning/10', barWidth: '58%', barColor: 'bg-warning' };
const FALLBACK_MEDS: { name: string; dose: string; status?: string; time?: string; active?: boolean; dimmed?: boolean; id?: string }[] = [
    { name: 'Metformin', dose: '1000mg · After Breakfast', status: 'Taken', time: '08:30 AM' },
    { name: 'Aspirin', dose: '75mg · After Breakfast', status: 'Taken', time: '08:30 AM' },
    { name: 'Amlodipine', dose: '5mg · Before Lunch', active: true },
    { name: 'Lisinopril', dose: '10mg · After Lunch', time: 'Scheduled: 01:30 PM', dimmed: true },
    { name: 'Atorvastatin', dose: '20mg · Before Bed', time: 'Scheduled: 09:00 PM', dimmed: true },
];
const FALLBACK_APPT = { title: 'HbA1c Test', date: 'Wednesday, April 17', time: '08:00 AM', location: 'Apollo Clinic, Mumbai', note: 'Fasting required', daysUntil: 'In 10 Days' };

const SUGGESTED_PROMPTS = [
    { text: "How am I doing today?", icon: "solar:heart-pulse-linear" },
    { text: "Check my blood pressure trend", icon: "solar:graph-up-linear" },
    { text: "What should I eat for lunch?", icon: "solar:fork-spoon-linear" },
    { text: "When is my next appointment?", icon: "solar:calendar-linear" },
];

const TYPING_MESSAGES = [
    "Checking your health summary for today...",
    "Your blood pressure is being monitored.",
    "Metformin 1000mg — next dose at 1:00 PM.",
    "Your HbA1c test is in 10 days.",
    "Priya was notified about your last visit.",
];

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

/* -- Skeleton Component -------------------------------------------------- */
const Skeleton = ({ className }: { className?: string }) => (
    <div className={cn("animate-pulse skeleton-shimmer rounded-lg", className)} />
);

const PatientDashboardView: React.FC<PatientDashboardViewProps> = ({ agentChat, onViewChange }) => {
    const { messages, status, sendMessage, agentActivities } = agentChat;
    const [inputText, setInputText] = useState('');
    const [takenMeds, setTakenMeds] = useState<Set<string>>(new Set());
    const [chatExpanded, setChatExpanded] = useState(true);
    const [drugAlertsExpanded, setDrugAlertsExpanded] = useState(false);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    // API-driven state with hardcoded fallbacks
    const [bpData, setBpData] = useState(FALLBACK_BP);
    const [glucoseData, setGlucoseData] = useState(FALLBACK_GLUCOSE);
    const [medsData, setMedsData] = useState(FALLBACK_MEDS);
    const [apptData, setApptData] = useState(FALLBACK_APPT);
    const [loading, setLoading] = useState(true);
    const [emergencyAlerts, setEmergencyAlerts] = useState<
        { type: 'hypertensive_crisis' | 'hypoglycemia' | 'hyperglycemia'; message: string; value: string }[]
    >([]);

    const drugInteractionAlerts = [
        {
            drug1: 'Metformin',
            drug2: 'Lisinopril',
            severity: 'MODERATE' as const,
            description: 'Lisinopril may increase the hypoglycemic effect of Metformin. Monitor blood glucose closely, especially after dose changes.',
            source: 'openFDA Drug Label',
        },
        {
            drug1: 'Amlodipine',
            drug2: 'Atorvastatin',
            severity: 'MODERATE' as const,
            description: 'Amlodipine may increase Atorvastatin blood levels, raising the risk of myopathy. Monitor for muscle pain or weakness.',
            source: 'openFDA Drug Label',
        },
    ];

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    // Auto-expand chat when messages arrive
    useEffect(() => {
        if (messages.length > 0) setChatExpanded(true);
    }, [messages.length]);

    // Fetch live data on mount
    useEffect(() => {
        let mounted = true;

        async function loadData() {
            const [bp, glucose, meds, appts] = await Promise.all([
                fetchLatestMetric('blood_pressure'),
                fetchLatestMetric('blood_glucose'),
                fetchActiveMedications(),
                fetchAppointments(),
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
                    badge: isElevated ? 'Elevated' : 'Normal',
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
                    badge: isOptimal ? 'Normal' : isNearTarget ? 'Near Target' : 'Elevated',
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
                    status: m.taken_today ? 'Taken' : undefined,
                    time: m.taken_today ? 'Today' : undefined,
                    active: !m.taken_today,
                    dimmed: false,
                })));
            }

            if (appts?.length) {
                const next = appts[0];
                const apptDate = new Date(next.date);
                const now = new Date();
                const diffDays = Math.ceil((apptDate.getTime() - now.getTime()) / (1000 * 60 * 60 * 24));
                const daysLabel = diffDays === 0 ? 'Today' : diffDays === 1 ? 'Tomorrow' : `In ${diffDays} Days`;
                setApptData({
                    title: next.title,
                    date: next.date,
                    time: next.time,
                    location: next.location,
                    note: next.note || '',
                    daysUntil: daysLabel,
                });
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
        setChatExpanded(true);
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
                    Namaste, Rajesh.
                </h1>
                <TypingAnimation texts={TYPING_MESSAGES} />
            </div>

            {/* -- Row 2: Compact Vitals Chips (horizontal scroll) --------- */}
            <div className="flex gap-3 overflow-x-auto pb-4 no-scrollbar animate-reveal stagger-1">
                <VitalChip
                    icon="solar:heart-pulse-bold"
                    iconColor="text-red-500"
                    label="BP"
                    value={loading ? '...' : bpData.value}
                    badge={loading ? undefined : bpData.badge}
                    badgeColor={bpData.badge === 'Elevated' ? 'text-red-600 bg-red-50' : 'text-secondary bg-secondary-container'}
                />
                <VitalChip
                    icon="solar:water-bold"
                    iconColor="text-blue-500"
                    label="Glucose"
                    value={loading ? '...' : `${glucoseData.value} ${glucoseData.unit}`}
                    badge={loading ? undefined : glucoseData.badge}
                    badgeColor={glucoseData.badge === 'Elevated' ? 'text-red-600 bg-red-50' : glucoseData.badge === 'Near Target' ? 'text-amber-600 bg-amber-50' : 'text-secondary bg-secondary-container'}
                />
                <VitalChip
                    icon="solar:pill-bold"
                    iconColor="text-primary"
                    label="Next"
                    value={loading ? '...' : 'Metformin 1:00 PM'}
                />
                <VitalChip
                    icon="solar:calendar-bold"
                    iconColor="text-violet-500"
                    label="HbA1c"
                    value={loading ? '...' : apptData.daysUntil.toLowerCase()}
                />
            </div>

            {/* -- Row 3: CHAT (Main Focus) -------------------------------- */}
            <div className="animate-reveal stagger-2 mb-5">
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
                                    key={prompt.text}
                                    onClick={() => handleSend(prompt.text)}
                                    disabled={isStreaming}
                                    className="prompt-chip shrink-0 flex items-center gap-2 px-4 py-2.5 rounded-full bg-primary/5 text-primary text-sm font-semibold
                                               border border-primary/12 min-h-[44px]
                                               disabled:opacity-40 disabled:cursor-not-allowed active:scale-[0.98]"
                                >
                                    <Icon icon={prompt.icon} width={16} className="shrink-0 opacity-70" />
                                    {prompt.text}
                                </button>
                            ))}
                        </div>

                        {/* Messages area */}
                        <div className={cn(
                            'flex-1 overflow-y-auto space-y-4 pr-1 transition-all duration-500',
                            hasMessages && chatExpanded ? 'max-h-[60vh] mb-4' : hasMessages ? 'max-h-0 overflow-hidden' : 'max-h-0',
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
                                                <ReactMarkdown>{msg.content || 'Let me look into that for you...'}</ReactMarkdown>
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
                                    <span className="text-sm text-slate-400 ml-2">CareFlow is thinking...</span>
                                </div>
                            )}
                            <div ref={messagesEndRef} />
                        </div>

                        {/* Collapse toggle for messages */}
                        {hasMessages && (
                            <button
                                onClick={() => setChatExpanded(!chatExpanded)}
                                className="flex items-center justify-center gap-1.5 text-sm text-slate-400 hover:text-primary spring mb-3 mx-auto"
                            >
                                <Icon
                                    icon={chatExpanded ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'}
                                    width={16}
                                />
                                {chatExpanded ? 'Collapse' : `${messages.length} messages`}
                            </button>
                        )}

                        {/* Agent Activity Feed */}
                        <AgentActivityFeed
                            events={agentActivities}
                            visible={isStreaming || agentActivities.length > 0}
                        />

                        {/* Input area */}
                        <div className="relative">
                            <textarea
                                ref={textareaRef}
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                onKeyDown={handleKeyDown}
                                disabled={isStreaming}
                                rows={2}
                                className={cn(
                                    'w-full bg-surface-container-low border border-transparent rounded-2xl',
                                    'p-4 pr-28 text-base focus:outline-none resize-none',
                                    'placeholder:text-slate-300 disabled:opacity-60',
                                    'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                    'focus:border-primary/20 focus:bg-surface focus:shadow-[0_0_0_4px_rgba(28,110,242,0.07)]',
                                )}
                                placeholder={
                                    isStreaming
                                        ? 'CareFlow is responding...'
                                        : 'Type a message or tap a suggestion above...'
                                }
                            />
                            <div className="absolute bottom-3 right-3 flex gap-2 items-center">
                                {isStreaming && (
                                    <Icon
                                        icon="solar:refresh-circle-bold"
                                        width={18}
                                        className="text-primary animate-spin"
                                    />
                                )}
                                {/* Mic button */}
                                <button
                                    className="w-10 h-10 rounded-full bg-primary/10 text-primary flex items-center justify-center hover:bg-primary/20 spring"
                                    aria-label="Voice input"
                                >
                                    <Icon icon="solar:microphone-bold" width={18} />
                                </button>
                                <button
                                    id="send-message-btn"
                                    onClick={() => handleSend()}
                                    disabled={isStreaming || !inputText.trim()}
                                    className="btn-primary py-2 px-5 text-sm disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none"
                                >
                                    <span>Send</span>
                                    <div className="btn-icon-wrap">
                                        <Icon icon="solar:arrow-up-bold" width={14} />
                                    </div>
                                </button>
                            </div>
                        </div>
                    </div>
                </BentoCard>
            </div>

            {/* -- Row 4: Quick Actions (compact) -------------------------- */}
            <div className="flex gap-3 overflow-x-auto no-scrollbar animate-reveal stagger-3">
                <QuickActionCard
                    icon="solar:pill-bold"
                    iconColor="bg-primary/10 text-primary"
                    label="Medications"
                    count={activeMedCount}
                    onClick={() => onViewChange?.('schedule')}
                />
                <QuickActionCard
                    icon="solar:shield-warning-bold"
                    iconColor="bg-amber-100 text-amber-600"
                    label="Drug Alerts"
                    count={alertCount}
                    onClick={() => setDrugAlertsExpanded(!drugAlertsExpanded)}
                />
                <QuickActionCard
                    icon="solar:calendar-bold"
                    iconColor="bg-violet-100 text-violet-600"
                    label="Schedule"
                    onClick={() => onViewChange?.('schedule')}
                />
            </div>

            {/* -- Drug Interaction Alerts (collapsible) -------------------- */}
            {drugAlertsExpanded && drugInteractionAlerts.length > 0 && (
                <div className="mt-4 animate-reveal">
                    <div className="flex items-center gap-2.5 mb-3">
                        <Icon icon="solar:shield-warning-bold" width={18} className="text-amber-600" />
                        <h3 className="text-base font-bold text-slate-900 tracking-tight">Drug Interaction Alerts</h3>
                        <span className="text-xs font-bold text-amber-700 bg-amber-100 px-2 py-0.5 rounded-full">
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
                <span className={cn('text-[11px] font-bold px-2 py-0.5 rounded-full whitespace-nowrap', badgeColor)}>
                    {badge}
                </span>
            )}
        </div>
    </div>
);

/** Quick action card for Row 4 */
const QuickActionCard: React.FC<{
    icon: string;
    iconColor: string;
    label: string;
    count?: number;
    onClick?: () => void;
}> = ({ icon, iconColor, label, count, onClick }) => (
    <button
        onClick={onClick}
        className="shrink-0 flex items-center gap-3 px-5 py-3.5 rounded-2xl bg-white border border-slate-100
                   shadow-[0_2px_8px_-2px_rgba(0,0,0,0.06)] hover-lift active:scale-[0.98]
                   transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] min-h-[48px]"
    >
        <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center', iconColor)}>
            <Icon icon={icon} width={18} />
        </div>
        <div className="text-left">
            <span className="text-sm font-bold text-slate-800 whitespace-nowrap">{label}</span>
            {count !== undefined && (
                <span className="text-xs text-slate-400 ml-1">({count})</span>
            )}
        </div>
        <Icon icon="solar:alt-arrow-right-linear" width={14} className="text-slate-300 ml-1" />
    </button>
);

export default PatientDashboardView;
