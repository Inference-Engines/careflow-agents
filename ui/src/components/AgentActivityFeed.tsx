import React, { useState, useEffect, useRef } from 'react';
import { Icon } from '@iconify/react';
import { cn } from '@/src/lib/utils';
import { t } from '../lib/i18n';

interface AgentActivity {
    agent: string;
    action: string;
    status: 'active' | 'done' | 'waiting';
    icon: string;
    color: string;
}

interface AgentActivityFeedProps {
    events: AgentActivity[];
    visible: boolean;
}

/* ── Processing Steps ─────────────────────────────────────────────────────── */
interface ProcessingStep {
    id: string;
    label: string;
    /** tool / agent names that map to this step */
    triggers: string[];
    icon: string;
}

const STEPS: ProcessingStep[] = [
    {
        id: 'routing',
        label: 'routing',
        triggers: ['root_agent', 'transfer_to_agent'],
        icon: 'solar:routing-bold-duotone',
    },
    {
        id: 'medications',
        label: 'checking_meds',
        triggers: ['get_patient_medications', 'task_agent'],
        icon: 'solar:pill-bold-duotone',
    },
    {
        id: 'health',
        label: 'analyzing_health',
        triggers: ['get_health_metrics', 'get_recent_health_metrics', 'health_insight', 'calculate_trend'],
        icon: 'solar:heart-pulse-bold-duotone',
    },
    {
        id: 'records',
        label: 'consulting_records',
        triggers: ['search_medical_history', 'agentic_rag_search', 'medical_info'],
        icon: 'solar:document-medicine-bold-duotone',
    },
    {
        id: 'interactions',
        label: 'checking_interactions',
        triggers: ['check_drug_interactions', 'check_food_drug_interaction'],
        icon: 'solar:shield-warning-bold-duotone',
    },
    {
        id: 'response',
        label: 'preparing_response',
        triggers: ['__generating'],
        icon: 'solar:chat-round-dots-bold-duotone',
    },
];

type StepStatus = 'pending' | 'active' | 'done';

function deriveStepStatuses(events: AgentActivity[]): Record<string, StepStatus> {
    const statuses: Record<string, StepStatus> = {};
    STEPS.forEach((s) => (statuses[s.id] = 'pending'));

    // Collect all agent/tool identifiers that have appeared
    const seen = new Set<string>();
    const activeSet = new Set<string>();
    events.forEach((evt) => {
        seen.add(evt.agent);
        // action may contain the tool label — also try to match the raw action string
        seen.add(evt.action);
        if (evt.status === 'active') activeSet.add(evt.agent);
    });

    let lastActiveIdx = -1;

    STEPS.forEach((step, idx) => {
        const triggered = step.triggers.some((t) => seen.has(t));
        if (triggered) {
            const isActive = step.triggers.some((t) => activeSet.has(t));
            statuses[step.id] = isActive ? 'active' : 'done';
            if (isActive) lastActiveIdx = idx;
        }
    });

    // If any event is active but we couldn't map it, at least mark routing done + last step active
    const anyActive = events.some((e) => e.status === 'active');
    if (anyActive && lastActiveIdx === -1) {
        // Mark routing as done, mark the "response" step active
        statuses['routing'] = 'done';
        statuses['response'] = 'active';
    }

    // All events done → mark response done too
    const allDone = events.length > 0 && events.every((e) => e.status === 'done');
    if (allDone) {
        STEPS.forEach((s) => {
            if (statuses[s.id] === 'active') statuses[s.id] = 'done';
        });
        // Also mark response done
        statuses['response'] = 'done';
    }

    // Everything before the last active step should be "done"
    if (lastActiveIdx > 0) {
        STEPS.slice(0, lastActiveIdx).forEach((s) => {
            if (statuses[s.id] !== 'done') statuses[s.id] = 'done';
        });
    }

    return statuses;
}

/* ── Agent Display Names ──────────────────────────────────────────────────── */
const AGENT_LABELS: Record<string, string> = {
    root_agent: 'CareFlow Orchestrator',
    task_agent: 'Task Manager',
    health_insight: 'Health Insights Agent',
    medical_info: 'Medical Info Agent',
    agentic_rag_search: 'Medical Records Search',
    check_drug_interactions: 'Drug Interaction Checker',
    check_food_drug_interaction: 'Food-Drug Interaction Checker',
    get_patient_medications: 'Medication Agent',
    get_health_metrics: 'Health Metrics Agent',
    get_recent_health_metrics: 'Health Metrics Agent',
    search_medical_history: 'Medical History Agent',
    calculate_trend: 'Trend Analysis Agent',
    transfer_to_agent: 'Agent Router',
};

function getAgentDisplayName(raw: string): string {
    return AGENT_LABELS[raw] || raw.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/* ── Component ────────────────────────────────────────────────────────────── */
const AgentActivityFeed: React.FC<AgentActivityFeedProps> = ({ events, visible }) => {
    const [elapsed, setElapsed] = useState(0);
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null);
    const startRef = useRef<number | null>(null);

    // Start / stop timer based on visibility & active events
    useEffect(() => {
        const anyActive = events.some((e) => e.status === 'active');
        if (visible && anyActive) {
            if (!startRef.current) startRef.current = Date.now();
            timerRef.current = setInterval(() => {
                setElapsed(Math.floor((Date.now() - startRef.current!) / 1000));
            }, 200);
        } else if (!anyActive && timerRef.current) {
            clearInterval(timerRef.current);
            timerRef.current = null;
        }
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [visible, events]);

    // Reset timer when events go to zero
    useEffect(() => {
        if (events.length === 0) {
            startRef.current = null;
            setElapsed(0);
        }
    }, [events.length]);

    if (!visible || events.length === 0) return null;

    const stepStatuses = deriveStepStatuses(events);
    const activeSteps = STEPS.filter((s) => stepStatuses[s.id] !== 'pending');
    const doneCount = STEPS.filter((s) => stepStatuses[s.id] === 'done').length;
    const progress = Math.round((doneCount / STEPS.length) * 100);
    const currentStep = STEPS.find((s) => stepStatuses[s.id] === 'active');
    const allDone = events.every((e) => e.status === 'done');

    const fmtTime = (s: number) => {
        const m = Math.floor(s / 60);
        const sec = s % 60;
        return m > 0 ? `${m}m ${sec}s` : `${sec}s`;
    };

    // Current live action text from the latest active event (with friendly agent name)
    const latestActive = events.filter((e) => e.status === 'active').slice(-1)[0];
    const liveAction = latestActive
        ? `${getAgentDisplayName(latestActive.agent)}: ${latestActive.action}`
        : undefined;

    return (
        <div className="bg-white/95 backdrop-blur-xl rounded-2xl border border-slate-200 shadow-lg shadow-primary/5 p-5 space-y-4 animate-reveal">
            {/* ── Header ─────────────────────────────────────────────────── */}
            <div className="flex items-center justify-between">
                <div className="flex items-center gap-2.5">
                    {!allDone ? (
                        <div className="relative w-7 h-7 flex items-center justify-center">
                            <div className="absolute inset-0 rounded-full bg-primary/10 animate-pulse" />
                            <Icon icon="solar:health-bold-duotone" width={18} className="text-primary relative z-10" />
                        </div>
                    ) : (
                        <div className="w-7 h-7 rounded-full bg-secondary/10 flex items-center justify-center">
                            <Icon icon="solar:check-circle-bold-duotone" width={18} className="text-secondary" />
                        </div>
                    )}
                    <div>
                        <p className="text-sm font-bold text-slate-800 tracking-tight leading-none">
                            {allDone ? t('analysis_complete') : t('agent_analyzing')}
                        </p>
                        {currentStep && !allDone && (
                            <p className="text-xs text-slate-500 mt-0.5">{t(currentStep.label)}</p>
                        )}
                    </div>
                </div>
                <div className="flex items-center gap-2">
                    {events.length > 0 && (
                        <span className="text-xs font-bold text-primary bg-primary/8 px-2 py-0.5 rounded-full">
                            {new Set(events.map((e) => e.agent)).size} agents
                        </span>
                    )}
                    <span className="text-xs font-mono text-slate-400 tabular-nums">{fmtTime(elapsed)}</span>
                </div>
            </div>

            {/* ── Progress Bar ────────────────────────────────────────────── */}
            <div className="relative h-1.5 rounded-full bg-slate-100 overflow-hidden">
                <div
                    className="absolute inset-y-0 left-0 rounded-full bg-gradient-to-r from-primary via-primary-container to-secondary transition-all duration-700 ease-out"
                    style={{ width: `${allDone ? 100 : Math.max(progress, 8)}%` }}
                />
                {!allDone && (
                    <div className="absolute inset-0 overflow-hidden rounded-full">
                        <div className="w-full h-full bg-gradient-to-r from-transparent via-white/40 to-transparent animate-shimmer-bar" />
                    </div>
                )}
            </div>

            {/* ── Steps ──────────────────────────────────────────────────── */}
            <div className="space-y-1">
                {STEPS.map((step, idx) => {
                    const st = stepStatuses[step.id];
                    const show = st !== 'pending' || activeSteps.length === 0;
                    if (!show && st === 'pending') return null;

                    return (
                        <div
                            key={step.id}
                            className={cn(
                                'flex items-center gap-3 px-3 py-2 rounded-xl transition-all duration-300',
                                st === 'active' && 'bg-primary/[0.04]',
                                st === 'done' && 'opacity-100',
                                st === 'pending' && 'opacity-40',
                            )}
                            style={{ animationDelay: `${idx * 60}ms` }}
                        >
                            {/* Icon / spinner */}
                            <div
                                className={cn(
                                    'w-7 h-7 rounded-lg flex items-center justify-center shrink-0 transition-colors duration-300',
                                    st === 'active' && 'bg-primary/10',
                                    st === 'done' && 'bg-secondary/10',
                                    st === 'pending' && 'bg-slate-100',
                                )}
                            >
                                {st === 'active' ? (
                                    <div className="w-3.5 h-3.5 rounded-full border-2 border-primary border-t-transparent animate-spin" />
                                ) : st === 'done' ? (
                                    <Icon icon="solar:check-circle-bold" width={16} className="text-secondary" />
                                ) : (
                                    <Icon icon={step.icon} width={16} className="text-slate-300" />
                                )}
                            </div>

                            {/* Label */}
                            <span
                                className={cn(
                                    'text-sm font-medium transition-colors duration-300',
                                    st === 'active' && 'text-slate-800',
                                    st === 'done' && 'text-slate-500',
                                    st === 'pending' && 'text-slate-400',
                                )}
                            >
                                {t(step.label)}
                            </span>

                            {/* Done check */}
                            {st === 'done' && (
                                <span className="ml-auto text-xs font-semibold text-secondary">{t('done')}</span>
                            )}
                        </div>
                    );
                })}
            </div>

            {/* ── Live Activity Text ─────────────────────────────────────── */}
            {liveAction && !allDone && (
                <div className="flex items-center gap-2 pt-2 border-t border-slate-100">
                    <div className="w-1.5 h-1.5 rounded-full bg-primary animate-pulse" />
                    <p className="text-xs text-slate-500 truncate animate-fade-in">{liveAction}</p>
                </div>
            )}
        </div>
    );
};

export default AgentActivityFeed;
