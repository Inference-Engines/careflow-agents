import React from 'react';
import { cn } from '@/src/lib/utils';
import {
    LayoutGrid,
    Pill,
    BarChart3,
    Calendar,
    Mic,
    Settings,
    HelpCircle
} from 'lucide-react';

interface SidebarProps {
    activeView: string;
    onViewChange: (view: string) => void;
}

const Sidebar: React.FC<SidebarProps> = ({ activeView, onViewChange }) => {
    const navItems = [
        { id: 'dashboard', label: 'Dashboard', icon: LayoutGrid },
        { id: 'medication', label: 'Medication', icon: Pill },
        { id: 'insights', label: 'Insights', icon: BarChart3 },
        { id: 'schedule', label: 'Schedule', icon: Calendar },
    ];

    return (
        <aside className="h-screen w-72 fixed left-0 top-0 bg-white shadow-[0_12px_40px_rgba(0,88,189,0.06)] flex flex-col py-8 z-50">
            <div className="px-8 mb-12">
                <h1 className="text-2xl font-black text-primary">CareFlow AI</h1>
                <p className="text-sm text-slate-500 font-medium mt-1">Autonomous Partner</p>
            </div>

            <nav className="flex-1 flex flex-col">
                {navItems.map((item) => {
                    const Icon = item.icon;
                    const isActive = activeView === item.id;
                    return (
                        <button
                            key={item.id}
                            onClick={() => onViewChange(item.id)}
                            className={cn(
                                "flex items-center gap-4 p-4 transition-all duration-300 w-full text-left",
                                isActive
                                    ? "bg-primary-container text-white rounded-r-full mr-4 shadow-lg scale-95 origin-left"
                                    : "text-slate-500 hover:text-primary hover:bg-background"
                            )}
                        >
                            <Icon size={20} fill={isActive ? "currentColor" : "none"} />
                            <span className="font-medium">{item.label}</span>
                        </button>
                    );
                })}
            </nav>

            <div className="px-4 mb-6">
                <button className="w-full flex items-center justify-center gap-3 bg-primary-container text-white py-4 rounded-full font-bold shadow-md hover:scale-[0.98] transition-all">
                    <Mic size={20} />
                    Voice Assistant
                </button>
            </div>

            <div className="border-t border-slate-100 pt-6">
                <button className="flex items-center gap-4 text-slate-500 p-4 hover:text-primary transition-all w-full text-left">
                    <Settings size={20} />
                    <span className="font-medium">Settings</span>
                </button>
                <button className="flex items-center gap-4 text-slate-500 p-4 hover:text-primary transition-all w-full text-left">
                    <HelpCircle size={20} />
                    <span className="font-medium">Support</span>
                </button>
            </div>
        </aside>
    );
};

export default Sidebar;
