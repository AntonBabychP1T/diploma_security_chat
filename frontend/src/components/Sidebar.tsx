import React, { useState } from 'react';
import { Chat } from '../api/client';
import { MessageSquare, Plus, BarChart2, Trash2, Edit2, Check, X, Search, User as UserIcon } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import { useAuth } from '../context/AuthContext';

interface Props {
    chats: Chat[];
    activeChatId?: number;
    onNewChat: () => void;
    onDeleteChat: (id: number) => void;
    onRenameChat: (id: number, newTitle: string) => void;
}

export const Sidebar: React.FC<Props> = ({ chats, activeChatId, onNewChat, onDeleteChat, onRenameChat }) => {
    const navigate = useNavigate();
    const { user } = useAuth();
    const [editingId, setEditingId] = useState<number | null>(null);
    const [editTitle, setEditTitle] = useState("");
    const [searchTerm, setSearchTerm] = useState("");

    const filteredChats = chats.filter(c =>
        c.title.toLowerCase().includes(searchTerm.toLowerCase())
    );

    const startEditing = (e: React.MouseEvent, chat: Chat) => {
        e.stopPropagation();
        setEditingId(chat.id);
        setEditTitle(chat.title);
    };

    const cancelEditing = (e: React.MouseEvent) => {
        e.stopPropagation();
        setEditingId(null);
        setEditTitle("");
    };

    const saveEditing = (e: React.MouseEvent, id: number) => {
        e.stopPropagation();
        if (editTitle.trim()) {
            onRenameChat(id, editTitle);
        }
        setEditingId(null);
    };

    const handleDelete = (e: React.MouseEvent, id: number) => {
        e.stopPropagation();
        if (confirm("Are you sure you want to delete this chat?")) {
            onDeleteChat(id);
        }
    };

    return (
        <div className="w-72 flex flex-col h-full bg-gray-950 border-r border-white/5 relative z-20">
            {/* Header Area */}
            <div className="p-4 space-y-4">
                <button
                    onClick={onNewChat}
                    className="w-full group flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl py-3 px-4 transition-all duration-200 shadow-lg shadow-primary-900/20 font-medium"
                >
                    <Plus size={20} className="group-hover:scale-110 transition-transform" />
                    <span>New Chat</span>
                </button>

                <div className="relative group">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500 group-focus-within:text-primary-400 transition-colors" />
                    <input
                        type="text"
                        placeholder="Search chats..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-gray-900/50 border border-white/5 rounded-lg py-2 pl-9 pr-3 text-sm text-gray-300 focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:bg-gray-900 transition-all placeholder:text-gray-600"
                />
            </div>
            </div>

            {/* Chat List */}
            <div className="flex-1 overflow-y-auto px-3 pb-2 space-y-1">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-3 py-2 mb-1">
                    Recent Chats
                </div>

                {filteredChats.map(chat => (
                    <div
                        key={chat.id}
                        onClick={() => navigate(`/chats/${chat.id}`)}
                        className={clsx(
                            "group relative flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all duration-200 border border-transparent",
                            activeChatId === chat.id
                                ? "bg-gray-800/80 text-white shadow-md border-white/5"
                                : "text-gray-400 hover:bg-gray-800/40 hover:text-gray-200"
                        )}
                    >
                        <div className={clsx(
                            "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors",
                            activeChatId === chat.id ? "bg-primary-500/20 text-primary-400" : "bg-gray-800 text-gray-500 group-hover:bg-gray-700"
                        )}>
                            <MessageSquare size={16} />
                        </div>

                        {editingId === chat.id ? (
                            <div className="flex items-center gap-1 flex-1 min-w-0 animate-in fade-in zoom-in-95 duration-200">
                                <input
                                    value={editTitle}
                                    onChange={(e) => setEditTitle(e.target.value)}
                                    onClick={(e) => e.stopPropagation()}
                                    className="bg-gray-950 text-white text-sm p-1 rounded w-full outline-none border border-primary-500/50 focus:border-primary-500"
                                    autoFocus
                                    onKeyDown={(e) => {
                                        if (e.key === 'Enter') saveEditing(e as any, chat.id);
                                        if (e.key === 'Escape') cancelEditing(e as any);
                                    }}
                                />
                                <button onClick={(e) => saveEditing(e, chat.id)} className="p-1 text-green-500 hover:bg-green-500/10 rounded"><Check size={14} /></button>
                                <button onClick={cancelEditing} className="p-1 text-red-500 hover:bg-red-500/10 rounded"><X size={14} /></button>
                            </div>
                        ) : (
                            <>
                                <div className="flex-1 min-w-0 flex flex-col gap-0.5">
                                    <span className="truncate text-sm font-medium leading-tight">{chat.title}</span>
                                    <span className="truncate text-xs text-gray-500 font-normal">
                                        {chat.messages && chat.messages.length > 0
                                            ? chat.messages[chat.messages.length - 1].content.substring(0, 30) + "..."
                                            : "No messages yet"}
                                    </span>
                                </div>

                                {/* Hover Actions */}
                                <div className={clsx(
                                    "absolute right-2 flex items-center gap-1 bg-gray-800/90 backdrop-blur-sm rounded-lg p-1 shadow-sm transition-opacity duration-200",
                                    "opacity-0 group-hover:opacity-100",
                                    activeChatId === chat.id ? "bg-gray-800" : ""
                                )}>
                                    <button onClick={(e) => startEditing(e, chat)} className="p-1.5 text-gray-400 hover:text-primary-400 hover:bg-white/5 rounded-md transition-colors" title="Rename">
                                        <Edit2 size={13} />
                                    </button>
                                    <button onClick={(e) => handleDelete(e, chat.id)} className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-white/5 rounded-md transition-colors" title="Delete">
                                        <Trash2 size={13} />
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                ))}

                {filteredChats.length === 0 && (
                    <div className="text-center py-8 text-gray-600 text-sm">
                        No chats found
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-white/5 bg-gray-950/50 backdrop-blur-sm">
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-gray-900/60 border border-white/5 mb-3">
                    <div className="w-9 h-9 rounded-lg bg-primary-500/20 text-primary-400 flex items-center justify-center">
                        <UserIcon size={18} />
                    </div>
                    <div className="min-w-0">
                        <p className="text-xs text-gray-500">Увійшли як</p>
                        <p className="text-sm text-white font-medium truncate">{user?.email || "..."}</p>
                    </div>
                </div>

                <Link
                    to="/profile"
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-all duration-200 group mb-2"
                >
                    <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center group-hover:bg-primary-500/20 group-hover:text-primary-400 transition-colors">
                        <UserIcon size={18} />
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-medium">Мій профіль</p>
                        <p className="text-xs text-gray-500">Безпека та акаунт</p>
                    </div>
                </Link>

                <Link
                    to="/metrics"
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-400 hover:text-white hover:bg-white/5 transition-all duration-200 group"
                >
                    <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center group-hover:bg-primary-500/20 group-hover:text-primary-400 transition-colors">
                        <BarChart2 size={18} />
                    </div>
                    <span className="text-sm font-medium">Metrics Dashboard</span>
                </Link>
            </div>
        </div>
    );
};
