import React from 'react';
import TopBar from './TopBar';
import BentoCard from './BentoCard';
import { cn } from '@/src/lib/utils';
import {
    FileText,
    Zap,
    Pill,
    CalendarCheck,
    ClipboardCheck,
    TrendingUp,
    Users,
    MapPin,
    Utensils,
    CheckCircle2
} from 'lucide-react';
import { motion } from 'motion/react';
import type { UseAgentChatReturn } from '../lib/useAgentChat';

interface VisitSummaryViewProps {
    agentChat: UseAgentChatReturn;
}

const VisitSummaryView: React.FC<VisitSummaryViewProps> = ({ agentChat }) => {
    return (
        <div className="ml-72 min-h-screen pb-20">
            <TopBar
                title="Visit Summary: Apollo Hospital — April 3, 2026"
                icon={<FileText size={20} />}
            />

            <div className="px-12 mt-8 space-y-8">
                <section className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    <div className="lg:col-span-2 space-y-8">
                        {/* Extraction Panel */}
                        <BentoCard className="relative overflow-hidden">
                            <div className="absolute top-0 right-0 p-6 opacity-10">
                                <Zap size={96} className="text-primary" fill="currentColor" />
                            </div>
                            <div className="flex items-center gap-3 mb-8">
                                <Zap size={20} className="text-primary" fill="currentColor" />
                                <h3 className="text-lg font-bold tracking-tight text-slate-900">Autonomous AI Extraction</h3>
                            </div>

                            <div className="space-y-6">
                                <ExtractionItem
                                    icon={<Pill size={20} />}
                                    color="bg-primary/10 text-primary"
                                    label="Medication Adjustment"
                                    title={<>Metformin 500mg <span className="mx-2 text-primary">→</span> 1000mg</>}
                                    source='Extracted from: "Increase dosage of Metformin to twice daily."'
                                />
                                <ExtractionItem
                                    icon={<CalendarCheck size={20} />}
                                    color="bg-secondary/10 text-secondary"
                                    label="Laboratory Schedule"
                                    title="HbA1c Test booked (4/17)"
                                    source='Extracted from: "Please follow up with HbA1c lab in 2 weeks."'
                                />
                                <ExtractionItem
                                    icon={<ClipboardCheck size={20} />}
                                    color="bg-tertiary/10 text-tertiary"
                                    label="Actionable Task"
                                    title="Sodium restriction task created"
                                    source='Extracted from: "Patient should maintain a low-sodium diet."'
                                />
                            </div>
                        </BentoCard>

                        {/* Medication Comparison Card */}
                        <BentoCard
                            title="Medication Change Detail"
                            subtitle="Visual titration guide for new prescription"
                            badge="ACTIVE"
                            badgeColor="bg-primary"
                        >
                            <div className="grid grid-cols-2 gap-8">
                                <div className="bg-surface-container-low p-6 rounded-2xl border border-outline-variant/10">
                                    <span className="text-xs font-bold text-slate-400 uppercase">Previous Dose</span>
                                    <div className="mt-4 flex items-center gap-4">
                                        <div className="w-12 h-12 bg-white rounded-xl flex items-center justify-center">
                                            <Pill size={24} className="text-slate-400" />
                                        </div>
                                        <div>
                                            <h4 className="text-2xl font-bold text-slate-500">500mg</h4>
                                            <p className="text-slate-400 text-sm">Once Daily (AM)</p>
                                        </div>
                                    </div>
                                </div>

                                <div className="bg-primary/5 p-6 rounded-2xl border-2 border-primary/20 relative overflow-hidden">
                                    <div className="absolute -right-4 -top-4 opacity-10">
                                        <TrendingUp size={72} className="text-primary" />
                                    </div>
                                    <span className="text-xs font-bold text-primary uppercase">New Prescribed Dose</span>
                                    <div className="mt-4 flex items-center gap-4">
                                        <div className="w-12 h-12 bg-primary/10 rounded-xl flex items-center justify-center">
                                            <Pill size={24} className="text-primary" />
                                        </div>
                                        <div>
                                            <h4 className="text-2xl font-black text-primary">1000mg</h4>
                                            <p className="text-primary/70 text-sm font-semibold">Twice Daily (AM/PM)</p>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </BentoCard>
                    </div>

                    <div className="space-y-8">
                        {/* Calendar Sync */}
                        <BentoCard className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <div className="w-12 h-12 bg-secondary/10 text-secondary rounded-2xl flex items-center justify-center">
                                    <CalendarCheck size={24} />
                                </div>
                                <span className="bg-secondary-container text-secondary text-[10px] font-black px-2 py-1 rounded tracking-tighter">SYNCED</span>
                            </div>
                            <h4 className="text-lg font-bold mb-2">Calendar Sync Confirmation</h4>
                            <p className="text-sm text-slate-500 leading-relaxed mb-6">Autonomous scheduling successful. The follow-up test is reflected across all your devices.</p>
                            <div className="bg-surface-container-low p-4 rounded-2xl flex items-center gap-4">
                                <div className="w-10 h-10 bg-white rounded-lg flex items-center justify-center shadow-sm">
                                    <CalendarCheck size={20} className="text-primary" />
                                </div>
                                <div>
                                    <p className="text-xs font-bold text-slate-600">Google Calendar</p>
                                    <p className="text-sm font-semibold text-slate-900">HbA1c Lab Test • 9:00 AM</p>
                                </div>
                            </div>
                        </BentoCard>

                        {/* Caregiver Alert */}
                        <BentoCard className="p-6">
                            <div className="flex items-center justify-between mb-6">
                                <div className="w-12 h-12 bg-primary/10 text-primary rounded-2xl flex items-center justify-center">
                                    <Users size={24} />
                                </div>
                            </div>
                            <h4 className="text-lg font-bold mb-4">Caregiver Notification</h4>
                            <div className="space-y-4">
                                <div className="flex items-center gap-3 p-3 bg-primary/5 rounded-2xl">
                                    <div className="relative">
                                        <img
                                            src="https://picsum.photos/seed/priya/100/100"
                                            alt="Priya"
                                            className="w-10 h-10 rounded-full object-cover"
                                            referrerPolicy="no-referrer"
                                        />
                                        <div className="absolute bottom-0 right-0 w-3 h-3 bg-secondary border-2 border-white rounded-full"></div>
                                    </div>
                                    <div className="flex-1">
                                        <p className="text-sm font-bold">Daughter (Priya)</p>
                                        <p className="text-[10px] text-slate-500 font-medium uppercase tracking-widest">Primary Contact</p>
                                    </div>
                                </div>
                                <div className="flex items-center gap-2 px-1">
                                    <CheckCircle2 size={16} className="text-secondary" fill="currentColor" />
                                    <p className="text-sm text-slate-600">Notified via <span className="font-bold text-slate-900">Gmail</span> • 2m ago</p>
                                </div>
                            </div>
                        </BentoCard>

                        {/* Summary Map */}
                        <BentoCard className="p-0 overflow-hidden">
                            <div className="h-40 bg-slate-200 relative">
                                <img
                                    src="https://picsum.photos/seed/delhimap/600/400?blur=2"
                                    alt="Map"
                                    className="w-full h-full object-cover opacity-50"
                                    referrerPolicy="no-referrer"
                                />
                                <div className="absolute inset-0 bg-primary/10 mix-blend-multiply"></div>
                                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2">
                                    <MapPin size={40} className="text-primary" fill="currentColor" />
                                </div>
                            </div>
                            <div className="p-6">
                                <h5 className="font-bold text-slate-900">Apollo Hospital</h5>
                                <p className="text-sm text-slate-500">Sarita Vihar, New Delhi, 110076</p>
                            </div>
                        </BentoCard>
                    </div>
                </section>

                {/* Bottom Section */}
                <section className="grid grid-cols-1 md:grid-cols-4 gap-6">
                    <div className="md:col-span-1 bg-tertiary-container text-tertiary p-6 rounded-3xl flex flex-col justify-between">
                        <Utensils size={32} />
                        <div>
                            <h4 className="font-bold text-lg mt-4">Dietary Update</h4>
                            <p className="text-sm opacity-80">Sodium limit: 2,300mg/day</p>
                        </div>
                    </div>

                    <div className="md:col-span-3 bg-surface-container-high p-8 rounded-3xl flex flex-col md:flex-row items-center justify-between gap-8">
                        <div className="flex-1">
                            <h4 className="text-xl font-bold mb-2">Need to discuss this summary?</h4>
                            <p className="text-slate-600">The AI assistant is ready to answer specific questions about these changes or connect you to your physician.</p>
                        </div>
                        <div className="flex gap-4">
                            <button className="px-8 py-3 bg-white text-primary border border-primary/20 font-bold rounded-full hover:bg-primary/5 transition-all">
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
                                className="px-8 py-3 bg-primary text-white font-bold rounded-full shadow-lg shadow-primary/20 hover:scale-[0.98] transition-all disabled:opacity-50"
                            >
                                Ask AI Assistant
                            </button>
                        </div>
                    </div>
                </section>
            </div>
        </div>
    );
};

interface ExtractionItemProps {
    icon: React.ReactNode;
    color: string;
    label: string;
    title: React.ReactNode;
    source: string;
}

const ExtractionItem: React.FC<ExtractionItemProps> = ({ icon, color, label, title, source }) => (
    <motion.div
        whileHover={{ x: 4 }}
        className="flex items-start gap-6 group"
    >
        <div className={cn("mt-1 w-10 h-10 rounded-full flex items-center justify-center transition-transform group-hover:scale-110", color)}>
            {icon}
        </div>
        <div>
            <p className="text-slate-500 text-xs font-bold uppercase tracking-wider mb-1">{label}</p>
            <p className="text-slate-900 font-semibold text-lg leading-snug">{title}</p>
            <p className="text-slate-400 text-sm mt-1">{source}</p>
        </div>
    </motion.div>
);

export default VisitSummaryView;
