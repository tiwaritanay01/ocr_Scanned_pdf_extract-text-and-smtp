import React, { useState } from 'react';
import { BookOpen, Users, MoreHorizontal, Plus, Laptop, Brain, Settings, ArrowLeft, Mail, Phone, Calendar, Activity, ChevronRight, GraduationCap } from 'lucide-react';

const mockDepartments = [
    {
        id: 1,
        name: "Computer Engineering",
        head: "Dr. Sarah Wilson",
        email: "sarah.cs@college.edu",
        phone: "+91 98765 43210",
        joinDate: "Aug 2018",
        students: 450,
        faculty: 24,
        courses: 12,
        passRate: "94%",
        icon: Laptop,
        status: "Active",
        description: "Focus on software development, algorithms, and system architecture."
    },
    {
        id: 2,
        name: "Information Technology",
        head: "Prof. James Miller",
        email: "james.it@college.edu",
        phone: "+91 98765 43211",
        joinDate: "Jul 2019",
        students: 380,
        faculty: 18,
        courses: 10,
        passRate: "91%",
        icon: GlobeIcon,
        status: "Active",
        description: "Emphasis on network systems, database management, and web technologies."
    },
    {
        id: 3,
        name: "AIML",
        head: "Dr. Emily Chen",
        email: "emily.aiml@college.edu",
        phone: "+91 98765 43212",
        joinDate: "Jan 2022",
        students: 240,
        faculty: 12,
        courses: 8,
        passRate: "96%",
        icon: Brain,
        status: "New",
        description: "Advanced studies in Artificial Intelligence, Machine Learning, and Data Science."
    },
    {
        id: 4,
        name: "Mechatronics",
        head: "Prof. Alex Brown",
        email: "alex.mech@college.edu",
        phone: "+91 98765 43213",
        joinDate: "Sep 2020",
        students: 180,
        faculty: 10,
        courses: 6,
        passRate: "88%",
        icon: Settings,
        status: "Active",
        description: "Interdisciplinary field uniting mechanical, electrical, and computer engineering."
    },
];

const mockStudentsData = {
    SE: [
        { id: 101, name: "Aarav Patel", roll: "SE-101", sem3: 8.5, sem4: "-" },
        { id: 102, name: "Isha Sharma", roll: "SE-102", sem3: 9.1, sem4: "-" },
        { id: 103, name: "Rohan Gupta", roll: "SE-103", sem3: 7.8, sem4: "-" },
        { id: 104, name: "Meera Singh", roll: "SE-104", sem3: 8.2, sem4: "-" },
        { id: 105, name: "Kabir Das", roll: "SE-105", sem3: 6.9, sem4: "-" },
    ],
    TE: [
        { id: 201, name: "Aditi Rao", roll: "TE-201", sem3: 8.8, sem4: 8.9, sem5: 9.0, sem6: "-" },
        { id: 202, name: "Vihaan Kumar", roll: "TE-202", sem3: 7.5, sem4: 7.8, sem5: 7.6, sem6: "-" },
        { id: 203, name: "Ananya Mishra", roll: "TE-203", sem3: 9.2, sem4: 9.1, sem5: 9.3, sem6: "-" },
        { id: 204, name: "Arjun Reddy", roll: "TE-204", sem3: 8.0, sem4: 8.2, sem5: 8.1, sem6: "-" },
        { id: 205, name: "Sanya Mehta", roll: "TE-205", sem3: 7.2, sem4: 7.5, sem5: 7.4, sem6: "-" },
    ]
};

function GlobeIcon(props) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <circle cx="12" cy="12" r="10"></circle>
            <path d="M12 2a14.5 14.5 0 0 0 0 20 14.5 14.5 0 0 0 0-20"></path>
            <path d="M2 12h20"></path>
        </svg>
    )
}

function ActivityIcon(props) {
    return (
        <svg
            {...props}
            xmlns="http://www.w3.org/2000/svg"
            width="24"
            height="24"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            strokeWidth="2"
            strokeLinecap="round"
            strokeLinejoin="round"
        >
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
        </svg>
    )
}

export default function Departments() {
    const [selectedDept, setSelectedDept] = useState(null);
    const [viewMode, setViewMode] = useState('dashboard'); // 'dashboard', 'year-select', 'student-list'
    const [selectedYear, setSelectedYear] = useState(null); // 'SE' or 'TE'

    const handleDeptClick = (dept) => {
        setSelectedDept(dept);
        setViewMode('dashboard');
        setSelectedYear(null);
    };

    const handleBackToDepts = () => {
        setSelectedDept(null);
        setViewMode('dashboard');
    };

    const handleBackToDashboard = () => {
        setViewMode('dashboard');
        setSelectedYear(null);
    };

    const handleBackToYearSelect = () => {
        setViewMode('year-select');
        setSelectedYear(null);
    };

    if (selectedDept) {
        return (
            <div className="space-y-6 animate-fade-in pb-10">

                {/* Navigation Breadcrumb area */}
                <div className="flex items-center gap-2 mb-4">
                    <button
                        onClick={handleBackToDepts}
                        className="flex items-center gap-1 text-slate-500 hover:text-blue-600 transition-colors"
                    >
                        <ArrowLeft className="w-4 h-4" />
                        <span>Departments</span>
                    </button>

                    <ChevronRight className="w-4 h-4 text-slate-300" />

                    <button
                        onClick={handleBackToDashboard}
                        className={`flex items-center gap-1 transition-colors ${viewMode === 'dashboard' ? 'text-slate-900 dark:text-white font-medium cursor-default' : 'text-slate-500 hover:text-blue-600'}`}
                    >
                        <span>{selectedDept.name}</span>
                    </button>

                    {viewMode !== 'dashboard' && (
                        <>
                            <ChevronRight className="w-4 h-4 text-slate-300" />
                            <button
                                onClick={handleBackToYearSelect}
                                className={`flex items-center gap-1 transition-colors ${viewMode === 'year-select' ? 'text-slate-900 dark:text-white font-medium cursor-default' : 'text-slate-500 hover:text-blue-600'}`}
                            >
                                <span>Student Years</span>
                            </button>
                        </>
                    )}

                    {viewMode === 'student-list' && (
                        <>
                            <ChevronRight className="w-4 h-4 text-slate-300" />
                            <span className="text-slate-900 dark:text-white font-medium">{selectedYear} Students</span>
                        </>
                    )}
                </div>

                {/* Dashboard View */}
                {viewMode === 'dashboard' && (
                    <>
                        {/* Header Section */}
                        <div className="glass-card p-6 border-l-4 border-blue-500">
                            <div className="flex flex-col md:flex-row md:items-start justify-between gap-6">
                                <div className="flex items-start gap-4">
                                    <div className="p-4 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400">
                                        <selectedDept.icon className="w-10 h-10" />
                                    </div>
                                    <div>
                                        <h2 className="text-2xl font-bold text-slate-900 dark:text-white">{selectedDept.name} Department</h2>
                                        <p className="text-slate-500 mt-1 max-w-2xl">{selectedDept.description}</p>
                                        <div className="flex items-center gap-2 mt-3">
                                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${selectedDept.status === 'Active'
                                                ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-100 dark:border-emerald-800'
                                                : 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 border-purple-100 dark:border-purple-800'
                                                }`}>
                                                {selectedDept.status}
                                            </span>
                                        </div>
                                    </div>
                                </div>

                                <div className="flex gap-3">
                                    <button className="btn-secondary">Edit Details</button>
                                    <button className="btn-primary">View Reports</button>
                                </div>
                            </div>
                        </div>

                        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            {/* Admin Profile Card */}
                            <div className="glass-card p-6 lg:col-span-1 h-fit">
                                <h3 className="font-bold text-lg text-slate-900 dark:text-white mb-4">Department Head</h3>
                                <div className="flex flex-col items-center text-center p-4 border border-slate-100 dark:border-slate-800 rounded-xl bg-slate-50/50 dark:bg-slate-800/20">
                                    <div className="w-20 h-20 rounded-full bg-gradient-to-tr from-blue-500 to-purple-600 p-[2px] mb-3">
                                        <div className="w-full h-full rounded-full bg-white dark:bg-slate-900 flex items-center justify-center text-2xl font-bold text-slate-700 dark:text-slate-200">
                                            {selectedDept.head.split(' ').map(n => n[0]).join('')}
                                        </div>
                                    </div>
                                    <h4 className="font-bold text-slate-900 dark:text-white">{selectedDept.head}</h4>
                                    <p className="text-xs text-slate-500 mb-4">Head of Department</p>

                                    <div className="w-full space-y-3 text-left">
                                        <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
                                            <Mail className="w-4 h-4 text-blue-500" />
                                            <span>{selectedDept.email}</span>
                                        </div>
                                        <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
                                            <Phone className="w-4 h-4 text-blue-500" />
                                            <span>{selectedDept.phone}</span>
                                        </div>
                                        <div className="flex items-center gap-3 text-sm text-slate-600 dark:text-slate-400">
                                            <Calendar className="w-4 h-4 text-blue-500" />
                                            <span>Joined: {selectedDept.joinDate}</span>
                                        </div>
                                    </div>
                                </div>
                            </div>

                            {/* Stats Grid */}
                            <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
                                {/* Clickable Total Students Card */}
                                <div
                                    onClick={() => setViewMode('year-select')}
                                    className="glass-card p-6 flex flex-col justify-between cursor-pointer hover:shadow-lg hover:border-blue-300 dark:hover:border-blue-700 transition-all group relative overflow-hidden"
                                >
                                    <div className="absolute top-0 right-0 p-2 opacity-0 group-hover:opacity-100 transition-opacity">
                                        <ChevronRight className="text-blue-500 w-5 h-5" />
                                    </div>
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1 group-hover:text-blue-600 transition-colors">Total Students</p>
                                            <h3 className="text-3xl font-bold text-slate-900 dark:text-white">{selectedDept.students}</h3>
                                        </div>
                                        <div className="p-3 bg-blue-50 dark:bg-blue-900/20 text-blue-600 rounded-lg group-hover:scale-110 transition-transform">
                                            <Users className="w-6 h-6" />
                                        </div>
                                    </div>
                                    <div className="mt-4 text-sm text-emerald-500 font-medium">+12% from last year</div>
                                </div>

                                <div className="glass-card p-6 flex flex-col justify-between">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">Faculty Members</p>
                                            <h3 className="text-3xl font-bold text-slate-900 dark:text-white">{selectedDept.faculty}</h3>
                                        </div>
                                        <div className="p-3 bg-purple-50 dark:bg-purple-900/20 text-purple-600 rounded-lg">
                                            <BookOpen className="w-6 h-6" />
                                        </div>
                                    </div>
                                    <div className="mt-4 text-sm text-emerald-500 font-medium">Fully Staffed</div>
                                </div>

                                <div className="glass-card p-6 flex flex-col justify-between">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">Active Courses</p>
                                            <h3 className="text-3xl font-bold text-slate-900 dark:text-white">{selectedDept.courses}</h3>
                                        </div>
                                        <div className="p-3 bg-amber-50 dark:bg-amber-900/20 text-amber-600 rounded-lg">
                                            <Laptop className="w-6 h-6" />
                                        </div>
                                    </div>
                                    <div className="mt-4 text-sm text-slate-500 font-medium">Updated 2 days ago</div>
                                </div>

                                <div className="glass-card p-6 flex flex-col justify-between">
                                    <div className="flex justify-between items-start">
                                        <div>
                                            <p className="text-sm text-slate-500 mb-1">Avg. Pass Rate</p>
                                            <h3 className="text-3xl font-bold text-slate-900 dark:text-white">{selectedDept.passRate}</h3>
                                        </div>
                                        <div className="p-3 bg-emerald-50 dark:bg-emerald-900/20 text-emerald-600 rounded-lg">
                                            <ActivityIcon className="w-6 h-6" />
                                        </div>
                                    </div>
                                    <div className="mt-4 text-sm text-emerald-500 font-medium">Top performing dept</div>
                                </div>
                            </div>
                        </div>
                    </>
                )}

                {/* Year Select View */}
                {viewMode === 'year-select' && (
                    <div className="animate-fade-in">
                        <div className="text-center mb-10">
                            <h2 className="text-2xl font-bold text-slate-900 dark:text-white">Select Academic Year</h2>
                            <p className="text-slate-500 mt-2">View detailed results and student lists.</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 max-w-4xl mx-auto">
                            <button
                                onClick={() => { setViewMode('student-list'); setSelectedYear('SE'); }}
                                className="glass-card p-10 flex flex-col items-center justify-center gap-6 hover:scale-105 transition-all group border-2 border-transparent hover:border-blue-500/20"
                            >
                                <div className="w-24 h-24 rounded-full bg-blue-50 dark:bg-blue-900/20 text-blue-600 flex items-center justify-center group-hover:bg-blue-600 group-hover:text-white transition-colors">
                                    <GraduationCap className="w-12 h-12" />
                                </div>
                                <div className="text-center">
                                    <h3 className="text-2xl font-bold text-slate-900 dark:text-white">SE Students</h3>
                                    <p className="text-slate-500 mt-2">Second Year • Results Sem 3 & 4</p>
                                </div>
                            </button>

                            <button
                                onClick={() => { setViewMode('student-list'); setSelectedYear('TE'); }}
                                className="glass-card p-10 flex flex-col items-center justify-center gap-6 hover:scale-105 transition-all group border-2 border-transparent hover:border-purple-500/20"
                            >
                                <div className="w-24 h-24 rounded-full bg-purple-50 dark:bg-purple-900/20 text-purple-600 flex items-center justify-center group-hover:bg-purple-600 group-hover:text-white transition-colors">
                                    <ActivityIcon className="w-12 h-12" />
                                </div>
                                <div className="text-center">
                                    <h3 className="text-2xl font-bold text-slate-900 dark:text-white">TE Students</h3>
                                    <p className="text-slate-500 mt-2">Third Year • Results Sem 3, 4, 5 & 6</p>
                                </div>
                            </button>
                        </div>
                    </div>
                )}

                {/* Student List View */}
                {viewMode === 'student-list' && (
                    <div className="animate-fade-in">
                        <div className="flex justify-between items-center mb-6">
                            <h2 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                                <span className={`w-3 h-8 rounded-full ${selectedYear === 'SE' ? 'bg-blue-500' : 'bg-purple-500'}`}></span>
                                {selectedYear} Student Records
                            </h2>
                            <div className="flex gap-2">
                                <button className="btn-secondary">Export Results</button>
                            </div>
                        </div>

                        <div className="glass-card overflow-hidden">
                            <table className="w-full text-left text-sm">
                                <thead>
                                    <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800">
                                        <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Roll No</th>
                                        <th className="px-6 py-4 font-semibold text-slate-700 dark:text-slate-300">Name</th>
                                        <th className="px-6 py-4 text-center font-semibold text-slate-700 dark:text-slate-300">Sem 3</th>
                                        <th className="px-6 py-4 text-center font-semibold text-slate-700 dark:text-slate-300">Sem 4</th>
                                        {selectedYear === 'TE' && (
                                            <>
                                                <th className="px-6 py-4 text-center font-semibold text-slate-700 dark:text-slate-300">Sem 5</th>
                                                <th className="px-6 py-4 text-center font-semibold text-slate-700 dark:text-slate-300">Sem 6</th>
                                            </>
                                        )}
                                        <th className="px-6 py-4 text-center font-semibold text-slate-700 dark:text-slate-300">Actions</th>
                                    </tr>
                                </thead>
                                <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                    {mockStudentsData[selectedYear].map((student) => (
                                        <tr key={student.id} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors">
                                            <td className="px-6 py-4 font-mono text-slate-500">{student.roll}</td>
                                            <td className="px-6 py-4 font-medium text-slate-900 dark:text-white">{student.name}</td>
                                            <td className="px-6 py-4 text-center text-slate-600 dark:text-slate-300">{student.sem3}</td>
                                            <td className="px-6 py-4 text-center text-slate-600 dark:text-slate-300">{student.sem4}</td>
                                            {selectedYear === 'TE' && (
                                                <>
                                                    <td className="px-6 py-4 text-center text-slate-600 dark:text-slate-300">{student.sem5}</td>
                                                    <td className="px-6 py-4 text-center text-slate-600 dark:text-slate-300">{student.sem6}</td>
                                                </>
                                            )}
                                            <td className="px-6 py-4 text-center">
                                                <button className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-blue-50 text-blue-700 hover:bg-blue-100 dark:bg-blue-900/30 dark:text-blue-400 dark:hover:bg-blue-900/50 transition-colors border border-blue-200 dark:border-blue-800">
                                                    <Activity className="w-3 h-3" />
                                                    View Result
                                                </button>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>
                )}
            </div>
        );
    }

    // List of Departments (Default List View)
    return (
        <div className="space-y-6 animate-fade-in">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                    <h2 className="text-xl font-bold text-slate-900 dark:text-white">Academic Departments</h2>
                    <p className="text-sm text-slate-500">Manage department heads, faculty, and student allocations.</p>
                </div>
                <button className="btn-primary flex items-center gap-2">
                    <Plus className="w-4 h-4" />
                    <span>Add Department</span>
                </button>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {mockDepartments.map((dept) => (
                    <button
                        key={dept.id}
                        onClick={() => handleDeptClick(dept)}
                        className="glass-card p-6 flex items-start gap-4 hover:shadow-md transition-all hover:scale-[1.01] text-left group w-full"
                    >
                        <div className="p-3 rounded-xl bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 group-hover:bg-blue-100 dark:group-hover:bg-blue-900/40 transition-colors">
                            <dept.icon className="w-8 h-8" />
                        </div>
                        <div className="flex-1">
                            <div className="flex items-start justify-between">
                                <div>
                                    <h3 className="text-lg font-bold text-slate-900 dark:text-white group-hover:text-blue-600 dark:group-hover:text-blue-400 transition-colors">{dept.name}</h3>
                                    <p className="text-sm text-slate-500 mb-2">HOD: {dept.head}</p>
                                </div>
                                <div className="text-slate-400 group-hover:text-slate-600 dark:group-hover:text-slate-200">
                                    <MoreHorizontal className="w-5 h-5" />
                                </div>
                            </div>

                            <div className="flex items-center gap-4 mt-2">
                                <div className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-400">
                                    <Users className="w-4 h-4" />
                                    <span>{dept.students} Students</span>
                                </div>
                                <div className="flex items-center gap-1.5 text-sm text-slate-600 dark:text-slate-400">
                                    <BookOpen className="w-4 h-4" />
                                    <span>{dept.faculty} Faculty</span>
                                </div>
                            </div>

                            <div className="mt-4 flex items-center gap-2">
                                <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${dept.status === 'Active'
                                    ? 'bg-emerald-50 text-emerald-700 dark:bg-emerald-900/30 dark:text-emerald-400 border-emerald-100 dark:border-emerald-800'
                                    : 'bg-purple-50 text-purple-700 dark:bg-purple-900/30 dark:text-purple-400 border-purple-100 dark:border-purple-800'
                                    }`}>
                                    {dept.status}
                                </span>
                            </div>
                        </div>
                    </button>
                ))}
            </div>
        </div>
    );
}
