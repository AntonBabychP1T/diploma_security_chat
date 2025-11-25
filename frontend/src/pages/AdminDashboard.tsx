import React, { useEffect, useState } from 'react';
import { api } from '../api/client';
import { PieChart, Pie, Cell, Tooltip, ResponsiveContainer } from 'recharts';
import { Users, MessageSquare, Shield, Zap, ArrowLeft } from 'lucide-react';
import { Link } from 'react-router-dom';

interface GlobalStats {
    total_users: number;
    total_messages: number;
    masked_messages: number;
    total_tokens: number;
    model_usage: Record<string, number>;
}

export const AdminDashboard: React.FC = () => {
    const [stats, setStats] = useState<GlobalStats | null>(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const res = await api.get<GlobalStats>('/metrics/global');
                setStats(res.data);
            } catch (err) {
                console.error("Failed to fetch admin stats", err);
            } finally {
                setLoading(false);
            }
        };
        fetchStats();
    }, []);

    if (loading) return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-white">Loading...</div>;
    if (!stats) return <div className="min-h-screen bg-gray-950 flex items-center justify-center text-white">Access Denied</div>;

    const modelData = Object.entries(stats.model_usage).map(([name, value]) => ({ name, value }));
    const COLORS = ['#0ea5e9', '#6366f1', '#8b5cf6', '#ec4899'];

    return (
        <div className="min-h-screen bg-gray-950 text-gray-100 p-8 font-sans">
            <div className="max-w-7xl mx-auto">
                <div className="flex items-center gap-4 mb-8">
                    <Link to="/" className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                        <ArrowLeft size={24} />
                    </Link>
                    <h1 className="text-3xl font-bold">Admin Analytics</h1>
                </div>

                {/* KPI Cards */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
                    <div className="bg-gray-900/50 border border-white/5 p-6 rounded-2xl">
                        <div className="flex items-center gap-4 mb-2">
                            <div className="p-3 bg-blue-500/10 text-blue-400 rounded-xl">
                                <Users size={24} />
                            </div>
                            <span className="text-gray-400">Total Users</span>
                        </div>
                        <div className="text-3xl font-bold">{stats.total_users}</div>
                    </div>

                    <div className="bg-gray-900/50 border border-white/5 p-6 rounded-2xl">
                        <div className="flex items-center gap-4 mb-2">
                            <div className="p-3 bg-purple-500/10 text-purple-400 rounded-xl">
                                <MessageSquare size={24} />
                            </div>
                            <span className="text-gray-400">Total Messages</span>
                        </div>
                        <div className="text-3xl font-bold">{stats.total_messages}</div>
                    </div>

                    <div className="bg-gray-900/50 border border-white/5 p-6 rounded-2xl">
                        <div className="flex items-center gap-4 mb-2">
                            <div className="p-3 bg-green-500/10 text-green-400 rounded-xl">
                                <Shield size={24} />
                            </div>
                            <span className="text-gray-400">Masked Messages</span>
                        </div>
                        <div className="text-3xl font-bold">{stats.masked_messages}</div>
                        <div className="text-sm text-gray-500 mt-1">
                            {((stats.masked_messages / stats.total_messages) * 100).toFixed(1)}% of total
                        </div>
                    </div>

                    <div className="bg-gray-900/50 border border-white/5 p-6 rounded-2xl">
                        <div className="flex items-center gap-4 mb-2">
                            <div className="p-3 bg-yellow-500/10 text-yellow-400 rounded-xl">
                                <Zap size={24} />
                            </div>
                            <span className="text-gray-400">Total Tokens</span>
                        </div>
                        <div className="text-3xl font-bold">{stats.total_tokens.toLocaleString()}</div>
                    </div>
                </div>

                {/* Charts */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                    <div className="bg-gray-900/50 border border-white/5 p-6 rounded-2xl">
                        <h3 className="text-xl font-semibold mb-6">Model Usage Distribution</h3>
                        <div className="h-80">
                            <ResponsiveContainer width="100%" height="100%">
                                <PieChart>
                                    <Pie
                                        data={modelData}
                                        cx="50%"
                                        cy="50%"
                                        innerRadius={60}
                                        outerRadius={100}
                                        fill="#8884d8"
                                        paddingAngle={5}
                                        dataKey="value"
                                    >
                                        {modelData.map((_, index) => (
                                            <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                                        ))}
                                    </Pie>
                                    <Tooltip
                                        contentStyle={{ backgroundColor: '#1f2937', borderColor: '#374151', color: '#f3f4f6' }}
                                        itemStyle={{ color: '#f3f4f6' }}
                                    />
                                </PieChart>
                            </ResponsiveContainer>
                        </div>
                        <div className="flex justify-center gap-6 mt-4">
                            {modelData.map((entry, index) => (
                                <div key={entry.name} className="flex items-center gap-2">
                                    <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[index % COLORS.length] }} />
                                    <span className="text-sm text-gray-400">{entry.name}</span>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
};
