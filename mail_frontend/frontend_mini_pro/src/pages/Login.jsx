import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTheme } from '../context/ThemeContext';
import { Moon, Sun, Lock, Mail, ArrowRight, ShieldCheck, GraduationCap, Eye, EyeOff } from 'lucide-react';
import { API_BASE_URL } from '../config/api';

export default function Login() {
    const { theme, toggleTheme } = useTheme();
    const navigate = useNavigate();
    const [role, setRole] = useState('dept-admin');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [showPassword, setShowPassword] = useState(false);
    const [isLoading, setIsLoading] = useState(false);

    const handleLogin = async (e) => {
        e.preventDefault();
        setIsLoading(true);
        try {
            const response = await fetch(`${API_BASE_URL}/login`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ email, password }),
            });

            if (!response.ok) {
                const errorData = await response.json();
                throw new Error(errorData.detail || 'Login failed');
            }

            const data = await response.json();
            localStorage.setItem('user', JSON.stringify(data.user));
            
            // Allow accuracy metrics to reset on new login session
            sessionStorage.removeItem('session_accuracy_synced');
            
            // Redirect based on backend detected role
            navigate(data.user.role === 'super-admin' ? '/super-admin' : '/dept-admin');
        } catch (err) {
            alert(err.message);
        } finally {
            setIsLoading(false);
        }
    };

    return (
        <div className="relative min-h-screen flex items-center justify-center overflow-hidden bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-950 dark:to-slate-900 transition-all duration-300">

            {/* Abstract Shapes */}
            <div className="absolute top-0 left-0 w-full h-full overflow-hidden pointer-events-none">
                <div className="absolute -top-40 -left-40 w-96 h-96 bg-blue-500/20 rounded-full blur-3xl animate-pulse"></div>
                <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[800px] bg-indigo-500/10 rounded-full blur-[100px]"></div>
                <div className="absolute -bottom-40 -right-40 w-96 h-96 bg-purple-500/20 rounded-full blur-3xl animate-pulse delay-1000"></div>
            </div>

            {/* Theme Toggle */}
            <button
                onClick={toggleTheme}
                className="absolute top-6 right-6 p-3 rounded-full bg-white/10 backdrop-blur-md border border-white/20 text-slate-600 dark:text-slate-300 hover:bg-white/20 transition-all shadow-lg"
            >
                {theme === 'dark' ? <Sun size={20} /> : <Moon size={20} />}
            </button>

            <div className="relative z-10 w-full max-w-md mx-4">
                <div className="glass-card p-8 md:p-10 animate-fade-in">

                    <div className="text-center mb-10">
                        <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-tr from-blue-600 to-indigo-600 shadow-xl shadow-blue-500/30 mb-8 transform rotate-3 hover:rotate-6 transition-transform">
                            <GraduationCap className="text-white w-10 h-10" />
                        </div>
                        <h1 className="text-3xl font-extrabold text-slate-900 dark:text-white mb-2 tracking-tight">System Login</h1>
                        <p className="text-slate-500 dark:text-slate-400">Authenticated access to the Exam Cell Portal</p>
                    </div>

                    <form onSubmit={handleLogin} className="space-y-6">
                        <div className="space-y-4">
                            <div className="relative group">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Mail className="h-5 w-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                                </div>
                                <input
                                    type="text"
                                    className="glass-input w-full pl-11 py-3.5"
                                    placeholder="Username or email (e.g. dept_admin)"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                />
                            </div>

                            <div className="relative group">
                                <div className="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none">
                                    <Lock className="h-5 w-5 text-slate-400 group-focus-within:text-blue-500 transition-colors" />
                                </div>
                                <input
                                    type={showPassword ? "text" : "password"}
                                    className="glass-input w-full pl-11 pr-11 py-3.5"
                                    placeholder="••••••••"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    required
                                />
                                <button
                                    type="button"
                                    onClick={() => setShowPassword(!showPassword)}
                                    className="absolute inset-y-0 right-0 pr-4 flex items-center text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 transition-colors focus:outline-none"
                                    aria-label={showPassword ? "Hide password" : "Show password"}
                                >
                                    {showPassword ? (
                                        <EyeOff className="h-5 w-5" />
                                    ) : (
                                        <Eye className="h-5 w-5" />
                                    )}
                                </button>
                            </div>
                        </div>

                        <div className="flex items-center justify-between text-sm py-2">
                            <label className="flex items-center text-slate-600 dark:text-slate-400 cursor-pointer group">
                                <input type="checkbox" className="mr-2 rounded border-gray-300 text-blue-600 focus:ring-blue-500 group-hover:border-blue-400 transition-colors" />
                                Remember me
                            </label>
                            <a href="#" className="font-semibold text-blue-600 hover:text-blue-500 dark:text-blue-400 transition-colors">
                                Forgot password?
                            </a>
                        </div>

                        <button
                            type="submit"
                            disabled={isLoading}
                            className="w-full h-12 btn-primary flex items-center justify-center gap-3 group bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 border-none text-white shadow-lg shadow-blue-500/25"
                        >
                            {isLoading ? (
                                <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                            ) : (
                                <>
                                    <span className="font-bold text-lg">Sign In</span>
                                    <ArrowRight className="w-5 h-5 group-hover:translate-x-1.5 transition-transform" />
                                </>
                            )}
                        </button>
                    </form>

                    <div className="mt-10 pt-8 border-t border-slate-100 dark:border-slate-800 text-center">
                        <p className="text-xs text-slate-400 dark:text-slate-500 flex items-center justify-center gap-2">
                            <ShieldCheck className="w-4 h-4" />
                            Secure Enterprise Authentication v2.0
                        </p>
                    </div>
                </div>
            </div>
        </div>
    );
}
