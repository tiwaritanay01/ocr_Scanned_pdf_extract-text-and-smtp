import React, { useState, useEffect, useMemo } from 'react';
import { Database, Search, RefreshCw, Save, Trash2, Edit2, Check, X, AlertCircle, Plus, Filter } from 'lucide-react';
import { API_BASE_URL } from '../../config/api';

export default function Databases() {
    const [tables, setTables] = useState([]);
    const [selectedTable, setSelectedTable] = useState('');
    const [data, setData] = useState([]);
    const [schema, setSchema] = useState([]);
    const [isLoading, setIsLoading] = useState(false);
    const [searchQuery, setSearchQuery] = useState('');
    const [editingRow, setEditingRow] = useState(null); // PK value of row being edited
    const [editData, setEditData] = useState({});
    const [message, setMessage] = useState(null);
    const [semesterFilter, setSemesterFilter] = useState('all');

    useEffect(() => {
        fetchTables();
    }, []);

    const fetchTables = async () => {
        try {
            const res = await fetch(`${API_BASE_URL}/db/tables`);
            const d = await res.json();
            if (d.success) {
                setTables(d.tables);
                if (d.tables.length > 0) setSelectedTable(d.tables[0]);
            }
        } catch (e) {
            console.error("Failed to fetch tables", e);
        }
    };

    useEffect(() => {
        if (selectedTable) {
            fetchTableData(selectedTable);
            setSemesterFilter(selectedTable === 'student_performance' ? 'sem3' : 'all');
        }
    }, [selectedTable]);

    const fetchTableData = async (tableName) => {
        setIsLoading(true);
        try {
            const res = await fetch(`${API_BASE_URL}/db/table/${tableName}`);
            const d = await res.json();
            if (d.success) {
                setData(d.data);
                setSchema(d.schema);
                setEditingRow(null);
            }
        } catch (e) {
            console.error("Failed to fetch table data", e);
        } finally {
            setIsLoading(false);
        }
    };

    const getPrimaryField = () => {
        const pk = schema.find(s => s[3] === 'PRI');
        return pk ? pk[0] : (schema.length > 0 ? schema[0][0] : null);
    };

    const handleEdit = (row) => {
        const pkField = getPrimaryField();
        setEditingRow(row[pkField]);
        setEditData({ ...row });
    };

    const handleSave = async () => {
        const pkField = getPrimaryField();
        const pkValue = editingRow;
        
        // Remove PK from data to avoid updating PK itself if not needed
        const { [pkField]: _, ...updateData } = editData;

        try {
            const res = await fetch(`${API_BASE_URL}/db/update-row`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    table: selectedTable,
                    pk_field: pkField,
                    pk_value: pkValue,
                    data: editData // Send all data
                })
            });
            const d = await res.json();
            if (d.success) {
                setMessage({ type: 'success', text: 'Row updated successfully!' });
                setEditingRow(null);
                fetchTableData(selectedTable);
            } else {
                setMessage({ type: 'error', text: d.error || 'Update failed' });
            }
        } catch (e) {
            setMessage({ type: 'error', text: 'Connection error' });
        }
        setTimeout(() => setMessage(null), 3000);
    };

    const handleDelete = async (pkValue) => {
        if (!window.confirm("Are you sure you want to delete this record?")) return;
        const pkField = getPrimaryField();

        try {
            const res = await fetch(`${API_BASE_URL}/db/delete-row`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    table: selectedTable,
                    pk_field: pkField,
                    pk_value: pkValue,
                    data: {}
                })
            });
            const d = await res.json();
            if (d.success) {
                setMessage({ type: 'success', text: 'Row deleted successfully!' });
                fetchTableData(selectedTable);
            }
        } catch (e) {
            setMessage({ type: 'error', text: 'Delete failed' });
        }
        setTimeout(() => setMessage(null), 3000);
    };

    const handleAddRow = async () => {
        const pkField = getPrimaryField();
        const initialData = {};
        schema.forEach(s => {
            initialData[s[0]] = s[0] === pkField && s[5] === 'auto_increment' ? null : "";
        });

        // Prompt for essential data if PK is NOT auto-increment
        if (pkField && schema.find(s => s[0] === pkField)[5] !== 'auto_increment') {
            const val = prompt(`Enter value for primary key (${pkField}):`);
            if (!val) return;
            initialData[pkField] = val;
        }

        try {
            const res = await fetch(`${API_BASE_URL}/db/add-row`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table: selectedTable, data: initialData })
            });
            const d = await res.json();
            if (d.success) {
                setMessage({ type: 'success', text: 'New row added!' });
                fetchTableData(selectedTable);
            } else {
                setMessage({ type: 'error', text: d.error || 'Failed to add row' });
            }
        } catch (e) {
            setMessage({ type: 'error', text: 'Add row failed' });
        }
        setTimeout(() => setMessage(null), 3000);
    };

    const handleAddColumn = async () => {
        const colName = prompt("Enter new column name:");
        if (!colName) return;
        const colType = prompt("Enter column type (e.g. VARCHAR(255), INT, DATE):", "VARCHAR(255)");
        
        try {
            const res = await fetch(`${API_BASE_URL}/db/add-column`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table: selectedTable, column_name: colName, column_type: colType })
            });
            const d = await res.json();
            if (d.success) {
                setMessage({ type: 'success', text: `Column ${colName} added!` });
                fetchTableData(selectedTable);
            }
        } catch (e) {
            setMessage({ type: 'error', text: 'Add column failed' });
        }
        setTimeout(() => setMessage(null), 3000);
    };

    const handleRenameColumn = async (oldName) => {
        const newName = prompt(`Rename column '${oldName}' to:`, oldName);
        if (!newName || newName === oldName) return;

        try {
            const res = await fetch(`${API_BASE_URL}/db/rename-column`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ table: selectedTable, column_name: newName, old_name: oldName })
            });
            const d = await res.json();
            if (d.success) {
                setMessage({ type: 'success', text: 'Column renamed!' });
                fetchTableData(selectedTable);
            }
        } catch (e) {
            setMessage({ type: 'error', text: 'Rename failed' });
        }
        setTimeout(() => setMessage(null), 3000);
    };

    // Extract unique semesters when student_performance is selected
    const availableSemesters = useMemo(() => {
        if (selectedTable !== 'student_performance') return [];
        const sems = [...new Set(data.map(row => row.semester).filter(Boolean))];
        sems.sort();
        return sems;
    }, [data, selectedTable]);

    const SEMESTER_LABELS = {
        sem1: 'Sem 1', sem2: 'Sem 2', sem3: 'Sem 3', sem4: 'Sem 4',
        sem5: 'Sem 5', sem6: 'Sem 6', sem7: 'Sem 7', sem8: 'Sem 8',
    };

    const filteredData = data.filter(row => {
        const matchesSearch = Object.values(row).some(val => 
            String(val).toLowerCase().includes(searchQuery.toLowerCase())
        );
        const matchesSemester = selectedTable !== 'student_performance' 
            || semesterFilter === 'all' 
            || row.semester === semesterFilter;
        return matchesSearch && matchesSemester;
    });

    return (
        <div className="space-y-6">
            <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                <div className="flex items-center gap-3">
                    <div className="p-2 bg-indigo-500/10 rounded-lg">
                        <Database className="w-5 h-5 text-indigo-600" />
                    </div>
                    <div>
                        <h2 className="text-xl font-bold text-slate-900 dark:text-white">Database Explorer</h2>
                        <p className="text-xs text-slate-500 font-medium">Full Schema & Data Management Control</p>
                    </div>
                </div>

                <div className="flex items-center gap-3">
                    <button 
                        onClick={handleAddColumn}
                        className="px-4 py-2 text-xs font-bold text-white bg-indigo-600 hover:bg-indigo-700 rounded-xl transition-all flex items-center gap-2"
                    >
                        <Plus className="w-4 h-4" /> Add Column
                    </button>
                    <div className="h-8 w-px bg-slate-200 dark:bg-slate-800 mx-1"></div>
                    <select 
                        value={selectedTable}
                        onChange={(e) => setSelectedTable(e.target.value)}
                        className="bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl px-4 py-2 text-sm font-bold text-slate-700 dark:text-white outline-none focus:ring-2 focus:ring-indigo-500"
                    >
                        {tables.map(t => <option key={t} value={t}>{t.toUpperCase()}</option>)}
                    </select>
                    <button 
                        onClick={() => fetchTableData(selectedTable)}
                        className="p-2 text-slate-500 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/10 rounded-xl transition-all"
                    >
                        <RefreshCw className={`w-5 h-5 ${isLoading ? 'animate-spin' : ''}`} />
                    </button>
                </div>
            </div>

            {message && (
                <div className={`p-4 rounded-xl flex items-center gap-3 animate-in fade-in slide-in-from-top-2 ${
                    message.type === 'success' ? 'bg-emerald-50 text-emerald-700 border border-emerald-100' : 'bg-rose-50 text-rose-700 border border-rose-100'
                }`}>
                    {message.type === 'success' ? <Check className="w-5 h-5" /> : <AlertCircle className="w-5 h-5" />}
                    <span className="text-sm font-bold">{message.text}</span>
                </div>
            )}

            <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden text-slate-800 dark:text-slate-100">
                <div className="p-4 border-b border-slate-100 dark:border-slate-800 flex flex-col gap-3">
                    <div className="flex items-center justify-between gap-4">
                        <div className="relative flex-1 max-w-md">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                            <input 
                                type="text" 
                                placeholder={`Search in ${selectedTable}...`}
                                value={searchQuery}
                                onChange={(e) => setSearchQuery(e.target.value)}
                                className="w-full pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:ring-2 focus:ring-indigo-500 outline-none" 
                            />
                        </div>
                        
                        <button 
                            onClick={handleAddRow}
                            className="px-4 py-2 text-xs font-bold text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/10 border border-emerald-200 dark:border-emerald-900/30 rounded-xl transition-all flex items-center gap-2"
                        >
                            <Plus className="w-4 h-4" /> Add Row
                        </button>
                    </div>

                    {/* Semester filter pills for student_performance table */}
                    {selectedTable === 'student_performance' && availableSemesters.length > 0 && (
                        <div className="flex items-center gap-2 flex-wrap">
                            <Filter className="w-4 h-4 text-slate-400 mr-1" />
                            <button
                                onClick={() => setSemesterFilter('all')}
                                className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
                                    semesterFilter === 'all'
                                        ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                                        : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'
                                }`}
                            >
                                All ({data.length})
                            </button>
                            {availableSemesters.map(sem => {
                                const count = data.filter(r => r.semester === sem).length;
                                return (
                                    <button
                                        key={sem}
                                        onClick={() => setSemesterFilter(sem)}
                                        className={`px-3 py-1.5 rounded-full text-xs font-bold uppercase tracking-wider transition-all ${
                                            semesterFilter === sem
                                                ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/20'
                                                : 'bg-slate-100 dark:bg-slate-800 text-slate-500 hover:bg-slate-200 dark:hover:bg-slate-700'
                                        }`}
                                    >
                                        {SEMESTER_LABELS[sem] || sem} ({count})
                                    </button>
                                );
                            })}
                        </div>
                    )}
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-sm text-left">
                        <thead>
                            <tr key="header-row" className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                                {schema.map((s, sIdx) => (
                                    <th 
                                        key={`${s[0]}-${sIdx}`} 
                                        className="px-6 py-4 font-bold uppercase tracking-wider text-[10px] cursor-pointer hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors group/th"
                                        onClick={() => handleRenameColumn(s[0])}
                                    >
                                        <div className="flex items-center gap-1">
                                            {s[0]}
                                            {s[3] === 'PRI' && <span className="text-indigo-500">*</span>}
                                            <Edit2 className="w-3 h-3 opacity-0 group-hover/th:opacity-100 transition-opacity ml-auto" />
                                        </div>
                                    </th>
                                ))}
                                <th className="px-6 py-4 font-bold uppercase tracking-wider text-[10px] text-right">Actions</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                            {filteredData.map((row, idx) => {
                                const pkField = getPrimaryField();
                                const pkValue = row[pkField];
                                const isEditing = editingRow === pkValue;

                                return (
                                    <tr key={pkValue !== undefined && pkValue !== null ? `row-${pkValue}` : `row-idx-${idx}`} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 transition-colors group">
                                        {schema.map(s => {
                                            const field = s[0];
                                            return (
                                                <td key={field} className="px-6 py-4">
                                                    {isEditing ? (
                                                        <input 
                                                            className="w-full bg-white dark:bg-slate-700 border border-slate-200 dark:border-slate-600 rounded px-2 py-1 text-sm outline-none focus:ring-2 focus:ring-indigo-500 font-medium"
                                                            value={editData[field] ?? ''}
                                                            onChange={(e) => setEditData({...editData, [field]: e.target.value})}
                                                            disabled={field === pkField} // Don't allow PK editing usually
                                                        />
                                                    ) : (
                                                        <span className={`font-medium ${field === pkField ? 'text-indigo-600 dark:text-indigo-400 font-mono text-xs' : 'text-slate-700 dark:text-slate-300'}`}>
                                                            {String(row[field] ?? '-')}
                                                        </span>
                                                    )}
                                                </td>
                                            );
                                        })}
                                        <td className="px-6 py-4 text-right">
                                            <div className="flex items-center justify-end gap-2">
                                                {isEditing ? (
                                                    <>
                                                        <button 
                                                            onClick={handleSave}
                                                            className="p-1.5 text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/10 rounded-lg transition-colors"
                                                        >
                                                            <Check className="w-4 h-4" />
                                                        </button>
                                                        <button 
                                                            onClick={() => setEditingRow(null)}
                                                            className="p-1.5 text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/10 rounded-lg transition-colors"
                                                        >
                                                            <X className="w-4 h-4" />
                                                        </button>
                                                    </>
                                                ) : (
                                                    <>
                                                        <button 
                                                            onClick={() => handleEdit(row)}
                                                            className="p-1.5 text-slate-400 hover:text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/10 rounded-lg transition-colors"
                                                        >
                                                            <Edit2 className="w-4 h-4" />
                                                        </button>
                                                        <button 
                                                            onClick={() => handleDelete(pkValue)}
                                                            className="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/10 rounded-lg transition-colors"
                                                        >
                                                            <Trash2 className="w-4 h-4" />
                                                        </button>
                                                    </>
                                                )}
                                            </div>
                                        </td>
                                    </tr>
                                );
                            })}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}
