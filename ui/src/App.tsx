import React, { useState } from 'react';
import Sidebar from './components/Sidebar';
import VisitSummaryView from './components/VisitSummaryView';
import DoctorSummaryView from './components/DoctorSummaryView';
import PatientDashboardView from './components/PatientDashboardView';
import VoiceAssistant from './components/VoiceAssistant';
import { motion, AnimatePresence } from 'motion/react';
import { useAgentChat } from './lib/useAgentChat';

export default function App() {
    const [activeView, setActiveView] = useState('dashboard');

    // ── Agent chat state lifted here so all views share one session ──────────
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
                return <VisitSummaryView agentChat={agentChat} />;
            default:
                return <PatientDashboardView agentChat={agentChat} />;
        }
    };

    const getVoicePrompt = () => {
        switch (activeView) {
            case 'dashboard':
                return 'Explain my HbA1c test';
            case 'insights':
                return 'Review with CareFlow AI';
            case 'medication':
                return 'Explain my medication change';
            default:
                return 'How can I help you today?';
        }
    };

    return (
        <div className="min-h-screen bg-background text-slate-900">
            <Sidebar activeView={activeView} onViewChange={setActiveView} />

            <main className="transition-all duration-500">
                <AnimatePresence mode="wait">
                    <motion.div
                        key={activeView}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{ duration: 0.3 }}
                    >
                        {renderView()}
                    </motion.div>
                </AnimatePresence>
            </main>

            <VoiceAssistant prompt={getVoicePrompt()} onSend={agentChat.sendMessage} />

            {/* View Switcher for Demo Purposes */}
            <div className="fixed bottom-4 left-80 z-[60] flex gap-2 bg-white/50 backdrop-blur-md p-2 rounded-full border border-slate-200 shadow-sm">
                <button
                    onClick={() => setActiveView('dashboard')}
                    className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${activeView === 'dashboard' ? 'bg-primary text-white' : 'text-slate-500 hover:bg-slate-100'}`}
                >
                    Patient View
                </button>
                <button
                    onClick={() => setActiveView('insights')}
                    className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${activeView === 'insights' ? 'bg-primary text-white' : 'text-slate-500 hover:bg-slate-100'}`}
                >
                    Doctor View
                </button>
                <button
                    onClick={() => setActiveView('medication')}
                    className={`px-4 py-1.5 rounded-full text-xs font-bold transition-all ${activeView === 'medication' ? 'bg-primary text-white' : 'text-slate-500 hover:bg-slate-100'}`}
                >
                    Visit Summary
                </button>
            </div>
        </div>
    );
}
