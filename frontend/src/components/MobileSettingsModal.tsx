import React from 'react';
import { X, Bot, Swords, Settings2 } from 'lucide-react';
import { StyleSelector } from './StyleSelector';
import clsx from 'clsx';

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
    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center p-0 sm:p-4">
            {/* Backdrop */}
            <div
                className="absolute inset-0 bg-black/60 backdrop-blur-sm animate-in fade-in duration-200"
                onClick={onClose}
            />

            {/* Modal Content */}
            <div className="relative w-full max-w-md bg-gray-900 border-t sm:border border-white/10 rounded-t-2xl sm:rounded-2xl shadow-2xl animate-in slide-in-from-bottom duration-300">
                <div className="flex items-center justify-between p-4 border-b border-white/5">
                    <div className="flex items-center gap-2 text-white font-medium">
                        <Settings2 size={18} />
                        <span>Chat Settings</span>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-gray-400 hover:text-white bg-white/5 hover:bg-white/10 rounded-full transition-colors"
                    >
                        <X size={18} />
                    </button>
                </div>

                <div className="p-4 space-y-6 max-h-[80vh] overflow-y-auto">
                    {/* Mode Selection */}
                    <div className="space-y-3">
                        <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Mode</label>
                        <div className="grid grid-cols-2 gap-2 bg-gray-950/50 p-1 rounded-xl border border-white/5">
                            <button
                                onClick={() => onArenaModeChange(false)}
                                className={clsx(
                                    "flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all",
                                    !isArenaMode ? "bg-primary-600 text-white shadow-lg" : "text-gray-400 hover:text-white"
                                )}
                            >
                                <Bot size={16} />
                                <span>Standard</span>
                            </button>
                            <button
                                onClick={() => onArenaModeChange(true)}
                                className={clsx(
                                    "flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all",
                                    isArenaMode ? "bg-primary-600 text-white shadow-lg" : "text-gray-400 hover:text-white"
                                )}
                            >
                                <Swords size={16} />
                                <span>Arena</span>
                            </button>
                        </div>
                    </div>

                    {isArenaMode ? (
                        /* Arena Mobile Config */
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Model A</label>
                                <select
                                    value={arenaModelA}
                                    onChange={(e) => onArenaModelAChange(e.target.value)}
                                    className="w-full bg-gray-800 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-primary-500 transition-colors appearance-none"
                                >
                                    {modelOptions.map((m) => (
                                        <option key={m.id} value={m.id}>{m.label}</option>
                                    ))}
                                </select>
                            </div>
                            <div className="flex justify-center text-primary-500 font-bold text-sm">VS</div>
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Model B</label>
                                <select
                                    value={arenaModelB}
                                    onChange={(e) => onArenaModelBChange(e.target.value)}
                                    className="w-full bg-gray-800 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-primary-500 transition-colors appearance-none"
                                >
                                    {modelOptions.map((m) => (
                                        <option key={m.id} value={m.id}>{m.label}</option>
                                    ))}
                                </select>
                            </div>
                        </div>
                    ) : (
                        /* Standard Mobile Config */
                        <div className="space-y-4">
                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Provider</label>
                                <div className="grid grid-cols-2 gap-2">
                                    {providerOptions.map((p) => (
                                        <button
                                            key={p.id}
                                            onClick={() => onProviderChange(p.id)}
                                            className={clsx(
                                                "px-4 py-3 rounded-xl border text-sm font-medium transition-all",
                                                provider === p.id
                                                    ? "bg-primary-500/10 border-primary-500 text-primary-400"
                                                    : "bg-gray-800/50 border-white/5 text-gray-400 hover:bg-gray-800"
                                            )}
                                        >
                                            {p.label}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="space-y-2">
                                <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Model</label>
                                <select
                                    value={model}
                                    onChange={(e) => onModelChange(e.target.value)}
                                    className="w-full bg-gray-800 border border-white/10 rounded-xl px-4 py-3 text-white outline-none focus:border-primary-500 transition-colors appearance-none"
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
                        <label className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Response Style</label>
                        <div className="bg-gray-800/30 rounded-xl p-2 border border-white/5">
                            <StyleSelector value={style} onChange={onStyleChange} />
                        </div>
                    </div>
                </div>

                <div className="p-4 border-t border-white/5 bg-gray-900/50">
                    <button
                        onClick={onClose}
                        className="w-full bg-gray-100 hover:bg-white text-gray-900 font-semibold py-3.5 rounded-xl transition-colors"
                    >
                        Apply Changes
                    </button>
                </div>
            </div>
        </div>
    );
};
