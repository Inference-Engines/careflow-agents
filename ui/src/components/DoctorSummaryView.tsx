import React from 'react';
import {
    LineChart,
    Line,
    XAxis,
    YAxis,
    CartesianGrid,
    Tooltip,
    ResponsiveContainer,
    AreaChart,
    Area
} from 'recharts';
import {
    TrendingUp,
    TrendingDown,
    Minus,
    CheckCircle2,
    Lightbulb,
    Plus,
    History,
    Edit3,
    Sparkles,
    AlertCircle,
    Weight,
    Activity,
    Heart,
    Moon
} from 'lucide-react';
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
        <div className="lg:ml-72 min-h-screen p-4 md:p-8 lg:p-12">
            {/* Header */}
            <section className="mb-10">
                <div className="flex flex-col md:flex-row md:items-end justify-between gap-6">
                    <div>
                        <span className="bg-primary/10 text-primary px-3 py-1 rounded-full text-xs font-bold tracking-wider mb-3 inline-block">PRE-VISIT SUMMARY</span>
                        <h2 className="text-4xl lg:text-5xl font-extrabold text-slate-900 tracking-tight">Rajesh Sharma <span className="text-slate-400 font-normal">(63)</span></h2>
                        <p className="text-xl text-slate-500 font-medium mt-2">Diagnosis: DM2 + HTN <span className="mx-2 text-slate-300">|</span> Last Visit: 45 days ago</p>
                    </div>
                    <div className="flex gap-3">
                        <button className="bg-white text-primary px-6 py-3 rounded-full font-bold shadow-sm flex items-center gap-2 hover:bg-slate-50 transition-all">
                            <History size={18} />
                            Full History
                        </button>
                        <button className="bg-primary text-white px-8 py-3 rounded-full font-bold shadow-xl shadow-primary/20 flex items-center gap-2 hover:scale-[1.02] transition-transform">
                            <Edit3 size={18} />
                            Start Consult
                        </button>
                    </div>
                </div>
            </section>

            {/* Insights Grid */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                {/* Adherence Report */}
                <div className="md:col-span-4 bg-secondary-container rounded-3xl p-8 flex flex-col justify-between relative overflow-hidden group">
                    <div className="relative z-10">
                        <h3 className="text-secondary text-lg font-bold mb-1">Adherence Report</h3>
                        <p className="text-secondary/70 text-sm">Last 30 Days Compliance</p>
                    </div>
                    <div className="relative z-10 mt-8">
                        <div className="text-7xl font-black text-secondary tracking-tighter">92%</div>
                        <div className="flex items-center gap-2 mt-2">
                            <TrendingUp size={20} className="text-secondary" />
                            <span className="text-secondary font-semibold">+4% from last month</span>
                        </div>
                    </div>
                    <div className="absolute -right-10 -bottom-10 w-40 h-40 bg-secondary/10 rounded-full group-hover:scale-110 transition-transform duration-700"></div>
                </div>

                {/* AI-Generated Insights */}
                <BentoCard className="md:col-span-8 flex flex-col justify-between">
                    <div className="flex items-start justify-between">
                        <div>
                            <div className="flex items-center gap-2 mb-2">
                                <Sparkles size={20} className="text-primary" fill="currentColor" />
                                <h3 className="text-primary font-bold text-lg tracking-tight">Autonomous AI Insights</h3>
                            </div>
                            <p className="text-slate-500 text-base max-w-lg">Autonomous scanning of connected devices and daily logs detected a critical correlation requiring immediate review.</p>
                        </div>
                        <span className="bg-tertiary-container text-tertiary px-3 py-1 rounded-full text-xs font-bold">HIGH PRIORITY</span>
                    </div>
                    <div className="mt-8 bg-background rounded-2xl p-6 flex items-start gap-4">
                        <div className="bg-primary-container p-3 rounded-xl text-white">
                            <AlertCircle size={24} />
                        </div>
                        <div>
                            <p className="font-bold text-slate-900 mb-1">BP trend upward over 30 days — Review medication adjustment</p>
                            <p className="text-sm text-slate-500 leading-relaxed">Systolic average has increased from 132 to 144 mmHg. Correlation suggests potential salt sensitivity or missed evening dosage. Recommend adjustment of Amlodipine.</p>
                        </div>
                    </div>
                </BentoCard>

                {/* Medication Correlation Analysis */}
                <BentoCard className="md:col-span-12 lg:col-span-8">
                    <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
                        <div>
                            <h3 className="text-xl font-bold text-slate-900">Medication Correlation</h3>
                            <p className="text-sm text-slate-400">Fasting Glucose vs. Metformin Dosage</p>
                        </div>
                        <div className="flex items-center gap-4">
                            <div className="flex items-center gap-2">
                                <span className="w-3 h-3 rounded-full bg-primary"></span>
                                <span className="text-xs font-semibold">Glucose (mg/dL)</span>
                            </div>
                            <div className="flex items-center gap-2">
                                <span className="w-3 h-3 rounded-full bg-secondary"></span>
                                <span className="text-xs font-semibold">Dosage (mg)</span>
                            </div>
                        </div>
                    </div>

                    <div className="h-64 w-full">
                        <ResponsiveContainer width="100%" height="100%">
                            <AreaChart data={data}>
                                <defs>
                                    <linearGradient id="colorGlucose" x1="0" y1="0" x2="0" y2="1">
                                        <stop offset="5%" stopColor="#0058bd" stopOpacity={0.1} />
                                        <stop offset="95%" stopColor="#0058bd" stopOpacity={0} />
                                    </linearGradient>
                                </defs>
                                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f1f5f9" />
                                <XAxis dataKey="name" hide />
                                <YAxis hide />
                                <Tooltip />
                                <Area
                                    type="monotone"
                                    dataKey="glucose"
                                    stroke="#0058bd"
                                    strokeWidth={3}
                                    fillOpacity={1}
                                    fill="url(#colorGlucose)"
                                />
                                <Line
                                    type="stepAfter"
                                    dataKey="dosage"
                                    stroke="#006e2c"
                                    strokeWidth={2}
                                    strokeDasharray="5 5"
                                />
                            </AreaChart>
                        </ResponsiveContainer>
                    </div>

                    <div className="mt-8 flex items-center gap-4 bg-secondary/5 p-4 rounded-xl border border-secondary/10">
                        <CheckCircle2 size={20} className="text-secondary" />
                        <p className="text-sm font-medium text-secondary">Fasting glucose has stabilized within 90-110 range following the Metformin increase on Day 20.</p>
                    </div>
                </BentoCard>

                {/* Consult Topics */}
                <div className="md:col-span-12 lg:col-span-4 space-y-6">
                    <BentoCard className="h-full">
                        <div className="flex items-center gap-2 mb-6">
                            <Lightbulb size={20} className="text-tertiary" fill="currentColor" />
                            <h3 className="text-lg font-bold text-slate-900">Consult Topics</h3>
                        </div>
                        <ul className="space-y-4">
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
                        <button className="w-full mt-6 py-4 border-2 border-dashed border-outline-variant rounded-2xl text-slate-400 font-bold text-sm hover:border-primary hover:text-primary transition-colors flex items-center justify-center gap-2">
                            <Plus size={18} />
                            Add Custom Topic
                        </button>
                    </BentoCard>
                </div>
            </div>

            {/* Recent Vitals */}
            <section className="mt-12">
                <h3 className="text-2xl font-bold text-slate-900 mb-6">Recent Vitals</h3>
                <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
                    <VitalCard
                        label="Weight"
                        value="88.4"
                        unit="kg"
                        trend="+0.5kg"
                        trendIcon={<TrendingUp size={14} />}
                        trendColor="text-error"
                    />
                    <VitalCard
                        label="A1C (Est.)"
                        value="7.1"
                        unit="%"
                        trend="-0.3%"
                        trendIcon={<TrendingDown size={14} />}
                        trendColor="text-secondary"
                    />
                    <VitalCard
                        label="HR (Avg)"
                        value="72"
                        unit="bpm"
                        trend="Stable"
                        trendIcon={<Minus size={14} />}
                        trendColor="text-slate-500"
                    />
                    <VitalCard
                        label="Sleep"
                        value="6.5"
                        unit="hrs"
                        trend="Below Target"
                        trendIcon={<TrendingDown size={14} />}
                        trendColor="text-error"
                    />
                </div>
            </section>
        </div>
    );
};

const ConsultTopic = ({ number, title, desc }: { number: number, title: string, desc: string }) => (
    <li className="p-4 rounded-2xl bg-background transition-all hover:bg-surface-container-low cursor-pointer">
        <div className="flex items-start gap-3">
            <span className="bg-primary text-white w-6 h-6 rounded-full flex items-center justify-center text-xs font-bold shrink-0">{number}</span>
            <div>
                <p className="font-bold text-sm text-slate-900">{title}</p>
                <p className="text-xs text-slate-500 mt-1">{desc}</p>
            </div>
        </div>
    </li>
);

const VitalCard = ({ label, value, unit, trend, trendIcon, trendColor }: any) => (
    <div className="bg-white p-6 rounded-3xl shadow-sm">
        <p className="text-sm font-semibold text-slate-400 mb-2">{label}</p>
        <div className="flex items-baseline gap-1">
            <span className="text-3xl font-black text-slate-900">{value}</span>
            <span className="text-sm font-bold text-slate-400">{unit}</span>
        </div>
        <div className={cn("mt-3 flex items-center gap-1 text-xs font-bold", trendColor)}>
            {trendIcon}
            {trend}
        </div>
    </div>
);

export default DoctorSummaryView;
