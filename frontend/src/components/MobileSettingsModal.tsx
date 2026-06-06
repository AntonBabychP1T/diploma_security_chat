import React from 'react';
import { X, Bot, Swords, Settings2 } from 'lucide-react';
import { StyleSelector } from './StyleSelector';
import clsx from 'clsx';
import { useI18n } from '../i18n/I18nProvider';

interface Option {
    id: string;
    label: string;
}

interface Props {
    isOpen: boolean;
    onClose: () => void;
    style: string;
    provider: string;
    model: string;
    providerOptions: Option[];
    modelOptions: Option[];
    arenaModelOptions: Option[];
    onStyleChange: (style: string) => void;
    onProviderChange: (provider: string) => void;
    onModelChange: (model: string) => void;
    isArenaMode: boolean;
    onArenaModeChange: (enabled: boolean) => void;
    arenaModelA: string;
    arenaModelB: string;
    onArenaModelAChange: (model: string) => void;
    onArenaModelBChange: (model: string) => void;
}

export const MobileSettingsModal: React.FC<Props> = ({
    isOpen,
    onClose,
    style,
    provider,
    model,
    providerOptions,
    modelOptions,
    arenaModelOptions,
    onStyleChange,
    onProviderChange,
    onModelChange,
    isArenaMode,
    onArenaModeChange,
    arenaModelA,
    arenaModelB,
    onArenaModelAChange,
    onArenaModelBChange
}) => {
    const { t } = useI18n();

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
                onClick={onClose}
            />

            {/* Modal Content */}
            <div className="relative w-full max-w-md bg-white border-t sm:border border-gray-200 rounded-t-2xl sm:rounded-2xl shadow-2xl animate-in slide-in-from-bottom duration-300 dark:bg-gray-900 dark:border-white/10">
                <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-white/5">
                    <div className="flex items-center gap-2 text-gray-950 font-medium dark:text-white">
                        <Settings2 size={18} />
                        <span>{t('chat.settings')}</span>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-gray-500 hover:text-gray-950 bg-gray-100 hover:bg-gray-200 rounded-full transition-colors dark:text-gray-400 dark:hover:text-white dark:bg-white/5 dark:hover:bg-white/10"
                    >
                        <X size={18} />
                    </button>
                </div>

                <div className="p-4 space-y-6 max-h-[80vh] overflow-y-auto">
                    {/* Mode Selection */}
                    <div className="space-y-3">
                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('chat.mode')}</label>
                        <div className="grid grid-cols-2 gap-2 bg-gray-100 p-1 rounded-xl border border-gray-200 dark:bg-gray-950/50 dark:border-white/5">
                            <button
                                onClick={() => onArenaModeChange(false)}
                                className={clsx(
                                    "flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all",
                                    !isArenaMode ? "bg-primary-600 text-white shadow-lg" : "text-gray-500 hover:text-gray-950 dark:text-gray-400 dark:hover:text-white"
                                )}
                            >
                                <Bot size={16} />
                                <span>{t('chat.standard')}</span>
                            </button>
                            <button
                                onClick={() => onArenaModeChange(true)}
                                className={clsx(
                                    "flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all",
                                    isArenaMode ? "bg-primary-600 text-white shadow-lg" : "text-gray-500 hover:text-gray-950 dark:text-gray-400 dark:hover:text-white"
                                )}
                            >
                                <Swords size={16} />
                                <span>{t('chat.arena')}</span>
                            </button>
                        </div>
                    </div>

                    {isArenaMode ? (
                        /* Arena Mobile Config */
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('chat.modelA')}</label>
                                <select
                                    value={arenaModelA}
                                    onChange={(e) => onArenaModelAChange(e.target.value)}
                                    className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-900 outline-none focus:border-primary-500 transition-colors appearance-none dark:bg-gray-800 dark:border-white/10 dark:text-white"
                                >
                                    {arenaModelOptions.map((m) => (
                                        <option key={m.id} value={m.id}>{m.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="flex justify-center text-primary-500 font-bold text-sm">VS</div>
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('chat.modelB')}</label>
                                <select
                                    value={arenaModelB}
                                    onChange={(e) => onArenaModelBChange(e.target.value)}
                                    className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-900 outline-none focus:border-primary-500 transition-colors appearance-none dark:bg-gray-800 dark:border-white/10 dark:text-white"
                                >
                                    {arenaModelOptions.map((m) => (
                                        <option key={m.id} value={m.id}>{m.label}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    ) : (
                        /* Standard Mobile Config */
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('chat.provider')}</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {providerOptions.map((p) => (
                                        <button
                                            key={p.id}
                                            onClick={() => onProviderChange(p.id)}
                                            className={clsx(
                                                "px-4 py-3 rounded-xl border text-sm font-medium transition-all",
                                                provider === p.id
                                                    ? "bg-primary-500/10 border-primary-500 text-primary-400"
                                                    : "bg-white border-gray-200 text-gray-500 hover:bg-gray-50 dark:bg-gray-800/50 dark:border-white/5 dark:text-gray-400 dark:hover:bg-gray-800"
                                            )}
                                        >
                                            {p.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('chat.model')}</label>
                                <select
                                    value={model}
                                    onChange={(e) => onModelChange(e.target.value)}
                                    className="w-full bg-white border border-gray-200 rounded-xl px-4 py-3 text-gray-900 outline-none focus:border-primary-500 transition-colors appearance-none dark:bg-gray-800 dark:border-white/10 dark:text-white"
                                >
                                    {modelOptions.map((m) => (
                                        <option key={m.id} value={m.id}>{m.label}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    )}

                    {/* Style Section */}
                    <div className="space-y-3">
                        <label className="text-xs font-semibold text-gray-500 uppercase tracking-wider dark:text-gray-400">{t('chat.responseStyle')}</label>
                        <div className="bg-gray-50 rounded-xl p-2 border border-gray-200 dark:bg-gray-800/30 dark:border-white/5">
                            <StyleSelector value={style} onChange={onStyleChange} />
                        </div>
                    </div>
                </div>

                <div className="p-4 border-t border-gray-200 bg-gray-50 dark:border-white/5 dark:bg-gray-900/50">
                    <button
                        onClick={onClose}
                        className="w-full bg-gray-100 hover:bg-white text-gray-900 font-semibold py-3.5 rounded-xl transition-colors"
                    >
                        {t('common.applyChanges')}
                    </button>
                </div>
            </div>
        </div>
    );
};
