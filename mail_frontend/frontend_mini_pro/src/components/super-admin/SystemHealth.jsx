import React from 'react';
import { Activity, Server, Database, Shield, AlertCircle, CheckCircle } from 'lucide-react';

export default function SystemHealth() {
    return (
        <div className="space-y-6">
            <div className="mb-6">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">System Status</h2>
                <p className="text-sm text-slate-500">Real-time infrastructure monitoring.</p>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                <HealthCard title="API Server (Port 8000)" status="Operational" latency="12ms" icon={Server} color="text-emerald-500" />
                <HealthCard title="OCR Engine (Tesseract)" status="Operational" latency="3.2s/pg" icon={Activity} color="text-indigo-500" />
                <HealthCard title="Storage (PDFs)" status="Healthy" latency="92% Free" icon={Database} color="text-emerald-500" />
                <HealthCard title="Security" status="Secure" latency="Ok" icon={Shield} color="text-blue-500" />
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <div className="glass-card p-6">
                    <h3 className="font-bold text-slate-900 dark:text-white mb-4">Recent System Logs</h3>
                    <div className="space-y-4">
                        {[
                            { msg: "OCR Engine processed marksheet: 'New_Input.pdf'", time: "Just now", ok: true },
                            { msg: "Exported 42 student records to Excel format", time: "5 mins ago", ok: true },
                            { msg: "System backup initiated by SuperAdmin", time: "1 hour ago", ok: true },
                            { msg: "Large PDF file upload detected (84.2MB)", time: "2 hours ago", ok: false },
                            { msg: "Admin logged into Computer Science Dept.", time: "4 hours ago", ok: true }
                        ].map((log, i) => (
                            <div key={i} className="flex items-start gap-3 p-3 rounded-lg bg-slate-50 dark:bg-slate-800/50 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                                <div className={`mt-1.5 w-2 h-2 rounded-full ${log.ok ? 'bg-emerald-500' : 'bg-amber-500 animate-pulse'}`} />
                                <div className="flex-1">
                                    <p className="text-sm font-medium text-slate-900 dark:text-white">
                                        {log.msg}
                                    </p>
                                    <p className="text-xs text-slate-500 font-mono uppercase">{log.time}</p>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                <div className="glass-card p-6">
                    <h3 className="font-bold text-slate-900 dark:text-white mb-4">Load Average</h3>
                    <div className="h-64 flex items-end justify-between gap-2 px-4 pb-4 border-b border-slate-200 dark:border-slate-800">
                        {[40, 65, 30, 50, 85, 45, 60, 35, 20, 55, 70, 45].map((h, i) => (
                            <div key={i} className="w-full bg-indigo-100 dark:bg-indigo-900/30 rounded-t-md relative group">
                                <div
                                    style={{ height: `${h}%` }}
                                    className={`w-full absolute bottom-0 rounded-t-md transition-all duration-500 ${h > 80 ? 'bg-red-500' : 'bg-indigo-500'}`}
                                />
                            </div>
                        ))}
                    </div>
                    <div className="flex justify-between text-xs text-slate-500 mt-2">
                        <span>00:00</span>
                        <span>12:00</span>
                        <span>23:59</span>
                    </div>
                </div>
            </div>
        </div>
    );
}

function HealthCard({ title, status, latency, icon: Icon, color, warning }) {
    return (
        <div className="bg-white dark:bg-slate-900 p-5 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="flex justify-between items-start mb-4">
                <div className={`p-2 rounded-lg bg-slate-100 dark:bg-slate-800 ${color}`}>
                    <Icon className="w-5 h-5" />
                </div>
                {warning ? (
                    <AlertCircle className="w-5 h-5 text-amber-500 animate-pulse" />
                ) : (
                    <CheckCircle className="w-5 h-5 text-emerald-500" />
                )}
            </div>
            <h4 className="font-semibold text-slate-900 dark:text-white">{title}</h4>
            <div className="flex justify-between items-center mt-2">
                <span className={`text-sm font-medium ${warning ? 'text-amber-500' : 'text-emerald-500'}`}>
                    {status}
                </span>
                <span className="text-xs text-slate-400">{latency}</span>
            </div>
        </div>
    )
}
