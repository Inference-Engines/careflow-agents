import React, { useState, useRef, useEffect } from 'react';
import { Icon } from '@iconify/react';
import BentoCard from './BentoCard';
import { cn } from '@/src/lib/utils';
import ReactMarkdown from 'react-markdown';
import type { UseAgentChatReturn } from '../lib/useAgentChat';

interface PatientDashboardViewProps {
    agentChat: UseAgentChatReturn;
}

const PatientDashboardView: React.FC<PatientDashboardViewProps> = ({ agentChat }) => {
    const { messages, status, sendMessage } = agentChat;
    const [inputText, setInputText] = useState('');
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
    }, [messages]);

    const handleSend = async () => {
        const text = inputText.trim();
        if (!text || status === 'streaming') return;
        setInputText('');
        await sendMessage(text);
    };

    const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSend();
        }
    };

    const hasMessages = messages.length > 0;
    const isStreaming = status === 'streaming';

    return (
        <div className="md:ml-72 pt-16 pb-28 px-6 md:px-10 min-h-dvh">

            {/* ── Welcome Header ───────────────────────────────────── */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8 animate-reveal">
                <div>
                    <h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 tracking-tight">
                        Namaste, Rajesh.
                    </h1>
                    <p className="text-slate-400 mt-1.5 font-medium">
                        Here is your health summary for today.
                    </p>
                </div>

                {/* Agent status badge */}
                <div
                    className={cn(
                        'flex items-center gap-2 px-4 py-2 rounded-full text-sm font-semibold spring',
                        'border border-secondary/15 bg-secondary/5',
                    )}
                >
                    <div className="flex -space-x-1.5">
                        <div className="w-5 h-5 rounded-full bg-secondary flex items-center justify-center text-[9px] text-white ring-2 ring-white font-bold">AI</div>
                        <div className="w-5 h-5 rounded-full bg-primary flex items-center justify-center ring-2 ring-white">
                            <Icon icon="solar:heart-pulse-bold" className="text-white" width={10} />
                        </div>
                    </div>
                    <span className="text-secondary tracking-tight">CareFlow Agents: Active</span>
                    <span
                        className={cn(
                            'w-2 h-2 rounded-full shrink-0',
                            isStreaming ? 'bg-yellow-400 animate-ping' : 'bg-secondary animate-pulse',
                        )}
                    />
                </div>
            </div>

            {/* ── Main Bento Grid ──────────────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-5">

                {/* AI Chat Input — spans 8 cols */}
                <BentoCard
                    className="md:col-span-8"
                    innerClassName="flex flex-col p-0 overflow-hidden"
                    noReveal
                    stagger="animate-reveal stagger-1"
                >
                    <div className="p-7 flex flex-col flex-1">
                        <div className="flex items-center gap-2.5 mb-1">
                            <Icon icon="solar:stars-bold" className="text-primary" width={20} />
                            <h3 className="text-base font-bold text-slate-900 tracking-tight">
                                Update your Care Partner
                            </h3>
                        </div>
                        <p className="text-slate-400 text-sm mb-5">
                            Tell me how you're feeling or about any changes in your routine.
                        </p>

                        {/* Message history */}
                        {hasMessages && (
                            <div className="flex-1 overflow-y-auto mb-4 max-h-72 space-y-4 pr-1">
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
                                                'max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
                                                msg.role === 'user'
                                                    ? 'bg-primary text-white rounded-tr-sm'
                                                    : 'bg-surface-container-low text-slate-800 rounded-tl-sm',
                                            )}
                                        >
                                            {msg.role === 'assistant' ? (
                                                <div className="prose prose-sm prose-slate max-w-none">
                                                    <ReactMarkdown>{msg.content || '…'}</ReactMarkdown>
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
                                <div ref={messagesEndRef} />
                            </div>
                        )}

                        {/* Input box */}
                        <div className="relative">
                            <textarea
                                ref={textareaRef}
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                onKeyDown={handleKeyDown}
                                disabled={isStreaming}
                                className={cn(
                                    'w-full bg-surface-container-low border border-transparent rounded-2xl',
                                    'p-5 pb-16 text-sm focus:outline-none min-h-[110px] resize-none',
                                    'placeholder:text-slate-300 disabled:opacity-60',
                                    'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                    'focus:border-primary/20 focus:bg-surface focus:shadow-[0_0_0_4px_rgba(28,110,242,0.07)]',
                                )}
                                placeholder={
                                    isStreaming
                                        ? 'CareFlow is responding…'
                                        : 'Doctor changed my medication today…'
                                }
                            />
                            <div className="absolute bottom-3.5 right-3.5 flex gap-2 items-center">
                                {isStreaming && (
                                    <Icon
                                        icon="solar:refresh-circle-bold"
                                        width={18}
                                        className="text-primary animate-spin"
                                    />
                                )}
                                <button
                                    id="send-message-btn"
                                    onClick={handleSend}
                                    disabled={isStreaming || !inputText.trim()}
                                    className="btn-primary py-2 px-5 text-sm disabled:opacity-40 disabled:cursor-not-allowed disabled:transform-none disabled:shadow-none"
                                >
                                    <span>Send</span>
                                    <div className="btn-icon-wrap">
                                        <Icon icon="solar:arrow-up-bold" width={14} />
                                    </div>
                                </button>
                                <button
                                    id="voice-input-btn"
                                    className={cn(
                                        'p-2.5 rounded-full spring',
                                        'bg-primary/8 text-primary hover:bg-primary/15 hover:scale-105 active:scale-95',
                                    )}
                                    title="Use the mic button at the bottom-right to speak"
                                    onClick={() => {
                                        alert('Use the mic button at the bottom-right of the screen to speak to CareFlow.');
                                    }}
                                >
                                    <Icon icon="solar:microphone-bold" width={18} />
                                </button>
                            </div>
                        </div>
                    </div>
                </BentoCard>

                {/* ── Quick Metrics — 4 cols ─────────────────────── */}
                <div className="md:col-span-4 flex flex-col gap-5">
                    {/* Blood Pressure */}
                    <MetricCard
                        icon="solar:heart-pulse-bold"
                        iconBg="bg-primary/10 text-primary"
                        badge="Elevated"
                        badgeColor="text-error bg-error-container"
                        value="140/90"
                        unit="mmHg"
                        label="Blood Pressure"
                        barWidth="84%"
                        barColor="bg-error"
                        stagger="stagger-2"
                    />
                    {/* Blood Glucose */}
                    <MetricCard
                        icon="solar:drop-bold"
                        iconBg="bg-secondary/10 text-secondary"
                        badge="Optimal"
                        badgeColor="text-secondary bg-secondary-container"
                        value="128"
                        unit="mg/dL"
                        label="Blood Glucose"
                        barWidth="58%"
                        barColor="bg-secondary"
                        stagger="stagger-3"
                    />
                </div>

                {/* ── Medication Tracker — 7 cols ───────────────── */}
                <BentoCard className="md:col-span-7" stagger="stagger-2" innerClassName="p-7">
                    <div className="flex justify-between items-center mb-7">
                        <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                            Upcoming Medications
                        </h3>
                        <button className="flex items-center gap-1 text-primary font-semibold text-sm spring hover:gap-2">
                            View Schedule
                            <Icon icon="solar:alt-arrow-right-linear" width={15} />
                        </button>
                    </div>
                    <div className="space-y-3">
                        <MedicationItem
                            icon="solar:check-circle-bold"
                            color="bg-secondary/10 text-secondary"
                            name="Metformin"
                            dose="500mg · After Breakfast"
                            status="Taken"
                            time="08:30 AM"
                        />
                        <MedicationItem
                            icon="solar:pill-bold"
                            color="bg-primary/10 text-primary"
                            name="Amlodipine"
                            dose="5mg · Before Lunch"
                            action="Mark Taken"
                            active
                        />
                        <MedicationItem
                            icon="solar:moon-bold"
                            color="bg-slate-100 text-slate-400"
                            name="Atorvastatin"
                            dose="10mg · Before Bed"
                            time="Scheduled: 09:00 PM"
                            dimmed
                        />
                    </div>
                </BentoCard>

                {/* ── Appointment Card — 5 cols ─────────────────── */}
                <section className="md:col-span-5 animate-reveal stagger-3">
                    <div className="bg-primary rounded-[1.5rem] p-7 text-white relative overflow-hidden h-full flex flex-col justify-between shadow-[0_20px_60px_-10px_rgba(28,110,242,0.45)]">
                        {/* Decorative orbs */}
                        <div className="absolute -top-12 -right-12 w-44 h-44 bg-white/10 rounded-full blur-3xl pointer-events-none" />
                        <div className="absolute -bottom-8 -left-8 w-36 h-36 bg-black/10 rounded-full blur-3xl pointer-events-none" />

                        <div className="relative z-10">
                            <div className="flex justify-between items-start mb-7">
                                <div className="bg-white/15 backdrop-blur-sm p-3 rounded-2xl">
                                    <Icon icon="solar:calendar-bold" width={22} />
                                </div>
                                <span className="eyebrow bg-white text-primary px-3 py-1.5 font-bold">
                                    In 3 Days
                                </span>
                            </div>

                            <p className="text-xs font-bold opacity-70 uppercase tracking-[0.12em] mb-1.5">
                                Next Appointment
                            </p>
                            <h2 className="text-3xl font-black mb-5 tracking-tight">HbA1c Test</h2>

                            <div className="space-y-2.5 mb-7">
                                <div className="flex items-center gap-2.5">
                                    <Icon icon="solar:calendar-linear" width={16} className="opacity-70" />
                                    <span className="font-medium text-sm">Wednesday, April 17</span>
                                </div>
                                <div className="flex items-center gap-2.5">
                                    <Icon icon="solar:clock-circle-linear" width={16} className="opacity-70" />
                                    <span className="font-medium text-sm">08:00 AM · Diagnostics Lab</span>
                                </div>
                            </div>
                        </div>

                        {/* Fasting notice */}
                        <div className="relative z-10 bg-white/10 border border-white/20 p-4 rounded-2xl backdrop-blur-sm">
                            <div className="flex items-start gap-3">
                                <Icon icon="solar:danger-triangle-bold" width={20} className="text-yellow-300 shrink-0 mt-0.5" />
                                <div>
                                    <p className="text-xs font-bold text-yellow-200 uppercase tracking-widest mb-1">
                                        Fasting Required
                                    </p>
                                    <p className="text-[11px] leading-relaxed opacity-85">
                                        Do not eat or drink anything except water for 8 hours prior to the test.
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
};

/* ── Sub-components ──────────────────────────────────────────────────────── */

interface MetricCardProps {
    icon: string;
    iconBg: string;
    badge: string;
    badgeColor: string;
    value: string;
    unit: string;
    label: string;
    barWidth: string;
    barColor: string;
    stagger: string;
}

const MetricCard: React.FC<MetricCardProps> = ({
    icon, iconBg, badge, badgeColor, value, unit, label, barWidth, barColor, stagger
}) => (
    <div
        className={cn(
            'animate-reveal bg-white rounded-[1.5rem] p-6 flex-1',
            'shadow-[0_4px_24px_-8px_rgba(28,110,242,0.08)]',
            stagger,
        )}
    >
        <div className="flex justify-between items-start mb-4">
            <span className={cn('p-2 rounded-xl', iconBg)}>
                <Icon icon={icon} width={20} />
            </span>
            <span className={cn('text-xs font-bold px-2.5 py-1 rounded-lg', badgeColor)}>
                {badge}
            </span>
        </div>
        <div className="flex items-baseline gap-1 mb-1">
            <span className="metric-value text-3xl font-black text-slate-900">{value}</span>
            <span className="text-sm text-slate-400 font-medium">{unit}</span>
        </div>
        <p className="text-xs font-semibold text-slate-400 mb-3">{label}</p>
        <div className="h-1 w-full bg-surface-container rounded-full overflow-hidden">
            <div
                className={cn('h-full rounded-full transition-all duration-700 ease-[cubic-bezier(0.16,1,0.3,1)]', barColor)}
                style={{ width: barWidth }}
            />
        </div>
    </div>
);

const MedicationItem = ({ icon, color, name, dose, status, time, action, active, dimmed }: {
    icon: string; color: string; name: string; dose: string;
    status?: string; time?: string; action?: string; active?: boolean; dimmed?: boolean;
}) => (
    <div
        className={cn(
            'bg-white p-4 rounded-2xl flex items-center justify-between group',
            'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
            'hover:shadow-[0_8px_32px_-8px_rgba(28,110,242,0.1)] hover:-translate-y-0.5',
            active && 'ring-2 ring-primary/10',
            dimmed && 'opacity-55',
        )}
    >
        <div className="flex items-center gap-3.5">
            <div className={cn('w-11 h-11 rounded-full flex items-center justify-center shrink-0', color)}>
                <Icon icon={icon} width={22} />
            </div>
            <div>
                <h4 className={cn('font-bold text-sm tracking-tight', active ? 'text-primary' : 'text-slate-800')}>
                    {name}
                </h4>
                <p className="text-xs text-slate-400 mt-0.5">{dose}</p>
            </div>
        </div>
        <div className="text-right shrink-0">
            {status && (
                <>
                    <span className="text-[10px] font-bold text-secondary uppercase tracking-widest block mb-1">
                        {status}
                    </span>
                    <p className="text-xs text-slate-400">{time}</p>
                </>
            )}
            {action && (
                <button className="btn-primary py-1.5 px-4 text-xs">
                    {action}
                </button>
            )}
            {!status && !action && time && (
                <p className="text-xs text-slate-400">{time}</p>
            )}
        </div>
    </div>
);

export default PatientDashboardView;
