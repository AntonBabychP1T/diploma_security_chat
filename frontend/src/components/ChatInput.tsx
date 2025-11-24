import React, { useState, useRef, useEffect } from 'react';
import { Send, Paperclip, Square, ArrowUp } from 'lucide-react';
import clsx from 'clsx';

interface Props {
    onSend: (text: string) => void;
    disabled?: boolean;
    isSending?: boolean;
    onStop?: () => void;
}

export const ChatInput: React.FC<Props> = ({ onSend, disabled, isSending, onStop }) => {
    const [text, setText] = useState("");
    const textareaRef = useRef<HTMLTextAreaElement>(null);

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        if (text.trim() && !disabled) {
            onSend(text);
            setText("");
            if (textareaRef.current) {
                textareaRef.current.style.height = 'auto';
            }
        }
    };

    const handleKeyDown = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            handleSubmit();
        }
    };

    // Auto-grow textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto';
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
        }
    }, [text]);

    return (
        <div className="w-full max-w-4xl mx-auto px-4 pb-6 pt-2">
            <div className={clsx(
                "relative flex items-end gap-2 bg-gray-800/80 backdrop-blur-xl border border-white/10 rounded-3xl p-2 shadow-2xl shadow-black/20 transition-all duration-200",
                "focus-within:border-primary-500/30 focus-within:ring-1 focus-within:ring-primary-500/20"
            )}>
                {/* Attachment Button (Mock) */}
                <button
                    className="p-3 text-gray-400 hover:text-gray-200 hover:bg-white/5 rounded-full transition-colors mb-0.5"
                    title="Add attachment"
                >
                    <Paperclip size={20} />
                </button>

                <textarea
                    ref={textareaRef}
                    value={text}
                    onChange={(e) => setText(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Type a message..."
                    disabled={disabled}
                    rows={1}
                    className="flex-1 bg-transparent border-none focus:ring-0 text-gray-100 placeholder:text-gray-500 resize-none py-3.5 max-h-[200px] scrollbar-hide"
                    style={{ minHeight: '52px' }}
                />

                {/* Send / Stop Button */}
                {isSending ? (
                    <button
                        onClick={onStop}
                        className="p-3 rounded-full mb-0.5 transition-all duration-200 flex items-center justify-center bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-900/20"
                        title="Зупинити генерацію"
                    >
                        <Square size={18} />
                    </button>
                ) : (
                    <button
                        onClick={() => handleSubmit()}
                        disabled={!text.trim() || disabled}
                        className={clsx(
                            "p-3 rounded-full mb-0.5 transition-all duration-200 flex items-center justify-center",
                            text.trim() && !disabled
                                ? "bg-primary-600 text-white hover:bg-primary-500 shadow-lg shadow-primary-900/20 scale-100"
                                : "bg-gray-700 text-gray-500 cursor-not-allowed"
                        )}
                    >
                        <ArrowUp size={20} />
                    </button>
                )}
            </div>

            <div className="text-center mt-2">
                <p className="text-[10px] text-gray-500">
                    AI can make mistakes. Please verify important information.
                </p>
            </div>
        </div>
    );
};
