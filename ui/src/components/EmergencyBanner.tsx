import React, { useState } from 'react';
import { Icon } from '@iconify/react';
import { cn } from '@/src/lib/utils';
import { t } from '../lib/i18n';

interface EmergencyBannerProps {
    type: 'hypertensive_crisis' | 'hypoglycemia' | 'hyperglycemia';
    message: string;
    value: string;
}

const EmergencyBanner: React.FC<EmergencyBannerProps> = ({ type, message, value }) => {
    const [dismissed, setDismissed] = useState(false);

    if (dismissed) return null;

    const typeLabels: Record<EmergencyBannerProps['type'], string> = {
        hypertensive_crisis: 'Hypertensive Crisis',
        hypoglycemia: 'Hypoglycemia',
        hyperglycemia: 'Hyperglycemia',
    };

    return (
        <div
            role="alert"
            aria-live="assertive"
            className={cn(
                'fixed top-0 left-0 right-0 z-[100]',
                'bg-red-600 text-white',
                'border-l-4 border-red-800',
            )}
        >
            <div className="max-w-7xl mx-auto px-4 py-3 flex items-center justify-between gap-4">
                <div className="flex items-center gap-3 min-w-0">
                    <Icon
                        icon="solar:danger-triangle-bold"
                        width={28}
                        className="text-white shrink-0"
                    />
                    <div className="min-w-0">
                        <p className="text-lg font-bold leading-tight">
                            {typeLabels[type]}: {value}
                        </p>
                        <p className="text-sm text-red-100 leading-snug truncate">
                            {message}
                        </p>
                    </div>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                    <a
                        href="tel:112"
                        className={cn(
                            'inline-flex items-center gap-2 px-5 py-2.5 rounded-full',
                            'bg-white text-red-600 font-bold text-sm',
                            'hover:bg-red-50 active:scale-95 transition-transform',
                            'min-h-[48px]',
                        )}
                    >
                        <Icon icon="solar:phone-bold" width={18} />
                        {t('call_emergency')}
                    </a>
                    <button
                        onClick={() => {
                            if (window.confirm('This is a critical health alert. I have read and understood this warning.')) {
                                setDismissed(true);
                            }
                        }}
                        className={cn(
                            'p-2 rounded-full hover:bg-red-500 transition-colors',
                            'min-h-[48px] min-w-[48px] flex items-center justify-center',
                        )}
                        aria-label="Dismiss emergency alert"
                    >
                        <Icon icon="solar:close-circle-bold" width={24} />
                    </button>
                </div>
            </div>
        </div>
    );
};

export default EmergencyBanner;
