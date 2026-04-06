import React, { useState, useRef, useEffect } from 'react';
import {
    Sparkles,
    Send,
    Mic,
    Activity,
    Droplets,
    CheckCircle2,
    Pill,
    Moon,
    ChevronRight,
    Calendar,
    AlertTriangle,
    User,
    Bot,
    Loader2,
} from 'lucide-react';
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

    // Auto-scroll chat to bottom on new messages
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

    return (
        <div className="md:ml-72 pt-20 pb-24 px-4 md:px-10 min-h-screen">
            {/* Welcome Section */}
            <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mb-8">
                <div>
                    <h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 tracking-tight">
                        Namaste, Rajesh.
                    </h1>
                    <p className="text-slate-500 mt-1">Here is your health summary for today.</p>
                </div>
                <div className="flex items-center gap-2 bg-secondary-container/30 px-4 py-2 rounded-full border border-secondary-container/50">
                    <div className="flex space-x-[-8px]">
                        <div className="w-6 h-6 rounded-full bg-secondary flex items-center justify-center text-[10px] text-white ring-2 ring-white">
                            AI
                        </div>
                        <div className="w-6 h-6 rounded-full bg-primary flex items-center justify-center text-[10px] text-white ring-2 ring-white">
                            Care
                        </div>
                    </div>
                    <span className="text-xs font-bold text-secondary">CareFlow Agents: Active</span>
                    <div
                        className={cn(
                            'w-2 h-2 rounded-full',
                            status === 'streaming' ? 'bg-tertiary animate-ping' : 'bg-secondary animate-pulse',
                        )}
                    />
                </div>
            </div>

            {/* Bento Grid */}
            <div className="grid grid-cols-1 md:grid-cols-12 gap-6">
                {/* AI Chat Input */}
                <section className="md:col-span-8 bg-white rounded-[2rem] shadow-[0_12px_40px_rgba(0,88,189,0.06)] relative overflow-hidden group flex flex-col">
                    <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-primary to-primary-container" />

                    <div className="p-8 flex flex-col flex-1">
                        <h3 className="text-xl font-bold mb-1 flex items-center gap-2 text-slate-900">
                            <Sparkles size={20} className="text-primary" fill="currentColor" />
                            Update your Care Partner
                        </h3>
                        <p className="text-slate-500 text-sm mb-4">
                            Tell me how you're feeling or about any changes in your routine.
                        </p>

                        {/* ── Message History ───────────────────────────────────── */}
                        {hasMessages && (
                            <div className="flex-1 overflow-y-auto mb-4 max-h-80 space-y-4 pr-1 scrollbar-thin">
                                {messages.map((msg) => (
                                    <div
                                        key={msg.id}
                                        className={cn(
                                            'flex gap-3',
                                            msg.role === 'user' ? 'flex-row-reverse' : 'flex-row',
                                        )}
                                    >
                                        {/* Avatar */}
                                        <div
                                            className={cn(
                                                'w-8 h-8 rounded-full flex items-center justify-center shrink-0 mt-1',
                                                msg.role === 'user'
                                                    ? 'bg-primary text-white'
                                                    : 'bg-primary/10 text-primary',
                                            )}
                                        >
                                            {msg.role === 'user' ? (
                                                <User size={14} />
                                            ) : (
                                                <Bot size={14} />
                                            )}
                                        </div>

                                        {/* Bubble */}
                                        <div
                                            className={cn(
                                                'max-w-[80%] rounded-2xl px-4 py-3 text-sm leading-relaxed',
                                                msg.role === 'user'
                                                    ? 'bg-primary text-white rounded-tr-sm'
                                                    : 'bg-background text-slate-800 rounded-tl-sm',
                                            )}
                                        >
                                            {msg.role === 'assistant' ? (
                                                <div className="prose prose-sm prose-slate max-w-none">
                                                    <ReactMarkdown>{msg.content || '…'}</ReactMarkdown>
                                                </div>
                                            ) : (
                                                msg.content
                                            )}

                                            {/* Streaming cursor for the last assistant message */}
                                            {msg.role === 'assistant' &&
                                                status === 'streaming' &&
                                                msg === messages[messages.length - 1] && (
                                                    <span className="inline-block w-1.5 h-4 bg-primary/60 ml-0.5 animate-pulse rounded-sm align-middle" />
                                                )}
                                        </div>
                                    </div>
                                ))}
                                <div ref={messagesEndRef} />
                            </div>
                        )}

                        {/* ── Input Box ────────────────────────────────────────── */}
                        <div className="relative">
                            <textarea
                                ref={textareaRef}
                                value={inputText}
                                onChange={(e) => setInputText(e.target.value)}
                                onKeyDown={handleKeyDown}
                                disabled={status === 'streaming'}
                                className="w-full bg-background border-none rounded-2xl p-6 pb-16 text-base focus:ring-2 focus:ring-primary-container min-h-[120px] resize-none placeholder:text-slate-300 outline-none disabled:opacity-60"
                                placeholder={
                                    status === 'streaming'
                                        ? 'CareFlow is responding…'
                                        : 'Doctor changed my medication today…'
                                }
                            />
                            <div className="absolute bottom-4 right-4 flex gap-3 items-center">
                                {status === 'streaming' && (
                                    <Loader2 size={18} className="text-primary animate-spin" />
                                )}
                                <button
                                    id="send-message-btn"
                                    onClick={handleSend}
                                    disabled={status === 'streaming' || !inputText.trim()}
                                    className="bg-primary text-white px-6 py-2 rounded-full font-bold flex items-center gap-2 hover:scale-[0.98] transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                                >
                                    <span>Send</span>
                                    <Send size={16} />
                                </button>
                                <button
                                    id="voice-input-btn"
                                    className="bg-primary-container/10 text-primary-container p-3 rounded-full hover:bg-primary-container/20 transition-colors"
                                    title="Use the voice button at the bottom-right to speak"
                                    onClick={() => {
                                        const msg =
                                            "Use the 🎤 button at the bottom-right of the screen to speak to CareFlow.";
                                        alert(msg);
                                    }}
                                >
                                    <Mic size={20} fill="currentColor" />
                                </button>
                            </div>
                        </div>
                    </div>
                </section>

                {/* Quick Metrics */}
                <div className="md:col-span-4 flex flex-col gap-6">
                    {/* Blood Pressure */}
                    <div className="bg-white p-6 rounded-[2rem] shadow-sm flex-1 border-l-4 border-primary">
                        <div className="flex justify-between items-start mb-4">
                            <span className="p-2 bg-primary/10 rounded-xl text-primary">
                                <Activity size={20} />
                            </span>
                            <span className="text-xs font-bold text-error bg-error-container px-2 py-1 rounded-md">
                                Elevated
                            </span>
                        </div>
                        <div className="flex items-baseline gap-1">
                            <span className="text-4xl font-black text-slate-900">140/90</span>
                            <span className="text-sm text-slate-400 font-medium">mmHg</span>
                        </div>
                        <p className="text-xs font-bold mt-2 text-slate-500">Blood Pressure</p>
                        <div className="mt-4 h-1 w-full bg-background rounded-full overflow-hidden">
                            <div className="h-full bg-error w-[85%] rounded-full" />
                        </div>
                    </div>

                    {/* Blood Glucose */}
                    <div className="bg-white p-6 rounded-[2rem] shadow-sm flex-1 border-l-4 border-secondary">
                        <div className="flex justify-between items-start mb-4">
                            <span className="p-2 bg-secondary/10 rounded-xl text-secondary">
                                <Droplets size={20} />
                            </span>
                            <span className="text-xs font-bold text-secondary bg-secondary-container px-2 py-1 rounded-md">
                                Optimal
                            </span>
                        </div>
                        <div className="flex items-baseline gap-1">
                            <span className="text-4xl font-black text-slate-900">128</span>
                            <span className="text-sm text-slate-400 font-medium">mg/dL</span>
                        </div>
                        <p className="text-xs font-bold mt-2 text-slate-500">Blood Glucose</p>
                        <div className="mt-4 h-1 w-full bg-background rounded-full overflow-hidden">
                            <div className="h-full bg-secondary w-[60%] rounded-full" />
                        </div>
                    </div>
                </div>

                {/* Medication Tracker */}
                <section className="md:col-span-7 bg-surface-container-low rounded-[2rem] p-8">
                    <div className="flex justify-between items-center mb-8">
                        <h3 className="text-2xl font-bold text-slate-900">Upcoming Medications</h3>
                        <button className="text-primary font-bold text-sm flex items-center gap-1">
                            View Schedule <ChevronRight size={16} />
                        </button>
                    </div>
                    <div className="space-y-4">
                        <MedicationItem
                            icon={<CheckCircle2 size={24} />}
                            color="bg-secondary/10 text-secondary"
                            name="Metformin"
                            dose="500mg • After Breakfast"
                            status="Taken"
                            time="08:30 AM"
                        />
                        <MedicationItem
                            icon={<Pill size={24} />}
                            color="bg-primary/10 text-primary"
                            name="Amlodipine"
                            dose="5mg • Before Lunch"
                            action="Mark Taken"
                            active
                        />
                        <MedicationItem
                            icon={<Moon size={24} />}
                            color="bg-slate-100 text-slate-400"
                            name="Atorvastatin"
                            dose="10mg • Before Bed"
                            time="Scheduled: 09:00 PM"
                            dimmed
                        />
                    </div>
                </section>

                {/* Appointment Card */}
                <section className="md:col-span-5">
                    <div className="bg-primary-container rounded-[2rem] p-8 text-white relative overflow-hidden h-full flex flex-col justify-between shadow-xl">
                        <div className="absolute -top-10 -right-10 w-40 h-40 bg-white/10 rounded-full blur-3xl" />
                        <div className="absolute -bottom-10 -left-10 w-40 h-40 bg-black/10 rounded-full blur-3xl" />
                        <div className="relative z-10">
                            <div className="flex justify-between items-start mb-6">
                                <div className="bg-white/20 p-3 rounded-2xl backdrop-blur-md">
                                    <Calendar size={24} />
                                </div>
                                <span className="text-xs font-bold bg-white text-primary px-3 py-1 rounded-full">
                                    In 3 Days
                                </span>
                            </div>
                            <h3 className="text-sm font-bold opacity-80 uppercase tracking-widest mb-1">
                                Next Appointment
                            </h3>
                            <h2 className="text-3xl font-black mb-4">HbA1c Test</h2>
                            <div className="space-y-3 mb-8">
                                <div className="flex items-center gap-3">
                                    <Calendar size={16} className="opacity-70" />
                                    <span className="font-medium">Wednesday, April 17</span>
                                </div>
                                <div className="flex items-center gap-3">
                                    <Activity size={16} className="opacity-70" />
                                    <span className="font-medium">08:00 AM - Diagnostics Lab</span>
                                </div>
                            </div>
                        </div>
                        <div className="relative z-10 bg-white/10 border border-white/20 p-4 rounded-2xl backdrop-blur-md">
                            <div className="flex items-start gap-3">
                                <AlertTriangle size={20} className="text-tertiary-container" />
                                <div>
                                    <p className="text-xs font-bold text-tertiary-container">FASTING REQUIRED</p>
                                    <p className="text-[11px] leading-tight opacity-90 mt-1">
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

const MedicationItem = ({ icon, color, name, dose, status, time, action, active, dimmed }: any) => (
    <div
        className={cn(
            'bg-white p-5 rounded-2xl flex items-center justify-between transition-all',
            active && 'border-2 border-primary/10',
            dimmed && 'opacity-60',
        )}
    >
        <div className="flex items-center gap-4">
            <div className={cn('w-12 h-12 rounded-full flex items-center justify-center', color)}>
                {icon}
            </div>
            <div>
                <h4 className={cn('font-bold text-lg', active ? 'text-primary' : 'text-slate-900')}>
                    {name}
                </h4>
                <p className="text-sm text-slate-400">{dose}</p>
            </div>
        </div>
        <div className="text-right">
            {status && (
                <>
                    <span className="text-[10px] font-bold text-secondary uppercase tracking-widest block mb-1">
                        {status}
                    </span>
                    <p className="text-xs text-slate-400">{time}</p>
                </>
            )}
            {action && (
                <button className="bg-primary text-white px-6 py-2 rounded-full font-bold text-sm shadow-md hover:scale-95 transition-all">
                    {action}
                </button>
            )}
            {!status && !action && time && <p className="text-xs text-slate-400">{time}</p>}
        </div>
    </div>
);

export default PatientDashboardView;
