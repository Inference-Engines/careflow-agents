import React, { useState, useEffect } from 'react';
import TopBar from './TopBar';
import BentoCard from './BentoCard';
import { Icon } from '@iconify/react';
import { cn } from '@/src/lib/utils';
import { t } from '../lib/i18n';
import { motion } from 'motion/react';
import type { UseAgentChatReturn } from '../lib/useAgentChat';
import { fetchRecentVisits, fetchCaregiver } from '../lib/api';

// TODO: move to env var for production
const GOOGLE_MAPS_API_KEY = 'REDACTED_MAPS_KEY';

interface VisitSummaryViewProps {
    agentChat: UseAgentChatReturn;
    onViewChange?: (view: string) => void;
}

const FALLBACK_VISIT = {
    title: 'Visit Summary: Apollo Hospital \u2014 April 3, 2026',
    extractions: [
        { icon: 'solar:pill-bold', color: 'bg-primary/10 text-primary', label: 'Medication Adjustment', title: 'Metformin 500mg \u2192 1000mg', source: 'Extracted from: "Increase dosage of Metformin to twice daily."' },
        { icon: 'solar:calendar-bold', color: 'bg-secondary/10 text-secondary', label: 'Laboratory Schedule', title: 'HbA1c Test booked (4/17)', source: 'Extracted from: "Please follow up with HbA1c lab in 2 weeks."' },
        { icon: 'solar:clipboard-check-bold', color: 'bg-tertiary/10 text-tertiary', label: 'Actionable Task', title: 'Sodium restriction task created', source: 'Extracted from: "Patient should maintain a low-sodium diet."' },
    ],
};

const FALLBACK_CAREGIVER = { name: 'Priya Sharma', relation: 'Daughter · Primary Caregiver' };

const VisitSummaryView: React.FC<VisitSummaryViewProps> = ({ agentChat, onViewChange }) => {
    const [visitTitle, setVisitTitle] = useState(FALLBACK_VISIT.title);
    const [extractions, setExtractions] = useState(FALLBACK_VISIT.extractions);
    const [caregiver, setCaregiver] = useState(FALLBACK_CAREGIVER);

    useEffect(() => {
        let mounted = true;

        async function loadData() {
            const [visits, cg] = await Promise.all([
                fetchRecentVisits(1),
                fetchCaregiver(),
            ]);

            if (!mounted) return;

            if (visits?.length) {
                const v = visits[0];
                if (v.date && v.location) {
                    setVisitTitle(`Visit Summary: ${v.location} \u2014 ${v.date}`);
                }
                if (Array.isArray(v.extractions) && v.extractions.length) {
                    setExtractions(v.extractions as typeof FALLBACK_VISIT.extractions);
                }
            }

            if (cg) {
                setCaregiver({ name: cg.name || FALLBACK_CAREGIVER.name, relation: cg.relation || FALLBACK_CAREGIVER.relation });
            }
        }

        loadData();
        return () => { mounted = false; };
    }, []);

    return (
        <div className="lg:ml-72 min-h-dvh pb-28">
            <TopBar
                title={visitTitle}
                icon={<Icon icon="solar:document-text-linear" width={20} />}
            />

            <div className="px-4 md:px-10 mt-8 space-y-7">
                <section className="grid grid-cols-1 lg:grid-cols-3 gap-7">

                    {/* ── Left column ──────────────────────────────── */}
                    <div className="lg:col-span-2 space-y-7">

                        {/* Extraction Panel */}
                        <BentoCard stagger="animate-reveal stagger-1" className="relative overflow-hidden hover-lift">
                            {/* Watermark icon */}
                            <div className="absolute top-4 right-4 opacity-[0.06] pointer-events-none">
                                <Icon icon="solar:bolt-bold" width={88} className="text-primary" />
                            </div>

                            <div className="flex items-center gap-2.5 mb-7">
                                <Icon icon="solar:bolt-bold" width={20} className="text-primary" />
                                <h3 className="text-base font-bold text-slate-900 tracking-tight">
                                    {t('visit_summary')}
                                </h3>
                            </div>

                            <div className="space-y-6">
                                {extractions.map((ext, i) => (
                                    <ExtractionItem
                                        key={i}
                                        icon={ext.icon}
                                        color={ext.color}
                                        label={ext.label}
                                        title={ext.title}
                                        source={ext.source}
                                    />
                                ))}
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
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 mt-2">
                                {/* Previous */}
                                <div className="bg-surface-container-low p-5 rounded-2xl border border-outline-variant/10">
                                    <span className="text-sm font-bold text-slate-600 uppercase tracking-wider">
                                        Previous Dose
                                    </span>
                                    <div className="mt-4 flex items-center gap-3">
                                        <div className="w-11 h-11 bg-white rounded-xl flex items-center justify-center shadow-sm">
                                            <Icon icon="solar:pill-linear" width={22} className="text-slate-300" />
                                        </div>
                                        <div>
                                            <h4 className="metric-value text-2xl font-bold text-slate-400">500mg</h4>
                                            <p className="text-slate-600 text-sm mt-0.5">Once Daily (AM)</p>
                                        </div>
                                    </div>
                                </div>

                                {/* New */}
                                <div className="relative bg-primary/5 p-5 rounded-2xl border-2 border-primary/15 overflow-hidden">
                                    <div className="absolute -right-3 -top-3 opacity-[0.07] pointer-events-none">
                                        <Icon icon="solar:graph-up-bold" width={68} className="text-primary" />
                                    </div>
                                    <span className="text-sm font-bold text-primary uppercase tracking-wider">
                                        New Prescribed Dose
                                    </span>
                                    <div className="mt-4 flex items-center gap-3">
                                        <div className="w-11 h-11 bg-primary/10 rounded-xl flex items-center justify-center">
                                            <Icon icon="solar:pill-bold" width={22} className="text-primary" />
                                        </div>
                                        <div>
                                            <h4 className="metric-value text-2xl font-black text-primary">1000mg</h4>
                                            <p className="text-primary/70 text-sm font-semibold mt-0.5">Twice Daily (AM/PM)</p>
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
                                    <Icon icon="solar:calendar-bold" width={22} />
                                </div>
                                <div className="flex items-center gap-1.5 bg-secondary/10 px-2.5 py-1 rounded-full">
                                    <span className="w-1.5 h-1.5 bg-secondary rounded-full" />
                                    <span className="text-secondary text-xs font-black uppercase tracking-wider">Synced</span>
                                </div>
                            </div>
                            <h4 className="text-base font-bold mb-1.5 tracking-tight">Calendar Sync Confirmation</h4>
                            <p className="text-base text-slate-600 leading-relaxed mb-5">
                                Your follow-up test has been scheduled and synced to your calendar.
                            </p>
                            <div className="bg-surface-container-low p-4 rounded-2xl flex items-center gap-3">
                                <div className="w-9 h-9 bg-white rounded-xl flex items-center justify-center shadow-sm shrink-0">
                                    <Icon icon="solar:calendar-bold" width={18} className="text-primary" />
                                </div>
                                <div>
                                    <p className="text-sm font-bold text-slate-500">Google Calendar</p>
                                    <p className="text-sm font-semibold text-slate-900">HbA1c Lab Test · 9:00 AM</p>
                                </div>
                            </div>
                        </BentoCard>

                        {/* Caregiver Alert */}
                        <BentoCard stagger="stagger-4" innerClassName="p-6">
                            <div className="w-11 h-11 bg-primary/10 text-primary rounded-2xl flex items-center justify-center mb-5">
                                <Icon icon="solar:users-group-rounded-bold" width={22} />
                            </div>
                            <h4 className="text-base font-bold mb-4 tracking-tight">{t('caregiver_notification')}</h4>
                            <div className="space-y-3">
                                <div className="flex items-center gap-3 p-3 bg-primary/5 rounded-2xl">
                                    <div className="relative shrink-0">
                                        <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center">
                                            <Icon icon="solar:user-bold" width={20} className="text-primary" />
                                        </div>
                                        <div className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-secondary border-2 border-white rounded-full" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm font-bold text-slate-900 tracking-tight">{caregiver.name}</p>
                                        <p className="text-sm text-slate-600 font-medium uppercase tracking-widest">{caregiver.relation}</p>
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

                        {/* Map Card — 클릭 시 Google Maps 열림 */}
                        <a
                            href="https://www.google.com/maps/search/Apollo+Hospital+Sarita+Vihar+New+Delhi"
                            target="_blank"
                            rel="noopener noreferrer"
                            className="block cursor-pointer"
                        >
                        <BentoCard stagger="stagger-5" innerClassName="p-0 overflow-hidden hover:shadow-lg transition-shadow">
                            <div className="h-40 relative bg-surface-container-low">
                                <img
                                    src={`https://maps.googleapis.com/maps/api/staticmap?center=Apollo+Hospital+Sarita+Vihar+New+Delhi&zoom=15&size=600x400&maptype=roadmap&markers=color:red%7CApollo+Hospital+Sarita+Vihar+New+Delhi&key=${GOOGLE_MAPS_API_KEY}&style=feature:all%7Csaturation:-30`}
                                    alt="Apollo Hospital location map"
                                    className="w-full h-full object-cover"
                                    style={{ filter: 'saturate(0.4) brightness(0.9)' }}
                                    loading="lazy"
                                    decoding="async"
                                    referrerPolicy="no-referrer"
                                    onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                                />
                                <div className="absolute inset-0 bg-gradient-to-t from-primary/20 to-transparent" />
                                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                                    <Icon icon="solar:map-point-bold" width={36} className="text-primary drop-shadow-lg" />
                                </div>
                            </div>
                            <div className="p-5 flex items-center justify-between">
                                <div>
                                    <h5 className="font-bold text-slate-900 tracking-tight">Apollo Hospital</h5>
                                    <p className="text-base text-slate-600 mt-0.5">Sarita Vihar, New Delhi, 110076</p>
                                </div>
                                <Icon icon="solar:arrow-right-up-linear" width={18} className="text-primary shrink-0" />
                            </div>
                        </BentoCard>
                        </a>
                    </div>
                </section>

                {/* ── Bottom Section ────────────────────────────────── */}
                <section className="grid grid-cols-1 md:grid-cols-4 gap-5">
                    {/* Dietary Update */}
                    <div
                        className="md:col-span-1 animate-reveal stagger-1 p-7 rounded-[1.75rem] flex flex-col justify-between dietary-gradient"
                    >
                        <Icon icon="solar:chef-hat-bold" width={32} className="text-tertiary" />
                        <div className="mt-6">
                            <h4 className="font-bold text-lg text-slate-900 tracking-tight">{t('dietary_update')}</h4>
                            <p className="text-sm text-slate-600 mt-1 opacity-80">Sodium limit: 2,300mg/day</p>
                        </div>
                    </div>

                    {/* Discuss CTA */}
                    <div
                        className="md:col-span-3 animate-reveal stagger-2 p-8 rounded-[1.75rem] flex flex-col md:flex-row items-center justify-between gap-7 discuss-cta-gradient"
                    >
                        <div className="flex-1">
                            <h4 className="text-xl font-bold mb-2 tracking-tight">Have questions about these changes?</h4>
                            <p className="text-slate-500 text-sm leading-relaxed">
                                Ask about your updated medications, upcoming tests, or dietary recommendations. You can also reach out to your care team directly.
                            </p>
                        </div>
                        <div className="flex gap-3 shrink-0">
                            <button
                                className={cn(
                                    'px-7 py-3 bg-white text-slate-700 border border-slate-200 font-semibold rounded-full text-sm',
                                    'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                    'hover:border-primary/20 hover:text-primary hover:-translate-y-0.5 hover:shadow-sm',
                                )}
                                onClick={() => onViewChange?.('insights')}
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
                                <span>{t('ask_careflow')}</span>
                                <div className="btn-icon-wrap">
                                    <Icon icon="solar:stars-bold" width={13} />
                                </div>
                            </button>
                        </div>
                    </div>
                </section>

                {/* ── Powered By Footer ──────────────────────────────── */}
                <div className="text-center py-2">
                    <p className="text-sm text-slate-400 font-medium">
                        Powered by CareFlow Multi-Agent System
                    </p>
                </div>

                {/* ── Download PDF Button ──────────────────────────── */}
                <section className="animate-reveal stagger-3">
                    <button
                        onClick={() => window.print()}
                        className={cn(
                            'w-full py-4 rounded-2xl bg-primary text-white font-semibold text-base',
                            'flex items-center justify-center gap-3',
                            'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                            'hover:bg-primary/90 hover:-translate-y-0.5 hover:shadow-[0_8px_32px_-8px_rgba(28,110,242,0.35)]',
                            'active:scale-[0.98]',
                        )}
                    >
                        <Icon icon="solar:document-add-bold" width={20} />
                        {t('download_report')}
                    </button>
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
            <p className="text-slate-600 text-sm font-bold uppercase tracking-widest mb-1">
                {label}
            </p>
            <p className="text-slate-900 font-semibold text-base leading-snug tracking-tight">
                {title}
            </p>
            <p className="text-slate-600 text-sm mt-1.5 leading-relaxed">{source}</p>
        </div>
    </motion.div>
);

export default VisitSummaryView;
