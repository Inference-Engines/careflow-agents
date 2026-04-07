import React, { useState } from 'react';
import { Icon } from '@iconify/react';
import { cn } from '@/src/lib/utils';

interface DrugAlert {
    drug1: string;
    drug2: string;
    severity: 'CONTRAINDICATED' | 'HIGH' | 'MODERATE';
    description: string;
    source: string;
}

interface DrugInteractionAlertProps {
    alerts: DrugAlert[];
}

const severityConfig: Record<DrugAlert['severity'], { bg: string; badge: string; border: string; text: string }> = {
    CONTRAINDICATED: {
        bg: 'bg-red-50',
        badge: 'bg-red-600 text-white',
        border: 'border-red-200',
        text: 'text-red-800',
    },
    HIGH: {
        bg: 'bg-orange-50',
        badge: 'bg-orange-500 text-white',
        border: 'border-orange-200',
        text: 'text-orange-800',
    },
    MODERATE: {
        bg: 'bg-amber-50',
        badge: 'bg-amber-500 text-white',
        border: 'border-amber-200',
        text: 'text-amber-800',
    },
};

const DrugInteractionAlert: React.FC<DrugInteractionAlertProps> = ({ alerts }) => {
    const [expanded, setExpanded] = useState(false);

    if (!alerts.length) return null;

    const visibleAlerts = expanded ? alerts : [alerts[0]];
    const hasMore = alerts.length > 1;

    return (
        <div role="alert" className="space-y-3">
            {visibleAlerts.map((alert, i) => {
                const config = severityConfig[alert.severity];
                return (
                    <div
                        key={`${alert.drug1}-${alert.drug2}-${i}`}
                        className={cn(
                            'rounded-2xl border p-5',
                            config.bg,
                            config.border,
                        )}
                    >
                        <div className="flex items-start gap-3">
                            <Icon
                                icon="solar:danger-triangle-bold"
                                width={22}
                                className={cn('shrink-0 mt-0.5', config.text)}
                            />
                            <div className="flex-1 min-w-0">
                                <div className="flex items-center gap-2 flex-wrap mb-1.5">
                                    <span className={cn('font-bold text-sm', config.text)}>
                                        {alert.drug1} + {alert.drug2}
                                    </span>
                                    <span
                                        className={cn(
                                            'text-xs font-bold px-2 py-0.5 rounded-md uppercase tracking-wide',
                                            config.badge,
                                        )}
                                    >
                                        {alert.severity}
                                    </span>
                                </div>
                                <p className={cn('text-sm leading-relaxed', config.text)}>
                                    {alert.description}
                                </p>
                                <p className="text-xs text-slate-500 mt-2 font-medium">
                                    Source: {alert.source}
                                </p>
                            </div>
                        </div>
                    </div>
                );
            })}

            {hasMore && (
                <button
                    onClick={() => setExpanded((prev) => !prev)}
                    className={cn(
                        'flex items-center gap-1.5 text-sm font-semibold text-primary',
                        'hover:underline spring',
                    )}
                >
                    <Icon
                        icon={expanded ? 'solar:alt-arrow-up-linear' : 'solar:alt-arrow-down-linear'}
                        width={16}
                    />
                    {expanded
                        ? 'Show less'
                        : `Show ${alerts.length - 1} more interaction${alerts.length - 1 > 1 ? 's' : ''}`}
                </button>
            )}
        </div>
    );
};

export default DrugInteractionAlert;
