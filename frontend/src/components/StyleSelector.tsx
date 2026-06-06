import React from 'react';
import clsx from 'clsx';
import { Briefcase, Coffee, MessageCircle, Zap } from 'lucide-react';
import { useI18n } from '../i18n/I18nProvider';

interface Props {
    value: string;
    onChange: (value: string) => void;
}

export const StyleSelector: React.FC<Props> = ({ value, onChange }) => {
    const { t } = useI18n();
    const styles = [
        { id: 'default', label: t('style.default'), icon: Zap },
        { id: 'professional', label: t('style.professional'), icon: Briefcase },
        { id: 'friendly', label: t('style.friendly'), icon: MessageCircle },
        { id: 'casual', label: t('style.casual'), icon: Coffee },
    ];

    return (
        <div className="flex items-center bg-white p-1 rounded-lg border border-gray-200 dark:bg-gray-800/50 dark:border-white/5">
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
                                ? "bg-gray-100 text-gray-950 shadow-sm dark:bg-gray-700 dark:text-white"
                                : "text-gray-500 hover:text-gray-900 hover:bg-gray-100 dark:text-gray-400 dark:hover:text-gray-200 dark:hover:bg-white/5"
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
