import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import VisitSummaryView from './components/VisitSummaryView';
import DoctorSummaryView from './components/DoctorSummaryView';
import PatientDashboardView from './components/PatientDashboardView';
import ScheduleView from './components/ScheduleView';
import ErrorBoundary from './components/ErrorBoundary';
import { motion, AnimatePresence } from 'motion/react';
import { useAgentChat } from './lib/useAgentChat';

type ViewId = 'dashboard' | 'insights' | 'medication' | 'schedule';

export default function App() {
    const [activeView, setActiveView] = useState<ViewId>('dashboard');

    // Shared agent session across all views
    const agentChat = useAgentChat();

    const renderView = () => {
        switch (activeView) {
            case 'dashboard':
                return <PatientDashboardView agentChat={agentChat} onViewChange={(v) => setActiveView(v as ViewId)} />;
            case 'medication':
                return <VisitSummaryView agentChat={agentChat} onViewChange={(v) => setActiveView(v as ViewId)} />;
            case 'insights':
                return <DoctorSummaryView agentChat={agentChat} onViewChange={(v) => setActiveView(v as ViewId)} />;
            case 'schedule':
                return <ScheduleView agentChat={agentChat} onViewChange={(v) => setActiveView(v as ViewId)} />;
            default:
                return <PatientDashboardView agentChat={agentChat} onViewChange={(v) => setActiveView(v as ViewId)} />;
        }
    };

    return (
        <ErrorBoundary>
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

                {/* Voice input integrated into chat — floating mic removed */}
            </div>
        </ErrorBoundary>
    );
}
