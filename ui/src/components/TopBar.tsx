import React from 'react';
import { Icon } from '@iconify/react';

interface TopBarProps {
    title: string;
    icon?: React.ReactNode;
}

const TopBar: React.FC<TopBarProps> = ({ title, icon }) => {
    return (
        <header
            className="flex justify-between items-center w-full px-10 h-[68px] sticky top-0 z-40 border-b border-black/[0.04]"
            style={{
                background: 'rgba(246, 248, 253, 0.85)',
                backdropFilter: 'blur(20px) saturate(180%)',
                WebkitBackdropFilter: 'blur(20px) saturate(180%)',
            }}
        >
            {/* Title */}
            <div className="flex items-center gap-3">
                {icon && (
                    <div className="bg-primary/8 p-2 rounded-xl text-primary">
                        {icon}
                    </div>
                )}
                <h2 className="text-base font-bold text-slate-800 tracking-tight">
                    {title}
                </h2>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-3">
                {/* Search pill */}
                <div
                    className="flex items-center gap-2.5 px-4 py-2 rounded-full border border-outline-variant/20 bg-surface/60 transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)] focus-within:border-primary/30 focus-within:shadow-[0_0_0_3px_rgba(28,110,242,0.08)]"
                >
                    <Icon icon="solar:magnifer-linear" width={15} className="text-slate-400 shrink-0" />
                    <input
                        id="topbar-search"
                        className="bg-transparent border-none focus:ring-0 text-sm w-40 outline-none text-slate-700 placeholder:text-slate-400"
                        placeholder="Search records..."
                        type="text"
                    />
                </div>

                {/* Notification bell */}
                <button
                    id="topbar-bell"
                    className="relative p-2.5 text-slate-500 rounded-full hover:bg-surface-container-low transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:text-slate-800 hover:scale-105 active:scale-95"
                >
                    <Icon icon="solar:bell-linear" width={20} />
                    <span className="absolute top-2 right-2 w-2 h-2 bg-error rounded-full border-2 border-background" />
                </button>

                {/* Avatar */}
                <button
                    id="topbar-profile"
                    className="p-2 text-slate-500 rounded-full hover:bg-surface-container-low transition-all duration-300 ease-[cubic-bezier(0.16,1,0.3,1)] hover:text-slate-800 hover:scale-105 active:scale-95"
                >
                    <Icon icon="solar:user-circle-linear" width={24} />
                </button>
            </div>
        </header>
    );
};

export default TopBar;
