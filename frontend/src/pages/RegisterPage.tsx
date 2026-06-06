import React, { useState } from 'react';
import { api, LoginResponse } from '../api/client';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Lock, Mail, Loader2 } from 'lucide-react';
import { useI18n } from '../i18n/I18nProvider';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { ThemeToggle } from '../components/ThemeToggle';

export const RegisterPage: React.FC = () => {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [inviteCode, setInviteCode] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const navigate = useNavigate();
    const { login } = useAuth();
    const { t, translateApiError } = useI18n();

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setLoading(true);
        setError("");

        try {
            // Register
            await api.post('/auth/register', { email, password, invite_code: inviteCode });

            // Auto-login after registration
            const formData = new FormData();
            formData.append('username', email);
            formData.append('password', password);

            const res = await api.post<LoginResponse>('/auth/login', formData);
            login(res.data.access_token);
            navigate('/');
        } catch (err: any) {
            setError(translateApiError(err.response?.data?.detail, 'errors.registrationFailed'));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4 dark:bg-gray-950">
            <div className="absolute right-4 top-4 flex flex-wrap justify-end gap-2">
                <ThemeToggle />
                <LanguageSwitcher />
            </div>
            <div className="w-full max-w-md bg-white/80 backdrop-blur-xl border border-gray-200 rounded-2xl p-8 shadow-2xl shadow-gray-200/70 dark:bg-gray-900/50 dark:border-white/10 dark:shadow-black/20">
                <div className="text-center mb-8">
                    <h1 className="text-2xl font-bold text-gray-950 mb-2 dark:text-white">{t('auth.registerTitle')}</h1>
                    <p className="text-gray-500 dark:text-gray-400">{t('auth.registerSubtitle')}</p>
                </div>

                {error && (
                    <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg mb-6 text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-600 mb-1.5 dark:text-gray-400">{t('auth.inviteCode')}</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                            <input
                                type="text"
                                value={inviteCode}
                                onChange={(e) => setInviteCode(e.target.value)}
                                className="w-full bg-white border border-gray-200 rounded-xl py-2.5 pl-10 pr-4 text-gray-950 focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all dark:bg-gray-800/50 dark:border-white/10 dark:text-white"
                                placeholder="ENTER-INVITE-CODE"
                                required
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-600 mb-1.5 dark:text-gray-400">{t('common.email')}</label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full bg-white border border-gray-200 rounded-xl py-2.5 pl-10 pr-4 text-gray-950 focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all dark:bg-gray-800/50 dark:border-white/10 dark:text-white"
                                placeholder="name@example.com"
                                required
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-600 mb-1.5 dark:text-gray-400">{t('common.password')}</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-white border border-gray-200 rounded-xl py-2.5 pl-10 pr-4 text-gray-950 focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all dark:bg-gray-800/50 dark:border-white/10 dark:text-white"
                                placeholder="••••••••"
                                required
                                minLength={6}
                            />
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={loading}
                        className="w-full bg-primary-600 hover:bg-primary-500 text-white font-medium py-2.5 rounded-xl transition-all shadow-lg shadow-primary-900/20 flex items-center justify-center gap-2 mt-6"
                    >
                        {loading ? <Loader2 className="animate-spin" size={20} /> : t('auth.createAccount')}
                    </button>
                </form>

                <div className="mt-6 text-center text-sm text-gray-500">
                    {t('auth.haveAccount')}{' '}
                    <Link to="/login" className="text-primary-700 hover:text-primary-600 font-medium dark:text-primary-400 dark:hover:text-primary-300">
                        {t('auth.signIn')}
                    </Link>
                </div>
            </div>
        </div>
    );
};
