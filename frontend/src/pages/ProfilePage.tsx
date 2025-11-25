import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    changePassword,
    fetchCurrentUser,
    User,
    fetchMemories,
    addMemory,
    deleteMemory,
    MemoryItem
} from '../api/client';
import { useAuth } from '../context/AuthContext';
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
    Link2
} from 'lucide-react';

const memoryCategories = [
    { id: 'profile', label: 'Профіль' },
    { id: 'preference', label: 'Уподобання' },
    { id: 'project', label: 'Проєкти' },
    { id: 'constraint', label: 'Обмеження' },
    { id: 'other', label: 'Інше' }
];

export const ProfilePage: React.FC = () => {
    const navigate = useNavigate();
    const { user, logout } = useAuth();

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

    useEffect(() => {
        if (!user) {
            loadProfile();
        } else {
            setProfile(user);
        }
        loadMemories();
    }, [user]);

    const loadProfile = async () => {
        setLoadingProfile(true);
        setError("");
        try {
            const res = await fetchCurrentUser();
            setProfile(res.data);
        } catch (err: any) {
            setError(err.response?.data?.detail || "Не вдалося завантажити профіль");
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
            setMemoryError(err.response?.data?.detail || "Не вдалося завантажити пам'ять");
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
            setError("Новий пароль і підтвердження не збігаються");
            return;
        }

        setSaving(true);
        try {
            await changePassword({
                current_password: currentPassword,
                new_password: newPassword
            });
            setSuccess("Пароль успішно оновлено");
            setCurrentPassword("");
            setNewPassword("");
            setConfirmPassword("");
        } catch (err: any) {
            setError(err.response?.data?.detail || "Не вдалося оновити пароль");
        } finally {
            setSaving(false);
        }
    };

    const formatDate = (iso?: string) => {
        if (!iso) return "—";
        return new Date(iso).toLocaleString('uk-UA', {
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
            setMemoryError(err.response?.data?.detail || "Не вдалося додати пам'ять");
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
            setMemoryError(err.response?.data?.detail || "Не вдалося видалити пам'ять");
        }
    };

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
                            <span>Назад</span>
                        </button>
                        <div>
                            <p className="text-sm text-gray-500">Акаунт</p>
                            <h1 className="text-2xl font-semibold text-white">Профіль та безпека</h1>
                        </div>
                    </div>
                    <button
                        onClick={handleLogout}
                        className="inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-red-600 hover:bg-red-500 text-white transition-colors shadow-lg shadow-red-900/20"
                    >
                        <LogOut size={16} />
                        <span>Вийти</span>
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
                                <p className="text-sm text-gray-500">Основна інформація</p>
                                <h2 className="text-lg font-semibold text-white">Профіль</h2>
                            </div>
                        </div>

                        {loadingProfile ? (
                            <div className="flex items-center gap-3 text-gray-500">
                                <Loader2 className="animate-spin" size={18} />
                                <span>Завантаження профілю...</span>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                <div className="flex items-center gap-3 bg-gray-800/40 border border-white/5 rounded-xl p-4">
                                    <Mail size={18} className="text-primary-400" />
                                    <div>
                                        <p className="text-xs text-gray-500">Email</p>
                                        <p className="text-sm text-white font-medium break-all">{profile?.email}</p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 bg-gray-800/40 border border-white/5 rounded-xl p-4">
                                    <ShieldCheck size={18} className="text-primary-400" />
                                    <div>
                                        <p className="text-xs text-gray-500">Роль</p>
                                        <p className="text-sm text-white font-medium">
                                            {profile?.is_admin ? "Адміністратор" : "Користувач"}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-3 bg-gray-800/40 border border-white/5 rounded-xl p-4">
                                    <CalendarDays size={18} className="text-primary-400" />
                                    <div>
                                        <p className="text-xs text-gray-500">З нами з</p>
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
                                <p className="text-sm text-gray-500">Безпека</p>
                                <h2 className="text-lg font-semibold text-white">Змінити пароль</h2>
                            </div>
                        </div>

                        <form onSubmit={handlePasswordChange} className="space-y-4">
                            <div>
                                <label className="block text-sm text-gray-400 mb-1.5">Поточний пароль</label>
                                <input
                                    type="password"
                                    required
                                    value={currentPassword}
                                    onChange={(e) => setCurrentPassword(e.target.value)}
                                    className="w-full bg-gray-800/60 border border-white/10 rounded-xl py-2.5 px-4 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                                />
                            </div>
                            <div>
                                <label className="block text-sm text-gray-400 mb-1.5">Новий пароль</label>
                                <input
                                    type="password"
                                    required
                                    value={newPassword}
                                    onChange={(e) => setNewPassword(e.target.value)}
                                    className="w-full bg-gray-800/60 border border-white/10 rounded-xl py-2.5 px-4 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                                />
                            </div>
                            <div>
                                <label className="block text-sm text-gray-400 mb-1.5">Підтвердження паролю</label>
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
                                    <span>Оновити пароль</span>
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
                                    Очистити
                                </button>
                            </div>
                        </form>
                    </div>
                </div>

                <div className="mt-6 bg-gray-900/60 border border-white/5 rounded-2xl p-6 shadow-xl shadow-black/20">
                    <div className="flex items-center justify-between mb-6">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-xl bg-primary-500/10 text-primary-300 flex items-center justify-center">
                                <Link2 size={22} />
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Інтеграції</p>
                                <h2 className="text-lg font-semibold text-white">Google OAuth</h2>
                            </div>
                        </div>
                    </div>
                    <p className="text-sm text-gray-400 mb-4">
                        Підключіть Gmail та Google Calendar, щоб секретар-агент міг читати пошту та події.
                    </p>
                    <div className="flex items-center gap-3">
                        <button
                            onClick={async () => {
                                try {
                                    setGoogleConnecting(true);
                                    const res = await fetch('/api/auth/google/login', {
                                        headers: {
                                            'Authorization': localStorage.getItem('token') ? `Bearer ${localStorage.getItem('token')}` : ''
                                        }
                                    });
                                    const data = await res.json();
                                    if (data.url) {
                                        window.location.href = data.url;
                                    } else {
                                        alert('Не вдалося отримати Google OAuth URL');
                                    }
                                } catch (err) {
                                    console.error('Google connect failed', err);
                                    alert('Не вдалося ініціювати OAuth, спробуйте ще раз.');
                                } finally {
                                    setGoogleConnecting(false);
                                }
                            }}
                            disabled={googleConnecting}
                            className="px-4 py-2.5 bg-primary-600 hover:bg-primary-500 disabled:opacity-60 text-white rounded-xl font-medium transition-all shadow-lg shadow-primary-900/20"
                        >
                            {googleConnecting ? 'Підключення...' : 'Підключити Google'}
                        </button>
                        <div className="flex items-center gap-2 text-sm text-gray-400">
                            <label className="flex items-center gap-2 cursor-pointer">
                                <input
                                    type="checkbox"
                                    checked={autoSecretary}
                                    onChange={(e) => handleToggleAutoSecretary(e.target.checked)}
                                    className="accent-primary-500"
                                />
                                <span>Автозапуск секретаря за ключовими словами</span>
                            </label>
                        </div>
                    </div>
                </div>

                <div className="mt-6 bg-gray-900/60 border border-white/5 rounded-2xl p-6 shadow-xl shadow-black/20">
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-3">
                            <div className="w-12 h-12 rounded-xl bg-primary-500/10 text-primary-300 flex items-center justify-center">
                                <Brain size={22} />
                            </div>
                            <div>
                                <p className="text-sm text-gray-500">Пам'ять про користувача</p>
                                <h2 className="text-lg font-semibold text-white">Факти для збереження</h2>
                            </div>
                        </div>
                    </div>

                    <form onSubmit={handleAddMemory} className="grid grid-cols-1 md:grid-cols-4 gap-3 mb-4">
                        <div className="md:col-span-1">
                            <label className="block text-xs text-gray-500 mb-1">Категорія</label>
                            <select
                                value={memoryForm.category}
                                onChange={(e) => setMemoryForm({ ...memoryForm, category: e.target.value })}
                                className="w-full bg-gray-800/60 border border-white/10 rounded-xl py-2.5 px-3 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                            >
                                {memoryCategories.map((c) => (
                                    <option key={c.id} value={c.id} className="bg-gray-900 text-gray-100">
                                        {c.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div className="md:col-span-1">
                            <label className="block text-xs text-gray-500 mb-1">Ключ</label>
                            <input
                                value={memoryForm.key}
                                onChange={(e) => setMemoryForm({ ...memoryForm, key: e.target.value })}
                                required
                                className="w-full bg-gray-800/60 border border-white/10 rounded-xl py-2.5 px-3 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                                placeholder="name, language, likes..."
                            />
                        </div>
                        <div className="md:col-span-1">
                            <label className="block text-xs text-gray-500 mb-1">Значення</label>
                            <input
                                value={memoryForm.value}
                                onChange={(e) => setMemoryForm({ ...memoryForm, value: e.target.value })}
                                required
                                className="w-full bg-gray-800/60 border border-white/10 rounded-xl py-2.5 px-3 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                                placeholder="Наприклад: Відповідай українською"
                            />
                        </div>
                        <div className="md:col-span-1 flex items-end gap-2">
                            <button
                                type="submit"
                                disabled={memorySaving}
                                className="w-full inline-flex items-center justify-center gap-2 px-4 py-2.5 bg-primary-600 hover:bg-primary-500 disabled:opacity-60 text-white rounded-xl font-medium transition-all shadow-lg shadow-primary-900/20"
                            >
                                {memorySaving ? <Loader2 className="animate-spin" size={18} /> : <Plus size={18} />}
                                <span>Додати</span>
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
                            <span>Завантаження пам'яті...</span>
                        </div>
                    ) : (
                        <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
                            {memories.map((m) => (
                                <div key={m.id} className="bg-gray-800/40 border border-white/5 rounded-xl p-4 relative">
                                    <div className="flex items-start justify-between gap-2">
                                        <div>
                                            <p className="text-xs text-gray-500 uppercase tracking-wide">{m.category}</p>
                                            <p className="text-sm font-semibold text-white">{m.key}</p>
                                        </div>
                                        <button
                                            onClick={() => handleDeleteMemory(m.id)}
                                            className="text-gray-400 hover:text-red-400 transition-colors"
                                        >
                                            <Trash2 size={16} />
                                        </button>
                                    </div>
                                    <p className="text-sm text-gray-300 mt-2">{m.value}</p>
                                    <div className="text-xs text-gray-500 mt-3 flex justify-between">
                                        <span>Довіра: {(m.confidence * 100).toFixed(0)}%</span>
                                        <span>{new Date(m.created_at).toLocaleDateString('uk-UA')}</span>
                                    </div>
                                </div>
                            ))}
                            {memories.length === 0 && (
                                <div className="text-gray-500 text-sm">Поки що немає збережених фактів.</div>
                            )}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
