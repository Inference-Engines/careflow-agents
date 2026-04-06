import React from 'react';
import { Search, Bell, UserCircle } from 'lucide-react';

interface TopBarProps {
    title: string;
    icon?: React.ReactNode;
}

const TopBar: React.FC<TopBarProps> = ({ title, icon }) => {
    return (
        <header className="flex justify-between items-center w-full px-12 h-20 bg-background sticky top-0 z-40">
            <div className="flex items-center gap-4">
                {icon && (
                    <div className="bg-primary/10 p-2 rounded-xl text-primary">
                        {icon}
                    </div>
                )}
                <h2 className="text-xl font-bold text-primary font-headline">{title}</h2>
            </div>

            <div className="flex items-center gap-6">
                <div className="flex items-center gap-3 bg-surface-container-low px-4 py-2 rounded-full border border-outline-variant/10">
                    <Search size={16} className="text-slate-400" />
                    <input
                        className="bg-transparent border-none focus:ring-0 text-sm w-48 outline-none"
                        placeholder="Search records..."
                        type="text"
                    />
                </div>
                <div className="flex items-center gap-3">
                    <button className="p-2 text-slate-600 hover:bg-surface-container-low rounded-full transition-colors relative">
                        <Bell size={20} />
                        <span className="absolute top-2 right-2 w-2 h-2 bg-error rounded-full"></span>
                    </button>
                    <button className="p-2 text-slate-600 hover:bg-surface-container-low rounded-full transition-colors">
                        <UserCircle size={24} />
                    </button>
                </div>
            </div>
        </header>
    );
};

export default TopBar;
