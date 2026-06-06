import React, { useState } from 'react';
import { StyleSelector } from './StyleSelector';
import { MobileSettingsModal } from './MobileSettingsModal';
import { Bot, Swords, Settings2 } from 'lucide-react';
import clsx from 'clsx';
import { useI18n } from '../i18n/I18nProvider';

interface Option {
    id: string;
    label: string;
}

interface Props {
    title: string;
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

export const ChatHeader: React.FC<Props> = ({
    title,
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
    const [isSettingsOpen, setIsSettingsOpen] = useState(false);

    return (
        <>
            <MobileSettingsModal
                isOpen={isSettingsOpen}
                onClose={() => setIsSettingsOpen(false)}
                style={style}
                provider={provider}
                model={model}
                providerOptions={providerOptions}
                modelOptions={modelOptions}
                arenaModelOptions={arenaModelOptions}
                onStyleChange={onStyleChange}
                onProviderChange={onProviderChange}
                onModelChange={onModelChange}
                isArenaMode={isArenaMode}
                onArenaModeChange={onArenaModeChange}
                arenaModelA={arenaModelA}
                arenaModelB={arenaModelB}
                onArenaModelAChange={onArenaModelAChange}
                onArenaModelBChange={onArenaModelBChange}
            />
            <div className="h-16 border-b border-gray-200 bg-white/80 backdrop-blur-md flex items-center justify-between px-4 sm:px-6 sticky top-0 z-10 dark:border-white/5 dark:bg-gray-900/50">
                <div className="flex items-center gap-4">
                    <h2 className="font-semibold text-lg text-gray-950 truncate max-w-md dark:text-gray-100">
                        {title}
                    </h2>
                </div>

                <div className="flex items-center gap-2 sm:gap-3">
                    {/* Mobile Settings Toggle */}
                    <button
                        onClick={() => setIsSettingsOpen(true)}
                        className="sm:hidden p-2 text-gray-500 hover:text-gray-950 bg-gray-100 hover:bg-gray-200 rounded-lg transition-colors dark:text-gray-400 dark:hover:text-white dark:bg-gray-800/50 dark:hover:bg-gray-700/50"
                    >
                        <Settings2 size={18} />
                    </button>

                    {/* Desktop Controls */}
                    <div className="hidden sm:flex items-center gap-2 bg-white border border-gray-200 rounded-xl px-3 py-2 transition-all duration-300 dark:bg-gray-800/50 dark:border-white/10">
                        <button
                            onClick={() => onArenaModeChange(!isArenaMode)}
                            className={clsx(
                                "p-1.5 rounded-lg transition-colors mr-2",
                                isArenaMode ? "bg-primary-500/15 text-primary-600 dark:bg-primary-500/20 dark:text-primary-400" : "hover:bg-gray-100 text-gray-500 dark:hover:bg-gray-700 dark:text-gray-400"
                            )}
                            title={t('chat.toggleArena')}
                        >
                            <Swords size={16} />
                        </button>

                        {isArenaMode ? (
                            <div className="flex items-center gap-2 animate-in fade-in slide-in-from-left-2 duration-300">
                                <select
                                    value={arenaModelA}
                                    onChange={(e) => onArenaModelAChange(e.target.value)}
                                    className="bg-transparent text-sm text-gray-900 outline-none max-w-[100px] sm:max-w-[140px] dark:text-white"
                                >
                                    {arenaModelOptions.map((m) => (
                                        <option key={m.id} value={m.id} className="bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100">
                                            {m.label}
                                        </option>
                                    ))}
                                </select>
                                <span className="text-gray-500 font-bold">VS</span>
                                <select
                                    value={arenaModelB}
                                    onChange={(e) => onArenaModelBChange(e.target.value)}
                                    className="bg-transparent text-sm text-gray-900 outline-none max-w-[100px] sm:max-w-[140px] dark:text-white"
                                >
                                    {arenaModelOptions.map((m) => (
                                        <option key={m.id} value={m.id} className="bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100">
                                            {m.label}
                                        </option>
                                    ))}
                                </select>
                            </div>
                        ) : (
                            <>
                                <Bot size={14} className="text-primary-400" />
                                <select
                                    value={provider}
                                    onChange={(e) => onProviderChange(e.target.value)}
                                    className="bg-transparent text-sm text-gray-900 outline-none dark:text-white"
                                >
                                    {providerOptions.map((p) => (
                                        <option key={p.id} value={p.id} className="bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100">
                                            {p.label}
                                        </option>
                                    ))}
                                </select>
                                <span className="text-gray-500">/</span>
                                <select
                                    value={model}
                                    onChange={(e) => onModelChange(e.target.value)}
                                    className="bg-transparent text-sm text-gray-900 outline-none dark:text-white"
                                >
                                    {modelOptions.map((m) => (
                                        <option key={m.id} value={m.id} className="bg-white text-gray-900 dark:bg-gray-900 dark:text-gray-100">
                                            {m.label}
                                        </option>
                                    ))}
                                </select>
                            </>
                        )}
                    </div>
                    <div className="hidden sm:block">
                        <StyleSelector value={style} onChange={onStyleChange} />
                    </div>
                </div>
            </div>
        </>
    );
};
