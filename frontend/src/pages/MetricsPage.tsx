import React, { useEffect, useState } from 'react';
import { api, Metrics } from '../api/client';
import { Link } from 'react-router-dom';
import { ArrowLeft, Activity, Shield, Clock, MessageSquare, Trophy, TrendingUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

interface LeaderboardEntry {
    model: string;
    win_rate: number;
    votes: number;
    wins: number;
}

export const MetricsPage: React.FC = () => {
    const [metrics, setMetrics] = useState<Metrics | null>(null);
    const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);

    useEffect(() => {
        api.get<Metrics>('/metrics').then(res => setMetrics(res.data));
        api.get<LeaderboardEntry[]>('/metrics/leaderboard').then(res => setLeaderboard(res.data));
    }, []);

    if (!metrics) return <div className="p-8 text-white">Loading...</div>;

    const data = [
        { name: 'Total Messages', value: metrics.total_messages },
        { name: 'Masked Messages (Recent)', value: metrics.recent_masked_count },
    ];

    return (
        <div className="min-h-screen bg-gray-900 text-gray-100 p-8">
            <Link to="/" className="flex items-center gap-2 text-gray-400 hover:text-white mb-8 transition-colors">
                <ArrowLeft size={20} /> Back to Chat
            </Link>

            <h1 className="text-3xl font-bold mb-8 flex items-center gap-3">
                <Activity className="text-blue-500" /> System Metrics
            </h1>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-400">Total Messages</h3>
                        <MessageSquare className="text-blue-500" />
                    </div>
                    <p className="text-3xl font-bold">{metrics.total_messages}</p>
                </div>

                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-400">Avg Latency (Last 100)</h3>
                        <Clock className="text-green-500" />
                    </div>
                    <p className="text-3xl font-bold">{metrics.recent_avg_latency.toFixed(3)}s</p>
                </div>

                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-400">Masked Messages (Last 100)</h3>
                        <Shield className="text-yellow-500" />
                    </div>
                    <p className="text-3xl font-bold">{metrics.recent_masked_count}</p>
                    <p className="text-sm text-gray-500 mt-2">
                        {((metrics.recent_masked_count / metrics.sample_size) * 100).toFixed(1)}% of recent traffic
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 h-96">
                    <h3 className="text-xl font-semibold mb-6">Activity Overview</h3>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="name" stroke="#9CA3AF" />
                            <YAxis stroke="#9CA3AF" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1F2937', borderColor: '#374151', color: '#F3F4F6' }}
                                itemStyle={{ color: '#F3F4F6' }}
                            />
                            <Legend />
                            <Bar dataKey="value" fill="#3B82F6" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
                        <Activity className="text-purple-500" />
                        Model Usage (Last 100 Messages)
                    </h3>
                    {Object.keys(metrics.model_usage).length === 0 ? (
                        <p className="text-gray-500 text-center py-8">
                            No model usage data yet
                        </p>
                    ) : (
                        <div className="space-y-3">
                            {Object.entries(metrics.model_usage)
                                .sort(([, a], [, b]) => b - a)
                                .map(([model, count]) => {
                                    const percentage = ((count / metrics.sample_size) * 100).toFixed(1);
                                    return (
                                        <div key={model} className="bg-gray-900/50 p-4 rounded-lg border border-gray-700">
                                            <div className="flex items-center justify-between mb-2">
                                                <p className="font-semibold text-white">{model}</p>
                                                <span className="text-xl font-bold text-purple-400">{count}</span>
                                            </div>
                                            <div className="w-full bg-gray-700 rounded-full h-2">
                                                <div
                                                    className="bg-gradient-to-r from-purple-500 to-pink-500 h-2 rounded-full transition-all"
                                                    style={{ width: `${percentage}%` }}
                                                />
                                            </div>
                                            <p className="text-sm text-gray-400 mt-1">{percentage}% of recent messages</p>
                                        </div>
                                    );
                                })}
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 gap-8 mb-8">
                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700 h-96">
                    <h3 className="text-xl font-semibold mb-6">Activity Overview</h3>
                    <ResponsiveContainer width="100%" height="100%">
                        <BarChart data={data}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                            <XAxis dataKey="name" stroke="#9CA3AF" />
                            <YAxis stroke="#9CA3AF" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#1F2937', borderColor: '#374151', color: '#F3F4F6' }}
                                itemStyle={{ color: '#F3F4F6' }}
                            />
                            <Legend />
                            <Bar dataKey="value" fill="#3B82F6" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                    <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
                        <Trophy className="text-yellow-500" />
                        Model Leaderboard (Arena Votes)
                    </h3>
                    {leaderboard.length === 0 ? (
                        <p className="text-gray-500 text-center py-8">
                            No votes yet. Use Arena Mode to compare models!
                        </p>
                    ) : (
                        <div className="space-y-4">
                            {leaderboard.map((entry, index) => (
                                <div key={entry.model} className="flex items-center gap-4 bg-gray-900/50 p-4 rounded-lg border border-gray-700">
                                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-yellow-500 to-orange-500 font-bold text-sm">
                                        #{index + 1}
                                    </div>
                                    <div className="flex-1">
                                        <p className="font-semibold text-white">{entry.model}</p>
                                        <p className="text-sm text-gray-400">
                                            {entry.wins} wins / {entry.votes} votes
                                        </p>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        <TrendingUp className="text-green-500" size={16} />
                                        <span className="text-2xl font-bold text-green-400">
                                            {entry.win_rate}%
                                        </span>
                                    </div>
                                </div>
                            ))}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};
