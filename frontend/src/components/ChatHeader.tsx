import React from 'react';
import { StyleSelector } from './StyleSelector';
import { Bot, Sparkles } from 'lucide-react';

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
    onStyleChange: (style: string) => void;
    onProviderChange: (provider: string) => void;
    onModelChange: (model: string) => void;
    onSecretary?: () => void;
}

export const ChatHeader: React.FC<Props> = ({
    title,
    style,
    provider,
    model,
    providerOptions,
    modelOptions,
    onStyleChange,
    onProviderChange,
    onModelChange,
    onSecretary
}) => {
    return (
        <div className="h-16 border-b border-white/5 bg-gray-900/50 backdrop-blur-md flex items-center justify-between px-4 sm:px-6 sticky top-0 z-10">
            <div className="flex items-center gap-4">
                <h2 className="font-semibold text-lg text-gray-100 truncate max-w-md">
                    {title}
                </h2>
            </div>

            <div className="flex items-center gap-2 sm:gap-3">
                <div className="hidden sm:flex items-center gap-2 bg-gray-800/50 border border-white/10 rounded-xl px-3 py-2">
                    <Bot size={14} className="text-primary-400" />
                    <select
                        value={provider}
                        onChange={(e) => onProviderChange(e.target.value)}
                        className="bg-transparent text-sm text-white outline-none"
                    >
                        {providerOptions.map((p) => (
                            <option key={p.id} value={p.id} className="bg-gray-900 text-gray-100">
                                {p.label}
                            </option>
                        ))}
                    </select>
                    <span className="text-gray-500">/</span>
                    <select
                        value={model}
                        onChange={(e) => onModelChange(e.target.value)}
                        className="bg-transparent text-sm text-white outline-none"
                    >
                        {modelOptions.map((m) => (
                            <option key={m.id} value={m.id} className="bg-gray-900 text-gray-100">
                                {m.label}
                            </option>
                        ))}
                    </select>
                </div>
                <StyleSelector value={style} onChange={onStyleChange} />
                {onSecretary && (
                    <button
                        onClick={onSecretary}
                        className="flex items-center gap-1 px-3 py-2 bg-primary-600 hover:bg-primary-500 text-white rounded-lg text-sm font-medium transition-all shadow-primary-900/20 shadow"
                    >
                        <Sparkles size={14} />
                        <span className="hidden sm:inline">Секретар</span>
                        <span className="sm:hidden">AI</span>
                    </button>
                )}
            </div>
        </div>
    );
};
