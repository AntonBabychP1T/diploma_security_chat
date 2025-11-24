import React, { useState } from 'react';
import { api, LoginResponse } from '../api/client';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Lock, Mail, Loader2 } from 'lucide-react';

export const RegisterPage: React.FC = () => {
    const [email, setEmail] = useState("");
    const [password, setPassword] = useState("");
    const [inviteCode, setInviteCode] = useState("");
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const navigate = useNavigate();
    const { login } = useAuth();

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
            setError(err.response?.data?.detail || "Registration failed");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-950 p-4">
            <div className="w-full max-w-md bg-gray-900/50 backdrop-blur-xl border border-white/10 rounded-2xl p-8 shadow-2xl">
                <div className="text-center mb-8">
                    <h1 className="text-2xl font-bold text-white mb-2">Create Account</h1>
                    <p className="text-gray-400">Join Secure Chat today</p>
                </div>

                {error && (
                    <div className="bg-red-500/10 border border-red-500/20 text-red-400 px-4 py-3 rounded-lg mb-6 text-sm">
                        {error}
                    </div>
                )}

                <form onSubmit={handleSubmit} className="space-y-4">
                    <div>
                        <label className="block text-sm font-medium text-gray-400 mb-1.5">Invite Code</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                            <input
                                type="text"
                                value={inviteCode}
                                onChange={(e) => setInviteCode(e.target.value)}
                                className="w-full bg-gray-800/50 border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                                placeholder="ENTER-INVITE-CODE"
                                required
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-400 mb-1.5">Email</label>
                        <div className="relative">
                            <Mail className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                            <input
                                type="email"
                                value={email}
                                onChange={(e) => setEmail(e.target.value)}
                                className="w-full bg-gray-800/50 border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
                                placeholder="name@example.com"
                                required
                            />
                        </div>
                    </div>

                    <div>
                        <label className="block text-sm font-medium text-gray-400 mb-1.5">Password</label>
                        <div className="relative">
                            <Lock className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500" size={18} />
                            <input
                                type="password"
                                value={password}
                                onChange={(e) => setPassword(e.target.value)}
                                className="w-full bg-gray-800/50 border border-white/10 rounded-xl py-2.5 pl-10 pr-4 text-white focus:ring-2 focus:ring-primary-500/50 focus:border-primary-500 outline-none transition-all"
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
                        {loading ? <Loader2 className="animate-spin" size={20} /> : "Create Account"}
                    </button>
                </form>

                <div className="mt-6 text-center text-sm text-gray-500">
                    Already have an account?{' '}
                    <Link to="/login" className="text-primary-400 hover:text-primary-300 font-medium">
                        Sign in
                    </Link>
                </div>
            </div>
        </div>
    );
};
