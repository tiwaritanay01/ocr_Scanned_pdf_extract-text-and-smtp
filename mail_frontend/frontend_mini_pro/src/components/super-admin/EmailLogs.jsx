
import React, { useState, useEffect } from 'react';
import { Mail, Clock, User, CheckCircle, AlertCircle, RefreshCcw, Send } from 'lucide-react';
import { API_BASE_URL } from '../../config/api';

export default function EmailLogs() {
    const [logs, setLogs] = useState([]);
    const [isLoading, setIsLoading] = useState(true);

    const fetchLogs = async () => {
        setIsLoading(true);
        try {
            // New endpoint for email logs (Gap 3)
            const response = await fetch(`${API_BASE_URL}/db/table/email_logs`);
            const data = await response.json();
            setLogs(data.data.reverse());
        } catch (err) {
            console.error("Failed to fetch email logs", err);
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
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Email Distribution History</h2>
                    <p className="text-sm text-slate-500">Track all results sent to students via automated mailing.</p>
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
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Sent Time</th>
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Student Name</th>
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Email Address</th>
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Semester</th>
                                <th className="px-6 py-4 text-center font-semibold text-slate-700 dark:text-slate-300">Status</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {logs.length === 0 ? (
                                <tr>
                                    <td colSpan="5" className="px-6 py-10 text-center text-slate-500">
                                        No emails sent yet.
                                    </td>
                                </tr>
                            ) : (
                                logs.map((log) => (
                                    <tr key={log.mail_id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group">
                                        <td className="px-6 py-4 whitespace-nowrap">
                                            <div className="flex items-center gap-2 text-slate-500">
                                                <Clock className="w-3 h-3" />
                                                <span className="font-mono text-xs">{log.sent_time}</span>
                                            </div>
                                        </td>
                                        <td className="px-6 py-4 whitespace-nowrap font-medium text-slate-900 dark:text-white">
                                            {log.student_name}
                                        </td>
                                        <td className="px-6 py-4 text-slate-600 dark:text-slate-400">
                                            {log.student_email}
                                        </td>
                                        <td className="px-6 py-4">
                                            <span className="px-2 py-1 bg-slate-100 dark:bg-slate-800 rounded text-xs font-bold uppercase">
                                                {log.subject_semester}
                                            </span>
                                        </td>
                                        <td className="px-6 py-4 text-center">
                                            <div className="flex justify-center">
                                                {log.status === 'sent' ? (
                                                    <div className="flex items-center gap-1 text-emerald-600 bg-emerald-50 dark:bg-emerald-900/20 px-2 py-0.5 rounded-full">
                                                        <CheckCircle className="w-3 h-3" />
                                                        <span className="text-[10px] font-bold uppercase">Sent</span>
                                                    </div>
                                                ) : (
                                                    <div className="flex items-center gap-1 text-red-600 bg-red-50 dark:bg-red-900/20 px-2 py-0.5 rounded-full">
                                                        <AlertCircle className="w-3 h-3" />
                                                        <span className="text-[10px] font-bold uppercase">Failed</span>
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
