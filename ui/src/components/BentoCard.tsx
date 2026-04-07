import React, { useEffect, useRef } from 'react';
import { cn } from '@/src/lib/utils';

interface BentoCardProps {
    children: React.ReactNode;
    className?: string;
    innerClassName?: string;
    title?: string;
    subtitle?: string;
    icon?: React.ReactNode;
    badge?: string;
    badgeColor?: string;
    /** Skip scroll-reveal animation (e.g. for nested cards) */
    noReveal?: boolean;
    /** Stagger delay class, e.g. 'stagger-1' */
    stagger?: string;
}

const BentoCard: React.FC<BentoCardProps> = ({
    children,
    className,
    innerClassName,
    title,
    subtitle,
    icon,
    badge,
    badgeColor = 'bg-primary',
    noReveal = false,
    stagger,
}) => {
    const ref = useRef<HTMLDivElement>(null);

    useEffect(() => {
        if (noReveal || !ref.current) return;
        const el = ref.current;
        const observer = new IntersectionObserver(
            ([entry]) => {
                if (entry.isIntersecting) {
                    el.style.animation = `fadeInUp 0.6s cubic-bezier(0.16, 1, 0.3, 1) forwards`;
                    observer.unobserve(el);
                }
            },
            { threshold: 0.1, rootMargin: '0px 0px -40px 0px' }
        );
        observer.observe(el);
        return () => observer.disconnect();
    }, [noReveal]);

    return (
        /* Outer shell — the "aluminum tray" */
        <div
            ref={ref}
            style={noReveal ? undefined : { opacity: 0 }}
            className={cn(
                'card-outer spring',
                stagger,
                className,
            )}
        >
            {/* Inner core — the "glass plate" */}
            <div className={cn('card-inner p-7', innerClassName)}>
                {(title || icon || badge) && (
                    <div className="flex justify-between items-start mb-5">
                        <div>
                            {icon && <div className="mb-3">{icon}</div>}
                            {title && (
                                <h3 className="text-lg font-bold text-slate-900 tracking-tight">
                                    {title}
                                </h3>
                            )}
                            {subtitle && (
                                <p className="text-slate-600 text-base mt-0.5">{subtitle}</p>
                            )}
                        </div>
                        {badge && (
                            <span
                                className={cn(
                                    'text-white text-xs font-bold px-3 py-1 rounded-full uppercase tracking-wider',
                                    badgeColor,
                                )}
                            >
                                {badge}
                            </span>
                        )}
                    </div>
                )}
                {children}
            </div>
        </div>
    );
};

export default BentoCard;
