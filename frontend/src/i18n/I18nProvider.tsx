import React, { createContext, useContext, useEffect, useMemo, useState } from 'react';
import { defaultLanguage, Language, languages, translations } from './translations';

type Vars = Record<string, string | number>;

interface I18nContextType {
    language: Language;
    setLanguage: (language: Language) => void;
    t: (key: string, vars?: Vars) => string;
    translateApiError: (message: unknown, fallbackKey?: string) => string;
}

const I18nContext = createContext<I18nContextType | null>(null);

const storageKey = 'ui_language';

const apiErrorKeys: Record<string, string> = {
    'Email already registered': 'errors.emailRegistered',
    'Invalid invite code': 'errors.invalidInvite',
    'Invite code already used': 'errors.inviteUsed',
    'Invite code expired': 'errors.inviteExpired',
    'Incorrect username or password': 'errors.badCredentials',
    'Could not validate credentials': 'errors.invalidCredentials',
    'Not authorized': 'errors.notAuthorized',
    'Current password is incorrect': 'errors.currentPasswordIncorrect',
    'Failed to update password': 'errors.passwordUpdateFailed',
    'Chat not found': 'errors.chatNotFound',
    'Message not found': 'errors.messageNotFound',
};

const interpolate = (template: string, vars?: Vars) => {
    if (!vars) return template;
    return Object.entries(vars).reduce(
        (value, [key, replacement]) => value.split(`{{${key}}}`).join(String(replacement)),
        template
    );
};

const getInitialLanguage = (): Language => {
    if (typeof window === 'undefined') return defaultLanguage;
    const saved = window.localStorage.getItem(storageKey);
    return languages.includes(saved as Language) ? (saved as Language) : defaultLanguage;
};

export const I18nProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [language, setLanguageState] = useState<Language>(getInitialLanguage);

    useEffect(() => {
        document.documentElement.lang = language;
        window.localStorage.setItem(storageKey, language);
    }, [language]);

    const value = useMemo<I18nContextType>(() => {
        const t = (key: string, vars?: Vars) => {
            const template = translations[language][key] ?? translations.en[key] ?? key;
            return interpolate(template, vars);
        };

        const translateApiError = (message: unknown, fallbackKey = 'common.error') => {
            if (typeof message !== 'string' || !message.trim()) return t(fallbackKey);
            const key = apiErrorKeys[message];
            if (key) return t(key);
            return language === 'en' ? message : t(fallbackKey);
        };

        return {
            language,
            setLanguage: setLanguageState,
            t,
            translateApiError,
        };
    }, [language]);

    return (
        <I18nContext.Provider value={value}>
            {children}
        </I18nContext.Provider>
    );
};

export const useI18n = () => {
    const context = useContext(I18nContext);
    if (!context) throw new Error('useI18n must be used within I18nProvider');
    return context;
};
