import React from 'react';
import {
    AreaChart,
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

const data = [
    { name: 'Day 0', glucose: 140, dosage: 500 },
    { name: 'Day 5', glucose: 135, dosage: 500 },
    { name: 'Day 10', glucose: 145, dosage: 500 },
    { name: 'Day 15', glucose: 142, dosage: 500 },
    { name: 'Day 20', glucose: 130, dosage: 1000 },
    { name: 'Day 25', glucose: 110, dosage: 1000 },
    { name: 'Day 30', glucose: 105, dosage: 1000 },
    { name: 'Today', glucose: 102, dosage: 1000 },
];

const DoctorSummaryView: React.FC = () => {
    return (
        <div className="lg:ml-72 min-h-dvh p-6 md:p-8 lg:p-12">

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
                            Diagnosis: DM2 + HTN
                            <span className="mx-2 text-outline-variant">|</span>
                            Last Visit: 45 days ago
                        </p>
                    </div>
                    <div className="flex gap-3">
                        <button
                            className={cn(
                                'flex items-center gap-2 bg-white text-slate-600 px-6 py-3 rounded-full font-semibold text-sm',
                                'border border-outline-variant/20 shadow-sm',
                                'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                'hover:bg-surface-container-low hover:text-slate-900 hover:-translate-y-0.5',
                            )}
                        >
                            <Icon icon="solar:history-linear" width={17} />
                            Full History
                        </button>
                        <button className="btn-primary">
                            <Icon icon="solar:pen-2-bold" width={16} />
                            <span>Start Consult</span>
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
                    className="md:col-span-4 animate-reveal stagger-1 relative overflow-hidden rounded-[1.75rem] p-8 flex flex-col justify-between"
                    style={{
                        background: 'linear-gradient(135deg, #D1FAE5 0%, #A7F3D0 100%)',
                    }}
                >
                    {/* Floating decorative orb */}
                    <div className="absolute -right-8 -bottom-8 w-36 h-36 bg-secondary/15 rounded-full animate-float pointer-events-none" />

                    <div className="relative z-10">
                        <h3 className="text-secondary font-bold text-lg tracking-tight">Adherence Report</h3>
                        <p className="text-secondary/70 text-sm mt-0.5">Last 30 Days Compliance</p>
                    </div>
                    <div className="relative z-10 mt-8">
                        <div className="metric-value text-7xl font-black text-secondary tracking-tighter leading-none">
                            92%
                        </div>
                        <div className="flex items-center gap-2 mt-3">
                            <Icon icon="solar:trending-up-bold" width={18} className="text-secondary" />
                            <span className="text-secondary font-semibold text-sm">+4% from last month</span>
                        </div>
                    </div>
                </div>

                {/* AI Insights */}
                <BentoCard className="md:col-span-8" stagger="stagger-2">
                    <div className="flex items-start justify-between">
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <Icon icon="solar:stars-bold" className="text-primary" width={20} />
                                <h3 className="text-primary font-bold text-base tracking-tight">
                                    Autonomous AI Insights
                                </h3>
                            </div>
                            <p className="text-slate-500 text-sm max-w-md leading-relaxed">
                                Autonomous scanning of connected devices and daily logs detected a critical correlation requiring immediate review.
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
                <BentoCard className="md:col-span-12 lg:col-span-8" stagger="stagger-3">
                    <div className="flex flex-col md:flex-row md:items-center justify-between mb-7 gap-4">
                        <div>
                            <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                                Medication Correlation
                            </h3>
                            <p className="text-sm text-slate-400 mt-0.5">
                                Fasting Glucose vs. Metformin Dosage
                            </p>
                        </div>
                        <div className="flex items-center gap-5">
                            <div className="flex items-center gap-2">
                                <span className="w-2.5 h-2.5 rounded-full bg-primary" />
                                <span className="text-xs font-semibold text-slate-600">Glucose (mg/dL)</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="w-2.5 h-2.5 rounded-full bg-secondary" />
                                <span className="text-xs font-semibold text-slate-600">Dosage (mg)</span>
                            </div>
                        </div>
                    </div>

                    <div className="h-56 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={data} margin={{ top: 4, right: 4, left: -20, bottom: 4 }}>
                                <defs>
                                    <linearGradient id="colorGlucose" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="0%" stopColor="#1C6EF2" stopOpacity={0.15} />
                                        <stop offset="95%" stopColor="#1C6EF2" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis dataKey="name" tick={{ fontSize: 11, fill: '#94a3b8' }} axisLine={false} tickLine={false} />
                                <YAxis hide />
                                <Tooltip
                                    contentStyle={{
                                        background: '#fff',
                                        border: '1px solid #e2e8f0',
                                        borderRadius: '12px',
                                        boxShadow: '0 8px 32px -8px rgba(0,0,0,0.12)',
                                        fontSize: 12,
                                        fontWeight: 600,
                                    }}
                                />
                                <Area
                                    type="monotone"
                                    dataKey="glucose"
                                    stroke="#1C6EF2"
                                    strokeWidth={2.5}
                                    fillOpacity={1}
                                    fill="url(#colorGlucose)"
                                    dot={false}
                                />
                                <Line
                                    type="stepAfter"
                                    dataKey="dosage"
                                    stroke="#059669"
                                    strokeWidth={2}
                                    strokeDasharray="5 4"
                                    dot={false}
                                />
                            </AreaChart>
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
                            <h3 className="text-base font-bold text-slate-900 tracking-tight">Consult Topics</h3>
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
                        </ul>
                        <button
                            className={cn(
                                'w-full mt-5 py-3.5 border-2 border-dashed border-outline-variant/40 rounded-2xl',
                                'text-slate-400 font-semibold text-sm flex items-center justify-center gap-2',
                                'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                'hover:border-primary/30 hover:text-primary hover:bg-primary/3',
                            )}
                        >
                            <Icon icon="solar:add-circle-linear" width={17} />
                            Add Custom Topic
                        </button>
                    </BentoCard>
                </div>
            </div>

            {/* ── Recent Vitals ─────────────────────────────────────── */}
            <section className="mt-10">
                <h3 className="text-xl font-bold text-slate-900 tracking-tight mb-5">Recent Vitals</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-5">
                    <VitalCard label="Weight" value="88.4" unit="kg" trend="+0.5kg" trendIcon="solar:trending-up-bold" trendColor="text-error" stagger="stagger-1" />
                    <VitalCard label="A1C (Est.)" value="7.1" unit="%" trend="−0.3%" trendIcon="solar:trending-down-bold" trendColor="text-secondary" stagger="stagger-2" />
                    <VitalCard label="HR (Avg)" value="72" unit="bpm" trend="Stable" trendIcon="solar:minus-square-linear" trendColor="text-slate-500" stagger="stagger-3" />
                    <VitalCard label="Sleep" value="6.5" unit="hrs" trend="Below Target" trendIcon="solar:trending-down-bold" trendColor="text-error" stagger="stagger-4" />
                </div>
            </section>
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
                <p className="text-xs text-slate-400 mt-1 leading-relaxed">{desc}</p>
            </div>
        </div>
    </li>
);

const VitalCard = ({
    label, value, unit, trend, trendIcon, trendColor, stagger,
}: {
    label: string; value: string; unit: string;
    trend: string; trendIcon: string; trendColor: string; stagger: string;
}) => (
    <div
        className={cn(
            'animate-reveal bg-white p-6 rounded-2xl',
            'shadow-[0_4px_24px_-8px_rgba(28,110,242,0.07)]',
            'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
            'hover:-translate-y-1 hover:shadow-[0_12px_40px_-12px_rgba(28,110,242,0.12)]',
            stagger,
        )}
    >
        <p className="text-xs font-semibold text-slate-400 mb-3 uppercase tracking-wide">{label}</p>
        <div className="flex items-baseline gap-1 mb-3">
            <span className="metric-value text-3xl font-black text-slate-900">{value}</span>
            <span className="text-sm font-semibold text-slate-400">{unit}</span>
        </div>
        <div className={cn('flex items-center gap-1.5 text-xs font-semibold', trendColor)}>
            <Icon icon={trendIcon} width={14} />
            {trend}
        </div>
    </div>
);

export default DoctorSummaryView;
