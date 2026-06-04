import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    changePassword,
    fetchCurrentUser,
    User,
    fetchMemories,
    addMemory,
    deleteMemory,
    MemoryItem,
    getConnectedAccounts,
    ConnectedAccounts,
    deleteAccount,
    updateAccountLabel
} from '../api/client';
import { useAuth } from '../context/AuthContext';
import { useI18n } from '../i18n/I18nProvider';
import {
    ArrowLeft,
    CalendarDays,
    CheckCircle2,
    KeyRound,
    Loader2,
    LogOut,
    Mail,
    ShieldCheck,
    User as UserIcon,
    AlertCircle,
    Brain,
    Plus,
    Trash2,
    Link2,
    Pencil
} from 'lucide-react';
import { PushSubscriptionManager } from '../components/PushSubscriptionManager';

const memoryCategoryIds = ['profile', 'preference', 'project', 'constraint', 'other'];
const accountLabels = ['personal', 'work', 'other'];

export const ProfilePage: React.FC = () => {
    const navigate = useNavigate();
    const { user, logout } = useAuth();
    const { language, t, translateApiError } = useI18n();

    const [profile, setProfile] = useState<User | null>(user);
    const [loadingProfile, setLoadingProfile] = useState(!user);
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [saving, setSaving] = useState(false);
    const [success, setSuccess] = useState("");
    const [error, setError] = useState("");

    const [memories, setMemories] = useState<MemoryItem[]>([]);
    const [memoryLoading, setMemoryLoading] = useState(false);
    const [memoryError, setMemoryError] = useState("");
    const [memoryForm, setMemoryForm] = useState({
        category: 'profile',
        key: '',
        value: '',
        confidence: 0.8
    });
    const [memorySaving, setMemorySaving] = useState(false);
    const [autoSecretary, setAutoSecretary] = useState<boolean>(() => {
        const stored = localStorage.getItem('auto_secretary');
        return stored === 'true';
    });
    const [googleConnecting, setGoogleConnecting] = useState(false);
    const [microsoftConnecting, setMicrosoftConnecting] = useState(false);
    const [accounts, setAccounts] = useState<ConnectedAccounts>({ google: [], microsoft: [] });
    const [loadingAccounts, setLoadingAccounts] = useState(false);

    useEffect(() => {
        if (!user) {
            loadProfile();
        } else {
            setProfile(user);
        }
        loadMemories();
        loadAccounts();
    }, [user]);

    const loadAccounts = async () => {
        setLoadingAccounts(true);
        try {
            const res = await getConnectedAccounts();
            setAccounts(res.data || { google: [], microsoft: [] });
        } catch (err) {
            console.error("Failed to load accounts", err);
        } finally {
            setLoadingAccounts(false);
        }
    };

    const handleDeleteAccount = async (provider: 'google' | 'microsoft', id: number) => {
        if (!window.confirm(t('profile.confirmDeleteAccount'))) return;

        try {
            await deleteAccount(provider, id);
            await loadAccounts();
            setSuccess(t('profile.accountDeleted'));
            setTimeout(() => setSuccess(''), 3000);
        } catch (err: any) {
            setError(translateApiError(err.response?.data?.detail, 'profile.deleteAccountFailed'));
        }
    };

    const handleUpdateLabel = async (provider: 'google' | 'microsoft', id: number, currentLabel: string) => {
        const newLabel = window.prompt(t('profile.newLabelPrompt'), currentLabel);
        if (!newLabel || newLabel === currentLabel) return;

        if (!accountLabels.includes(newLabel)) {
            alert(t('profile.invalidLabel'));
            return;
        }

        try {
            await updateAccountLabel(provider, id, newLabel);
            await loadAccounts();
            setSuccess(t('profile.labelUpdated'));
            setTimeout(() => setSuccess(''), 3000);
        } catch (err: any) {
            setError(translateApiError(err.response?.data?.detail, 'profile.labelUpdateFailed'));
        }
    };

    const loadProfile = async () => {
        setLoadingProfile(true);
        setError("");
        try {
            const res = await fetchCurrentUser();
            setProfile(res.data);
        } catch (err: any) {
            setError(translateApiError(err.response?.data?.detail, 'profile.profileLoadFailed'));
        } finally {
            setLoadingProfile(false);
        }
    };

    const loadMemories = async () => {
        setMemoryLoading(true);
        setMemoryError("");
        try {
            const res = await fetchMemories();
            setMemories(res.data);
        } catch (err: any) {
            setMemoryError(translateApiError(err.response?.data?.detail, 'profile.memoryLoadFailed'));
        } finally {
            setMemoryLoading(false);
        }
    };

    const handleLogout = () => {
        logout();
        navigate('/login');
    };

    const handlePasswordChange = async (e: React.FormEvent) => {
        e.preventDefault();
        setError("");
        setSuccess("");

        if (newPassword !== confirmPassword) {
            setError(t('profile.passwordMismatch'));
            return;
        }

        setSaving(true);
        try {
            await changePassword({
                current_password: currentPassword,
                new_password: newPassword
            });
            setSuccess(t('profile.passwordUpdated'));
            setCurrentPassword("");
            setNewPassword("");
            setConfirmPassword("");
        } catch (err: any) {
            setError(translateApiError(err.response?.data?.detail, 'errors.passwordUpdateFailed'));
        } finally {
            setSaving(false);
        }
    };

    const formatDate = (iso?: string) => {
        if (!iso) return "-";
        return new Date(iso).toLocaleString(language === 'uk' ? 'uk-UA' : 'en-US', {
            dateStyle: 'medium',
            timeStyle: 'short'
        });
    };

    const handleAddMemory = async (e: React.FormEvent) => {
        e.preventDefault();
        setMemoryError("");
        setMemorySaving(true);
        try {
            const res = await addMemory(memoryForm);
            setMemories([res.data, ...memories]);
            setMemoryForm({ category: 'profile', key: '', value: '', confidence: 0.8 });
        } catch (err: any) {
            setMemoryError(translateApiError(err.response?.data?.detail, 'profile.memoryAddFailed'));
        } finally {
            setMemorySaving(false);
        }
    };

    const handleToggleAutoSecretary = (value: boolean) => {
        setAutoSecretary(value);
        localStorage.setItem('auto_secretary', value ? 'true' : 'false');
    };

    const handleDeleteMemory = async (id: number) => {
        setMemoryError("");
        try {
            await deleteMemory(id);
            setMemories(memories.filter(m => m.id !== id));
        } catch (err: any) {
            setMemoryError(translateApiError(err.response?.data?.detail, 'profile.memoryDeleteFailed'));
        }
    };

    const startOAuth = async (provider: 'google' | 'microsoft') => {
        const setConnecting = provider === 'google' ? setGoogleConnecting : setMicrosoftConnecting;
        const urlErrorKey = provider === 'google' ? 'profile.googleOauthFailed' : 'profile.microsoftOauthFailed';

        try {
            setConnecting(true);
            const res = await fetch(`/api/auth/${provider}/login`, {
                headers: {
                    'Authorization': localStorage.getItem('token') ? `Bearer ${localStorage.getItem('token')}` : ''
                }
            });
            const data = await res.json();
            if (data.url) {
                window.location.href = data.url;
            } else {
                alert(t(urlErrorKey));
            }
        } catch (err) {
            console.error(`${provider} connect failed`, err);
            alert(t('profile.oauthStartFailed'));
        } finally {
            setConnecting(false);
        }
    };

    const categoryLabel = (category: string) => {
        const key = `memory.${category}`;
        const translated = t(key);
        return translated === key ? category : translated;
    };

    const accountLabel = (label: string) => {
        const key = `profile.label.${label}`;
        const translated = t(key);
        return translated === key ? label : translated;
    };

    const renderAccount = (provider: 'google' | 'microsoft', acc: { id?: number; email: string; label: string }) => (
        <div key={`${provider}-${acc.id ?? acc.email}`} className="flex items-center justify-between bg-gray-800/40 border border-white/5 rounded-xl p-3">
            <div className="flex items-center gap-3">
                <div className={provider === 'google'
                    ? "w-8 h-8 rounded-lg bg-white flex items-center justify-center text-black font-bold text-xs"
                    : "w-8 h-8 rounded-lg bg-gray-700 flex items-center justify-center text-white font-bold text-xs"
                }>
                    {provider === 'google' ? 'G' : 'MS'}
                </div>
                <div>
                    <p className="text-sm font-medium text-white">{acc.email}</p>
                    <p className="text-xs text-gray-500">{provider === 'google' ? 'Google' : 'Microsoft'} • {accountLabel(acc.label)}</p>
                </div>
            </div>
            <div className="flex items-center gap-2">
                <button
                    onClick={() => acc.id && handleUpdateLabel(provider, acc.id, acc.label)}
                    className="p-1.5 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                    title={t('profile.changeLabel')}
                >
                    <Pencil size={14} />
                </button>
                <button
                    onClick={() => acc.id && handleDeleteAccount(provider, acc.id)}
                    className="p-1.5 text-gray-400 hover:text-red-400 hover:bg-red-500/10 rounded-lg transition-colors"
                    title={t('profile.deleteAccount')}
                >
                    <Trash2 size={14} />
                </button>
            </div>
        </div>
    );

    return (
        <div className="min-h-screen bg-gray-950 text-gray-100">
            <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,_var(--tw-gradient-stops))] from-gray-900 via-gray-950 to-gray-950 pointer-events-none" />
            <div className="relative max-w-5xl mx-auto px-4 py-10">
                <div className="flex items-center justify-between gap-4 mb-8">
                    <div className="flex items-center gap-3">
                        <button
                            onClick={() => navigate(-1)}
                            className="inline-flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
                        >
                            <ArrowLeft size={18} />
                            <span>{t('common.back')}</span>
                        </button>
                        <div>
                            <p className="text-sm text-gray-500">{t('profile.account')}</p>
                            <h1 className="text-2xl font-semibold text-white">{t('profile.title')}</h1>
                        </div>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white transition-colors shadow-lg shadow-red-900/20"
                    >
                        <LogOut size={16} />
                        <span>{t('profile.logout')}</span>
                    </button>
                </div>

                {(error || success) && (
                    <div className="mb-6 space-y-3">
                        {error && (
                            <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-200 px-4 py-3 rounded-lg text-sm">
                                <AlertCircle size={16} />
                                <span>{error}</span>
                            </div>
                        )}
                        {success && (
                            <div className="flex items-center gap-2 bg-emerald-500/10 border border-emerald-500/30 text-emerald-200 px-4 py-3 rounded-lg text-sm">
                                <CheckCircle2 size={16} />
                                <span>{success}</span>
                            </div>
                        )}
                    </div>
                )}

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    <div className="bg-gray-900/60 border border-white/5 rounded-2xl p-6 shadow-xl shadow-black/20">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-12 h-12 rounded-xl bg-primary-500/10 text-primary-300 flex items-center justify-center">
                                <UserIcon size={22} />
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">{t('profile.basicInfo')}</p>
                                <h2 className="text-lg font-semibold text-white">{t('profile.profile')}</h2>
                            </div>
                        </div>

                        {loadingProfile ? (
                            <div className="flex items-center gap-3 text-gray-500">
                                <Loader2 className="animate-spin" size={18} />
                                <span>{t('profile.loadingProfile')}</span>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="flex items-center gap-3 bg-gray-800/40 border border-white/5 rounded-xl p-4">
                                    <Mail size={18} className="text-primary-400" />
                                    <div>
                                        <p className="text-xs text-gray-500">{t('common.email')}</p>
                                        <p className="text-sm text-white font-medium break-all">{profile?.email}</p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 bg-gray-800/40 border border-white/5 rounded-xl p-4">
                                    <ShieldCheck size={18} className="text-primary-400" />
                                    <div>
                                        <p className="text-xs text-gray-500">{t('profile.role')}</p>
                                        <p className="text-sm text-white font-medium">
                                            {profile?.is_admin ? t('common.admin') : t('common.user')}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 bg-gray-800/40 border border-white/5 rounded-xl p-4">
                                    <CalendarDays size={18} className="text-primary-400" />
                                    <div>
                                        <p className="text-xs text-gray-500">{t('profile.memberSince')}</p>
                                        <p className="text-sm text-white font-medium">{formatDate(profile?.created_at)}</p>
                                    </div>
                                </div>
                            </div>
                        )}
                    </div>

                    <div className="bg-gray-900/60 border border-white/5 rounded-2xl p-6 shadow-xl shadow-black/20">
                        <div className="flex items-center gap-3 mb-6">
                            <div className="w-12 h-12 rounded-xl bg-primary-500/10 text-primary-300 flex items-center justify-center">
                                <KeyRound size={22} />
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">{t('profile.security')}</p>
                                <h2 className="text-lg font-semibold text-white">{t('profile.changePassword')}</h2>
                            </div>
                        </div>

                        <form onSubmit={handlePasswordChange} className="space-y-4">
                            <div>
                                <label className="block text-sm text-gray-400 mb-1.5">{t('profile.currentPassword')}</label>
                                <input
                                    type="password"
                                    required
                                    value={currentPassword}
                                    onChange={(e) => setCurrentPassword(e.target.value)}
                                    className="w-full bg-gray-800/60 border border-white/10 rounded-xl py-2.5 px-4 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                                />
                            </div>
                            <div>
                                <label className="block text-sm text-gray-400 mb-1.5">{t('profile.newPassword')}</label>
                                <input
                                    type="password"
                                    required
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="w-full bg-gray-800/60 border border-white/10 rounded-xl py-2.5 px-4 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                                />
                            </div>
                            <div>
                                <label className="block text-sm text-gray-400 mb-1.5">{t('profile.confirmPassword')}</label>
                                <input
                                    type="password"
                                    required
                                    value={confirmPassword}
                                    onChange={(e) => setConfirmPassword(e.target.value)}
                                    className="w-full bg-gray-800/60 border border-white/10 rounded-xl py-2.5 px-4 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                                />
                            </div>

                            <div className="flex items-center justify-between gap-3 pt-2">
                                <button
                                    type="submit"
                                    disabled={saving}
                                    className="inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-500 disabled:opacity-60 text-white rounded-xl font-medium transition-all shadow-lg shadow-primary-900/20"
                                >
                                    {saving ? <Loader2 className="animate-spin" size={18} /> : <CheckCircle2 size={18} />}
                                    <span>{t('profile.updatePassword')}</span>
                                </button>
                                <button
                                    type="button"
                                    onClick={() => {
                                        setCurrentPassword("");
                                        setNewPassword("");
                                        setConfirmPassword("");
                                        setError("");
                                        setSuccess("");
                                    }}
                                    className="text-gray-400 hover:text-white text-sm transition-colors"
                                >
                                    {t('common.clear')}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>

                <div className="mt-6 bg-gray-900/60 border border-white/5 rounded-2xl p-6 shadow-xl shadow-black/20">
                    <div className="flex items-center gap-3 mb-6">
                        <div className="w-12 h-12 rounded-xl bg-primary-500/10 text-primary-300 flex items-center justify-center">
                            <Link2 size={22} />
                        </div>
                        <div>
                            <p className="text-sm text-gray-500">{t('profile.integrations')}</p>
                            <h2 className="text-lg font-semibold text-white">{t('profile.connectedAccounts')}</h2>
                        </div>
                    </div>

                    <div className="space-y-4 mb-6">
                        {loadingAccounts ? (
                            <div className="flex items-center gap-2 text-gray-500 text-sm">
                                <Loader2 className="animate-spin" size={14} />
                                <span>{t('profile.loadingAccounts')}</span>
                            </div>
                        ) : (
                            <>
                                {(!accounts?.google?.length && !accounts?.microsoft?.length) && (
                                    <p className="text-sm text-gray-500 italic">{t('profile.noConnectedAccounts')}</p>
                                )}

                                {(accounts?.google || []).map((acc: any) => renderAccount('google', acc))}
                                {(accounts?.microsoft || []).map((acc: any) => renderAccount('microsoft', acc))}
                            </>
                        )}
                    </div>

                    <div className="flex flex-wrap items-center gap-3">
                        <button
                            onClick={() => startOAuth('google')}
                            disabled={googleConnecting}
                            className="px-4 py-2.5 bg-white text-gray-900 hover:bg-gray-100 disabled:opacity-60 rounded-xl font-medium transition-all shadow-lg shadow-white/5 flex items-center gap-2"
                        >
                            {googleConnecting ? <Loader2 className="animate-spin" size={16} /> : <span>Google</span>}
                            <span>{googleConnecting ? t('common.connecting') : t('profile.connectGoogle')}</span>
                        </button>

                        <button
                            onClick={() => startOAuth('microsoft')}
                            disabled={microsoftConnecting}
                            className="px-4 py-2.5 bg-gray-700 text-white hover:bg-gray-600 disabled:opacity-60 rounded-xl font-medium transition-all shadow-lg shadow-black/20 flex items-center gap-2"
                        >
                            {microsoftConnecting ? <Loader2 className="animate-spin" size={16} /> : <span>Microsoft</span>}
                            <span>{microsoftConnecting ? t('common.connecting') : t('profile.connectMicrosoft')}</span>
                        </button>
                    </div>

                    <div className="mt-4 pt-4 border-t border-white/5">
                        <label className="flex items-center gap-2 cursor-pointer text-sm text-gray-400 hover:text-gray-300 transition-colors">
                            <input
                                type="checkbox"
                                checked={autoSecretary}
                                onChange={(e) => handleToggleAutoSecretary(e.target.checked)}
                                className="accent-primary-500 w-4 h-4 rounded border-gray-600 bg-gray-700"
                            />
                            <span>{t('profile.autoSecretary')}</span>
                        </label>
                    </div>
                </div>

                <div className="mt-6 bg-gray-900/60 border border-white/5 rounded-2xl p-6 shadow-xl shadow-black/20">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-xl bg-primary-500/10 text-primary-300 flex items-center justify-center">
                                <Brain size={22} />
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">{t('profile.userMemory')}</p>
                                <h2 className="text-lg font-semibold text-white">{t('profile.factsToSave')}</h2>
                            </div>
                        </div>
                    </div>

                    <form onSubmit={handleAddMemory} className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
                        <div className="md:col-span-1">
                            <label className="block text-xs text-gray-500 mb-1">{t('profile.category')}</label>
                            <select
                                value={memoryForm.category}
                                onChange={(e) => setMemoryForm({ ...memoryForm, category: e.target.value })}
                                className="w-full bg-gray-800/60 border border-white/10 rounded-xl py-2.5 px-3 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                            >
                                {memoryCategoryIds.map((id) => (
                                    <option key={id} value={id} className="bg-gray-900 text-gray-100">
                                        {categoryLabel(id)}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="md:col-span-1">
                            <label className="block text-xs text-gray-500 mb-1">{t('profile.key')}</label>
                            <input
                                value={memoryForm.key}
                                onChange={(e) => setMemoryForm({ ...memoryForm, key: e.target.value })}
                                required
                                className="w-full bg-gray-800/60 border border-white/10 rounded-xl py-2.5 px-3 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                                placeholder={t('profile.keyPlaceholder')}
                            />
                        </div>
                        <div className="md:col-span-1">
                            <label className="block text-xs text-gray-500 mb-1">{t('profile.value')}</label>
                            <input
                                value={memoryForm.value}
                                onChange={(e) => setMemoryForm({ ...memoryForm, value: e.target.value })}
                                required
                                className="w-full bg-gray-800/60 border border-white/10 rounded-xl py-2.5 px-3 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                                placeholder={t('profile.valuePlaceholder')}
                            />
                        </div>
                        <div className="md:col-span-1 flex items-end gap-2">
                            <button
                                type="submit"
                                disabled={memorySaving}
                                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-500 disabled:opacity-60 text-white rounded-xl font-medium transition-all shadow-lg shadow-primary-900/20"
                            >
                                {memorySaving ? <Loader2 className="animate-spin" size={18} /> : <Plus size={18} />}
                                <span>{t('profile.add')}</span>
                            </button>
                        </div>
                    </form>

                    {memoryError && (
                        <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/30 text-red-200 px-4 py-3 rounded-lg text-sm mb-4">
                            <AlertCircle size={16} />
                            <span>{memoryError}</span>
                        </div>
                    )}

                    {memoryLoading ? (
                        <div className="flex items-center gap-3 text-gray-500">
                            <Loader2 className="animate-spin" size={18} />
                            <span>{t('profile.loadingMemory')}</span>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {memories.map((m) => (
                                <div key={m.id} className="bg-gray-800/40 border border-white/5 rounded-xl p-4 relative">
                                    <div className="flex items-start justify-between gap-2">
                                        <div>
                                            <p className="text-xs text-gray-500 uppercase tracking-wide">{categoryLabel(m.category)}</p>
                                            <p className="text-sm font-semibold text-white">{m.key}</p>
                                        </div>
                                        <button
                                            onClick={() => handleDeleteMemory(m.id)}
                                            className="text-gray-400 hover:text-red-400 transition-colors"
                                            title={t('common.delete')}
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                    <p className="text-sm text-gray-300 mt-2">{m.value}</p>
                                    <div className="text-xs text-gray-500 mt-3 flex justify-between">
                                        <span>{t('profile.confidence')}: {(m.confidence * 100).toFixed(0)}%</span>
                                        <span>{new Date(m.created_at).toLocaleDateString(language === 'uk' ? 'uk-UA' : 'en-US')}</span>
                                    </div>
                                </div>
                            ))}
                            {memories.length === 0 && (
                                <div className="text-gray-500 text-sm">{t('profile.noSavedFacts')}</div>
                            )}
                        </div>
                    )}
                </div>

                <PushSubscriptionManager />

            </div>
        </div>
    );
};
