import React, { useState, useEffect } from 'react';
import {
    ComposedChart,
    Area,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    Line,
} from 'recharts';
import { Icon } from '@iconify/react';
import BentoCard from './BentoCard';
import { cn } from '@/src/lib/utils';
import { t } from '../lib/i18n';
import type { UseAgentChatReturn } from '../lib/useAgentChat';
import { fetchMetricTrend, fetchLatestMetric, fetchRecentVisits } from '../lib/api';

const FALLBACK_CHART_DATA = [
    { name: 'Day 0', glucose: 140, dosage: 500 },
    { name: 'Day 5', glucose: 135, dosage: 500 },
    { name: 'Day 10', glucose: 145, dosage: 500 },
    { name: 'Day 15', glucose: 142, dosage: 500 },
    { name: 'Day 20', glucose: 130, dosage: 1000 },
    { name: 'Day 25', glucose: 110, dosage: 1000 },
    { name: 'Day 30', glucose: 105, dosage: 1000 },
    { name: 'Today', glucose: 102, dosage: 1000 },
];

const FALLBACK_VITALS = {
    weight: { value: '88.4', unit: 'kg', trend: '+0.5kg', trendIcon: 'solar:graph-up-bold', trendColor: 'text-error' },
    a1c: { value: '7.1', unit: '%', trend: '\u22120.3%', trendIcon: 'solar:graph-down-bold', trendColor: 'text-secondary' },
    hr: { value: '72', unit: 'bpm', trend: 'Stable', trendIcon: 'solar:minus-square-linear', trendColor: 'text-slate-500' },
    sleep: { value: '6.5', unit: 'hrs', trend: 'Below Target', trendIcon: 'solar:graph-down-bold', trendColor: 'text-error' },
};

interface DoctorSummaryViewProps {
    agentChat?: UseAgentChatReturn;
    onViewChange?: (view: string) => void;
}

const DoctorSummaryView: React.FC<DoctorSummaryViewProps> = ({ agentChat, onViewChange }) => {
    const [chartData, setChartData] = useState(FALLBACK_CHART_DATA);
    const [vitals, setVitals] = useState(FALLBACK_VITALS);
    const [lastVisitLabel, setLastVisitLabel] = useState('45 days ago');
    const [loading, setLoading] = useState(true);
    const [showTopicModal, setShowTopicModal] = useState(false);
    const [topicInput, setTopicInput] = useState('');
    const [customTopics, setCustomTopics] = useState<{ title: string; desc: string }[]>([]);

    useEffect(() => {
        let mounted = true;

        async function loadData() {
            const [trend, bp, glucose, weight, hr, visits] = await Promise.all([
                fetchMetricTrend('blood_glucose', 90),
                fetchLatestMetric('blood_pressure'),
                fetchLatestMetric('blood_glucose'),
                fetchLatestMetric('weight'),
                fetchLatestMetric('heart_rate'),
                fetchRecentVisits(1),
            ]);

            if (!mounted) return;

            if (visits.length > 0 && visits[0].date) {
                const visitDate = new Date(visits[0].date);
                const now = new Date();
                const diffDays = Math.round((now.getTime() - visitDate.getTime()) / (1000 * 60 * 60 * 24));
                if (diffDays === 0) setLastVisitLabel('today');
                else if (diffDays === 1) setLastVisitLabel('1 day ago');
                else setLastVisitLabel(`${diffDays} days ago`);
            }

            if (trend?.length) {
                setChartData(trend.map((pt, i) => ({
                    name: i === trend.length - 1 ? 'Today' : `Day ${pt.day}`,
                    glucose: pt.value,
                    dosage: pt.day >= 20 ? 1000 : 500,
                })));
            }

            const updated = { ...FALLBACK_VITALS };
            if (weight?.value) {
                updated.weight = { ...updated.weight, value: weight.value, unit: weight.unit || 'kg' };
            }
            if (glucose?.value) {
                const gVal = parseInt(glucose.value, 10);
                const estA1c = ((gVal + 46.7) / 28.7).toFixed(1);
                updated.a1c = { ...updated.a1c, value: estA1c };
            }
            if (hr?.value) {
                updated.hr = { ...updated.hr, value: hr.value, unit: hr.unit || 'bpm' };
            }
            setVitals(updated);
            if (mounted) setLoading(false);
        }

        loadData();
        return () => { mounted = false; };
    }, []);

    return (
        <div className="lg:ml-72 min-h-dvh pb-28 px-6 md:px-10 pt-8 lg:pt-12">

            <div className="bg-gradient-to-r from-primary/10 via-primary/5 to-transparent border border-primary/15 rounded-2xl px-6 py-4 mb-6 flex items-center gap-4 shadow-sm">
                <div className="w-10 h-10 rounded-xl bg-primary flex items-center justify-center shrink-0 shadow-[0_4px_12px_rgba(28,110,242,0.3)]">
                    <Icon icon="solar:stethoscope-bold" width={20} className="text-white" />
                </div>
                <div>
                    <p className="text-base font-bold text-primary tracking-tight">{t('doctor_summary')}</p>
                    <p className="text-sm text-slate-600 mt-0.5">Prepared for your healthcare provider ahead of the consultation.</p>
                </div>
            </div>

            {/* ── Header ────────────────────────────────────────────── */}
            <section className="mb-10 animate-reveal">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div>
                        <span className="eyebrow mb-4 inline-block">Pre-visit Summary</span>
                        <h2 className="text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight">
                            Rajesh Sharma{' '}
                            <span className="text-slate-300 font-normal">(63)</span>
                        </h2>
                        <p className="text-slate-500 font-medium mt-2">
                            Diagnosis: Type 2 Diabetes + Hypertension
                            <span className="mx-2 text-outline-variant">|</span>
                            Last Visit: {lastVisitLabel}
                        </p>
                    </div>
                    <div className="flex gap-3">
                        <button
                            className={cn(
                                'flex items-center gap-2 bg-white text-slate-600 px-6 py-3 rounded-full font-semibold text-sm min-h-[48px]',
                                'border border-outline-variant/20 shadow-sm',
                                'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                'hover:bg-surface-container-low hover:text-slate-900 hover:-translate-y-0.5',
                            )}
                            aria-label="View full patient history"
                            onClick={() => onViewChange?.('medication')}
                        >
                            <Icon icon="solar:history-linear" width={17} />
                            {t('full_history')}
                        </button>
                        <button
                            className="btn-primary min-h-[48px]"
                            aria-label="Start consultation"
                            onClick={() => {
                                onViewChange?.('dashboard');
                                agentChat?.sendMessage('Starting consultation for patient Rajesh Sharma. Please prepare the visit summary.');
                            }}
                        >
                            <Icon icon="solar:pen-2-bold" width={16} />
                            <span>{t('start_consult')}</span>
                            <div className="btn-icon-wrap">
                                <Icon icon="solar:alt-arrow-right-bold" width={13} />
                            </div>
                        </button>
                    </div>
                </div>
            </section>

            {/* ── Insights Grid ─────────────────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-5">

                {/* Adherence Report */}
                <div
                    className="md:col-span-4 animate-reveal stagger-1 relative overflow-hidden rounded-[1.75rem] p-8 flex flex-col justify-between adherence-gradient"
                >
                    {/* Floating decorative orb */}
                    <div className="absolute -right-8 -bottom-8 w-36 h-36 bg-secondary/15 rounded-full animate-float pointer-events-none" />

                    <div className="relative z-10">
                        <h3 className="text-secondary font-bold text-lg tracking-tight">{t('adherence_report')}</h3>
                        <p className="text-secondary/70 text-sm mt-0.5">Last 30 Days Compliance</p>
                    </div>
                    <div className="relative z-10 mt-8">
                        <div className="metric-value text-7xl font-black text-secondary tracking-tighter leading-none">
                            92%
                        </div>
                        <div className="flex items-center gap-2 mt-3">
                            <Icon icon="solar:arrow-up-bold" width={18} className="text-secondary" />
                            <span className="text-secondary font-semibold text-sm">+4% from last month</span>
                        </div>
                    </div>
                </div>

                {/* AI Insights */}
                <BentoCard className="md:col-span-8 hover-lift" stagger="stagger-2">
                    <div className="flex items-start justify-between">
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <Icon icon="solar:stars-bold" className="text-primary" width={20} />
                                <h3 className="text-primary font-bold text-base tracking-tight">
                                    {t('health_insights')}
                                </h3>
                            </div>
                            <p className="text-slate-500 text-sm max-w-md leading-relaxed">
                                Blood pressure readings over the past 30 days suggest a pattern worth discussing during your next visit.
                            </p>
                        </div>
                        <span className="shrink-0 ml-4 bg-tertiary-container text-tertiary px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wide">
                            High Priority
                        </span>
                    </div>

                    <div className="mt-6 bg-surface-container-low rounded-2xl p-5 flex items-start gap-4 border border-outline-variant/10">
                        <div className="bg-primary p-2.5 rounded-xl text-white shrink-0">
                            <Icon icon="solar:danger-circle-bold" width={22} />
                        </div>
                        <div>
                            <p className="font-bold text-slate-900 text-sm mb-1 tracking-tight">
                                BP trend upward over 30 days — Review medication adjustment
                            </p>
                            <p className="text-sm text-slate-500 leading-relaxed">
                                Systolic average has increased from 132 to 144 mmHg. Correlation suggests potential salt sensitivity or missed evening dosage. Recommend adjustment of Amlodipine.
                            </p>
                        </div>
                    </div>
                </BentoCard>

                {/* Medication Correlation Chart */}
                <BentoCard className="md:col-span-12 lg:col-span-8 hover-lift" stagger="stagger-3">
                    <div className="flex flex-col md:flex-row md:items-center justify-between mb-7 gap-4">
                        <div>
                            <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                                Medication Correlation
                            </h3>
                            <p className="text-base text-slate-600 mt-0.5">
                                Fasting Glucose vs. Metformin Dosage
                            </p>
                        </div>
                        <div className="flex items-center gap-5">
                            <div className="flex items-center gap-2">
                                <span className="w-2.5 h-2.5 rounded-full bg-primary" />
                                <span className="text-sm font-semibold text-slate-600">Glucose (mg/dL)</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="w-2.5 h-2.5 rounded-full bg-secondary" />
                                <span className="text-sm font-semibold text-slate-600">Dosage (mg)</span>
                            </div>
                        </div>
                    </div>

                    <div className="h-64 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <ComposedChart data={chartData} margin={{ top: 8, right: 16, left: -10, bottom: 4 }}>
                                <defs>
                                    <linearGradient id="colorGlucose" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#1C6EF2" stopOpacity={0.25} />
                                        <stop offset="50%" stopColor="#1C6EF2" stopOpacity={0.08} />
                                        <stop offset="100%" stopColor="#1C6EF2" stopOpacity={0} />
                                    </linearGradient>
                                    <linearGradient id="colorDosage" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#059669" stopOpacity={0.1} />
                                        <stop offset="100%" stopColor="#059669" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" className="recharts-grid-lines" stroke="var(--color-surface-container-high, #f1f5f9)" strokeOpacity={0.8} />
                                <XAxis dataKey="name" tick={{ fontSize: 12, fill: '#94a3b8', fontWeight: 500 }} axisLine={false} tickLine={false} />
                                <YAxis
                                    yAxisId="glucose"
                                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                                    axisLine={false}
                                    tickLine={false}
                                    domain={['auto', 'auto']}
                                    label={{ value: 'mg/dL', angle: -90, position: 'insideLeft', style: { fontSize: 10, fill: '#94a3b8' } }}
                                />
                                <YAxis
                                    yAxisId="dosage"
                                    orientation="right"
                                    tick={{ fontSize: 11, fill: '#94a3b8' }}
                                    axisLine={false}
                                    tickLine={false}
                                    domain={[0, 1500]}
                                    label={{ value: 'mg', angle: 90, position: 'insideRight', style: { fontSize: 10, fill: '#94a3b8' } }}
                                />
                                <Tooltip
                                    contentStyle={{
                                        background: 'var(--color-surface, #ffffff)',
                                        border: '1px solid var(--color-outline-variant, #e2e8f0)',
                                        borderRadius: '16px',
                                        boxShadow: '0 12px 40px -8px rgba(0,0,0,0.15)',
                                        fontSize: 13,
                                        fontWeight: 600,
                                        padding: '12px 16px',
                                        color: 'var(--color-text, inherit)',
                                    }}
                                    labelStyle={{ color: 'var(--color-outline, #64748b)', fontWeight: 500, marginBottom: 4 }}
                                    formatter={(value: number, name: string) => {
                                        if (name === 'glucose') return [`${value} mg/dL`, 'Glucose'];
                                        if (name === 'dosage') return [`${value} mg`, 'Metformin'];
                                        return [value, name];
                                    }}
                                    cursor={{ stroke: '#1C6EF2', strokeWidth: 1, strokeDasharray: '4 4' }}
                                />
                                <Area
                                    yAxisId="glucose"
                                    type="monotone"
                                    dataKey="glucose"
                                    stroke="#1C6EF2"
                                    strokeWidth={2.5}
                                    fillOpacity={1}
                                    fill="url(#colorGlucose)"
                                    dot={{ r: 3, fill: '#1C6EF2', stroke: '#fff', strokeWidth: 2 }}
                                    activeDot={{ r: 5, fill: '#1C6EF2', stroke: '#fff', strokeWidth: 2 }}
                                />
                                <Line
                                    yAxisId="dosage"
                                    type="stepAfter"
                                    dataKey="dosage"
                                    stroke="#059669"
                                    strokeWidth={2}
                                    strokeDasharray="5 4"
                                    dot={false}
                                />
                            </ComposedChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="mt-5 flex items-center gap-3 bg-secondary/5 p-4 rounded-xl border border-secondary/10">
                        <Icon icon="solar:check-circle-bold" width={18} className="text-secondary shrink-0" />
                        <p className="text-sm font-medium text-secondary leading-tight">
                            Fasting glucose has stabilized within 90–110 range following the Metformin increase on Day 20.
                        </p>
                    </div>
                </BentoCard>

                {/* Consult Topics */}
                <div className="md:col-span-12 lg:col-span-4">
                    <BentoCard className="h-full" stagger="stagger-4">
                        <div className="flex items-center gap-2.5 mb-6">
                            <Icon icon="solar:lightbulb-bold" width={20} className="text-tertiary" />
                            <h3 className="text-base font-bold text-slate-900 tracking-tight">{t('consult_topics')}</h3>
                        </div>
                        <ul className="space-y-3">
                            <ConsultTopic
                                number={1}
                                title="Discuss BP volatility"
                                desc="Review salt intake and evening compliance issues detected."
                            />
                            <ConsultTopic
                                number={2}
                                title="Confirm Metformin tolerance"
                                desc="Screen for GI distress since dosage increase to 1000mg."
                            />
                            <ConsultTopic
                                number={3}
                                title="Lifestyle: Foot Care"
                                desc="Patient noted mild tingling in peripheral check-in 2 days ago."
                            />
                            {customTopics.map((topic, i) => (
                                <li key={`custom-${i}`} className="p-4 rounded-2xl group bg-surface-container-low hover:bg-primary/5 transition-all duration-300 relative">
                                    <div className="flex items-start gap-3">
                                        <span className="flex-shrink-0 w-7 h-7 rounded-lg bg-primary/10 text-primary font-bold text-sm flex items-center justify-center">{4 + i}</span>
                                        <div className="flex-1 min-w-0">
                                            <p className="font-semibold text-slate-900 text-sm tracking-tight">{topic.title}</p>
                                            <p className="text-slate-500 text-xs mt-1 leading-relaxed">{topic.desc}</p>
                                        </div>
                                        <button
                                            onClick={() => setCustomTopics(prev => prev.filter((_, idx) => idx !== i))}
                                            className="shrink-0 w-7 h-7 rounded-lg text-slate-300 hover:text-error hover:bg-error-container flex items-center justify-center transition-all opacity-0 group-hover:opacity-100"
                                            aria-label="Delete topic"
                                        >
                                            <Icon icon="solar:trash-bin-minimalistic-linear" width={15} />
                                        </button>
                                    </div>
                                </li>
                            ))}
                        </ul>
                        <button
                            className={cn(
                                'w-full mt-5 py-3.5 border-2 border-dashed border-outline-variant/40 rounded-2xl',
                                'text-slate-400 font-semibold text-sm flex items-center justify-center gap-2',
                                'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                'hover:border-primary/30 hover:text-primary hover:bg-primary/5',
                            )}
                            onClick={() => {
                                setShowTopicModal(true);
                            }}
                        >
                            <Icon icon="solar:add-circle-linear" width={17} />
                            {t('add_topic')}
                        </button>
                    </BentoCard>
                </div>
            </div>

            {/* ── Recent Vitals ─────────────────────────────────────── */}
            <section className="mt-10">
                <h3 className="text-xl font-bold text-slate-900 tracking-tight mb-5">Recent Vitals</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
                    <VitalCard label="Weight" value={vitals.weight.value} unit={vitals.weight.unit} trend={vitals.weight.trend} trendIcon={vitals.weight.trendIcon} trendColor={vitals.weight.trendColor} stagger="stagger-1" loading={loading} />
                    <VitalCard label="A1C (Est.)" value={vitals.a1c.value} unit={vitals.a1c.unit} trend={vitals.a1c.trend} trendIcon={vitals.a1c.trendIcon} trendColor={vitals.a1c.trendColor} stagger="stagger-2" loading={loading} />
                    <VitalCard label="HR (Avg)" value={vitals.hr.value} unit={vitals.hr.unit} trend={vitals.hr.trend} trendIcon={vitals.hr.trendIcon} trendColor={vitals.hr.trendColor} stagger="stagger-3" loading={loading} />
                    <VitalCard label="Sleep" value={vitals.sleep.value} unit={vitals.sleep.unit} trend={vitals.sleep.trend} trendIcon={vitals.sleep.trendIcon} trendColor={vitals.sleep.trendColor} stagger="stagger-4" loading={loading} />
                </div>
            </section>
            {/* ── Powered By Footer ─────────────────────────────────── */}
            <div className="mt-10 text-center">
                <p className="text-sm text-slate-400 font-medium">
                    Powered by 8 CareFlow AI Agents
                </p>
            </div>

            {/* ── Add Custom Topic Modal ─────────────────────────────── */}
            {showTopicModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowTopicModal(false)}>
                    <div
                        className="bg-white rounded-3xl shadow-2xl p-8 w-full max-w-md mx-4 animate-reveal"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                                <Icon icon="solar:lightbulb-bold" width={20} className="text-primary" />
                            </div>
                            <h3 className="text-lg font-bold text-slate-900 tracking-tight">Add Consult Topic</h3>
                        </div>
                        <input
                            type="text"
                            value={topicInput}
                            onChange={(e) => setTopicInput(e.target.value)}
                            onKeyDown={(e) => {
                                if (e.key === 'Enter' && topicInput.trim()) {
                                    setCustomTopics(prev => [...prev, { title: topicInput.trim(), desc: 'Custom topic added by doctor.' }]);
                                    setTopicInput('');
                                    setShowTopicModal(false);
                                }
                            }}
                            placeholder="e.g. Discuss sleep apnea screening"
                            className="w-full border border-slate-200 rounded-2xl px-4 py-3 text-base focus:outline-none focus:border-primary/30 focus:shadow-[0_0_0_4px_rgba(28,110,242,0.07)] placeholder:text-slate-300 transition-all"
                            autoFocus
                        />
                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => { setTopicInput(''); setShowTopicModal(false); }}
                                className="flex-1 py-3 rounded-2xl border border-slate-200 text-slate-600 font-semibold text-sm hover:bg-slate-50 transition-all"
                            >
                                {t('cancel')}
                            </button>
                            <button
                                onClick={() => {
                                    if (topicInput.trim()) {
                                        agentChat?.sendMessage(`Add consult topic: ${topicInput.trim()}`);
                                        setTopicInput('');
                                        setShowTopicModal(false);
                                    }
                                }}
                                disabled={!topicInput.trim()}
                                className="flex-1 py-3 rounded-2xl bg-primary text-white font-semibold text-sm hover:bg-primary/90 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                {t('add_topic')}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

/* ── Sub-components ──────────────────────────────────────────────────────── */

const ConsultTopic = ({ number, title, desc }: { number: number; title: string; desc: string }) => (
    <li
        className={cn(
            'p-4 rounded-2xl cursor-pointer group',
            'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
            'hover:bg-surface-container-low hover:translate-x-1',
        )}
    >
        <div className="flex items-start gap-3">
            <span className="w-6 h-6 rounded-full bg-primary text-white flex items-center justify-center text-xs font-bold shrink-0 mt-0.5 spring group-hover:scale-110">
                {number}
            </span>
            <div>
                <p className="font-semibold text-sm text-slate-900 tracking-tight">{title}</p>
                <p className="text-sm text-slate-600 mt-1 leading-relaxed">{desc}</p>
            </div>
        </div>
    </li>
);

const SkeletonPulse = ({ className }: { className?: string }) => (
    <div className={cn("animate-pulse bg-slate-200 rounded-lg", className)} />
);

const VitalCard = ({
    label, value, unit, trend, trendIcon, trendColor, stagger, loading,
}: {
    label: string; value: string; unit: string;
    trend: string; trendIcon: string; trendColor: string; stagger: string; loading?: boolean;
}) => {
    return (
        <div
            className={cn(
                'animate-reveal bg-white p-6 rounded-2xl',
                'shadow-[0_4px_24px_-8px_rgba(28,110,242,0.07)]',
                'hover-lift active:scale-[0.98]',
                stagger,
            )}
        >
            <p className="text-sm font-semibold text-slate-600 mb-3 uppercase tracking-wide">{label}</p>
            <div className="flex items-baseline gap-1 mb-3">
                {loading ? (
                    <SkeletonPulse className="h-8 w-20" />
                ) : (
                    <>
                        <span className="metric-value text-3xl font-black text-slate-900">{value}</span>
                        <span className="text-base font-semibold text-slate-600">{unit}</span>
                    </>
                )}
            </div>
            {loading ? (
                <SkeletonPulse className="h-4 w-24" />
            ) : (
                <div className={cn('flex items-center gap-1.5 text-sm font-semibold', trendColor)}>
                    <Icon icon={trendIcon} width={14} />
                    {trend}
                </div>
            )}
        </div>
    );
};

export default DoctorSummaryView;
