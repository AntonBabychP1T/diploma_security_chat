import React from 'react';
import { Message } from '../api/client';
import clsx from 'clsx';
import { User, Bot, Shield, Clock } from 'lucide-react';
import { useI18n } from '../i18n/I18nProvider';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
    message: Message;
    isFirstInGroup?: boolean;
}

export const MessageBubble: React.FC<Props> = ({ message, isFirstInGroup = true }) => {
    const { t } = useI18n();
    const isUser = message.role === 'user';

    return (
        <div className={clsx(
            "flex gap-4 max-w-4xl mx-auto w-full group",
            isUser ? "flex-row-reverse" : "flex-row",
            !isFirstInGroup && "mt-1"
        )}>
            {/* Avatar */}
            <div className={clsx(
                "w-8 h-8 rounded-full flex items-center justify-center shrink-0 shadow-sm mt-1",
                isUser
                    ? "bg-gray-200 text-gray-700 dark:bg-gray-700 dark:text-gray-300"
                    : "bg-primary-600 text-white shadow-primary-900/20",
                !isFirstInGroup && "opacity-0" // Hide avatar for subsequent messages in group
            )}>
                {isUser ? <User size={16} /> : <Bot size={16} />}
            </div>

            {/* Message Content */}
            <div className={clsx(
                "flex flex-col max-w-[85%] sm:max-w-[75%]",
                isUser ? "items-end" : "items-start"
            )}>
                {/* Name & Time (only for first message) */}
                {isFirstInGroup && (
                    <div className={clsx(
                        "flex items-center gap-2 mb-1 text-xs text-gray-500",
                        isUser ? "flex-row-reverse" : "flex-row"
                    )}>
                        <span className="font-medium text-gray-600 dark:text-gray-400">
                            {isUser ? t('message.you') : t('message.assistant')}
                        </span>
                        <span>•</span>
                        <time>{new Date(message.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</time>
                    </div>
                )}

                {/* Bubble */}
                <div className={clsx(
                    "px-5 py-3.5 rounded-2xl text-[15px] leading-relaxed shadow-sm break-words",
                    isUser ? "whitespace-pre-wrap" : "message-markdown",
                    isUser
                        ? "bg-primary-600 text-white rounded-tr-sm dark:bg-gray-800 dark:text-gray-100"
                        : "bg-white border border-gray-200 text-gray-800 rounded-tl-sm backdrop-blur-sm dark:bg-gray-800/50 dark:border-white/5 dark:text-gray-100"
                )}>
                    {isUser ? (
                        message.content
                    ) : (
                        <ReactMarkdown
                            remarkPlugins={[remarkGfm]}
                            components={{
                                a: ({ href, children }) => (
                                    <a href={href} target="_blank" rel="noreferrer">
                                        {children}
                                    </a>
                                )
                            }}
                        >
                            {message.content}
                        </ReactMarkdown>
                    )}
                </div>

                {/* Metadata / Footer */}
                {!isUser && message.meta_data && (
                    <div className="mt-1.5 flex flex-wrap items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                        {message.meta_data.masked_used && (
                            <div className="flex items-center gap-1 text-[10px] text-green-400/80 bg-green-500/10 px-1.5 py-0.5 rounded border border-green-500/20">
                                <Shield size={10} />
                                <span>{t('message.piiMasked')}</span>
                            </div>
                        )}
                        {message.meta_data.latency && (
                            <div className="flex items-center gap-1 text-[10px] text-gray-500">
                                <Clock size={10} />
                                <span>{message.meta_data.latency.toFixed(2)}s</span>
                            </div>
                        )}

                        <div className="mt-1.5 flex flex-wrap items-center gap-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
                            {message.meta_data.masked_used && (
                                <div className="flex items-center gap-1 text-[10px] text-green-400/80 bg-green-500/10 px-1.5 py-0.5 rounded border border-green-500/20">
                                    <Shield size={10} />
                                    <span>PII Masked</span>
                                </div>
                            )}
                            {message.meta_data.latency && (
                                <div className="flex items-center gap-1 text-[10px] text-gray-500">
                                    <Clock size={10} />
                                    <span>{message.meta_data.latency.toFixed(2)}s</span>
                                </div>
                            )}
                            {message.meta_data.source && (
                                <div className="flex items-center gap-1 text-[10px] text-blue-400/80 bg-blue-500/10 px-1.5 py-0.5 rounded border border-blue-500/20">
                                    <span>{message.meta_data.source}</span>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};
