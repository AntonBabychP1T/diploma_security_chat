import React, { useEffect, useState } from 'react';
import { api, Metrics } from '../api/client';
import { Link } from 'react-router-dom';
import { ArrowLeft, Activity, Shield, Clock, MessageSquare, Trophy, TrendingUp } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import { useI18n } from '../i18n/I18nProvider';

interface LeaderboardEntry {
    model: string;
    win_rate: number;
    votes: number;
    wins: number;
}

export const MetricsPage: React.FC = () => {
    const { t } = useI18n();
    const [metrics, setMetrics] = useState<Metrics | null>(null);
    const [leaderboard, setLeaderboard] = useState<LeaderboardEntry[]>([]);

    useEffect(() => {
        api.get<Metrics>('/metrics').then(res => setMetrics(res.data));
        api.get<LeaderboardEntry[]>('/metrics/leaderboard').then(res => setLeaderboard(res.data));
    }, []);

    if (!metrics) return <div className="p-8 text-gray-950 dark:text-white">{t('common.loading')}</div>;

    const data = [
        { name: t('metrics.totalMessages'), value: metrics.total_messages },
        { name: t('metrics.maskedRecent'), value: metrics.recent_masked_count },
    ];

    return (
        <div className="min-h-screen bg-gray-50 text-gray-950 p-8 dark:bg-gray-900 dark:text-gray-100">
            <Link to="/" className="flex items-center gap-2 text-gray-500 hover:text-gray-950 mb-8 transition-colors dark:text-gray-400 dark:hover:text-white">
                <ArrowLeft size={20} /> {t('metrics.backToChat')}
            </Link>

            <h1 className="text-3xl font-bold mb-8 flex items-center gap-3">
                <Activity className="text-primary-400" /> {t('metrics.systemMetrics')}
            </h1>

            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-500 dark:text-gray-400">{t('metrics.totalMessages')}</h3>
                        <MessageSquare className="text-primary-400" />
                    </div>
                    <p className="text-3xl font-bold">{metrics.total_messages}</p>
                </div>

                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-500 dark:text-gray-400">{t('metrics.avgLatency')}</h3>
                        <Clock className="text-green-500" />
                    </div>
                    <p className="text-3xl font-bold">{metrics.recent_avg_latency.toFixed(3)}s</p>
                </div>

                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                    <div className="flex items-center justify-between mb-4">
                        <h3 className="text-gray-500 dark:text-gray-400">{t('metrics.maskedMessagesLast100')}</h3>
                        <Shield className="text-yellow-500" />
                    </div>
                    <p className="text-3xl font-bold">{metrics.recent_masked_count}</p>
                    <p className="text-sm text-gray-500 mt-2">
                        {t('metrics.recentTraffic', { percent: ((metrics.recent_masked_count / metrics.sample_size) * 100).toFixed(1) })}
                    </p>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 mb-8">
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm dark:bg-gray-800 dark:border-gray-700 h-96">
                    <h3 className="text-xl font-semibold mb-6">{t('metrics.activityOverview')}</h3>
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
                            <Bar dataKey="value" fill="#667b4f" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                    <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
                        <Activity className="text-primary-400" />
                        {t('metrics.modelUsage')}
                    </h3>
                    {Object.keys(metrics.model_usage).length === 0 ? (
                        <p className="text-gray-500 text-center py-8">
                            {t('metrics.noModelUsage')}
                        </p>
                    ) : (
                        <div className="space-y-3">
                            {Object.entries(metrics.model_usage)
                                .sort(([, a], [, b]) => b - a)
                                .map(([model, count]) => {
                                    const percentage = ((count / metrics.sample_size) * 100).toFixed(1);
                                    return (
                                        <div key={model} className="bg-gray-50 p-4 rounded-lg border border-gray-200 dark:bg-gray-900/50 dark:border-gray-700">
                                            <div className="flex items-center justify-between mb-2">
                                                <p className="font-semibold text-gray-950 dark:text-white">{model}</p>
                                                <span className="text-xl font-bold text-primary-300">{count}</span>
                                            </div>
                                            <div className="w-full bg-gray-200 rounded-full h-2 dark:bg-gray-700">
                                                <div
                                                    className="bg-gradient-to-r from-primary-500 to-emerald-500 h-2 rounded-full transition-all"
                                                    style={{ width: `${percentage}%` }}
                                                />
                                            </div>
                                            <p className="text-sm text-gray-500 mt-1 dark:text-gray-400">{t('metrics.recentMessagesPercent', { percent: percentage })}</p>
                                        </div>
                                    );
                                })}
                        </div>
                    )}
                </div>
            </div>

            <div className="grid grid-cols-1 gap-8 mb-8">
                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm dark:bg-gray-800 dark:border-gray-700 h-96">
                    <h3 className="text-xl font-semibold mb-6">{t('metrics.activityOverview')}</h3>
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
                            <Bar dataKey="value" fill="#667b4f" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm dark:bg-gray-800 dark:border-gray-700">
                    <h3 className="text-xl font-semibold mb-6 flex items-center gap-2">
                        <Trophy className="text-yellow-500" />
                        {t('metrics.leaderboard')}
                    </h3>
                    {leaderboard.length === 0 ? (
                        <p className="text-gray-500 text-center py-8">
                            {t('metrics.noVotes')}
                        </p>
                    ) : (
                        <div className="space-y-4">
                            {leaderboard.map((entry, index) => (
                                <div key={entry.model} className="flex items-center gap-4 bg-gray-50 p-4 rounded-lg border border-gray-200 dark:bg-gray-900/50 dark:border-gray-700">
                                    <div className="flex items-center justify-center w-8 h-8 rounded-full bg-gradient-to-br from-yellow-500 to-orange-500 font-bold text-sm">
                                        #{index + 1}
                                    </div>
                                    <div className="flex-1">
                                        <p className="font-semibold text-gray-950 dark:text-white">{entry.model}</p>
                                        <p className="text-sm text-gray-500 dark:text-gray-400">
                                            {t('metrics.winsVotes', { wins: entry.wins, votes: entry.votes })}
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
