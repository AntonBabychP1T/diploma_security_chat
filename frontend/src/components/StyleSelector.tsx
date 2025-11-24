import React from 'react';
import clsx from 'clsx';
import { Briefcase, Coffee, MessageCircle, Zap } from 'lucide-react';

interface Props {
    value: string;
    onChange: (value: string) => void;
}

export const StyleSelector: React.FC<Props> = ({ value, onChange }) => {
    const styles = [
        { id: 'default', label: 'Default', icon: Zap },
        { id: 'professional', label: 'Pro', icon: Briefcase },
        { id: 'friendly', label: 'Friendly', icon: MessageCircle },
        { id: 'casual', label: 'Casual', icon: Coffee },
    ];

    return (
        <div className="flex items-center bg-gray-800/50 p-1 rounded-lg border border-white/5">
            {styles.map((style) => {
                const Icon = style.icon;
                const isActive = value === style.id;
                return (
                    <button
                        key={style.id}
                        onClick={() => onChange(style.id)}
                        className={clsx(
                            "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-all duration-200",
                            isActive
                                ? "bg-gray-700 text-white shadow-sm"
                                : "text-gray-400 hover:text-gray-200 hover:bg-white/5"
                        )}
                        title={style.label}
                    >
                        <Icon size={12} />
                        <span className="hidden sm:inline">{style.label}</span>
                    </button>
                );
            })}
        </div>
    );
};
