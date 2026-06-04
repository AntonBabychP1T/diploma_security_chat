import React from 'react';
import { Languages } from 'lucide-react';
import clsx from 'clsx';
import { useI18n } from '../i18n/I18nProvider';
import { Language, languageLabels, languages } from '../i18n/translations';

interface Props {
    compact?: boolean;
}

export const LanguageSwitcher: React.FC<Props> = ({ compact = false }) => {
    const { language, setLanguage, t } = useI18n();

    return (
        <div
            className={clsx(
                "inline-flex items-center gap-1 rounded-lg border border-white/10 bg-gray-900/60 p-1",
                compact ? "text-xs" : "text-sm"
            )}
            title={t('language.switch')}
        >
            <Languages size={compact ? 14 : 16} className="ml-1 text-gray-400" />
            {languages.map((item: Language) => (
                <button
                    key={item}
                    type="button"
                    onClick={() => setLanguage(item)}
                    className={clsx(
                        "rounded-md px-2 py-1 font-medium transition-colors",
                        language === item
                            ? "bg-primary-600 text-white"
                            : "text-gray-400 hover:bg-white/5 hover:text-white"
                    )}
                >
                    {languageLabels[item]}
                </button>
            ))}
        </div>
    );
};
