import React, { useState } from 'react';
import { useTheme } from '../context/ThemeContext';
import {
    Users, Activity, Settings, LogOut, Search, Bell, Menu, X,
    BarChart3, Shield, LayoutGrid, ChevronRight, Plus, Trash2, Database, Mail
} from 'lucide-react';
import { mockAdmins } from '../data/mock';
import { useNavigate } from 'react-router-dom';

// Import Sub-pages
import Departments from '../components/super-admin/Departments';
import SystemHealth from '../components/super-admin/SystemHealth';
import Analytics from '../components/super-admin/Analytics';
import GlobalSettings from '../components/super-admin/Settings';
import ActivityLogs from '../components/super-admin/ActivityLogs';
import DatabaseExplorer from '../components/super-admin/Databases';
import EmailLogs from '../components/super-admin/EmailLogs';

import { useData } from '../context/DataContext';
import { API_BASE_URL } from '../config/api';

export default function SuperAdminDashboard() {
    const { toggleTheme, theme } = useTheme();
    const { students } = useData();
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('dept-admins');
    const [sidebarOpen, setSidebarOpen] = useState(false);
    const [admins, setAdmins] = useState([]);
    const [searchQuery, setSearchQuery] = useState('');
    const [isLoadingAdmins, setIsLoadingAdmins] = useState(true);

    const fetchAdmins = async () => {
        setIsLoadingAdmins(true);
        try {
            const response = await fetch(`${API_BASE_URL}/db/table/admins`);
            const data = await response.json();
            // Map DB fields to UI fields
            const mapped = data.data.map(a => ({
                id: a.admin_id,
                name: a.name,
                email: a.email,
                username: a.username,
                dept: a.role === 'superadmin' ? 'Central Admin' : 'Dept. Head',
                status: a.status === 'active' ? 'Active' : 'Inactive',
                lastActive: 'Connected'
            }));
            setAdmins(mapped);
        } catch (err) {
            console.error("Failed to fetch admins", err);
        } finally {
            setIsLoadingAdmins(false);
        }
    };

    React.useEffect(() => {
        fetchAdmins();
    }, []);
    const [isAddingAdmin, setIsAddingAdmin] = useState(false);
    
    // Notification Logic
    const [hasNewActivity, setHasNewActivity] = useState(false);
    const [lastActivityCount, setLastActivityCount] = useState(
        parseInt(localStorage.getItem('lastActivityCount') || '0')
    );

    React.useEffect(() => {
        const checkLogs = async () => {
            try {
                const response = await fetch(`${API_BASE_URL}/logs`);
                const data = await response.json();
                const currentCount = data.logs.length;
                
                if (currentCount > lastActivityCount) {
                    // Only show red dot if we aren't currently viewing the health tab
                    if (activeTab !== 'health') {
                        setHasNewActivity(true);
                    } else {
                        // If we ARE on health tab, keep count synced
                        setLastActivityCount(currentCount);
                        localStorage.setItem('lastActivityCount', currentCount.toString());
                    }
                }
            } catch (err) {
                console.error("Failed to check logs", err);
            }
        };

        checkLogs();
        const interval = setInterval(checkLogs, 10000);
        return () => clearInterval(interval);
    }, [lastActivityCount, activeTab]);

    React.useEffect(() => {
        if (activeTab === 'health') {
            setHasNewActivity(false);
            // Sync the count when viewing logs
            const syncCount = async () => {
                try {
                    const response = await fetch(`${API_BASE_URL}/logs`);
                    const data = await response.json();
                    setLastActivityCount(data.logs.length);
                    localStorage.setItem('lastActivityCount', data.logs.length.toString());
                } catch (e) {}
            };
            syncCount();
        }
    }, [activeTab]);

    const handleDeleteAdmin = (id) => {
        if (window.confirm("Delete this admin account?")) {
            setAdmins(admins.filter(a => a.id !== id));
        }
    };

    const handleAddAdmin = () => {
        const name = prompt("Enter Admin Name:");
        const dept = prompt("Enter Department:");
        const email = prompt("Enter Email:");
        if (name && dept && email) {
            const newAdmin = {
                id: Date.now(),
                name,
                dept,
                email,
                status: 'Active',
                lastActive: 'Just now'
            };
            setAdmins([newAdmin, ...admins]);
        }
    };

    const filteredAdmins = admins.filter(admin => 
        admin.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        admin.dept.toLowerCase().includes(searchQuery.toLowerCase())
    );

    // Render content based on active tab
    const renderContent = () => {
        switch (activeTab) {
            case 'dept-admins':
                return (
                    <DeptAdminsTable 
                        admins={filteredAdmins} 
                        onDelete={handleDeleteAdmin} 
                        onAdd={handleAddAdmin}
                        searchQuery={searchQuery}
                        setSearchQuery={setSearchQuery}
                        students={students}
                    />
                );
            case 'departments':
                return <Departments />;
            case 'health':
                return <ActivityLogs />;
            case 'emails':
                return <EmailLogs />;
            case 'analytics':
                return <Analytics students={students} />;
            case 'settings':
                return <GlobalSettings />;
            case 'databases':
                return <DatabaseExplorer />;
            default:
                return (
                    <DeptAdminsTable 
                        admins={filteredAdmins} 
                        onDelete={handleDeleteAdmin} 
                        onAdd={handleAddAdmin}
                        searchQuery={searchQuery}
                        setSearchQuery={setSearchQuery}
                        students={students}
                    />
                );
        }
    };

    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 transition-colors duration-300 font-sans">

            {/* Mobile Sidebar Overlay */}
            {sidebarOpen && (
                <div
                    className="fixed inset-0 bg-black/50 z-40 lg:hidden backdrop-blur-sm"
                    onClick={() => setSidebarOpen(false)}
                />
            )}

            {/* Sidebar */}
            <aside className={`
        fixed top-0 left-0 z-50 h-full w-72 bg-white dark:bg-slate-900 border-r border-slate-200 dark:border-slate-800 transform transition-transform duration-300 ease-in-out
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
                <div className="h-full flex flex-col">
                    <div className="p-6 flex items-center gap-3 border-b border-slate-100 dark:border-slate-800">
                        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white shadow-lg shadow-indigo-500/20">
                            <Shield className="w-6 h-6" />
                        </div>
                        <div>
                            <h1 className="text-lg font-bold text-slate-900 dark:text-white leading-tight">Admin Console</h1>
                            <p className="text-xs text-slate-500 font-medium">Super User Access</p>
                        </div>
                        <button
                            onClick={() => setSidebarOpen(false)}
                            className="ml-auto lg:hidden text-slate-400 hover:text-slate-600"
                        >
                            <X className="w-6 h-6" />
                        </button>
                    </div>

                    <nav className="flex-1 p-4 space-y-1 overflow-y-auto">
                        <NavItem icon={Users} label="Department Admins" id="dept-admins" activeTab={activeTab} setActiveTab={setActiveTab} />
                        <NavItem icon={LayoutGrid} label="Departments" id="departments" activeTab={activeTab} setActiveTab={setActiveTab} />
                        <NavItem icon={Activity} label="Activity Logs" id="health" activeTab={activeTab} setActiveTab={setActiveTab} />
                        <NavItem icon={Mail} label="Email History" id="emails" activeTab={activeTab} setActiveTab={setActiveTab} />
                        <NavItem icon={BarChart3} label="Analytics" id="analytics" activeTab={activeTab} setActiveTab={setActiveTab} />
                        <NavItem icon={Database} label="Raw Databases" id="databases" activeTab={activeTab} setActiveTab={setActiveTab} />
                        <NavItem icon={Settings} label="Global Settings" id="settings" activeTab={activeTab} setActiveTab={setActiveTab} />
                    </nav>

                    <div className="p-4 border-t border-slate-100 dark:border-slate-800">
                        <button
                            onClick={() => navigate('/')}
                            className="flex w-full items-center gap-3 p-3 rounded-lg text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/10 transition-colors"
                        >
                            <LogOut className="w-5 h-5" />
                            <span className="font-medium">Sign Out</span>
                        </button>
                    </div>
                </div>
            </aside>

            {/* Main Content */}
            <main className="lg:pl-72 min-h-screen flex flex-col">

                {/* Header */}
                <header className="sticky top-0 z-30 h-16 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800 px-4 sm:px-6 flex items-center justify-between">
                    <button
                        onClick={() => setSidebarOpen(true)}
                        className="lg:hidden p-2 -ml-2 text-slate-600 dark:text-slate-300"
                    >
                        <Menu className="w-6 h-6" />
                    </button>

                    <div className="flex items-center gap-4 ml-auto">


                        <button 
                            onClick={() => setActiveTab('health')}
                            className="relative p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors"
                        >
                            <Bell className="w-5 h-5" />
                            {hasNewActivity && (
                                <span className="absolute top-1.5 right-1.5 w-2.5 h-2.5 bg-red-500 rounded-full border-2 border-white dark:border-slate-900 animate-pulse"></span>
                            )}
                        </button>

                        <button
                            onClick={toggleTheme}
                            className="p-2 text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-full transition-colors"
                        >
                            <div className="text-xl">{theme === 'dark' ? '☀️' : '🌙'}</div>
                        </button>

                        <div className="h-8 w-8 rounded-full bg-gradient-to-r from-indigo-500 to-purple-500 p-[2px]">
                            <img
                                src="https://api.dicebear.com/7.x/avataaars/svg?seed=Admin"
                                alt="Profile"
                                className="rounded-full bg-white dark:bg-slate-900"
                            />
                        </div>
                    </div>
                </header>

                {/* Dashboard Content */}
                <div className="p-6 md:p-8 space-y-8 max-w-7xl mx-auto w-full animate-fade-in">
                    {renderContent()}
                </div>
            </main>
        </div>
    );
}

function DeptAdminsTable({ admins, onDelete, onAdd, searchQuery, setSearchQuery, students }) {
    // Calculate Dynamic OCR Accuracy across all cohorts
    // If a student's mark field gpa != ocrValue, it counts as a manual correction
    const allStudents = [
        ...(students?.FE || []),
        ...(students?.SE || []),
        ...(students?.TE || []),
        ...(students?.BE || [])
    ];
    let totalFields = 0;
    let manualCorrections = 0;

    allStudents.forEach(s => {
        Object.values(s.marks).forEach(m => {
            if (m.gpa > 0 || m.ocrValue > 0) {
                totalFields++;
                if (m.gpa !== (m.ocrValue || 0)) {
                    manualCorrections++;
                }
            }
        });
    });

    const ocrAccuracy = totalFields > 0 
        ? Math.max(0, ((totalFields - manualCorrections) / totalFields) * 100).toFixed(1) 
        : "98.5"; // High fallback if no data

    return (
        <>
            {/* Stats Grid */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                <StatCard
                    label="Total Departments"
                    value="4"
                    trend="Fixed View"
                    icon={LayoutGrid}
                    color="text-blue-500"
                    bg="bg-blue-500/10"
                />
                <StatCard
                    label="Active Admins"
                    value={admins.length.toString()}
                    trend="Real-time"
                    icon={Activity}
                    color="text-emerald-500"
                    bg="bg-emerald-500/10"
                />
                <StatCard
                    label="OCR Accuracy"
                    value={`${ocrAccuracy}%`}
                    trend={manualCorrections > 0 ? `${manualCorrections} manual fixes` : "Perfect Match"}
                    icon={Shield}
                    color="text-amber-500"
                    bg="bg-amber-500/10"
                />
            </div>

            {/* Admin Table Section */}
            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden animate-in fade-in slide-in-from-bottom-4 duration-500">
                <div className="p-6 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                    <div>
                        <h2 className="text-lg font-bold text-slate-900 dark:text-white">Department Representatives</h2>
                        <p className="text-sm text-slate-500 dark:text-slate-400">Manage access and sync with departmental logic</p>
                    </div>
                    <div className="flex items-center gap-3">
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                            <input 
                                type="text" 
                                placeholder="Search admins..." 
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="pl-9 pr-4 py-2 rounded-lg bg-slate-50 dark:bg-slate-800 border-none text-sm focus:ring-2 focus:ring-indigo-500 dark:text-white w-full sm:w-64"
                            />
                        </div>
                        <button onClick={onAdd} className="btn-primary flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 border-none">
                            <Plus className="w-4 h-4" />
                            <span>Add Admin</span>
                        </button>
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-left text-sm">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800">
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">User</th>
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Department</th>
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Status</th>
                                <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Last Active</th>
                                <th className="px-6 py-4 text-right font-semibold text-slate-700 dark:text-slate-300">Action</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {admins.map((admin) => (
                                <tr key={admin.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 group transition-colors">
                                    <td className="px-6 py-4">
                                        <div className="flex items-center gap-3">
                                            <div className="w-9 h-9 rounded-xl bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-700 dark:to-slate-800 flex items-center justify-center font-bold text-slate-600 dark:text-indigo-400">
                                                {admin.name.charAt(0)}
                                            </div>
                                            <div>
                                                <div className="font-semibold text-slate-900 dark:text-white">{admin.name}</div>
                                                <div className="text-xs text-slate-500">{admin.email}</div>
                                            </div>
                                        </div>
                                    </td>
                                    <td className="px-6 py-4 text-slate-600 dark:text-slate-400">
                                        <span className="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-indigo-50 text-indigo-700 dark:bg-indigo-900/30 dark:text-indigo-400 border border-indigo-100 dark:border-indigo-800">
                                            {admin.dept}
                                        </span>
                                    </td>
                                    <td className="px-6 py-4">
                                        <StatusBadge status={admin.status} />
                                    </td>
                                    <td className="px-6 py-4 text-slate-500 text-xs font-mono">
                                        {admin.lastActive}
                                    </td>
                                    <td className="px-6 py-4 text-right">
                                        <div className="flex items-center justify-end gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                            <button className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 rounded-lg transition-colors">
                                                <Settings className="w-4 h-4" />
                                            </button>
                                            <button 
                                                onClick={() => onDelete(admin.id)}
                                                className="p-1.5 text-slate-400 hover:text-red-600 hover:bg-red-50 dark:hover:bg-red-900/20 rounded-lg transition-colors"
                                            >
                                                <Trash2 className="w-4 h-4" />
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </>
    )
}

function NavItem({ icon: Icon, label, id, activeTab, setActiveTab }) {
    const active = activeTab === id;
    return (
        <button
            onClick={() => setActiveTab(id)}
            className={`
      w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-all duration-200
      ${active
                    ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400'
                    : 'text-slate-600 dark:text-slate-400 hover:bg-slate-50 dark:hover:bg-slate-800 hover:text-slate-900 dark:hover:text-white'}
    `}>
            <Icon className={`w-5 h-5 ${active ? 'text-indigo-600 dark:text-indigo-400' : 'text-slate-400'}`} />
            {label}
        </button>
    );
}

function StatCard({ label, value, trend, icon: Icon, color, bg }) {
    return (
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm hover:shadow-md transition-shadow">
            <div className="flex items-start justify-between mb-4">
                <div>
                    <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
                    <h3 className="text-3xl font-bold text-slate-900 dark:text-white mt-1">{value}</h3>
                </div>
                <div className={`p-3 rounded-xl ${bg} ${color}`}>
                    <Icon className="w-6 h-6" />
                </div>
            </div>
            <div className="flex items-center gap-2 text-xs">
                <span className="font-medium text-emerald-600 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-900/20 px-2 py-0.5 rounded-full">
                    {trend}
                </span>
                <span className="text-slate-400">vs last month</span>
            </div>
        </div>
    );
}

function StatusBadge({ status }) {
    const styles = status === 'Active'
        ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-100 dark:border-emerald-800'
        : 'bg-slate-100 text-slate-700 dark:bg-slate-800 dark:text-slate-400 border-slate-200 dark:border-slate-700';

    return (
        <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${styles}`}>
            <span className={`w-1.5 h-1.5 rounded-full mr-1.5 ${status === 'Active' ? 'bg-emerald-500' : 'bg-slate-500'}`} />
            {status}
        </span>
    );
}
