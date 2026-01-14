import React, { useState } from 'react';
import { api } from '../api/client';
import { Check, X, Loader2, Calendar, Archive, FileText, ChevronRight } from 'lucide-react';
import clsx from 'clsx';

interface ActionPayload {
    type: "ARCHIVE_PROMO" | "CREATE_DRAFT" | "CREATE_EVENT";
    payload_json: any;
    id: number;
    status: string; // PENDING, EXECUTED, etc.
}

interface Props {
    action: ActionPayload;
    onExecuted?: () => void;
}

export const ActionCard: React.FC<Props> = ({ action, onExecuted }) => {
    const [executing, setExecuting] = useState(false);
    const [status, setStatus] = useState(action.status || 'PENDING');
    const [error, setError] = useState("");

    const handleExecute = async () => {
        if (status !== 'PENDING') return;
        setExecuting(true);
        setError("");
        try {
            await api.post(`/digest/action/${action.id}/execute`, {});
            setStatus('EXECUTED');
            if (onExecuted) onExecuted();
        } catch (err: any) {
            console.error("Action execution failed", err);
            setError("Failed to execute");
        } finally {
            setExecuting(false);
        }
    };

    const renderContent = () => {
        const { type, payload } = action; // payload is actually inside payload_json usually, but check data structure
        // Wait, metadata.actions has "payload" which IS the payload_json
        const data = action.payload_json || action.payload || {}; // Handle both cases if inconsistency

        switch (type) {
            case "ARCHIVE_PROMO":
                return (
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-yellow-500/10 rounded-lg text-yellow-500">
                            <Archive size={18} />
                        </div>
                        <div>
                            <p className="font-medium text-gray-200">Архівувати промо ({data.message_ids?.length || 0})</p>
                            <p className="text-xs text-gray-500">Перемістити рекламні листи в архів</p>
                        </div>
                    </div>
                );
            case "CREATE_DRAFT":
                return (
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-blue-500/10 rounded-lg text-blue-500">
                            <FileText size={18} />
                        </div>
                        <div>
                            <p className="font-medium text-gray-200">Створити чернетку</p>
                            <p className="text-xs text-gray-500 line-clamp-1">To: {data.to} • Subj: {data.subject}</p>
                        </div>
                    </div>
                );
            case "CREATE_EVENT":
                return (
                    <div className="flex items-center gap-3">
                        <div className="p-2 bg-green-500/10 rounded-lg text-green-500">
                            <Calendar size={18} />
                        </div>
                        <div>
                            <p className="font-medium text-gray-200">Подія: {data.summary}</p>
                            <p className="text-xs text-gray-500">{new Date(data.start_time).toLocaleString('uk-UA')}</p>
                        </div>
                    </div>
                );
            default:
                return <p>Unknown Action: {type}</p>;
        }
    };

    return (
        <div className="bg-gray-900/50 border border-white/10 rounded-xl p-3 mb-2 last:mb-0">
            <div className="flex items-center justify-between">
                {renderContent()}

                {status === 'EXECUTED' ? (
                    <div className="flex items-center gap-1 text-green-400 text-xs font-medium px-2 py-1 bg-green-500/10 rounded-lg">
                        <Check size={14} />
                        <span>Done</span>
                    </div>
                ) : (
                    <button
                        onClick={handleExecute}
                        disabled={executing || status !== 'PENDING'}
                        className="bg-primary-600 hover:bg-primary-500 disabled:opacity-50 disabled:cursor-not-allowed text-white px-3 py-1.5 rounded-lg text-xs font-medium transition-colors flex items-center gap-1.5"
                    >
                        {executing ? <Loader2 size={14} className="animate-spin" /> : <ChevronRight size={14} />}
                        <span>Do it</span>
                    </button>
                )}
            </div>
            {error && <p className="text-xs text-red-400 mt-2">{error}</p>}
        </div>
    );
};
