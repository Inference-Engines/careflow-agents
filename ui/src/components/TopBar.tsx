import React, { useState, useRef, useEffect } from 'react';
import { Icon } from '@iconify/react';
import { cn } from '@/src/lib/utils';

interface TopBarProps {
    title: string;
    icon?: React.ReactNode;
}

const NOTIFICATIONS = [
    { id: 1, icon: 'solar:pill-bold', color: 'text-primary bg-primary/10', title: 'Medication reminder', desc: 'Amlodipine 5mg is due at 1:00 PM', time: '10 min ago', unread: true },
    { id: 2, icon: 'solar:calendar-bold', color: 'text-secondary bg-secondary/10', title: 'Appointment confirmed', desc: 'HbA1c Lab Test on April 17 at 8:00 AM', time: '2 hrs ago', unread: true },
    { id: 3, icon: 'solar:heart-pulse-bold', color: 'text-error bg-error/10', title: 'BP reading logged', desc: '140/90 mmHg — slightly elevated', time: 'Yesterday', unread: false },
];

const TopBar: React.FC<TopBarProps> = ({ title, icon }) => {
    const [bellOpen, setBellOpen] = useState(false);
    const bellRef = useRef<HTMLDivElement>(null);

    // Close dropdown on outside click
    useEffect(() => {
        const handler = (e: MouseEvent) => {
            if (bellRef.current && !bellRef.current.contains(e.target as Node)) {
                setBellOpen(false);
            }
        };
        if (bellOpen) document.addEventListener('mousedown', handler);
        return () => document.removeEventListener('mousedown', handler);
    }, [bellOpen]);

    const unreadCount = NOTIFICATIONS.filter(n => n.unread).length;

    return (
        <header
            className="flex justify-between items-center w-full px-4 md:px-10 h-[68px] sticky top-0 z-40 border-b border-black/[0.04]"
            style={{
                background: 'rgba(246, 248, 253, 0.85)',
                backdropFilter: 'blur(20px) saturate(180%)',
                WebkitBackdropFilter: 'blur(20px) saturate(180%)',
            }}
        >
            {/* Title */}
            <div className="flex items-center gap-3 min-w-0">
                {icon && (
                    <div className="bg-primary/8 p-2 rounded-xl text-primary shrink-0">
                        {icon}
                    </div>
                )}
                <h2 className="text-base font-bold text-slate-800 tracking-tight truncate">
                    {title}
                </h2>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 md:gap-3 shrink-0">
                {/* Notification bell with dropdown */}
                <div className="relative" ref={bellRef}>
                    <button
                        id="topbar-bell"
                        onClick={() => setBellOpen(prev => !prev)}
                        className="relative p-2.5 text-slate-500 rounded-full hover:bg-surface-container-low transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:text-slate-800 hover:scale-105 active:scale-95 min-h-[44px] min-w-[44px] flex items-center justify-center"
                        aria-label={`Notifications — ${unreadCount} unread`}
                        aria-expanded={bellOpen}
                    >
                        <Icon icon="solar:bell-linear" width={20} />
                        {unreadCount > 0 && (
                            <span className="absolute top-1.5 right-1.5 min-w-[18px] h-[18px] bg-error rounded-full border-2 border-background flex items-center justify-center text-[10px] text-white font-bold">
                                {unreadCount}
                            </span>
                        )}
                    </button>

                    {/* Dropdown */}
                    {bellOpen && (
                        <div className="absolute right-0 top-full mt-2 w-80 bg-white rounded-2xl shadow-[0_20px_60px_-15px_rgba(0,0,0,0.2)] border border-slate-100 overflow-hidden z-50 animate-fade-in">
                            <div className="p-4 border-b border-slate-100 flex items-center justify-between">
                                <h4 className="text-sm font-bold text-slate-900">Notifications</h4>
                                {unreadCount > 0 && (
                                    <span className="text-xs font-semibold text-primary bg-primary/8 px-2 py-0.5 rounded-full">
                                        {unreadCount} new
                                    </span>
                                )}
                            </div>
                            <div className="max-h-72 overflow-y-auto">
                                {NOTIFICATIONS.map(n => (
                                    <div key={n.id} className={cn(
                                        'flex items-start gap-3 px-4 py-3.5 hover:bg-surface-container-low transition-colors cursor-default',
                                        n.unread && 'bg-primary/[0.02]',
                                    )}>
                                        <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center shrink-0 mt-0.5', n.color)}>
                                            <Icon icon={n.icon} width={16} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <p className="text-sm font-semibold text-slate-900 truncate">{n.title}</p>
                                                {n.unread && <span className="w-2 h-2 rounded-full bg-primary shrink-0" />}
                                            </div>
                                            <p className="text-sm text-slate-500 mt-0.5 leading-snug">{n.desc}</p>
                                            <p className="text-xs text-slate-400 mt-1 font-medium">{n.time}</p>
                                        </div>
                                    </div>
                                ))}
                            </div>
                            <div className="p-3 border-t border-slate-100">
                                <button className="w-full text-center text-sm font-semibold text-primary hover:text-primary-dim py-2 rounded-xl hover:bg-primary/5 transition-colors">
                                    View all notifications
                                </button>
                            </div>
                        </div>
                    )}
                </div>

                {/* Avatar */}
                <button
                    id="topbar-profile"
                    onClick={() => alert('Profile settings coming soon.')}
                    className="p-2 text-slate-500 rounded-full hover:bg-surface-container-low transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:text-slate-800 hover:scale-105 active:scale-95 min-h-[44px] min-w-[44px] flex items-center justify-center"
                    aria-label="Profile settings"
                >
                    <Icon icon="solar:user-circle-linear" width={24} />
                </button>
            </div>
        </header>
    );
};

export default TopBar;
