import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { api, Chat, Message, updateChat, deleteChat } from '../api/client';
import { Sidebar } from '../components/Sidebar';
import { MessageBubble } from '../components/MessageBubble';
import { ChatInput } from '../components/ChatInput';
import { ChatHeader } from '../components/ChatHeader';
import { Loader2, Bot } from 'lucide-react';
import axios from 'axios';

export const ChatPage: React.FC = () => {
    const { id } = useParams<{ id: string }>();
    const navigate = useNavigate();

    const [chats, setChats] = useState<Chat[]>([]);
    const [activeChat, setActiveChat] = useState<Chat | null>(null);
    const [loading, setLoading] = useState(false);
    const [sending, setSending] = useState(false);
    const [style, setStyle] = useState("default");
    const [provider, setProvider] = useState("openai");
    const modelsByProvider: Record<string, { id: string; label: string; }[]> = {
        openai: [
            { id: "gpt-5.1", label: "GPT 5.1" },
            { id: "gpt-5-nano", label: "GPT 5 Nano" },
            { id: "gpt-5-mini", label: "GPT 5 Mini" },
        ],
        gemini: [
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
    const [abortController, setAbortController] = useState<AbortController | null>(null);
    const [optimisticUserId, setOptimisticUserId] = useState<number | null>(null);
    const [optimisticAssistantId, setOptimisticAssistantId] = useState<number | null>(null);

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
    }, [activeChat?.messages]);

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

    const fetchChat = async (chatId: number) => {
        setLoading(true);
        try {
            const res = await api.get<Chat>(`/chats/${chatId}`);
            setActiveChat(res.data);
        } catch (err) {
            console.error("Failed to fetch chat", err);
        } finally {
            setLoading(false);
        }
    };

    const handleNewChat = async () => {
        try {
            const res = await api.post<Chat>('/chats', { title: 'New Chat' });
            setChats([res.data, ...chats]);
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
            setChats(chats.map(c => c.id === id ? { ...c, title: newTitle } : c));
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
            setChats(chats.filter(c => c.id !== id));
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
        setAbortController(null);
        setOptimisticAssistantId(null);
    };

    const handleSend = async (text: string) => {
        if (!activeChat || sending) return;

        // Optimistic user message
        const optimisticMsg: Message = {
            id: Date.now(),
            role: 'user',
            content: text,
            created_at: new Date().toISOString()
        };

        const updatedChat = {
            ...activeChat,
            messages: [...(activeChat.messages || []), optimisticMsg]
        };
        setActiveChat(updatedChat);
        setSending(true);
        setOptimisticUserId(optimisticMsg.id);

        // Placeholder assistant message for streaming updates
        const assistantTempId = Date.now() + 1;
        setOptimisticAssistantId(assistantTempId);
        setActiveChat(prev => {
            if (!prev) return null;
            return {
                ...prev,
                messages: [...(prev.messages || []), {
                    id: assistantTempId,
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
                    model: model
                }),
                signal: controller.signal
            });

            if (!res.ok || !res.body) {
                throw new Error(`Streaming failed: ${res.status}`);
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
            await fetchChat(activeChat.id);
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
            setOptimisticUserId(null);
            setOptimisticAssistantId(null);
        }
    };

    return (
        <div className="flex h-screen bg-gray-950 text-gray-100 overflow-hidden font-sans">
            <Sidebar
                chats={chats}
                activeChatId={activeChat?.id}
                onNewChat={handleNewChat}
                onRenameChat={handleRenameChat}
                onDeleteChat={handleDeleteChat}
            />

            <div className="flex-1 flex flex-col min-w-0 relative bg-gray-950">
                {/* Background Gradient Effect */}
                <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-gray-900 via-gray-950 to-gray-950 pointer-events-none" />

                {activeChat ? (
                    <>
                        <ChatHeader
                            title={activeChat.title}
                            style={style}
                            provider={provider}
                            model={model}
                            providerOptions={providerOptions}
                            modelOptions={currentModelOptions}
                            onStyleChange={setStyle}
                            onProviderChange={handleProviderChange}
                            onModelChange={setModel}
                        />

                        {/* Messages Area */}
                        <div className="flex-1 overflow-y-auto p-4 space-y-6 scroll-smooth relative z-0">
                            {loading ? (
                                <div className="h-full flex flex-col items-center justify-center text-gray-500 gap-3">
                                    <Loader2 className="animate-spin text-primary-500" size={32} />
                                    <span className="text-sm">Loading conversation...</span>
                                </div>
                            ) : (
                                <div className="max-w-4xl mx-auto w-full py-4 space-y-6">
                                    {activeChat.messages?.map((msg, index) => {
                                        // Check if previous message was from same role to group them
                                        const prevMsg = activeChat.messages?.[index - 1];
                                        const isFirstInGroup = !prevMsg || prevMsg.role !== msg.role || (new Date(msg.created_at).getTime() - new Date(prevMsg.created_at).getTime() > 60000);

                                        return (
                                            <MessageBubble
                                                key={msg.id}
                                                message={msg}
                                                isFirstInGroup={isFirstInGroup}
                                            />
                                        );
                                    })}

                                    {sending && (
                                        <div className="flex gap-4 max-w-4xl mx-auto w-full animate-in fade-in duration-300">
                                            <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center shrink-0 shadow-sm mt-1">
                                                <Bot size={16} className="text-white" />
                                            </div>
                                            <div className="flex items-center gap-2 bg-gray-800/50 border border-white/5 px-4 py-3 rounded-2xl rounded-tl-sm">
                                                <div className="flex gap-1">
                                                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                                                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                                                    <span className="w-1.5 h-1.5 bg-gray-400 rounded-full animate-bounce"></span>
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
                            />
                        </div>
                    </>
                ) : (
                    <div className="flex-1 flex flex-col items-center justify-center text-gray-500 relative z-0">
                        <div className="w-16 h-16 bg-gray-900 rounded-2xl flex items-center justify-center mb-6 shadow-xl shadow-black/20 border border-white/5">
                            <Bot size={32} className="text-primary-500" />
                        </div>
                        <h3 className="text-xl font-semibold text-gray-200 mb-2">Welcome to AI Chat</h3>
                        <p className="text-gray-400 max-w-md text-center">
                            Select a chat from the sidebar or start a new conversation to begin.
                        </p>
                        <button
                            onClick={handleNewChat}
                            className="mt-8 px-6 py-2.5 bg-primary-600 hover:bg-primary-500 text-white rounded-full font-medium transition-all shadow-lg shadow-primary-900/20 hover:scale-105"
                        >
                            Start New Chat
                        </button>
                    </div>
                )}
            </div>
        </div>
    );
};
