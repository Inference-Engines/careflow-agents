import React, { useState, useEffect } from 'react';
import { Icon } from '@iconify/react';
import BentoCard from './BentoCard';
import { cn } from '@/src/lib/utils';
import { t } from '../lib/i18n';
import type { UseAgentChatReturn } from '../lib/useAgentChat';
import { fetchAppointments as fetchAppointmentsApi, fetchActiveMedications, markMedicationTaken } from '../lib/api';

type AppointmentStatus = 'upcoming' | 'today' | 'completed' | 'scheduled';

interface Appointment {
    id: string;
    title: string;
    date: string;
    time: string;
    doctor: string;
    location: string;
    status: AppointmentStatus;
    type: string;
    note?: string;
    fasting_required?: boolean;
}

const FALLBACK_APPOINTMENTS: Appointment[] = [
    {
        id: '1',
        title: 'HbA1c Lab Test',
        date: 'Wednesday, April 17',
        time: '08:00 AM',
        doctor: 'Dr. Mehta',
        location: 'Apollo Hospital Diagnostics, Sarita Vihar',
        status: 'upcoming',
        type: 'Laboratory',
        note: 'Fasting required — 8 hrs prior',
    },
    {
        id: '2',
        title: 'Cardiology Review',
        date: 'Friday, April 25',
        time: '11:30 AM',
        doctor: 'Dr. Kapoor',
        location: 'Apollo Hospital, OPD Block C',
        status: 'upcoming',
        type: 'Consultation',
    },
    {
        id: '3',
        title: 'Diabetology Follow-up',
        date: 'Monday, May 5',
        time: '10:00 AM',
        doctor: 'Dr. Mehta',
        location: 'Apollo Hospital, Endocrinology Wing',
        status: 'upcoming',
        type: 'Follow-up',
    },
    {
        id: '4',
        title: 'Pre-visit at Apollo Hospital',
        date: 'Thursday, April 3',
        time: '03:30 PM',
        doctor: 'Dr. Mehta',
        location: 'Apollo Hospital, OPD',
        status: 'completed',
        type: 'Consultation',
    },
];

const FALLBACK_MED_SCHEDULE = [
    { id: 'med-fm', name: 'Metformin', dose: '1000mg', time: '08:00 AM', meal: 'After Breakfast', icon: 'solar:pill-bold', color: 'bg-primary/10 text-primary' },
    { id: 'med-as', name: 'Aspirin', dose: '75mg', time: '08:00 AM', meal: 'After Breakfast', icon: 'solar:pill-bold', color: 'bg-tertiary/10 text-tertiary' },
    { id: 'med-am', name: 'Amlodipine', dose: '5mg', time: '01:00 PM', meal: 'Before Lunch', icon: 'solar:pill-bold', color: 'bg-secondary/10 text-secondary' },
    { id: 'med-li', name: 'Lisinopril', dose: '10mg', time: '01:30 PM', meal: 'After Lunch', icon: 'solar:pill-bold', color: 'bg-primary/10 text-primary' },
    { id: 'med-at', name: 'Atorvastatin', dose: '20mg', time: '09:00 PM', meal: 'Before Bed', icon: 'solar:moon-bold', color: 'bg-slate-100 text-slate-500' },
];

const statusConfig: Record<AppointmentStatus, { label: string; classes: string; dot: string; timelineColor: string }> = {
    upcoming: { label: 'Upcoming', classes: 'bg-primary/8 text-primary', dot: 'bg-primary', timelineColor: 'bg-primary' },
    scheduled: { label: 'Upcoming', classes: 'bg-primary/8 text-primary', dot: 'bg-primary', timelineColor: 'bg-primary' },
    today: { label: 'Today', classes: 'bg-secondary/10 text-secondary', dot: 'bg-secondary', timelineColor: 'bg-secondary' },
    completed: { label: 'Completed', classes: 'bg-slate-100 text-slate-400', dot: 'bg-slate-300', timelineColor: 'bg-slate-300' },
};

interface ScheduleViewProps {
    agentChat?: UseAgentChatReturn;
    onViewChange?: (view: string) => void;
}

const ScheduleView: React.FC<ScheduleViewProps> = ({ agentChat, onViewChange }) => {
    const [appointments, setAppointments] = useState<Appointment[]>(FALLBACK_APPOINTMENTS);
    const [medSchedule, setMedSchedule] = useState(FALLBACK_MED_SCHEDULE);
    const [takenMeds, setTakenMeds] = useState<Set<string>>(new Set());
    const [showAddModal, setShowAddModal] = useState(false);
    const [newApptTitle, setNewApptTitle] = useState('');
    const [newApptDate, setNewApptDate] = useState('');
    const [newApptTime, setNewApptTime] = useState('');

    useEffect(() => {
        let mounted = true;

        async function loadData() {
            const [appts, meds] = await Promise.all([
                fetchAppointmentsApi(),
                fetchActiveMedications(),
            ]);

            if (!mounted) return;

            if (appts?.length) {
                setAppointments(appts.map((a) => ({
                    id: a.id,
                    title: a.title,
                    date: a.date,
                    time: a.time,
                    doctor: a.doctor,
                    location: a.location,
                    status: (a.status as AppointmentStatus) || 'upcoming',
                    type: a.type,
                    note: a.note,
                })));
            }

            if (meds?.length) {
                setMedSchedule(meds.map((m) => ({
                    id: m.id,
                    name: m.name,
                    dose: m.dose,
                    time: m.schedule || '',
                    meal: m.schedule || '',
                    icon: 'solar:pill-bold',
                    color: 'bg-primary/10 text-primary',
                })));
                // Seed taken state from API
                const alreadyTaken = new Set<string>();
                meds.forEach((m) => { if (m.taken_today) alreadyTaken.add(m.id); });
                setTakenMeds(alreadyTaken);
            }
        }

        loadData();
        return () => { mounted = false; };
    }, []);

    const upcoming = appointments.filter(a => a.status !== 'completed');
    const past = appointments.filter(a => a.status === 'completed');

    return (
        <div className="lg:ml-72 pt-16 pb-28 px-6 md:px-10 min-h-dvh">

            {/* Header */}
            <div className="mb-8 animate-reveal">
                <h1 className="text-3xl md:text-4xl font-extrabold text-slate-900 tracking-tight">
                    {t('your_schedule')}
                </h1>
                <p className="text-slate-600 mt-1.5 font-medium text-base">
                    Upcoming appointments and daily medication plan.
                </p>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-12 gap-5">

                {/* Upcoming Appointments with Timeline */}
                <div className="lg:col-span-8 space-y-0">
                    <div className="flex items-center justify-between mb-4 animate-reveal stagger-1">
                        <h2 className="text-base font-bold text-slate-700 tracking-tight">
                            {t('upcoming_appointments')}
                        </h2>
                        <button
                            className="flex items-center gap-2 px-4 py-2 rounded-full bg-primary/8 text-primary font-semibold text-sm hover:bg-primary/15 hover:shadow-sm hover:-translate-y-0.5 transition-all duration-300 cursor-pointer min-h-[48px]"
                            aria-label="Add new appointment"
                            onClick={() => setShowAddModal(true)}
                        >
                            <Icon icon="solar:add-circle-linear" width={16} />
                            Add Appointment
                        </button>
                    </div>

                    {/* Timeline container */}
                    <div className="relative">
                        {/* Vertical timeline line */}
                        <div className="absolute left-[32px] top-4 bottom-4 w-[2px] bg-gradient-to-b from-primary/30 via-primary/15 to-transparent pointer-events-none" />

                        <div className="space-y-4">
                            {upcoming.map((appt, i) => (
                                <AppointmentCard key={appt.id} appt={appt} index={i + 1} isFirst={i === 0} />
                            ))}
                        </div>
                    </div>

                    {/* Past appointments */}
                    <div className="flex items-center gap-3 mt-10 mb-4 animate-reveal stagger-4">
                        <h2 className="text-base font-bold text-slate-400 tracking-tight">{t('past_appointments')}</h2>
                        <div className="flex-1 h-px bg-surface-container-high" />
                    </div>

                    <div className="relative">
                        {/* Gray timeline for past */}
                        <div className="absolute left-[32px] top-4 bottom-4 w-[2px] bg-slate-200 pointer-events-none" />

                        <div className="space-y-4">
                            {past.map((appt, i) => (
                                <AppointmentCard key={appt.id} appt={appt} index={i + upcoming.length + 1} dimmed />
                            ))}
                        </div>
                    </div>
                </div>

                {/* Right sidebar — medication schedule */}
                <div className="lg:col-span-4 space-y-5">
                    <BentoCard stagger="stagger-2" className="hover-lift">
                        <div className="flex items-center gap-2.5 mb-6">
                            <Icon icon="solar:medicine-bold" width={20} className="text-primary" />
                            <h3 className="text-base font-bold text-slate-900 tracking-tight">
                                {t('daily_medication_plan')}
                            </h3>
                        </div>

                        <div className="space-y-3">
                            {medSchedule.map((med, i) => {
                                const isTaken = med.id ? takenMeds.has(med.id) : false;
                                return (
                                    <div
                                        key={med.id || i}
                                        className={cn(
                                            'flex items-center gap-3 p-3.5 rounded-2xl',
                                            'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                                            'hover:bg-surface-container-low hover:-translate-y-0.5 hover:shadow-sm',
                                            isTaken && 'opacity-60',
                                        )}
                                    >
                                        <div className={cn('w-9 h-9 rounded-xl flex items-center justify-center shrink-0', med.color)}>
                                            <Icon icon={med.icon} width={18} />
                                        </div>
                                        <div className="flex-1 min-w-0">
                                            <p className="font-semibold text-sm text-slate-900 tracking-tight truncate">
                                                {med.name}
                                                <span className="text-slate-500 font-normal ml-1.5">{med.dose}</span>
                                            </p>
                                            <p className="text-sm text-slate-600 mt-0.5">{med.meal}</p>
                                        </div>
                                        <span className="text-sm font-semibold text-slate-500 shrink-0">
                                            {med.time}
                                        </span>
                                        {med.id && (
                                            <button
                                                onClick={async () => {
                                                    if (isTaken) return;
                                                    const ok = await markMedicationTaken(med.id!);
                                                    if (ok) setTakenMeds((prev) => new Set(prev).add(med.id!));
                                                }}
                                                disabled={isTaken}
                                                className={cn(
                                                    'shrink-0 w-8 h-8 rounded-xl flex items-center justify-center transition-all duration-300',
                                                    isTaken
                                                        ? 'bg-secondary/15 text-secondary cursor-default'
                                                        : 'bg-primary/8 text-primary hover:bg-primary/20 hover:scale-110 cursor-pointer',
                                                )}
                                                aria-label={isTaken ? `${med.name} taken` : `Mark ${med.name} as taken`}
                                                title={isTaken ? t('taken') : t('mark_taken')}
                                            >
                                                <Icon icon={isTaken ? 'solar:check-circle-bold' : 'solar:check-circle-linear'} width={18} />
                                            </button>
                                        )}
                                    </div>
                                );
                            })}
                        </div>
                    </BentoCard>

                    {/* Quick stats */}
                    <BentoCard stagger="stagger-3" className="hover-lift">
                        <div className="flex items-center gap-2.5 mb-5">
                            <Icon icon="solar:chart-square-bold" width={20} className="text-tertiary" />
                            <h3 className="text-base font-bold text-slate-900 tracking-tight">
                                {t('this_month')}
                            </h3>
                        </div>
                        <div className="grid grid-cols-2 gap-3">
                            {[
                                { label: 'Appointments', value: String(appointments.length), icon: 'solar:calendar-bold', color: 'text-primary bg-primary/10' },
                                { label: 'Completed', value: String(past.length), icon: 'solar:check-circle-bold', color: 'text-secondary bg-secondary/10' },
                                { label: 'Medications', value: String(medSchedule.length), icon: 'solar:pill-bold', color: 'text-primary bg-primary/10' },
                                { label: 'Adherence (est.)', value: '92%', icon: 'solar:shield-check-bold', color: 'text-secondary bg-secondary/10' },
                            ].map(({ label, value, icon, color }) => (
                                <div key={label} className="bg-surface-container-low rounded-2xl p-4 hover-lift">
                                    <div className={cn('w-8 h-8 rounded-xl flex items-center justify-center mb-3', color)}>
                                        <Icon icon={icon} width={16} />
                                    </div>
                                    <p className="metric-value text-2xl font-black text-slate-900">{value}</p>
                                    <p className="text-sm text-slate-600 mt-0.5">{label}</p>
                                </div>
                            ))}
                        </div>
                    </BentoCard>
                </div>
            </div>

            {/* ── Add Appointment Modal ─────────────────────────────── */}
            {showAddModal && (
                <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm" onClick={() => setShowAddModal(false)}>
                    <div
                        className="bg-white rounded-3xl shadow-2xl p-8 w-full max-w-md mx-4 animate-reveal"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-10 h-10 rounded-xl bg-primary/10 flex items-center justify-center">
                                <Icon icon="solar:calendar-bold" width={20} className="text-primary" />
                            </div>
                            <h3 className="text-lg font-bold text-slate-900 tracking-tight">New Appointment</h3>
                        </div>
                        <div className="space-y-4">
                            <div>
                                <label className="text-sm font-semibold text-slate-600 mb-1.5 block">Appointment Title</label>
                                <input
                                    type="text"
                                    lang="en"
                                    value={newApptTitle}
                                    onChange={(e) => setNewApptTitle(e.target.value)}
                                    placeholder="e.g. Follow-up with Dr. Mehta"
                                    className="w-full border border-slate-200 rounded-2xl px-4 py-3 text-base focus:outline-none focus:border-primary/30 focus:shadow-[0_0_0_4px_rgba(28,110,242,0.07)] placeholder:text-slate-300 transition-all"
                                    autoFocus
                                />
                            </div>
                            <div>
                                <label className="text-sm font-semibold text-slate-600 mb-1.5 block">Date (YYYY-MM-DD)</label>
                                <input
                                    type="text"
                                    value={newApptDate}
                                    onChange={(e) => setNewApptDate(e.target.value)}
                                    placeholder="2026-04-15"
                                    className="w-full border border-slate-200 rounded-2xl px-4 py-3 text-base focus:outline-none focus:border-primary/30 focus:shadow-[0_0_0_4px_rgba(28,110,242,0.07)] placeholder:text-slate-300 transition-all"
                                />
                            </div>
                            <div>
                                <label className="text-sm font-semibold text-slate-600 mb-1.5 block">Time (HH:MM)</label>
                                <input
                                    type="text"
                                    value={newApptTime}
                                    onChange={(e) => setNewApptTime(e.target.value)}
                                    placeholder="14:00"
                                    className="w-full border border-slate-200 rounded-2xl px-4 py-3 text-base focus:outline-none focus:border-primary/30 focus:shadow-[0_0_0_4px_rgba(28,110,242,0.07)] placeholder:text-slate-300 transition-all"
                                />
                            </div>
                        </div>
                        <div className="flex gap-3 mt-6">
                            <button
                                onClick={() => {
                                    setNewApptTitle('');
                                    setNewApptDate('');
                                    setNewApptTime('');
                                    setShowAddModal(false);
                                }}
                                className="flex-1 py-3 rounded-2xl border border-slate-200 text-slate-600 font-semibold text-sm hover:bg-slate-50 transition-all"
                            >
                                {t('cancel')}
                            </button>
                            <button
                                onClick={() => {
                                    const title = newApptTitle.trim();
                                    if (!title) return;
                                    const parts = [title];
                                    if (newApptDate) parts.push(`on ${newApptDate}`);
                                    if (newApptTime) parts.push(`at ${newApptTime}`);
                                    // 에이전트에게 Google Calendar 이벤트 생성 요청
                                    agentChat?.sendMessage(
                                        `Please book an appointment and create a Google Calendar event: ${parts.join(' ')}`,
                                    );
                                    // 프론트엔드 리스트에 즉시 반영
                                    setAppointments(prev => [...prev, {
                                        id: `new-${Date.now()}`,
                                        title,
                                        date: newApptDate || new Date().toISOString().split('T')[0],
                                        time: newApptTime || '10:00',
                                        doctor: '',
                                        location: '',
                                        type: 'appointment',
                                        status: 'upcoming',
                                        note: '',
                                        fasting_required: false,
                                    }]);
                                    setNewApptTitle('');
                                    setNewApptDate('');
                                    setNewApptTime('');
                                    setShowAddModal(false);
                                    // Home 채팅으로 이동하여 에이전트 응답 확인
                                    if (onViewChange) onViewChange('home');
                                }}
                                disabled={!newApptTitle.trim()}
                                className="flex-1 py-3 rounded-2xl bg-primary text-white font-semibold text-sm hover:bg-primary/90 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                            >
                                {t('book_appointment')}
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

/* ── Appointment Card with Timeline ──────────────────────────────────────── */

const AppointmentCard: React.FC<{ appt: Appointment; index: number; dimmed?: boolean; isFirst?: boolean }> = ({
    appt, index, dimmed, isFirst,
}) => {
    const cfg = statusConfig[appt.status];
    const isToday = appt.status === 'today';

    return (
        <div
            style={{ animationDelay: `${index * 70}ms` }}
            className={cn(
                'animate-reveal relative pl-16',
                dimmed && 'opacity-70 grayscale-[30%]',
            )}
        >
            {/* Timeline dot */}
            <div className={cn(
                'absolute left-[26px] top-6 w-[14px] h-[14px] rounded-full border-2 border-white z-10',
                isToday ? 'bg-secondary' : dimmed ? 'bg-slate-300' : cfg.timelineColor,
                isToday && 'ring-4 ring-secondary/20 animate-pulse',
                isFirst && !dimmed && 'ring-4 ring-primary/20',
            )} />

            <div
                className={cn(
                    'card-outer spring group',
                    'transition-all duration-500 ease-[cubic-bezier(0.16,1,0.3,1)]',
                    'hover:-translate-y-0.5 hover:shadow-[0_12px_40px_-12px_rgba(28,110,242,0.12)]',
                    isFirst && !dimmed && 'ring-2 ring-primary/15',
                )}
            >
                <div className="card-inner p-5">
                    <div className="flex items-start gap-4">
                        {/* Date badge */}
                        <div className="shrink-0 bg-primary/8 rounded-2xl p-3 text-center min-w-[52px]">
                            <Icon icon="solar:calendar-bold" width={20} className="text-primary mx-auto" />
                            <p className="text-sm font-bold text-primary mt-1 uppercase tracking-wide">
                                {appt.date.split(',')[0].slice(0, 3)}
                            </p>
                        </div>

                        <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2 flex-wrap mb-1.5">
                                <h3 className="font-bold text-base text-slate-900 tracking-tight">
                                    {appt.title}
                                </h3>
                                <div className="flex items-center gap-1.5">
                                    <span className={cn('w-1.5 h-1.5 rounded-full', cfg.dot)} />
                                    <span className={cn('text-sm font-bold uppercase tracking-wide px-2 py-0.5 rounded-full', cfg.classes)}>
                                        {cfg.label}
                                    </span>
                                </div>
                            </div>

                            <div className="flex flex-wrap gap-x-4 gap-y-1">
                                <span className="flex items-center gap-1.5 text-sm text-slate-500">
                                    <Icon icon="solar:clock-circle-linear" width={13} />
                                    {appt.date} · {appt.time}
                                </span>
                                <span className="flex items-center gap-1.5 text-sm text-slate-500">
                                    <Icon icon="solar:user-linear" width={13} />
                                    {appt.doctor}
                                </span>
                            </div>

                            <div className="flex items-center gap-1.5 mt-1.5 text-sm text-slate-500">
                                <Icon icon="solar:map-point-linear" width={13} className="shrink-0" />
                                <span className="truncate">{appt.location}</span>
                            </div>

                            {appt.note && (
                                <div className="mt-3 flex items-center gap-2 bg-tertiary-container/50 px-3 py-2 rounded-xl">
                                    <Icon icon="solar:danger-triangle-bold" width={13} className="text-tertiary shrink-0" />
                                    <p className="text-sm font-semibold text-tertiary">{appt.note}</p>
                                </div>
                            )}
                        </div>

                    </div>
                </div>
            </div>
        </div>
    );
};

export default ScheduleView;
