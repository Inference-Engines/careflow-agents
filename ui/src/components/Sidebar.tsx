import React from 'react';
import { Icon } from '@iconify/react';
import { cn } from '@/src/lib/utils';

interface SidebarProps {
    activeView: string;
    onViewChange: (view: string) => void;
}

const navItems = [
    {
        id: 'dashboard',
        label: 'My Health',
        iconActive: 'solar:widget-bold',
        iconIdle: 'solar:widget-linear',
    },
    {
        id: 'medication',
        label: 'Visit Notes',
        iconActive: 'solar:document-text-bold',
        iconIdle: 'solar:document-text-linear',
    },
    {
        id: 'insights',
        label: 'Doctor View',
        iconActive: 'solar:chart-square-bold',
        iconIdle: 'solar:chart-square-linear',
    },
    {
        id: 'schedule',
        label: 'Schedule',
        iconActive: 'solar:calendar-bold',
        iconIdle: 'solar:calendar-linear',
    },
];

const mobileNavItems = [
    { id: 'dashboard', label: 'My Health', icon: 'solar:widget-bold' },
    { id: 'medication', label: 'Visit Notes', icon: 'solar:document-text-bold' },
    { id: 'insights', label: 'Doctor View', icon: 'solar:chart-square-bold' },
    { id: 'schedule', label: 'Schedule', icon: 'solar:calendar-bold' },
];

const Sidebar: React.FC<SidebarProps> = ({ activeView, onViewChange }) => {
    return (
        <>
        <aside className="h-screen w-72 fixed left-0 top-0 bg-surface hidden lg:flex flex-col py-8 z-50 border-r border-[#1C6EF2]/5">
            {/* Premium gradient accent on left edge */}
            <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-gradient-to-b from-primary/60 via-secondary/40 to-primary/20 pointer-events-none" />

            {/* Top section: Logo + Patient Avatar */}
            <div className="px-8 mb-8 animate-reveal">
                <div className="flex items-center gap-2.5 mb-6">
                    <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center shadow-[0_4px_12px_rgba(28,110,242,0.35)]">
                        <Icon icon="solar:heart-pulse-bold" className="text-white" width={18} />
                    </div>
                    <div>
                        <h1 className="text-lg font-black text-slate-900 tracking-tight leading-none">
                            CareFlow AI
                        </h1>
                        <p className="text-xs text-slate-500 font-medium tracking-wide mt-0.5">
                            Your Care Partner
                        </p>
                    </div>
                </div>

                {/* Patient avatar circle */}
                <div className="flex items-center gap-3 p-3 rounded-2xl bg-surface-container-low">
                    <div className="w-10 h-10 rounded-full bg-primary/10 flex items-center justify-center shrink-0">
                        <span className="text-primary font-bold text-sm">RS</span>
                    </div>
                    <div className="min-w-0">
                        <p className="text-sm font-bold text-slate-900 tracking-tight truncate">Rajesh Sharma</p>
                        <p className="text-xs text-slate-500 font-medium">63 yrs · DM2 + HTN</p>
                    </div>
                </div>
            </div>

            {/* Nav */}
            <nav className="flex-1 flex flex-col px-4 space-y-1">
                {navItems.map((item, i) => {
                    const isActive = activeView === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => onViewChange(item.id)}
                            aria-label={`Navigate to ${item.label}`}
                            style={{ animationDelay: `${i * 60}ms` }}
                            className={cn(
                                'animate-reveal group flex items-center gap-3.5 w-full text-left px-4 py-3 rounded-2xl relative',
                                'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                'font-semibold text-sm tracking-tight min-h-[48px]',
                                isActive
                                    ? 'bg-primary text-white shadow-[0_8px_24px_-6px_rgba(28,110,242,0.4)]'
                                    : 'text-slate-500 hover:text-slate-900 hover:bg-surface-container-low',
                            )}
                        >
                            {/* Active left accent bar */}
                            {isActive && (
                                <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[4px] h-6 bg-white/60 rounded-r-full" />
                            )}
                            <Icon
                                icon={isActive ? item.iconActive : item.iconIdle}
                                width={20}
                                className={cn(
                                    'shrink-0 transition-transform duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                    isActive
                                        ? 'scale-110'
                                        : 'group-hover:scale-105',
                                )}
                            />
                            <span>{item.label}</span>
                            {isActive && (
                                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-white/60" />
                            )}
                        </button>
                    );
                })}
            </nav>

            {/* Voice Assistant CTA */}
            <div className="px-4 mb-5 animate-reveal stagger-4">
                <button
                    className="btn-primary w-full justify-center gap-3 py-3.5 active:scale-[0.98]"
                    onClick={() => {
                        window.dispatchEvent(new CustomEvent('careflow:voice-start'));
                    }}
                >
                    <div className="btn-icon-wrap">
                        <Icon icon="solar:microphone-bold" width={16} />
                    </div>
                    <span>Voice Assistant</span>
                </button>
            </div>

            {/* Settings / Support */}
            <div className="border-t border-surface-container px-4 pt-4 space-y-1 animate-reveal stagger-5">
                {[
                    { icon: 'solar:settings-linear', label: 'Settings' },
                    { icon: 'solar:question-circle-linear', label: 'Support' },
                ].map(({ icon, label }) => (
                    <button
                        key={label}
                        onClick={() => alert(`${label} page coming soon.`)}
                        className={cn(
                            'flex items-center gap-3.5 text-slate-400 px-4 py-3 rounded-2xl w-full text-left text-sm font-medium min-h-[48px]',
                            'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                            'hover:text-slate-700 hover:bg-surface-container-low',
                        )}
                    >
                        <Icon icon={icon} width={18} className="shrink-0" />
                        <span>{label}</span>
                    </button>
                ))}
            </div>

            {/* Powered by footer */}
            <div className="px-8 pt-4 mt-2">
                <p className="text-xs text-slate-400 font-medium tracking-wide text-center">
                    Powered by CareFlow AI
                </p>
            </div>
        </aside>

        {/* Mobile Bottom Navigation */}
        <nav className="lg:hidden fixed bottom-0 left-0 right-0 z-50 bg-white/90 backdrop-blur-xl border-t border-black/[0.06] pb-safe" aria-label="Mobile navigation">
            <div className="flex items-center justify-around px-2 py-2">
                {mobileNavItems.map((item) => {
                    const isActive = activeView === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => onViewChange(item.id)}
                            aria-label={`Navigate to ${item.label}`}
                            className={cn(
                                'flex flex-col items-center gap-1 px-3 py-2 rounded-2xl min-h-[48px] min-w-[64px]',
                                'transition-all duration-300',
                                isActive
                                    ? 'text-primary bg-primary/8'
                                    : 'text-slate-400 hover:text-slate-600',
                            )}
                        >
                            <Icon icon={item.icon} width={22} />
                            <span className="text-xs font-semibold tracking-tight">{item.label}</span>
                        </button>
                    );
                })}
            </div>
        </nav>
        </>
    );
};

export default Sidebar;
