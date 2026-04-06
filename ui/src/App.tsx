import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import VisitSummaryView from './components/VisitSummaryView';
import DoctorSummaryView from './components/DoctorSummaryView';
import PatientDashboardView from './components/PatientDashboardView';
import ScheduleView from './components/ScheduleView';
import VoiceAssistant from './components/VoiceAssistant';
import { motion, AnimatePresence } from 'motion/react';
import { useAgentChat } from './lib/useAgentChat';
import { cn } from './lib/utils';

const views = [
    { id: 'dashboard', label: 'Patient View' },
    { id: 'insights', label: 'Doctor View' },
    { id: 'medication', label: 'Visit Summary' },
    // 'schedule' is accessible via the sidebar nav only (not in the bottom switcher)
] as const;

type ViewId = typeof views[number]['id'] | 'schedule';

export default function App() {
    const [activeView, setActiveView] = useState<ViewId>('dashboard');

    // Shared agent session across all views
    const agentChat = useAgentChat();

    const renderView = () => {
        switch (activeView) {
            case 'dashboard':
                return <PatientDashboardView agentChat={agentChat} />;
            case 'medication':
                return <VisitSummaryView agentChat={agentChat} />;
            case 'insights':
                return <DoctorSummaryView />;
            case 'schedule':
                return <ScheduleView />;
            default:
                return <PatientDashboardView agentChat={agentChat} />;
        }
    };

    const getVoicePrompt = () => {
        switch (activeView) {
            case 'dashboard':  return 'Explain my HbA1c test';
            case 'insights':   return 'Review with CareFlow AI';
            case 'medication': return 'Explain my medication change';
            case 'schedule':   return 'Show my upcoming appointments';
            default:           return 'How can I help you today?';
        }
    };

    return (
        <div className="min-h-dvh bg-background text-slate-900">
            <Sidebar activeView={activeView} onViewChange={(v) => setActiveView(v as ViewId)} />

            <main>
                <AnimatePresence mode="wait">
                    <motion.div
                        key={activeView}
                        initial={{ opacity: 0, scale: 0.99, y: 8, filter: 'blur(3px)' }}
                        animate={{ opacity: 1, scale: 1, y: 0, filter: 'blur(0px)' }}
                        exit={{ opacity: 0, scale: 0.99, y: -8, filter: 'blur(3px)' }}
                        transition={{ duration: 0.38, ease: [0.16, 1, 0.3, 1] }}
                    >
                        {renderView()}
                    </motion.div>
                </AnimatePresence>
            </main>

            <VoiceAssistant prompt={getVoicePrompt()} onSend={agentChat.sendMessage} />

            {/* ── Glassmorphism View Switcher ────────────────────────────────── */}
            <div
                className="fixed bottom-6 left-[50%] -translate-x-[50%] ml-36 z-[60]"
                aria-label="Switch view"
            >
                <div className="relative flex items-center gap-1 p-1 rounded-full bg-white/80 backdrop-blur-xl border border-black/[0.06] shadow-[0_8px_32px_-8px_rgba(0,0,0,0.12)]">
                    {views.map((view) => {
                        const isActive = activeView === view.id;
                        return (
                            <button
                                key={view.id}
                                id={`view-tab-${view.id}`}
                                onClick={() => setActiveView(view.id)}
                                className={cn(
                                    'relative px-5 py-2 rounded-full text-xs font-semibold tracking-tight z-10',
                                    'transition-colors duration-300',
                                    isActive
                                        ? 'text-white'
                                        : 'text-slate-500 hover:text-slate-800',
                                )}
                            >
                                {/* Sliding active pill */}
                                {isActive && (
                                    <motion.div
                                        layoutId="active-pill"
                                        className="absolute inset-0 bg-primary rounded-full shadow-[0_4px_16px_-4px_rgba(28,110,242,0.45)]"
                                        transition={{ type: 'spring', stiffness: 500, damping: 35 }}
                                    />
                                )}
                                <span className="relative z-10">{view.label}</span>
                            </button>
                        );
                    })}
                </div>
            </div>
        </div>
    );
}
