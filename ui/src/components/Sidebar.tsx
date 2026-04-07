import React, { useState, useEffect } from 'react';
import { Icon } from '@iconify/react';
import { cn } from '@/src/lib/utils';
import { t, setLang, getLang } from '../lib/i18n';
import type { Lang } from '../lib/i18n';

interface SidebarProps {
    activeView: string;
    onViewChange: (view: string) => void;
}

const navItems = [
    {
        id: 'dashboard',
        labelKey: 'home',
        iconActive: 'solar:widget-bold',
        iconIdle: 'solar:widget-linear',
    },
    {
        id: 'medication',
        labelKey: 'my_visits',
        iconActive: 'solar:document-text-bold',
        iconIdle: 'solar:document-text-linear',
    },
    {
        id: 'insights',
        labelKey: 'doctor_view',
        iconActive: 'solar:chart-square-bold',
        iconIdle: 'solar:chart-square-linear',
    },
    {
        id: 'schedule',
        labelKey: 'schedule',
        iconActive: 'solar:calendar-bold',
        iconIdle: 'solar:calendar-linear',
    },
];

const mobileNavItems = [
    { id: 'dashboard', labelKey: 'home', icon: 'solar:widget-bold' },
    { id: 'medication', labelKey: 'my_visits', icon: 'solar:document-text-bold' },
    { id: 'insights', labelKey: 'doctor_view', icon: 'solar:chart-square-bold' },
    { id: 'schedule', labelKey: 'schedule', icon: 'solar:calendar-bold' },
];

const Sidebar: React.FC<SidebarProps> = ({ activeView, onViewChange }) => {
    const [darkMode, setDarkMode] = useState(() => document.documentElement.classList.contains('dark'));
    const [showSettingsModal, setShowSettingsModal] = useState(false);
    const [showSupportModal, setShowSupportModal] = useState(false);
    const [language, setLanguage] = useState<Lang>(getLang());
    const [, forceUpdate] = useState(0);
    const [textSize, setTextSize] = useState<'normal' | 'large' | 'xl'>('normal');
    const [colorVision, setColorVision] = useState<'normal' | 'colorblind-deutan' | 'high-contrast'>(() => {
        if (document.documentElement.classList.contains('colorblind-deutan')) return 'colorblind-deutan';
        if (document.documentElement.classList.contains('high-contrast')) return 'high-contrast';
        return 'normal';
    });

    useEffect(() => {
        if (darkMode) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
    }, [darkMode]);

    useEffect(() => {
        const sizeMap = { normal: '16px', large: '18px', xl: '20px' };
        document.documentElement.style.fontSize = sizeMap[textSize];
    }, [textSize]);

    useEffect(() => {
        document.documentElement.classList.remove('colorblind-deutan', 'high-contrast');
        if (colorVision !== 'normal') {
            document.documentElement.classList.add(colorVision);
        }
    }, [colorVision]);

    const toggleDarkMode = () => setDarkMode((prev) => !prev);

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
                            {t('care_partner')}
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
                        <p className="text-xs text-slate-500 font-medium">63 yrs · Diabetes & Blood Pressure</p>
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
                            aria-label={`Navigate to ${t(item.labelKey)}`}
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
                            <span>{t(item.labelKey)}</span>
                            {isActive && (
                                <span className="ml-auto w-1.5 h-1.5 rounded-full bg-white/60" />
                            )}
                        </button>
                    );
                })}
            </nav>

            {/* Settings / Support */}
            <div className="border-t border-surface-container px-4 pt-4 space-y-1 animate-reveal stagger-5">
                <button
                    onClick={() => setShowSettingsModal(true)}
                    className={cn(
                        'flex items-center gap-3.5 text-slate-400 px-4 py-3 rounded-2xl w-full text-left text-sm font-medium min-h-[48px]',
                        'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                        'hover:text-slate-700 hover:bg-surface-container-low',
                    )}
                >
                    <Icon icon="solar:settings-linear" width={18} className="shrink-0" />
                    <span>{t('settings')}</span>
                </button>
                <button
                    onClick={() => setShowSupportModal(true)}
                    className={cn(
                        'flex items-center gap-3.5 text-slate-400 px-4 py-3 rounded-2xl w-full text-left text-sm font-medium min-h-[48px]',
                        'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                        'hover:text-slate-700 hover:bg-surface-container-low',
                    )}
                >
                    <Icon icon="solar:question-circle-linear" width={18} className="shrink-0" />
                    <span>{t('support')}</span>
                </button>
            </div>

            {/* Powered by footer */}
            <div className="px-8 pt-4 mt-2">
                <p className="text-xs text-slate-400 font-medium tracking-wide text-center">
                    {t('powered_by')}
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
                            aria-label={`Navigate to ${t(item.labelKey)}`}
                            className={cn(
                                'flex flex-col items-center gap-1 px-3 py-2 rounded-2xl min-h-[48px] min-w-[64px]',
                                'transition-all duration-300',
                                isActive
                                    ? 'text-primary bg-primary/8'
                                    : 'text-slate-400 hover:text-slate-600',
                            )}
                        >
                            <Icon icon={item.icon} width={22} />
                            <span className="text-xs font-semibold tracking-tight">{t(item.labelKey)}</span>
                        </button>
                    );
                })}
            </div>
        </nav>

        {/* ── Settings Modal ─────────────────────────────────────────── */}
        {showSettingsModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowSettingsModal(false)}>
                <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6 space-y-6" onClick={(e) => e.stopPropagation()}>
                    <h2 className="text-lg font-bold text-slate-900 tracking-tight">{t('settings')}</h2>

                    {/* Dark Mode Toggle */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Icon icon={darkMode ? 'solar:moon-bold' : 'solar:sun-bold'} width={20} className="text-slate-600" />
                            <span className="text-sm font-medium text-slate-700">{t('dark_mode')}</span>
                        </div>
                        <button
                            onClick={toggleDarkMode}
                            className={cn(
                                'relative w-11 h-6 rounded-full transition-colors duration-300',
                                darkMode ? 'bg-primary' : 'bg-slate-300',
                            )}
                            aria-label="Toggle dark mode"
                        >
                            <span className={cn(
                                'absolute top-0.5 left-0.5 w-5 h-5 bg-white rounded-full shadow transition-transform duration-300',
                                darkMode && 'translate-x-5',
                            )} />
                        </button>
                    </div>

                    {/* Language Selector */}
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                            <Icon icon="solar:global-linear" width={20} className="text-slate-600" />
                            <span className="text-sm font-medium text-slate-700">{t('language')}</span>
                        </div>
                        <select
                            value={language}
                            onChange={(e) => { const lang = e.target.value as Lang; setLanguage(lang); setLang(lang); forceUpdate(n => n + 1); }}
                            className="text-sm font-medium text-slate-700 bg-surface-container-low rounded-xl px-3 py-1.5 border border-slate-200 focus:outline-none focus:ring-2 focus:ring-primary/30"
                        >
                            <option value="en">English</option>
                            <option value="ko">한국어</option>
                            <option value="hi">हिन्दी</option>
                        </select>
                    </div>

                    {/* Text Size Slider */}
                    <div className="space-y-2">
                        <div className="flex items-center gap-3">
                            <Icon icon="solar:text-field-linear" width={20} className="text-slate-600" />
                            <span className="text-sm font-medium text-slate-700">{t('text_size')}</span>
                        </div>
                        <div className="flex gap-2">
                            {([['normal', 'Normal'], ['large', 'Large'], ['xl', 'Extra Large']] as const).map(([value, label]) => (
                                <button
                                    key={value}
                                    onClick={() => setTextSize(value)}
                                    className={cn(
                                        'flex-1 text-xs font-semibold py-2 rounded-xl transition-all duration-300',
                                        textSize === value
                                            ? 'bg-primary text-white shadow-md'
                                            : 'bg-surface-container-low text-slate-500 hover:bg-surface-container',
                                    )}
                                >
                                    {label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Color Vision Selector */}
                    <div className="space-y-2">
                        <div className="flex items-center gap-3">
                            <Icon icon="solar:eye-linear" width={20} className="text-slate-600" />
                            <span className="text-sm font-medium text-slate-700">{t('color_vision')}</span>
                        </div>
                        <div className="flex gap-2">
                            {([['normal', 'Normal'], ['colorblind-deutan', 'Colorblind-friendly'], ['high-contrast', 'High Contrast']] as const).map(([value, label]) => (
                                <button
                                    key={value}
                                    onClick={() => setColorVision(value)}
                                    className={cn(
                                        'flex-1 text-xs font-semibold py-2 rounded-xl transition-all duration-300',
                                        colorVision === value
                                            ? 'bg-primary text-white shadow-md'
                                            : 'bg-surface-container-low text-slate-500 hover:bg-surface-container',
                                    )}
                                >
                                    {label}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Close */}
                    <button
                        onClick={() => setShowSettingsModal(false)}
                        className="w-full py-2.5 rounded-xl bg-surface-container-low text-sm font-semibold text-slate-600 hover:bg-surface-container transition-colors duration-300"
                    >
                        {t('close')}
                    </button>
                </div>
            </div>
        )}

        {/* ── Support Modal ──────────────────────────────────────────── */}
        {showSupportModal && (
            <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowSupportModal(false)}>
                <div className="bg-white rounded-2xl shadow-xl w-full max-w-md mx-4 p-6 space-y-5" onClick={(e) => e.stopPropagation()}>
                    <h2 className="text-lg font-bold text-slate-900 tracking-tight">{t('support')}</h2>

                    <div className="space-y-3">
                        <div className="flex items-center gap-3 p-3 rounded-xl bg-surface-container-low">
                            <Icon icon="solar:letter-linear" width={20} className="text-primary shrink-0" />
                            <div>
                                <p className="text-xs text-slate-500 font-medium">Email</p>
                                <p className="text-sm font-semibold text-slate-700">support@careflow.health</p>
                            </div>
                        </div>
                        <div className="flex items-center gap-3 p-3 rounded-xl bg-surface-container-low">
                            <Icon icon="solar:phone-linear" width={20} className="text-primary shrink-0" />
                            <div>
                                <p className="text-xs text-slate-500 font-medium">Phone</p>
                                <p className="text-sm font-semibold text-slate-700">1800-CARE-FLOW</p>
                            </div>
                        </div>
                    </div>

                    <button
                        onClick={() => setShowSupportModal(false)}
                        className="w-full py-2.5 rounded-xl bg-surface-container-low text-sm font-semibold text-slate-600 hover:bg-surface-container transition-colors duration-300"
                    >
                        {t('close')}
                    </button>
                </div>
            </div>
        )}
        </>
    );
};

export default Sidebar;
