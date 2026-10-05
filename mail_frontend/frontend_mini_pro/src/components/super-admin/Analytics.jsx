import React, { useState, useEffect } from 'react';
import { Users, GraduationCap, Trophy, BarChart3, PieChart as PieChartIcon, ChevronDown } from 'lucide-react';
import { 
    BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, 
    PieChart, Pie, Cell, Legend 
} from 'recharts';
import { API_BASE_URL } from '../../config/api';

const SEMESTER_LABELS = {
    all: 'All Semesters',
    sem1: 'Semester 1',
    sem2: 'Semester 2',
    sem3: 'Semester 3',
    sem4: 'Semester 4',
    sem5: 'Semester 5',
    sem6: 'Semester 6',
    sem7: 'Semester 7',
    sem8: 'Semester 8',
};

export default function Analytics() {
    const [stats, setStats] = useState(null);
    const [isLoading, setIsLoading] = useState(true);
    const [selectedSemester, setSelectedSemester] = useState('all');
    const [availableSemesters, setAvailableSemesters] = useState([]);

    const fetchSemesters = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/analytics/semesters`);
            const d = await res.json();
            if (d.success) setAvailableSemesters(d.semesters);
        } catch (err) {
            console.error("Failed to fetch semesters", err);
        }
    };

    const fetchStats = async (sem) => {
        setIsLoading(true);
        try {
            const url = sem && sem !== 'all' 
                ? `${API_BASE_URL}/analytics/stats?semester=${sem}` 
                : `${API_BASE_URL}/analytics/stats`;
            const response = await fetch(url);
            const data = await response.json();
            if (data.success) {
                setStats(data);
            }
        } catch (err) {
            console.error("Failed to fetch analytics", err);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchSemesters();
        fetchStats('all');
    }, []);

    const handleSemesterChange = (sem) => {
        setSelectedSemester(sem);
        fetchStats(sem);
    };

    if (isLoading && !stats) {
        return (
            <div className="flex items-center justify-center h-64">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600"></div>
            </div>
        );
    }

    const hasData = stats?.summary?.total_students > 0;

    if (!hasData && selectedSemester === 'all') {
        return (
            <div className="flex flex-col items-center justify-center p-12 bg-white dark:bg-slate-900 rounded-2xl border-2 border-dashed border-slate-200 dark:border-slate-800 text-center animate-fade-in">
                <div className="w-16 h-16 bg-slate-100 dark:bg-slate-800 rounded-full flex items-center justify-center mb-4">
                    <BarChart3 className="w-8 h-8 text-slate-400" />
                </div>
                <h3 className="text-xl font-bold text-slate-900 dark:text-white mb-2">No Performance Data Available</h3>
                <p className="text-slate-500 max-w-sm mb-6">
                    Start by uploading a student result PDF or Excel file in the Department Admin dashboard to generate class-wide analytics.
                </p>
                <button 
                    onClick={() => fetchStats('all')}
                    className="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white rounded-lg flex items-center gap-2 text-sm font-medium transition-colors"
                >
                    <ActivityIcon className="w-4 h-4" />
                    <span>Check for Data</span>
                </button>
            </div>
        );
    }

    const COLORS = ['#6366f1', '#a855f7', '#ec4899', '#f97316', '#eab308', '#22c55e', '#06b6d4', '#f43f5e'];

    return (
        <div className="space-y-8 animate-fade-in">
            {/* Header with semester selector */}
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
                <div>
                    <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Academic Performance Analytics</h2>
                    <p className="text-sm text-slate-500">
                        {selectedSemester === 'all' 
                            ? 'Showing combined insights across all semesters.' 
                            : `Filtered to ${SEMESTER_LABELS[selectedSemester] || selectedSemester} results.`}
                    </p>
                </div>
                <div className="flex items-center gap-3">
                    {/* Semester Selector */}
                    <div className="relative">
                        <select 
                            value={selectedSemester}
                            onChange={(e) => handleSemesterChange(e.target.value)}
                            className="appearance-none bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl pl-4 pr-10 py-2.5 text-sm font-bold text-slate-700 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500 cursor-pointer transition-all hover:border-indigo-400"
                        >
                            <option value="all">All Semesters</option>
                            {availableSemesters.map(s => (
                                <option key={s} value={s}>{SEMESTER_LABELS[s] || s.toUpperCase()}</option>
                            ))}
                        </select>
                        <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400 pointer-events-none" />
                    </div>
                    <button 
                        onClick={() => fetchStats(selectedSemester)}
                        className="flex items-center gap-2 px-4 py-2.5 bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600 dark:text-indigo-400 rounded-xl hover:bg-indigo-100 transition-colors text-sm font-medium"
                    >
                        <ActivityIcon className="w-4 h-4" />
                        Refresh
                    </button>
                </div>
            </div>

            {/* Semester Pills (quick-switch) */}
            {availableSemesters.length > 1 && (
                <div className="flex flex-wrap gap-2">
                    <button
                        onClick={() => handleSemesterChange('all')}
                        className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
                            selectedSemester === 'all' 
                                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' 
                                : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'
                        }`}
                    >
                        All
                    </button>
                    {availableSemesters.map(s => (
                        <button
                            key={s}
                            onClick={() => handleSemesterChange(s)}
                            className={`px-4 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
                                selectedSemester === s 
                                    ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20' 
                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'
                            }`}
                        >
                            {SEMESTER_LABELS[s] || s}
                        </button>
                    ))}
                </div>
            )}

            {/* No data for selected semester */}
            {!hasData && selectedSemester !== 'all' && (
                <div className="bg-amber-50 dark:bg-amber-900/10 border border-amber-200 dark:border-amber-800 rounded-xl p-4 flex items-center gap-3">
                    <BarChart3 className="w-5 h-5 text-amber-500 flex-shrink-0" />
                    <p className="text-sm text-amber-700 dark:text-amber-400 font-medium">
                        No data available for {SEMESTER_LABELS[selectedSemester] || selectedSemester}. Upload and distribute results for this semester first.
                    </p>
                </div>
            )}

            {/* Top Stats */}
            {hasData && (
                <>
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                        <StatCard 
                            label={selectedSemester === 'all' ? "Overall Average GPA" : `${SEMESTER_LABELS[selectedSemester]} Avg GPA`}
                            value={stats?.summary?.avg_gpa?.toFixed(2) || "0.00"} 
                            icon={GraduationCap}
                            color="text-indigo-600"
                            bg="bg-indigo-500/10"
                        />
                        <StatCard 
                            label="Students Processed" 
                            value={stats?.summary?.total_students || "0"} 
                            icon={Users}
                            color="text-purple-600"
                            bg="bg-purple-500/10"
                        />
                        <div className="bg-gradient-to-br from-indigo-600 to-purple-700 p-6 rounded-2xl shadow-lg shadow-indigo-500/20 text-white relative overflow-hidden group">
                            <Trophy className="absolute -right-4 -bottom-4 w-32 h-32 text-white/10 group-hover:scale-110 transition-transform duration-500" />
                            <div className="relative z-10">
                                <p className="text-indigo-100 text-sm font-medium mb-1">
                                    {selectedSemester === 'all' ? 'Overall Topper' : `${SEMESTER_LABELS[selectedSemester]} Topper`}
                                </p>
                                <h3 className="text-2xl font-bold mb-2">{stats?.topper?.student_name || "N/A"}</h3>
                                <div className="inline-flex items-center gap-2">
                                    <span className="px-2 py-1 bg-white/20 rounded-lg text-sm backdrop-blur-md">
                                        GPA: {stats?.topper?.pointer || "0.00"}
                                    </span>
                                    {stats?.topper?.semester && (
                                        <span className="px-2 py-1 bg-white/10 rounded-lg text-xs backdrop-blur-md uppercase">
                                            {stats.topper.semester}
                                        </span>
                                    )}
                                </div>
                            </div>
                        </div>
                    </div>

                    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                        {/* GPA Distribution Bar Chart */}
                        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                            <div className="flex items-center justify-between mb-6">
                                <div className="flex items-center gap-2">
                                    <BarChart3 className="w-5 h-5 text-indigo-500" />
                                    <h3 className="font-bold text-slate-900 dark:text-white">GPA Distribution</h3>
                                </div>
                                {selectedSemester !== 'all' && (
                                    <span className="text-xs font-bold text-indigo-600 bg-indigo-50 dark:bg-indigo-900/20 px-2 py-1 rounded-lg uppercase">
                                        {SEMESTER_LABELS[selectedSemester] || selectedSemester}
                                    </span>
                                )}
                            </div>
                            <div className="h-[300px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <BarChart data={stats?.distribution || []}>
                                        <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#33415520" />
                                        <XAxis dataKey="grade_range" axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} />
                                        <YAxis axisLine={false} tickLine={false} tick={{fill: '#64748b', fontSize: 12}} allowDecimals={false} />
                                        <Tooltip 
                                            contentStyle={{ backgroundColor: '#0f172a', border: 'none', borderRadius: '8px', color: '#fff' }}
                                            cursor={{fill: '#6366f110'}}
                                        />
                                        <Bar dataKey="count" fill="#6366f1" radius={[4, 4, 0, 0]} barSize={40} />
                                    </BarChart>
                                </ResponsiveContainer>
                            </div>
                        </div>

                        {/* Semester Comparison Pie Chart */}
                        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                            <div className="flex items-center gap-2 mb-6">
                                <PieChartIcon className="w-5 h-5 text-purple-500" />
                                <h3 className="font-bold text-slate-900 dark:text-white">Semester Comparison</h3>
                            </div>
                            <div className="h-[300px] w-full">
                                <ResponsiveContainer width="100%" height="100%">
                                    <PieChart>
                                        <Pie
                                            data={stats?.semester_averages || []}
                                            cx="50%"
                                            cy="50%"
                                            innerRadius={60}
                                            outerRadius={80}
                                            paddingAngle={5}
                                            dataKey="avg_gpa"
                                            nameKey="semester"
                                        >
                                            {(stats?.semester_averages || []).map((entry, index) => (
                                                <Cell 
                                                    key={`cell-${index}`} 
                                                    fill={COLORS[index % COLORS.length]} 
                                                    opacity={selectedSemester === 'all' || entry.semester === selectedSemester ? 1 : 0.3}
                                                    stroke={entry.semester === selectedSemester ? '#fff' : 'none'}
                                                    strokeWidth={entry.semester === selectedSemester ? 2 : 0}
                                                />
                                            ))}
                                        </Pie>
                                        <Tooltip 
                                            contentStyle={{ backgroundColor: '#0f172a', border: 'none', borderRadius: '8px', color: '#fff' }}
                                            formatter={(value, name) => [`Avg GPA: ${Number(value).toFixed(2)}`, SEMESTER_LABELS[name] || name]}
                                        />
                                        <Legend 
                                            verticalAlign="bottom" 
                                            height={36}
                                            formatter={(value) => SEMESTER_LABELS[value] || value}
                                        />
                                    </PieChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    </div>

                    {/* Semester breakdown table (always visible) */}
                    {stats?.semester_averages?.length > 0 && (
                        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                            <h3 className="font-bold text-slate-900 dark:text-white mb-4">Semester-wise Summary</h3>
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm">
                                    <thead>
                                        <tr className="border-b border-slate-100 dark:border-slate-800">
                                            <th className="text-left py-3 px-4 font-bold text-slate-500 text-xs uppercase tracking-wider">Semester</th>
                                            <th className="text-center py-3 px-4 font-bold text-slate-500 text-xs uppercase tracking-wider">Students</th>
                                            <th className="text-center py-3 px-4 font-bold text-slate-500 text-xs uppercase tracking-wider">Avg GPA</th>
                                            <th className="text-right py-3 px-4 font-bold text-slate-500 text-xs uppercase tracking-wider">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {stats.semester_averages.map(sa => (
                                            <tr 
                                                key={sa.semester} 
                                                className={`border-b border-slate-50 dark:border-slate-800/50 hover:bg-slate-50 dark:hover:bg-slate-800/30 transition-colors ${
                                                    selectedSemester === sa.semester ? 'bg-indigo-50/50 dark:bg-indigo-900/10' : ''
                                                }`}
                                            >
                                                <td className="py-3 px-4 font-semibold text-slate-900 dark:text-white">
                                                    {SEMESTER_LABELS[sa.semester] || sa.semester}
                                                </td>
                                                <td className="py-3 px-4 text-center text-slate-600 dark:text-slate-400 font-mono">
                                                    {sa.student_count}
                                                </td>
                                                <td className="py-3 px-4 text-center">
                                                    <span className={`font-bold ${
                                                        sa.avg_gpa >= 8 ? 'text-emerald-600' : sa.avg_gpa >= 6 ? 'text-amber-600' : 'text-rose-600'
                                                    }`}>
                                                        {Number(sa.avg_gpa).toFixed(2)}
                                                    </span>
                                                </td>
                                                <td className="py-3 px-4 text-right">
                                                    <button
                                                        onClick={() => handleSemesterChange(sa.semester)}
                                                        className={`text-xs font-bold px-3 py-1 rounded-lg transition-all ${
                                                            selectedSemester === sa.semester
                                                                ? 'bg-indigo-600 text-white'
                                                                : 'text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20'
                                                        }`}
                                                    >
                                                        {selectedSemester === sa.semester ? 'Active' : 'View'}
                                                    </button>
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </>
            )}
        </div>
    );
}

function StatCard({ label, value, icon: Icon, color, bg }) {
    return (
        <div className="bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
            <div className="flex items-center gap-4">
                <div className={`p-4 rounded-xl ${bg} ${color}`}>
                    <Icon className="w-6 h-6" />
                </div>
                <div>
                    <p className="text-sm font-medium text-slate-500 dark:text-slate-400">{label}</p>
                    <h3 className="text-2xl font-bold text-slate-900 dark:text-white mt-0.5">{value}</h3>
                </div>
            </div>
        </div>
    )
}

function ActivityIcon({ className }) {
    return (
        <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className={className}><path d="M22 12h-4l-3 9L9 3l-3 9H2"/></svg>
    )
}
