import React, { useState } from 'react';
import { Save, Lock, Mail, Globe, Bell } from 'lucide-react';

export default function GlobalSettings() {
    const [maintenance, setMaintenance] = useState(false);
    const [allowRegistration, setAllowRegistration] = useState(true);

    return (
        <div className="max-w-4xl mx-auto space-y-6">
            <div className="mb-6">
                <h2 className="text-xl font-bold text-slate-900 dark:text-white">Global Settings</h2>
                <p className="text-sm text-slate-500">Configure system-wide parameters.</p>
            </div>

            <div className="glass-card p-6 divide-y divide-slate-100 dark:divide-slate-800">

                {/* General Settings */}
                <div className="pb-6">
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <Globe className="w-5 h-5 text-blue-500" />
                        General Configuration
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">System Name</label>
                            <input type="text" defaultValue="College Result Portal" className="glass-input w-full" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Support Email</label>
                            <input type="email" defaultValue="support@college.edu" className="glass-input w-full" />
                        </div>
                    </div>
                </div>

                {/* Toggles */}
                <div className="py-6 space-y-4">
                    <div className="flex items-center justify-between">
                        <div>
                            <p className="font-medium text-slate-900 dark:text-white">Maintenance Mode</p>
                            <p className="text-xs text-slate-500">Temporarily disable access for a maintenance window.</p>
                        </div>
                        <button
                            onClick={() => setMaintenance(!maintenance)}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${maintenance ? 'bg-blue-600' : 'bg-slate-200 dark:bg-slate-700'}`}
                        >
                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${maintenance ? 'translate-x-6' : 'translate-x-1'}`} />
                        </button>
                    </div>

                    <div className="flex items-center justify-between">
                        <div>
                            <p className="font-medium text-slate-900 dark:text-white">External Registrations</p>
                            <p className="text-xs text-slate-500">Allow new colleges to sign up independently.</p>
                        </div>
                        <button
                            onClick={() => setAllowRegistration(!allowRegistration)}
                            className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${allowRegistration ? 'bg-blue-600' : 'bg-slate-200 dark:bg-slate-700'}`}
                        >
                            <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${allowRegistration ? 'translate-x-6' : 'translate-x-1'}`} />
                        </button>
                    </div>
                </div>

                {/* Security Section */}
                <div className="pt-6">
                    <h3 className="text-lg font-semibold text-slate-900 dark:text-white mb-4 flex items-center gap-2">
                        <Lock className="w-5 h-5 text-red-500" />
                        Security Policy
                    </h3>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Password Expiry (Days)</label>
                            <input type="number" defaultValue="90" className="glass-input w-full" />
                        </div>
                        <div>
                            <label className="block text-sm font-medium text-slate-700 dark:text-slate-300 mb-2">Max Login Attempts</label>
                            <input type="number" defaultValue="5" className="glass-input w-full" />
                        </div>
                    </div>
                </div>

            </div>

            <div className="flex justify-end">
                <button className="btn-primary flex items-center gap-2">
                    <Save className="w-4 h-4" />
                    <span>Save Changes</span>
                </button>
            </div>
        </div>
    );
}
