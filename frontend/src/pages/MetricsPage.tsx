import React, { useEffect, useState } from 'react';
import { api, Metrics } from '../api/client';
import { Link } from 'react-router-dom';
import { ArrowLeft, Activity, Shield, Clock, MessageSquare } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export const MetricsPage: React.FC = () => {
    const [metrics, setMetrics] = useState<Metrics | null>(null);

    useEffect(() => {
        api.get<Metrics>('/metrics').then(res => setMetrics(res.data));
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
        </div>
    );
};
