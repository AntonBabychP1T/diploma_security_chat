import React, { useState } from 'react';
import { Chat } from '../api/client';
import { MessageSquare, Plus, BarChart2, Trash2, Edit2, Check, X, Search, User as UserIcon } from 'lucide-react';
import { Link, useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import { useAuth } from '../context/AuthContext';
import { useI18n } from '../i18n/I18nProvider';
import { LanguageSwitcher } from './LanguageSwitcher';
import { ThemeToggle } from './ThemeToggle';

interface Props {
    chats: Chat[];
    activeChatId?: number;
    onNewChat: () => void;
    onDeleteChat: (id: number) => void;
    onRenameChat: (id: number, newTitle: string) => void;
    onCloseSidebar?: () => void;
}

export const Sidebar: React.FC<Props> = ({ chats, activeChatId, onNewChat, onDeleteChat, onRenameChat, onCloseSidebar }) => {
    const navigate = useNavigate();
    const { user } = useAuth();
    const { t } = useI18n();
    const [editingId, setEditingId] = useState<number | null>(null);
    const [editTitle, setEditTitle] = useState("");
    const [searchTerm, setSearchTerm] = useState("");

    const displayChatTitle = (title: string) => title === 'New Chat' ? t('chat.defaultTitle') : title;

    const filteredChats = chats.filter(c => {
        const needle = searchTerm.toLowerCase();
        return c.title.toLowerCase().includes(needle) || displayChatTitle(c.title).toLowerCase().includes(needle);
    });

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
        if (confirm(t('chat.deleteConfirm'))) {
            onDeleteChat(id);
        }
    };

    const handleNavigateChat = (id: number) => {
        navigate(`/chats/${id}`);
        onCloseSidebar?.();
    };

    return (
        <div className="w-full md:w-72 flex flex-col h-full bg-gray-50 border-r border-gray-200 relative z-20 dark:bg-gray-950 dark:border-white/5">
            {/* Header Area */}
            <div className="p-4 space-y-4">
                <button
                    onClick={() => {
                        onNewChat();
                        onCloseSidebar?.();
                    }}
                    className="w-full group flex items-center justify-center gap-2 bg-primary-600 hover:bg-primary-500 text-white rounded-xl py-3 px-4 transition-all duration-200 shadow-lg shadow-primary-900/20 font-medium"
                >
                    <Plus size={20} className="group-hover:scale-110 transition-transform" />
                    <span>{t('chat.newChat')}</span>
                </button>

                <div className="relative group">
                    <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400 group-focus-within:text-primary-500 transition-colors dark:text-gray-500 dark:group-focus-within:text-primary-400" />
                    <input
                        type="text"
                        placeholder={t('chat.searchChats')}
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                    className="w-full bg-white border border-gray-200 rounded-lg py-2 pl-9 pr-3 text-sm text-gray-700 focus:outline-none focus:ring-1 focus:ring-primary-500/50 focus:bg-white transition-all placeholder:text-gray-400 dark:bg-gray-900/50 dark:border-white/5 dark:text-gray-300 dark:focus:bg-gray-900 dark:placeholder:text-gray-600"
                />
            </div>
            </div>

            {/* Chat List */}
            <div className="flex-1 overflow-y-auto px-3 pb-2 space-y-1">
                <div className="text-xs font-semibold text-gray-500 uppercase tracking-wider px-3 py-2 mb-1 dark:text-gray-500">
                    {t('chat.recentChats')}
                </div>

                {filteredChats.map(chat => (
                    <div
                        key={chat.id}
                        onClick={() => handleNavigateChat(chat.id)}
                        className={clsx(
                            "group relative flex items-center gap-3 p-3 rounded-xl cursor-pointer transition-all duration-200 border border-transparent",
                            activeChatId === chat.id
                                ? "bg-white text-gray-950 shadow-sm border-gray-200 dark:bg-gray-800/80 dark:text-white dark:shadow-md dark:border-white/5"
                                : "text-gray-500 hover:bg-white hover:text-gray-900 dark:text-gray-400 dark:hover:bg-gray-800/40 dark:hover:text-gray-200"
                        )}
                    >
                        <div className={clsx(
                            "w-8 h-8 rounded-lg flex items-center justify-center shrink-0 transition-colors",
                            activeChatId === chat.id ? "bg-primary-500/15 text-primary-600 dark:bg-primary-500/20 dark:text-primary-400" : "bg-gray-100 text-gray-500 group-hover:bg-gray-200 dark:bg-gray-800 dark:group-hover:bg-gray-700"
                        )}>
                            <MessageSquare size={16} />
                        </div>

                        {editingId === chat.id ? (
                            <div className="flex items-center gap-1 flex-1 min-w-0 animate-in fade-in zoom-in-95 duration-200">
                                <input
                                    value={editTitle}
                                    onChange={(e) => setEditTitle(e.target.value)}
                                    onClick={(e) => e.stopPropagation()}
                                    className="bg-white text-gray-950 text-sm p-1 rounded w-full outline-none border border-primary-500/50 focus:border-primary-500 dark:bg-gray-950 dark:text-white"
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
                                    <span className="truncate text-sm font-medium leading-tight">{displayChatTitle(chat.title)}</span>
                                    <span className="truncate text-xs text-gray-500 font-normal">
                                        {chat.messages && chat.messages.length > 0
                                            ? chat.messages[chat.messages.length - 1].content.substring(0, 30) + "..."
                                            : t('chat.noMessagesYet')}
                                    </span>
                                </div>

                                {/* Hover Actions */}
                                <div className={clsx(
                                    "absolute right-2 flex items-center gap-1 bg-white/95 backdrop-blur-sm rounded-lg p-1 shadow-sm transition-opacity duration-200 dark:bg-gray-800/90",
                                    "opacity-0 group-hover:opacity-100",
                                    activeChatId === chat.id ? "bg-white dark:bg-gray-800" : ""
                                )}>
                                    <button onClick={(e) => startEditing(e, chat)} className="p-1.5 text-gray-500 hover:text-primary-600 hover:bg-gray-100 rounded-md transition-colors dark:text-gray-400 dark:hover:text-primary-400 dark:hover:bg-white/5" title={t('common.rename')}>
                                        <Edit2 size={13} />
                                    </button>
                                    <button onClick={(e) => handleDelete(e, chat.id)} className="p-1.5 text-gray-500 hover:text-red-500 hover:bg-red-50 rounded-md transition-colors dark:text-gray-400 dark:hover:text-red-400 dark:hover:bg-white/5" title={t('common.delete')}>
                                        <Trash2 size={13} />
                                    </button>
                                </div>
                            </>
                        )}
                    </div>
                ))}

                {filteredChats.length === 0 && (
                    <div className="text-center py-8 text-gray-400 text-sm dark:text-gray-600">
                        {t('chat.noChatsFound')}
                    </div>
                )}
            </div>

            {/* Footer */}
            <div className="p-4 border-t border-gray-200 bg-white/60 backdrop-blur-sm dark:border-white/5 dark:bg-gray-950/50">
                <div className="flex items-center gap-3 px-3 py-2.5 rounded-xl bg-white border border-gray-200 mb-3 dark:bg-gray-900/60 dark:border-white/5">
                    <div className="w-9 h-9 rounded-lg bg-primary-500/15 text-primary-600 flex items-center justify-center dark:bg-primary-500/20 dark:text-primary-400">
                        <UserIcon size={18} />
                    </div>
                    <div className="min-w-0">
                        <p className="text-xs text-gray-500">{t('chat.signedInAs')}</p>
                        <p className="text-sm text-gray-950 font-medium truncate dark:text-white">{user?.email || "..."}</p>
                    </div>
                </div>

                <Link
                    to="/profile"
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-500 hover:text-gray-950 hover:bg-white transition-all duration-200 group mb-2 dark:text-gray-400 dark:hover:text-white dark:hover:bg-white/5"
                >
                    <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center group-hover:bg-primary-500/15 group-hover:text-primary-600 transition-colors dark:bg-gray-800 dark:group-hover:bg-primary-500/20 dark:group-hover:text-primary-400">
                        <UserIcon size={18} />
                    </div>
                    <div className="flex-1">
                        <p className="text-sm font-medium">{t('chat.myProfile')}</p>
                        <p className="text-xs text-gray-500">{t('chat.securityAndAccount')}</p>
                    </div>
                </Link>

                <Link
                    to="/metrics"
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl text-gray-500 hover:text-gray-950 hover:bg-white transition-all duration-200 group dark:text-gray-400 dark:hover:text-white dark:hover:bg-white/5"
                >
                    <div className="w-8 h-8 rounded-lg bg-gray-100 flex items-center justify-center group-hover:bg-primary-500/15 group-hover:text-primary-600 transition-colors dark:bg-gray-800 dark:group-hover:bg-primary-500/20 dark:group-hover:text-primary-400">
                        <BarChart2 size={18} />
                    </div>
                    <span className="text-sm font-medium">{t('chat.metricsDashboard')}</span>
                </Link>
                <div className="mt-3 flex flex-wrap gap-2">
                    <ThemeToggle compact />
                    <LanguageSwitcher compact />
                </div>
            </div>
        </div>
    );
};
