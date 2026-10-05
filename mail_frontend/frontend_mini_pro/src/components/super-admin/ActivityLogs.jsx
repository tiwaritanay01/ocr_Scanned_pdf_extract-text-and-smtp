import React, { useState, useEffect } from 'react';
import { Activity, Clock, User, Info, AlertCircle, CheckCircle, RefreshCcw } from 'lucide-react';
import { API_BASE_URL } from '../../config/api';

export default function ActivityLogs() {
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(true);

    const fetchLogs = async () => {
        setIsLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/logs`);
            const data = await response.json();
            setLogs(data.logs);
        } catch (err) {
            console.error("Failed to fetch logs", err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchLogs();
    }, []);

    return (
        <div className="space-y-6 animate-fade-in">
            <div className="flex items-center justify-between mb-6">
                <div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Activity Logs</h2>
                    <p className="text-sm text-slate-500">Real-time tracking of portal usage and result generations.</p>
                </div>
                <button 
                    onClick={fetchLogs}
                    className="p-2 rounded-lg bg-white dark:bg-slate-900 border border-slate-200 dark:border-slate-800 text-slate-500 hover:text-indigo-600 transition-all flex items-center gap-2"
                >
                    <RefreshCcw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
                    <span className="text-sm font-medium">Refresh</span>
                </button>
            </div>

            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800">
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Timestamp</th>
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">User</th>
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Action</th>
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Details</th>
                                <th className="px-6 py-4 text-center font-semibold text-slate-700 dark:text-slate-300">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {isLoading && logs.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="px-6 py-10 text-center text-slate-500">
                                        Loading activity records...
                                    </td>
                                </tr>
                            ) : logs.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="px-6 py-10 text-center text-slate-500">
                                        No logs found yet. Once admins log in or process PDFs, history will appear here.
                                    </td>
                                </tr>
                            ) : (
                                logs.map((log) => (
                                    <tr key={log.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-2 text-slate-500">
                                                <Clock className="w-3 h-3" />
                                                <span className="font-mono text-xs">{log.time}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-2">
                                                <div className="w-6 h-6 rounded-full bg-slate-100 dark:bg-slate-800 flex items-center justify-center">
                                                    <User className="w-3 h-3 text-slate-500" />
                                                </div>
                                                <span className="font-medium text-slate-900 dark:text-white">{log.user}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <span className={`px-2 py-1 rounded-md text-xs font-bold uppercase ${
                                                log.action === 'Login' ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400' :
                                                log.action === 'Result Generation' ? 'bg-indigo-100 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400' :
                                                'bg-slate-100 text-slate-700 dark:bg-slate-800'
                                            }`}>
                                                {log.action}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 max-w-xs truncate">
                                            <div className="flex items-center gap-2 text-slate-600 dark:text-slate-400 italic">
                                                <Info className="w-3 h-3 flex-shrink-0" />
                                                <span className="text-xs truncate">{log.details}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <div className="flex justify-center">
                                                {log.status === 'Success' ? (
                                                    <div className="flex items-center gap-1 text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20 px-2 py-0.5 rounded-full">
                                                        <CheckCircle className="w-3 h-3" />
                                                        <span className="text-[10px] font-bold uppercase">Success</span>
                                                    </div>
                                                ) : (
                                                    <div className="flex items-center gap-1 text-red-600 bg-red-50 dark:bg-red-900/20 px-2 py-0.5 rounded-full">
                                                        <AlertCircle className="w-3 h-3" />
                                                        <span className="text-[10px] font-bold uppercase">{log.status}</span>
                                                    </div>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                ))
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
