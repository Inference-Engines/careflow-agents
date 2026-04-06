import React from 'react';
import { cn } from '@/src/lib/utils';

interface BentoCardProps {
    children: React.ReactNode;
    className?: string;
    title?: string;
    subtitle?: string;
    icon?: React.ReactNode;
    badge?: string;
    badgeColor?: string;
}

const BentoCard: React.FC<BentoCardProps> = ({
    children,
    className,
    title,
    subtitle,
    icon,
    badge,
    badgeColor = "bg-primary"
}) => {
    return (
        <div className={cn(
            "bg-white rounded-3xl p-8 shadow-[0_12px_40px_rgba(0,88,189,0.06)] relative overflow-hidden",
            className
        )}>
            {(title || icon || badge) && (
                <div className="flex justify-between items-start mb-6">
                    <div>
                        {icon && <div className="mb-4">{icon}</div>}
                        {title && <h3 className="text-xl font-bold text-slate-900">{title}</h3>}
                        {subtitle && <p className="text-slate-500 text-sm">{subtitle}</p>}
                    </div>
                    {badge && (
                        <div className={cn(
                            "text-white text-[10px] font-black px-3 py-1 rounded-full uppercase tracking-tighter",
                            badgeColor
                        )}>
                            {badge}
                        </div>
                    )}
                </div>
            )}
            {children}
        </div>
    );
};

export default BentoCard;
