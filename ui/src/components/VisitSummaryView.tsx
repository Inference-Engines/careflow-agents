import React from 'react';
import TopBar from './TopBar';
import BentoCard from './BentoCard';
import { Icon } from '@iconify/react';
import { cn } from '@/src/lib/utils';
import { motion } from 'motion/react';
import type { UseAgentChatReturn } from '../lib/useAgentChat';

interface VisitSummaryViewProps {
    agentChat: UseAgentChatReturn;
}

const VisitSummaryView: React.FC<VisitSummaryViewProps> = ({ agentChat }) => {
    return (
        <div className="ml-72 min-h-dvh pb-24">
            <TopBar
                title="Visit Summary: Apollo Hospital — April 3, 2026"
                icon={<Icon icon="solar:document-text-linear" width={20} />}
            />

            <div className="px-10 mt-8 space-y-7">
                <section className="grid grid-cols-1 lg:grid-cols-3 gap-7">

                    {/* ── Left column ──────────────────────────────── */}
                    <div className="lg:col-span-2 space-y-7">

                        {/* Extraction Panel */}
                        <BentoCard stagger="animate-reveal stagger-1" className="relative overflow-hidden">
                            {/* Watermark icon */}
                            <div className="absolute top-4 right-4 opacity-[0.06] pointer-events-none">
                                <Icon icon="solar:bolt-bold" width={88} className="text-primary" />
                            </div>

                            <div className="flex items-center gap-2.5 mb-7">
                                <Icon icon="solar:bolt-bold" width={20} className="text-primary" />
                                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                                    Autonomous AI Extraction
                                </h3>
                            </div>

                            <div className="space-y-6">
                                <ExtractionItem
                                    icon="solar:pill-bold"
                                    color="bg-primary/10 text-primary"
                                    label="Medication Adjustment"
                                    title={
                                        <>
                                            Metformin 500mg
                                            <span className="mx-2 inline-flex items-center">
                                                <Icon icon="solar:alt-arrow-right-bold" width={16} className="text-primary" />
                                            </span>
                                            1000mg
                                        </>
                                    }
                                    source='Extracted from: "Increase dosage of Metformin to twice daily."'
                                />
                                <ExtractionItem
                                    icon="solar:calendar-check-bold"
                                    color="bg-secondary/10 text-secondary"
                                    label="Laboratory Schedule"
                                    title="HbA1c Test booked (4/17)"
                                    source='Extracted from: "Please follow up with HbA1c lab in 2 weeks."'
                                />
                                <ExtractionItem
                                    icon="solar:clipboard-check-bold"
                                    color="bg-tertiary/10 text-tertiary"
                                    label="Actionable Task"
                                    title="Sodium restriction task created"
                                    source='Extracted from: "Patient should maintain a low-sodium diet."'
                                />
                            </div>
                        </BentoCard>

                        {/* Medication Comparison */}
                        <BentoCard
                            title="Medication Change Detail"
                            subtitle="Visual titration guide for new prescription"
                            badge="ACTIVE"
                            badgeColor="bg-primary"
                            stagger="stagger-2"
                        >
                            <div className="grid grid-cols-2 gap-5 mt-2">
                                {/* Previous */}
                                <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/10">
                                    <span className="text-xs font-bold text-slate-400 uppercase tracking-wider">
                                        Previous Dose
                                    </span>
                                    <div className="mt-4 flex items-center gap-3">
                                        <div className="w-11 h-11 bg-white rounded-xl flex items-center justify-center shadow-sm">
                                            <Icon icon="solar:pill-linear" width={22} className="text-slate-300" />
                                        </div>
                                        <div>
                                            <h4 className="metric-value text-2xl font-bold text-slate-400">500mg</h4>
                                            <p className="text-slate-400 text-xs mt-0.5">Once Daily (AM)</p>
                                        </div>
                                    </div>
                                </div>

                                {/* New */}
                                <div className="relative bg-primary/5 p-5 rounded-2xl border-2 border-primary/15 overflow-hidden">
                                    <div className="absolute -right-3 -top-3 opacity-[0.07] pointer-events-none">
                                        <Icon icon="solar:trending-up-bold" width={68} className="text-primary" />
                                    </div>
                                    <span className="text-xs font-bold text-primary uppercase tracking-wider">
                                        New Prescribed Dose
                                    </span>
                                    <div className="mt-4 flex items-center gap-3">
                                        <div className="w-11 h-11 bg-primary/10 rounded-xl flex items-center justify-center">
                                            <Icon icon="solar:pill-bold" width={22} className="text-primary" />
                                        </div>
                                        <div>
                                            <h4 className="metric-value text-2xl font-black text-primary">1000mg</h4>
                                            <p className="text-primary/70 text-xs font-semibold mt-0.5">Twice Daily (AM/PM)</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </BentoCard>
                    </div>

                    {/* ── Right column ─────────────────────────────── */}
                    <div className="space-y-7">

                        {/* Calendar Sync */}
                        <BentoCard stagger="stagger-3" innerClassName="p-6">
                            <div className="flex items-center justify-between mb-5">
                                <div className="w-11 h-11 bg-secondary/10 text-secondary rounded-2xl flex items-center justify-center">
                                    <Icon icon="solar:calendar-check-bold" width={22} />
                                </div>
                                <div className="flex items-center gap-1.5 bg-secondary/10 px-2.5 py-1 rounded-full">
                                    <span className="w-1.5 h-1.5 bg-secondary rounded-full" />
                                    <span className="text-secondary text-[10px] font-black uppercase tracking-wider">Synced</span>
                                </div>
                            </div>
                            <h4 className="text-base font-bold mb-1.5 tracking-tight">Calendar Sync Confirmation</h4>
                            <p className="text-sm text-slate-400 leading-relaxed mb-5">
                                Autonomous scheduling successful. The follow-up test is reflected across all your devices.
                            </p>
                            <div className="bg-surface-container-low p-4 rounded-2xl flex items-center gap-3">
                                <div className="w-9 h-9 bg-white rounded-xl flex items-center justify-center shadow-sm shrink-0">
                                    <Icon icon="solar:calendar-check-linear" width={18} className="text-primary" />
                                </div>
                                <div>
                                    <p className="text-xs font-bold text-slate-500">Google Calendar</p>
                                    <p className="text-sm font-semibold text-slate-900">HbA1c Lab Test · 9:00 AM</p>
                                </div>
                            </div>
                        </BentoCard>

                        {/* Caregiver Alert */}
                        <BentoCard stagger="stagger-4" innerClassName="p-6">
                            <div className="w-11 h-11 bg-primary/10 text-primary rounded-2xl flex items-center justify-center mb-5">
                                <Icon icon="solar:users-group-rounded-bold" width={22} />
                            </div>
                            <h4 className="text-base font-bold mb-4 tracking-tight">Caregiver Notification</h4>
                            <div className="space-y-3">
                                <div className="flex items-center gap-3 p-3 bg-primary/5 rounded-2xl">
                                    <div className="relative shrink-0">
                                        <img
                                            src="https://picsum.photos/seed/priya/100/100"
                                            alt="Priya"
                                            className="w-10 h-10 rounded-full object-cover"
                                            loading="lazy"
                                            decoding="async"
                                            referrerPolicy="no-referrer"
                                        />
                                        <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-secondary border-2 border-white rounded-full" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-bold text-slate-900 tracking-tight">Daughter (Priya)</p>
                                        <p className="text-[10px] text-slate-400 font-medium uppercase tracking-widest">Primary Contact</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 px-1">
                                    <Icon icon="solar:check-circle-bold" width={16} className="text-secondary shrink-0" />
                                    <p className="text-sm text-slate-500">
                                        Notified via <span className="font-bold text-slate-800">Gmail</span> · 2m ago
                                    </p>
                                </div>
                            </div>
                        </BentoCard>

                        {/* Map Card */}
                        <BentoCard stagger="stagger-5" innerClassName="p-0 overflow-hidden">
                            <div className="h-40 relative">
                                <img
                                    src="https://picsum.photos/seed/delhimap/600/400?blur=2"
                                    alt="Apollo Hospital location map"
                                    className="w-full h-full object-cover"
                                    style={{ filter: 'saturate(0.4) brightness(0.9)' }}
                                    loading="lazy"
                                    decoding="async"
                                    referrerPolicy="no-referrer"
                                />
                                <div className="absolute inset-0 bg-gradient-to-t from-primary/20 to-transparent" />
                                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                                    <Icon icon="solar:map-point-bold" width={36} className="text-primary drop-shadow-lg" />
                                </div>
                            </div>
                            <div className="p-5">
                                <h5 className="font-bold text-slate-900 tracking-tight">Apollo Hospital</h5>
                                <p className="text-sm text-slate-400 mt-0.5">Sarita Vihar, New Delhi, 110076</p>
                            </div>
                        </BentoCard>
                    </div>
                </section>

                {/* ── Bottom Section ────────────────────────────────── */}
                <section className="grid grid-cols-1 md:grid-cols-4 gap-5">
                    {/* Dietary Update */}
                    <div
                        className="md:col-span-1 animate-reveal stagger-1 p-7 rounded-[1.75rem] flex flex-col justify-between"
                        style={{ background: 'linear-gradient(135deg, #FEF3C7 0%, #FDE68A 100%)' }}
                    >
                        <Icon icon="solar:fork-spoon-bold" width={32} className="text-tertiary" />
                        <div className="mt-6">
                            <h4 className="font-bold text-lg text-slate-900 tracking-tight">Dietary Update</h4>
                            <p className="text-sm text-slate-600 mt-1 opacity-80">Sodium limit: 2,300mg/day</p>
                        </div>
                    </div>

                    {/* Discuss CTA */}
                    <div
                        className="md:col-span-3 animate-reveal stagger-2 p-8 rounded-[1.75rem] flex flex-col md:flex-row items-center justify-between gap-7"
                        style={{
                            background: 'linear-gradient(135deg, #EFF2FA 0%, #E8EBF5 100%)',
                            border: '1px solid rgba(28, 110, 242, 0.06)',
                        }}
                    >
                        <div className="flex-1">
                            <h4 className="text-xl font-bold mb-2 tracking-tight">Need to discuss this summary?</h4>
                            <p className="text-slate-500 text-sm leading-relaxed">
                                The AI assistant is ready to answer specific questions about these changes or connect you to your physician.
                            </p>
                        </div>
                        <div className="flex gap-3 shrink-0">
                            <button
                                className={cn(
                                    'px-7 py-3 bg-white text-slate-700 border border-slate-200 font-semibold rounded-full text-sm',
                                    'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                    'hover:border-primary/20 hover:text-primary hover:-translate-y-0.5 hover:shadow-sm',
                                )}
                            >
                                View Full Record
                            </button>
                            <button
                                id="ask-ai-btn"
                                onClick={() =>
                                    agentChat.sendMessage(
                                        'My doctor changed my Metformin to 1000mg twice daily and booked an HbA1c test on April 17. Can you explain these changes?',
                                    )
                                }
                                disabled={agentChat.status === 'streaming'}
                                className="btn-primary disabled:opacity-50 disabled:transform-none disabled:shadow-none"
                            >
                                <span>Ask AI Assistant</span>
                                <div className="btn-icon-wrap">
                                    <Icon icon="solar:stars-bold" width={13} />
                                </div>
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
};

/* ── Extraction Item ─────────────────────────────────────────────────────── */

interface ExtractionItemProps {
    icon: string;
    color: string;
    label: string;
    title: React.ReactNode;
    source: string;
}

const ExtractionItem: React.FC<ExtractionItemProps> = ({ icon, color, label, title, source }) => (
    <motion.div
        whileHover={{ x: 3 }}
        transition={{ type: 'spring', stiffness: 400, damping: 28 }}
        className="flex items-start gap-5 group cursor-default"
    >
        <div
            className={cn(
                'mt-0.5 w-10 h-10 rounded-xl flex items-center justify-center shrink-0',
                'transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                'group-hover:scale-110',
                color,
            )}
        >
            <Icon icon={icon} width={20} />
        </div>
        <div>
            <p className="text-slate-400 text-[10px] font-bold uppercase tracking-widest mb-1">
                {label}
            </p>
            <p className="text-slate-900 font-semibold text-base leading-snug tracking-tight">
                {title}
            </p>
            <p className="text-slate-400 text-xs mt-1.5 leading-relaxed">{source}</p>
        </div>
    </motion.div>
);

export default VisitSummaryView;
