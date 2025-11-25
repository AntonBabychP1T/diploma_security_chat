import React, { useState } from 'react';
import { Message } from '../api/client';
import { MessageBubble } from './MessageBubble';
import { ThumbsUp, Minus } from 'lucide-react';
import { api } from '../api/client';
import clsx from 'clsx';

interface Props {
    messageA: Message;
    messageB: Message;
    onVote: (messageId: number, type: 'better' | 'worse' | 'tie') => void;
}

export const ArenaMessagePair: React.FC<Props> = ({ messageA, messageB, onVote }) => {
    const [voted, setVoted] = useState<string | null>(null);

    const handleVote = async (winner: 'A' | 'B' | 'tie') => {
        if (voted) return;

        try {
            if (winner === 'tie') {
                await api.post(`/chats/${messageA.chat_id}/messages/${messageA.id}/vote`, null, { params: { vote_type: 'tie' } });
                await api.post(`/chats/${messageB.chat_id}/messages/${messageB.id}/vote`, null, { params: { vote_type: 'tie' } });
                setVoted('tie');
                onVote(messageA.id, 'tie');
            } else if (winner === 'A') {
                await api.post(`/chats/${messageA.chat_id}/messages/${messageA.id}/vote`, null, { params: { vote_type: 'better' } });
                await api.post(`/chats/${messageB.chat_id}/messages/${messageB.id}/vote`, null, { params: { vote_type: 'worse' } });
                setVoted('A');
                onVote(messageA.id, 'better');
            } else {
                await api.post(`/chats/${messageB.chat_id}/messages/${messageB.id}/vote`, null, { params: { vote_type: 'better' } });
                await api.post(`/chats/${messageA.chat_id}/messages/${messageA.id}/vote`, null, { params: { vote_type: 'worse' } });
                setVoted('B');
                onVote(messageB.id, 'better');
            }
        } catch (err) {
            console.error("Failed to submit vote", err);
        }
    };

    return (
        <div className="flex flex-col gap-4 w-full">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className={clsx("relative rounded-xl border p-2 transition-all", voted === 'A' ? "border-green-500/50 bg-green-500/5" : "border-white/5 bg-gray-900/20")}>
                    <div className="absolute top-2 right-2 text-xs text-gray-500 font-mono">
                        {messageA.meta_data?.model}
                    </div>
                    <MessageBubble message={messageA} isFirstInGroup={true} />
                </div>
                <div className={clsx("relative rounded-xl border p-2 transition-all", voted === 'B' ? "border-green-500/50 bg-green-500/5" : "border-white/5 bg-gray-900/20")}>
                    <div className="absolute top-2 right-2 text-xs text-gray-500 font-mono">
                        {messageB.meta_data?.model}
                    </div>
                    <MessageBubble message={messageB} isFirstInGroup={true} />
                </div>
            </div>

            {!voted && (
                <div className="flex justify-center gap-4 animate-in fade-in slide-in-from-bottom-4 duration-500">
                    <button
                        onClick={() => handleVote('A')}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg border border-white/10 transition-colors text-sm"
                    >
                        <ThumbsUp size={16} className="text-green-400" />
                        <span>Left is Better</span>
                    </button>
                    <button
                        onClick={() => handleVote('tie')}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg border border-white/10 transition-colors text-sm"
                    >
                        <Minus size={16} className="text-gray-400" />
                        <span>Tie</span>
                    </button>
                    <button
                        onClick={() => handleVote('B')}
                        className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 rounded-lg border border-white/10 transition-colors text-sm"
                    >
                        <ThumbsUp size={16} className="text-green-400" />
                        <span>Right is Better</span>
                    </button>
                </div>
            )}

            {voted && (
                <div className="text-center text-sm text-gray-400 animate-in fade-in zoom-in duration-300">
                    Thanks for voting!
                </div>
            )}
        </div>
    );
};
