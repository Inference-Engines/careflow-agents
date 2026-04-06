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
        label: 'Dashboard',
        iconActive: 'solar:widget-bold',
        iconIdle: 'solar:widget-linear',
    },
    {
        id: 'medication',
        label: 'Medication',
        iconActive: 'solar:pill-bold',
        iconIdle: 'solar:pill-linear',
    },
    {
        id: 'insights',
        label: 'Insights',
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

const Sidebar: React.FC<SidebarProps> = ({ activeView, onViewChange }) => {
    return (
        <aside className="h-screen w-72 fixed left-0 top-0 bg-surface flex flex-col py-8 z-50 border-r border-[#1C6EF2]/5">
            {/* Subtle left-edge gradient accent */}
            <div className="absolute left-0 top-0 bottom-0 w-[3px] bg-gradient-to-b from-transparent via-primary/40 to-transparent pointer-events-none" />

            {/* Logo */}
            <div className="px-8 mb-10 animate-reveal">
                <div className="flex items-center gap-2.5">
                    <div className="w-8 h-8 rounded-xl bg-primary flex items-center justify-center shadow-[0_4px_12px_rgba(28,110,242,0.35)]">
                        <Icon icon="solar:heart-pulse-bold" className="text-white" width={18} />
                    </div>
                    <div>
                        <h1 className="text-lg font-black text-slate-900 tracking-tight leading-none">
                            CareFlow AI
                        </h1>
                        <p className="text-[11px] text-slate-400 font-medium tracking-wide mt-0.5">
                            Autonomous Partner
                        </p>
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
                            style={{ animationDelay: `${i * 60}ms` }}
                            className={cn(
                                'animate-reveal group flex items-center gap-3.5 w-full text-left px-4 py-3 rounded-2xl',
                                'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                'font-semibold text-sm tracking-tight',
                                isActive
                                    ? 'bg-primary text-white shadow-[0_8px_24px_-6px_rgba(28,110,242,0.4)]'
                                    : 'text-slate-500 hover:text-slate-900 hover:bg-surface-container-low',
                            )}
                        >
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
                <button className="btn-primary w-full justify-center gap-3 py-3.5">
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
                        className={cn(
                            'flex items-center gap-3.5 text-slate-400 px-4 py-3 rounded-2xl w-full text-left text-sm font-medium',
                            'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                            'hover:text-slate-700 hover:bg-surface-container-low',
                        )}
                    >
                        <Icon icon={icon} width={18} className="shrink-0" />
                        <span>{label}</span>
                    </button>
                ))}
            </div>
        </aside>
    );
};

export default Sidebar;
