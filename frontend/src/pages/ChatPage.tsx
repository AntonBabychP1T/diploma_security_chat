import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, Chat, Message, updateChat, deleteChat, askSecretary } from '../api/client';
import { Sidebar } from '../components/Sidebar';
import { MessageBubble } from '../components/MessageBubble';
import { ChatInput } from '../components/ChatInput';
import { ChatHeader } from '../components/ChatHeader';
import { ArenaMessagePair } from '../components/ArenaMessagePair';
import { SecretaryThinking } from '../components/SecretaryThinking';
import { Loader2, Bot } from 'lucide-react';
import { Menu } from 'lucide-react';
import clsx from 'clsx';
import { useI18n } from '../i18n/I18nProvider';

export const ChatPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();
    const { t } = useI18n();

    const [chats, setChats] = useState<Chat[]>([]);
    const [activeChat, setActiveChat] = useState<Chat | null>(null);
    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [style, setStyle] = useState("default");
    const [provider, setProvider] = useState("openai");
    const modelsByProvider: Record<string, { id: string; label: string; }[]> = {
        openai: [
            { id: "gpt-5.5", label: "GPT 5.5" },
            { id: "gpt-5.4", label: "GPT 5.4" },
            { id: "gpt-5.4-mini", label: "GPT 5.4 Mini" },
            { id: "gpt-5.4-nano", label: "GPT 5.4 Nano" },
        ],
        gemini: [
            { id: "gemini-3.5-flash", label: "Gemini 3.5 Flash" },
            { id: "gemini-3.1-pro-preview", label: "Gemini 3.1 Pro Preview" },
            { id: "gemini-3.1-flash-lite", label: "Gemini 3.1 Flash-Lite" },
            { id: "gemini-2.5-pro", label: "Gemini 2.5 Pro" },
            { id: "gemini-2.5-flash", label: "Gemini 2.5 Flash" },
            { id: "gemini-2.5-flash-lite", label: "Gemini 2.5 Flash-Lite" },
        ]
    };
    const providerOptions = [
        { id: "openai", label: "OpenAI" },
        { id: "gemini", label: "Gemini" }
    ];
    const [model, setModel] = useState(modelsByProvider["openai"][0].id);
    const messagesEndRef = useRef<HTMLDivElement>(null);
    const currentModelOptions = modelsByProvider[provider] || [];
    const arenaModelOptions = [...modelsByProvider.openai, ...modelsByProvider.gemini];
    const [abortController, setAbortController] = useState<AbortController | null>(null);
    const [optimisticAssistantId, setOptimisticAssistantId] = useState<number | null>(null);
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [secretaryMode, setSecretaryMode] = useState(false);
    const [secretaryThinking, setSecretaryThinking] = useState(false);
    const autoSecretary = typeof window !== 'undefined' ? localStorage.getItem('auto_secretary') === 'true' : false;

    // Arena Mode State
    const [isArenaMode, setIsArenaMode] = useState(false);
    const [arenaModelA, setArenaModelA] = useState(modelsByProvider["openai"][2].id); // Default to mini
    const [arenaModelB, setArenaModelB] = useState(modelsByProvider["gemini"][0].id); // Default to Gemini 3.5 Flash

    const displayChatTitle = (title?: string | null) => title === 'New Chat' ? t('chat.defaultTitle') : title || t('chat.selectChat');

    useEffect(() => {
        fetchChats();
    }, []);

    useEffect(() => {
        if (id) {
            fetchChat(parseInt(id));
        } else {
            setActiveChat(null);
        }
    }, [id]);

    useEffect(() => {
        scrollToBottom();
    }, [activeChat?.messages, secretaryThinking]);

    const scrollToBottom = () => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
    };

    const fetchChats = async () => {
        try {
            const res = await api.get<Chat[]>('/chats');
            setChats(res.data);
        } catch (err) {
            console.error("Failed to fetch chats", err);
        }
    };

    const upsertChatInList = (chat: Chat) => {
        setChats(prev => {
            const exists = prev.some(c => c.id === chat.id);
            if (!exists) {
                return [chat, ...prev];
            }
            return prev.map(c => c.id === chat.id ? chat : c);
        });
    };

    const syncChat = async (chatId: number) => {
        const res = await api.get<Chat>(`/chats/${chatId}`);
        setActiveChat(prev => prev?.id === chatId ? res.data : prev);
        upsertChatInList(res.data);
        return res.data;
    };

    const fetchChat = async (chatId: number) => {
        setLoading(true);
        try {
            const res = await api.get<Chat>(`/chats/${chatId}`);
            setActiveChat(res.data);
            upsertChatInList(res.data);
        } catch (err) {
            console.error("Failed to fetch chat", err);
        } finally {
            setLoading(false);
        }
    };

    const handleNewChat = async () => {
        try {
            const res = await api.post<Chat>('/chats', { title: 'New Chat' });
            setChats(prev => [res.data, ...prev.filter(c => c.id !== res.data.id)]);
            navigate(`/chats/${res.data.id}`);
        } catch (err) {
            console.error("Failed to create chat", err);
        }
    };

    const handleProviderChange = (value: string) => {
        setProvider(value);
        const nextModel = modelsByProvider[value]?.[0]?.id;
        if (nextModel) {
            setModel(nextModel);
        } else {
            setModel("");
        }
    };

    const handleRenameChat = async (id: number, newTitle: string) => {
        try {
            await updateChat(id, newTitle);
            setChats(prev => prev.map(c => c.id === id ? { ...c, title: newTitle } : c));
            if (activeChat?.id === id) {
                setActiveChat({ ...activeChat, title: newTitle });
            }
        } catch (err) {
            console.error("Failed to rename chat", err);
        }
    };

    const handleDeleteChat = async (id: number) => {
        try {
            await deleteChat(id);
            setChats(prev => prev.filter(c => c.id !== id));
            if (activeChat?.id === id) {
                setActiveChat(null);
                navigate('/');
            }
        } catch (err) {
            console.error("Failed to delete chat", err);
        }
    };

    const handleStop = () => {
        if (abortController) {
            abortController.abort();
        }
        if (optimisticAssistantId && activeChat?.messages) {
            setActiveChat({
                ...activeChat,
                messages: activeChat.messages.filter(m => m.id !== optimisticAssistantId)
            });
        }
        setSending(false);
        setSecretaryThinking(false);
        setAbortController(null);
        setOptimisticAssistantId(null);
    };

    const handleSend = async (text: string, attachments: { name: string, type: string, content: string }[] = []) => {
        if (!activeChat || sending) return;

        const trimmed = text.trim();
        // If only attachments, allow sending
        if (!trimmed && attachments.length === 0) return;

        const secretaryCommand = secretaryMode || /^\/(sec|secretary|секретар)/i.test(trimmed);
        const secretaryQuery = secretaryCommand && !secretaryMode ? trimmed.replace(/^\/(sec|secretary|секретар)\s*/i, '') || trimmed : trimmed;

        // Optimistic user message
        const optimisticMsg: Message = {
            id: Date.now(),
            chat_id: activeChat.id,
            role: 'user',
            content: text + (attachments.length > 0 ? `\n[${t('chat.attached')}: ${attachments.map(a => a.name).join(', ')}]` : ''),
            created_at: new Date().toISOString()
        };

        const updatedChat = {
            ...activeChat,
            messages: [...(activeChat.messages || []), optimisticMsg]
        };
        setActiveChat(updatedChat);

        if (secretaryCommand) {
            const controller = new AbortController();
            setAbortController(controller);
            setSending(true);
            setSecretaryThinking(true);

            try {
                const res = await askSecretary(secretaryQuery || text, activeChat.id, controller.signal);
                setActiveChat(prev => {
                    if (!prev) return null;
                    return {
                        ...prev,
                        messages: [...(prev.messages || []), {
                            id: Date.now() + 1,
                            chat_id: activeChat.id,
                            role: 'assistant',
                            content: `${t('chat.secretaryPrefix')}: ${res.data.response}`,
                            created_at: new Date().toISOString()
                        }]
                    };
                });
                await syncChat(res.data.chat_id);
            } catch (err) {
                if ((err as any).name === "CanceledError" || (err as any).code === "ERR_CANCELED") {
                    console.warn("Secretary request cancelled");
                } else {
                    console.error("Secretary agent failed", err);
                    setActiveChat(prev => {
                        if (!prev) return null;
                        return {
                            ...prev,
                            messages: [...(prev.messages || []), {
                                id: Date.now() + 2,
                                chat_id: activeChat.id,
                                role: 'assistant',
                                content: t('chat.secretaryUnavailable'),
                                created_at: new Date().toISOString()
                            }]
                        };
                    });
                }
            } finally {
                setSending(false);
                setSecretaryThinking(false);
                setAbortController(null);
            }
            return;
        }
        setSending(true);

        // Arena Mode: Use non-streaming endpoint
        if (isArenaMode) {
            try {
                const res = await api.post<Message | Message[]>(`/chats/${activeChat.id}/messages`, {
                    message: text,
                    style: style,
                    models: [arenaModelA, arenaModelB],
                    attachments: attachments // Pass attachments
                });

                // Arena mode returns an array of messages
                const messages = Array.isArray(res.data) ? res.data : [res.data];

                console.log('Arena response:', res.data);
                console.log('Messages array:', messages);
                console.log('Messages count:', messages.length);

                // Add both assistant messages to chat
                setActiveChat(prev => {
                    if (!prev) return null;
                    const newMessages = [...(prev.messages || []), ...messages];
                    console.log('New messages array length:', newMessages.length);
                    return {
                        ...prev,
                        messages: newMessages
                    };
                });
                await syncChat(activeChat.id);
            } catch (err) {
                console.error("Failed to send arena message", err);
            } finally {
                setSending(false);
            }
            return;
        }

        // Standard Mode: Use streaming endpoint
        const assistantTempId = Date.now() + 1;
        setOptimisticAssistantId(assistantTempId);
        setActiveChat(prev => {
            if (!prev) return null;
            return {
                ...prev,
                messages: [...(prev.messages || []), {
                    id: assistantTempId,
                    chat_id: activeChat.id,
                    role: 'assistant',
                    content: '',
                    created_at: new Date().toISOString()
                }]
            };
        });

        const controller = new AbortController();
        setAbortController(controller);

        try {
            const token = localStorage.getItem('token');
            const baseURL = api.defaults.baseURL || '';
            const res = await fetch(`${baseURL}/chats/${activeChat.id}/messages/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    ...(token ? { Authorization: `Bearer ${token}` } : {})
                },
                body: JSON.stringify({
                    message: text,
                    style: style,
                    provider: provider,
                    model: model,
                    attachments: attachments // Pass attachments
                }),
                signal: controller.signal
            });

            if (!res.ok || !res.body) {
                throw new Error(`${t('chat.streamingFailed')}: ${res.status}`);
            }

            const reader = res.body.getReader();
            const decoder = new TextDecoder();
            let buffer = "";
            let assistantContent = "";

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                buffer += decoder.decode(value, { stream: true });

                const parts = buffer.split("\n\n");
                buffer = parts.pop() || "";

                for (const part of parts) {
                    const line = part.trimStart();
                    if (!line.startsWith("data:")) continue;
                    const dataStr = line.replace(/^data:\s*/, "");
                    if (!dataStr) continue;
                    try {
                        const payload = JSON.parse(dataStr);
                        if (payload.done) {
                            continue;
                        }
                        const delta: string = payload.delta ?? "";
                        if (!delta) continue;
                        assistantContent += delta;
                        setActiveChat(prev => {
                            if (!prev) return null;
                            return {
                                ...prev,
                                messages: (prev.messages || []).map(m =>
                                    m.id === assistantTempId ? { ...m, content: assistantContent } : m
                                )
                            };
                        });
                    } catch (e) {
                        console.error("Failed to parse stream chunk", e, dataStr);
                    }
                }
            }

            // Remove optimistic assistant before syncing
            setActiveChat(prev => {
                if (!prev) return null;
                return {
                    ...prev,
                    messages: (prev.messages || []).filter(m => m.id !== assistantTempId)
                };
            });

            // Refresh chat to sync with persisted message IDs/content
            await syncChat(activeChat.id);
        } catch (err) {
            if ((err as any).name === "AbortError") {
                console.warn("Request cancelled");
            } else {
                console.error("Failed to send message", err);
            }
            // Remove optimistic assistant on failure
            setActiveChat(prev => {
                if (!prev) return null;
                return {
                    ...prev,
                    messages: (prev.messages || []).filter(m => m.id !== assistantTempId)
                };
            });
        } finally {
            setSending(false);
            setAbortController(null);
            setOptimisticAssistantId(null);
        }

        // Auto trigger secretary if enabled and keywords match
        if (!secretaryCommand && autoSecretary && /\b(calendar|gmail|meeting|події|календар|лист|пошта|секретар)\b/i.test(text)) {
            try {
                const res = await askSecretary(text, activeChat.id);
                setActiveChat(prev => {
                    if (!prev) return null;
                    return {
                        ...prev,
                        messages: [...(prev.messages || []), {
                            id: Date.now(),
                            chat_id: activeChat.id,
                            role: 'assistant',
                            content: `${t('chat.secretaryPrefix')}: ${res.data.response}`,
                            created_at: new Date().toISOString()
                        }]
                    };
                });
                await syncChat(activeChat.id);
            } catch (err) {
                console.error("Secretary agent failed", err);
            }
        }
    };

    return (
        <div className="flex h-screen bg-gray-50 text-gray-950 overflow-hidden font-sans dark:bg-gray-950 dark:text-gray-100">
            {/* Sidebar with mobile overlay */}
            <div className={clsx(
                "fixed inset-0 z-30 transition-transform duration-200 md:static md:translate-x-0 md:w-72",
                sidebarOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"
            )}>
                <Sidebar
                    chats={chats}
                    activeChatId={activeChat?.id}
                    onNewChat={handleNewChat}
                    onRenameChat={handleRenameChat}
                    onDeleteChat={handleDeleteChat}
                    onCloseSidebar={() => setSidebarOpen(false)}
                />
                {sidebarOpen && (
                    <div
                        className="absolute inset-0 bg-black/60 md:hidden"
                        onClick={() => setSidebarOpen(false)}
                    />
                )}
            </div>

            <div className="flex-1 flex flex-col min-w-0 relative bg-gray-50 dark:bg-gray-950">
                {/* Background Gradient Effect */}
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-white via-gray-50 to-gray-100 pointer-events-none dark:from-gray-900 dark:via-gray-950 dark:to-gray-950" />

                {/* Mobile top bar */}
                <div className="md:hidden flex items-center gap-2 px-4 py-3 border-b border-gray-200 z-20 bg-white dark:border-white/5 dark:bg-gray-950">
                    <button
                        onClick={() => setSidebarOpen(true)}
                        className="p-2 rounded-lg bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-white"
                    >
                        <Menu size={18} />
                    </button>
                    <div className="flex-1 truncate text-sm text-gray-700 dark:text-gray-300">
                        {displayChatTitle(activeChat?.title)}
                    </div>
                </div>

                {activeChat ? (
                    <>
                        <ChatHeader
                            title={displayChatTitle(activeChat.title)}
                            style={style}
                            provider={provider}
                            model={model}
                            providerOptions={providerOptions}
                            modelOptions={currentModelOptions}
                            arenaModelOptions={arenaModelOptions}
                            onStyleChange={setStyle}
                            onProviderChange={handleProviderChange}
                            onModelChange={setModel}
                            isArenaMode={isArenaMode}
                            onArenaModeChange={setIsArenaMode}
                            arenaModelA={arenaModelA}
                            arenaModelB={arenaModelB}
                            onArenaModelAChange={setArenaModelA}
                            onArenaModelBChange={setArenaModelB}
                        />

                        {/* Messages Area */}
                        <div className="flex-1 overflow-y-auto p-2 sm:p-4 space-y-6 scroll-smooth relative z-0">
                            {loading ? (
                                <div className="h-full flex flex-col items-center justify-center text-gray-500 gap-3">
                                    <Loader2 className="animate-spin text-primary-500" size={32} />
                                    <span className="text-sm">{t('chat.loadingConversation')}</span>
                                </div>
                            ) : (
                                <div className="max-w-4xl mx-auto w-full py-4 space-y-6">
                                    {(() => {
                                        const renderedMessages = [];
                                        const messages = activeChat.messages || [];

                                        console.log('Total messages to render:', messages.length);

                                        for (let i = 0; i < messages.length; i++) {
                                            const msg = messages[i];
                                            
                                            // Skip rendering optimistic message if it's empty (we show the loader instead)
                                            if (msg.id === optimisticAssistantId && !msg.content) {
                                                continue;
                                            }

                                            const prevMsg = messages[i - 1];

                                            // Check for Arena Pair
                                            if (msg.meta_data?.comparison_id && msg.role === 'assistant') {
                                                console.log(`Message ${i}: Found Arena message with comparison_id:`, msg.meta_data.comparison_id, 'Model:', msg.meta_data.model);
                                                const nextMsg = messages[i + 1];
                                                if (nextMsg && nextMsg.meta_data?.comparison_id === msg.meta_data.comparison_id) {
                                                    // Found a pair
                                                    console.log(`  → Paired with message ${i + 1}, Model:`, nextMsg.meta_data?.model);
                                                    renderedMessages.push(
                                                        <ArenaMessagePair
                                                            key={`arena-${msg.id}`}
                                                            messageA={msg}
                                                            messageB={nextMsg}
                                                            onVote={(id, type) => {
                                                                console.log("Voted", id, type);
                                                                // Ideally refresh chat or update local state
                                                            }}
                                                        />
                                                    );
                                                    i++; // Skip next message
                                                    continue;
                                                } else {
                                                    console.log(`  → No pair found for this Arena message (next message comparison_id: ${nextMsg?.meta_data?.comparison_id})`);
                                                }
                                            }

                                            const isFirstInGroup = !prevMsg || prevMsg.role !== msg.role || (new Date(msg.created_at).getTime() - new Date(prevMsg.created_at).getTime() > 60000);
                                            renderedMessages.push(
                                                <MessageBubble
                                                    key={msg.id}
                                                    message={msg}
                                                    isFirstInGroup={isFirstInGroup}
                                                />
                                            );
                                        }
                                        return renderedMessages;
                                    })()}

                                    {secretaryThinking && (
                                        <SecretaryThinking />
                                    )}

                                    {sending && !secretaryThinking && (!optimisticAssistantId || (activeChat.messages || []).find(m => m.id === optimisticAssistantId && !m.content)) && (
                                        <div className="flex gap-3 sm:gap-4 max-w-4xl mx-auto w-full animate-in fade-in duration-300">
                                            <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center shrink-0 shadow-sm mt-1">
                                                <Bot size={16} className="text-white" />
                                            </div>
                                            <div className="flex items-center gap-2 bg-white border border-gray-200 px-4 py-3 rounded-2xl rounded-tl-sm shadow-sm dark:bg-gray-800/50 dark:border-white/5">
                                                <div className="flex gap-1">
                                                    <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.3s] dark:bg-gray-400"></span>
                                                    <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce [animation-delay:-0.15s] dark:bg-gray-400"></span>
                                                    <span className="w-1.5 h-1.5 bg-gray-500 rounded-full animate-bounce dark:bg-gray-400"></span>
                                                </div>
                                            </div>
                                        </div>
                                    )}
                                    <div ref={messagesEndRef} className="h-4" />
                                </div>
                            )}
                        </div>

                        {/* Input Area */}
                        <div className="relative z-10">
                            <ChatInput
                                onSend={handleSend}
                                disabled={sending}
                                isSending={sending}
                                onStop={handleStop}
                                secretaryMode={secretaryMode}
                                onSecretaryModeChange={setSecretaryMode}
                            />
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-500 relative z-0 px-4">
                        <div className="w-16 h-16 bg-white rounded-2xl flex items-center justify-center mb-6 shadow-xl shadow-gray-200/70 border border-gray-200 dark:bg-gray-900 dark:shadow-black/20 dark:border-white/5">
                            <Bot size={32} className="text-primary-500" />
                        </div>
                        <h3 className="text-xl font-semibold text-gray-900 mb-2 text-center dark:text-gray-200">{t('chat.welcomeTitle')}</h3>
                        <p className="text-gray-500 max-w-md text-center text-sm sm:text-base dark:text-gray-400">
                            {t('chat.welcomeSubtitle')}
                        </p>
                        <button
                            onClick={handleNewChat}
                            className="mt-8 px-6 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-full font-medium transition-all shadow-lg shadow-primary-900/20 hover:scale-105"
                        >
                            {t('chat.startNewChat')}
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};
