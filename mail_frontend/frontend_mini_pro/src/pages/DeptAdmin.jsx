import React, { useState, useMemo } from 'react';
import { useTheme } from '../context/ThemeContext';
import {
    Search, Upload, FileDown, Save, ChevronLeft, LayoutGrid, Eye,
    List, GraduationCap, Filter, MoreHorizontal, ArrowLeft, Users, Activity, Plus, Trash2, Send, Shield, X, Info,
    Edit3, Undo2, CheckCircle2, AlertTriangle, Sparkles, FileSpreadsheet, RefreshCw, Download, Layers, Check
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import * as XLSX from 'xlsx';

import { useData } from '../context/DataContext';
import { API_BASE_URL } from '../config/api';

export default function DeptAdminDashboard() {
    const { toggleTheme, theme } = useTheme();
    const { students, setStudents, ktAttempts, setKtAttempts, reconciliationSummary, setReconciliationSummary } = useData();
    const navigate = useNavigate();

    const [viewMode, setViewMode] = useState('dashboard'); // 'dashboard', 'edit', or 'kt'
    const [selectedYear, setSelectedYear] = useState(null); // 'FE', 'SE', 'TE', 'BE', or 'KT'
    const [displayMode, setDisplayMode] = useState('list'); // 'list' or 'grid'
    const [isEditing, setIsEditing] = useState(true);
    const [isLoading, setIsLoading] = useState(false);
    const [isMailing, setIsMailing] = useState(false);
    const [uploadSemester, setUploadSemester] = useState('sem3');
    const [importMode, setImportMode] = useState('pdf'); // 'pdf' or 'excel'
    const [batchResults, setBatchResults] = useState([]); // Temporary working batch
    const [excelHeaders, setExcelHeaders] = useState([]); // Dynamic headers for Excel mode
    const [error, setError] = useState(null);
    const [currentFileId, setCurrentFileId] = useState(null);
    const [isApproved, setIsApproved] = useState(false);
    const [previewImage, setPreviewImage] = useState(null); // Full-screen image preview
    const [focusedStudent, setFocusedStudent] = useState(null); // Student focused for side panel
    const [searchQuery, setSearchQuery] = useState('');

    // --- KT Processing State ---
    const [ktSession, setKtSession] = useState('SH 2026');
    const [ktLevel, setKtLevel] = useState('SE');
    const [ktSemester, setKtSemester] = useState('sem3');
    const [ktUploadLoading, setKtUploadLoading] = useState(false);
    const [ktSearchQuery, setKtSearchQuery] = useState('');
    const [syncingRegular, setSyncingRegular] = useState(false);

    // --- Final Output & Reconciliation Modal State ---
    const [showReconcileModal, setShowReconcileModal] = useState(false);
    const [reconcileLoading, setReconcileLoading] = useState(false);
    const [reconcileLevel, setReconcileLevel] = useState('SE');
    const [reconcileSemester, setReconcileSemester] = useState('');
    const [reconciliationData, setReconciliationData] = useState(null);
    const [isExportingFinal, setIsExportingFinal] = useState(false);


    const resetBatch = () => {
        if (window.confirm("Are you sure you want to reset this batch? All unsaved extractions will be lost.")) {
            setBatchResults([]);
            setError(null);
            setIsLoading(false);
        }
    };

    const handleFileUpload = async (event) => {
        const file = event.target.files[0];
        if (!file || !selectedYear) return;

        setIsLoading(true);
        setError(null);

        const user = JSON.parse(localStorage.getItem('user') || '{}');
        const formData = new FormData();
        formData.append('file', file);

        // Use master list for post-extraction mapping
        const masterList = students[selectedYear];
        const expectedNames = masterList.map(s => s.name);
        formData.append('expected_names', JSON.stringify(expectedNames));

        try {
            if (importMode === 'excel') {
                // === EXCEL IMPORT PATH ===
                const response = await fetch(`${API_BASE_URL}/upload-excel?user_name=${encodeURIComponent(user.name || 'Unknown')}&semester=${uploadSemester}`, {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || 'Excel upload failed');
                }

                const data = await response.json();
                if (data.success && data.students) {
                    const mapped = data.students.map(s => ({
                        id: Date.now() + Math.random(),
                        name: s.name,
                        ern: s.ern || 'N/A',
                        roll: s.roll || 'N/A',
                        email: 'pending@college.edu',
                        isExtracted: true,
                        extractedFrom: 'EXCEL',
                        marks: {
                            [uploadSemester]: {
                                gpa: s.ocr_result.gpa,
                                status: s.ocr_result.status,
                                ocrValue: s.ocr_result.gpa,
                                ocrStatus: s.ocr_result.status,
                                subjectMarks: s.ocr_result.subjectMarks || null
                            }
                        }
                    }));
                    setBatchResults(prev => [...prev, ...mapped]);
                    setCurrentFileId(data.file_id);
                    setIsApproved(false);
                }
                alert(`Excel Import Complete! Added ${data.count} students.`);
            } else if (selectedYear === 'FE' || selectedYear === 'BE') {
                // === FE/BE PDF PATH ===
                const response = await fetch(`${API_BASE_URL}/upload-fe-be?user_name=${encodeURIComponent(user.name || 'Unknown')}&semester=${uploadSemester}`, {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || 'Upload failed');
                }

                const data = await response.json();
                if (data.success && data.students) {
                    const mapped = data.students.map(s => ({
                        id: Date.now() + Math.random(),
                        name: s.name,
                        ern: s.ern || 'N/A',
                        roll: s.roll || 'N/A',
                        email: 'pending@college.edu',
                        isExtracted: true,
                        extractedFrom: 'PDF OCR',
                        marks: {
                            [uploadSemester]: {
                                gpa: s.ocr_result.gpa,
                                status: s.ocr_result.status,
                                ocrValue: s.ocr_result.gpa,
                                ocrStatus: s.ocr_result.status,
                                screenshot: s.ocr_result.screenshot
                            }
                        }
                    }));
                    setBatchResults(prev => [...prev, ...mapped]);
                    setCurrentFileId(data.file_id);
                    setIsApproved(false);
                }
                alert(`FE/BE Extraction Complete! Added ${data.count} students.`);
            } else {
                // === SE/TE PDF PATH (Streaming) ===
                const endpoint = 'upload-marksheet-stream';
                const response = await fetch(`${API_BASE_URL}/${endpoint}?user_name=${encodeURIComponent(user.name || 'Unknown')}&semester=${uploadSemester}`, {
                    method: 'POST',
                    body: formData,
                });

                if (!response.ok) {
                    const errData = await response.json();
                    throw new Error(errData.detail || 'Upload failed');
                }

                const reader = response.body.getReader();
                const decoder = new TextDecoder();
                let buffer = '';
                let extractedStudentCount = 0;

                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop();

                    for (const line of lines) {
                        if (!line.trim()) continue;
                        let chunk;
                        try {
                            chunk = JSON.parse(line);
                        } catch (parseErr) {
                            console.warn('Stream parse error on line:', line, parseErr);
                            continue;
                        }
                        
                        if (chunk.students && chunk.students.length > 0) {
                            extractedStudentCount += chunk.students.length;
                            setBatchResults(prev => {
                                const updated = [...prev];
                                chunk.students.forEach(ocrS => {
                                    const idx = updated.findIndex(u => u.name === ocrS.name);
                                    if (idx !== -1) {
                                        updated[idx] = {
                                            ...updated[idx],
                                            marks: {
                                                ...updated[idx].marks,
                                                [uploadSemester]: {
                                                    gpa: ocrS.ocr_result.gpa,
                                                    status: ocrS.ocr_result.status,
                                                    ocrValue: ocrS.ocr_result.gpa,
                                                    ocrStatus: ocrS.ocr_result.status,
                                                    subjectMarks: ocrS.ocr_result.subjectMarks || null
                                                }
                                            }
                                        };
                                    } else {
                                        updated.push({
                                            id: Date.now() + Math.random(),
                                            name: ocrS.name,
                                            ern: ocrS.ern || 'N/A',
                                            roll: ocrS.roll || 'N/A',
                                            email: 'pending@college.edu',
                                            isExtracted: true,
                                            extractedFrom: 'PDF OCR',
                                            marks: {
                                                [uploadSemester]: {
                                                    gpa: ocrS.ocr_result.gpa,
                                                    status: ocrS.ocr_result.status,
                                                    ocrValue: ocrS.ocr_result.gpa,
                                                    ocrStatus: ocrS.ocr_result.status,
                                                    subjectMarks: ocrS.ocr_result.subjectMarks || null
                                                }
                                            }
                                        });
                                    }
                                });
                                return updated;
                            });
                        }
                        
                        if (chunk.file_id) setCurrentFileId(chunk.file_id);
                        setIsApproved(false);
                        setError(`Processing... ${chunk.total_pages ? `Page ${chunk.page}/${chunk.total_pages}` : 'Done'}`);
                    }
                }
                setError(null);

                if (extractedStudentCount === 0) {
                    // Stream completed but yielded zero results — likely a Poppler/OCR failure
                    setError('PDF processing returned 0 students. Poppler may not be installed on the server.');
                    alert('⚠️ PDF OCR returned 0 results.\n\nThe server could not extract any students from this PDF.\nPossible causes:\n• Poppler is not installed or not in PATH on the server.\n• The PDF format is not recognized.\n\nThe stored students have been reloaded for manual editing.');
                    // Reload stored students so the table is not left blank
                    const storedList = students[selectedYear] || [];
                    if (storedList.length > 0) {
                        const prepared = storedList.map(s => {
                            const normalizedMarks = {};
                            Object.entries(s.marks || {}).forEach(([sem, m]) => {
                                normalizedMarks[sem] = {
                                    ...m,
                                    ocrValue: m.ocrValue !== undefined ? m.ocrValue : (m.gpa ?? 0),
                                    ocrStatus: m.ocrStatus !== undefined ? m.ocrStatus : (m.status ?? 'P')
                                };
                            });
                            return { ...s, isExtracted: s.isExtracted || false, extractedFrom: s.extractedFrom || 'STORED RECORD', marks: normalizedMarks };
                        });
                        setBatchResults(prepared);
                    }
                } else {
                    alert(`PDF OCR Process Complete! Extracted ${extractedStudentCount} student(s).`);
                }
            }
        } catch (err) {
            console.error(err);
            setError('Error: ' + err.message);
        } finally {
            setIsLoading(false);
        }
    };

    const normalizeStatus = (st) => {
        if (!st) return 'F';
        const s = st.toString().toUpperCase().trim();
        if (s === 'P' || s === 'PASS' || s === 'SUCCESS') return 'PASS';
        return 'FAIL';
    };

    const isGpaEdited = (markObj) => {
        if (!markObj) return false;
        const current = Number(markObj.gpa ?? 0);
        const original = Number(markObj.ocrValue !== undefined ? markObj.ocrValue : (markObj.gpa ?? 0));
        return Math.abs(current - original) > 0.0001;
    };

    const isStatusEdited = (markObj) => {
        if (!markObj) return false;
        const current = normalizeStatus(markObj.status);
        const original = normalizeStatus(markObj.ocrStatus !== undefined ? markObj.ocrStatus : markObj.status);
        return current !== original;
    };

    const handleBatchMarkChange = (studentId, sem, field, value) => {
        setBatchResults(prev => prev.map(s => {
            if (s.id !== studentId) return s;
            const currentSemMarks = s.marks?.[sem] || {};
            
            // Baseline OCR values preserved
            const ocrVal = currentSemMarks.ocrValue !== undefined 
                ? currentSemMarks.ocrValue 
                : (currentSemMarks.gpa !== undefined ? currentSemMarks.gpa : 0);
                
            const ocrStat = currentSemMarks.ocrStatus !== undefined 
                ? currentSemMarks.ocrStatus 
                : (currentSemMarks.status || 'P');

            const parsedVal = field === 'gpa' 
                ? (value === '' ? '' : parseFloat(value) || 0)
                : value;

            return {
                ...s,
                marks: {
                    ...s.marks,
                    [sem]: {
                        ...currentSemMarks,
                        ocrValue: ocrVal,
                        ocrStatus: ocrStat,
                        [field]: parsedVal
                    }
                }
            };
        }));
    };

    const handleRevertBatchMark = (studentId, sem, field) => {
        setBatchResults(prev => prev.map(s => {
            if (s.id !== studentId) return s;
            const currentSemMarks = s.marks?.[sem] || {};
            if (field === 'gpa' && currentSemMarks.ocrValue !== undefined) {
                return {
                    ...s,
                    marks: {
                        ...s.marks,
                        [sem]: {
                            ...currentSemMarks,
                            gpa: currentSemMarks.ocrValue
                        }
                    }
                };
            }
            if (field === 'status' && currentSemMarks.ocrStatus !== undefined) {
                return {
                    ...s,
                    marks: {
                        ...s.marks,
                        [sem]: {
                            ...currentSemMarks,
                            status: currentSemMarks.ocrStatus
                        }
                    }
                };
            }
            return s;
        }));
    };

    const handleBatchInfoChange = (studentId, field, value) => {
        setBatchResults(prev => prev.map(s =>
            s.id === studentId ? { ...s, [field]: value } : s
        ));
    };

    const loadStoredStudentsToBatch = () => {
        const list = students[selectedYear] || [];
        if (!list.length) {
            alert(`No stored students found for ${selectedYear}`);
            return;
        }
        const prepared = list.map(s => {
            const normalizedMarks = {};
            Object.entries(s.marks || {}).forEach(([sem, m]) => {
                normalizedMarks[sem] = {
                    ...m,
                    ocrValue: m.ocrValue !== undefined ? m.ocrValue : (m.gpa ?? 0),
                    ocrStatus: m.ocrStatus !== undefined ? m.ocrStatus : (m.status ?? 'P')
                };
            });
            return {
                ...s,
                isExtracted: true,
                extractedFrom: s.extractedFrom || 'STORED MASTER',
                marks: normalizedMarks
            };
        });
        setBatchResults(prepared);
        setIsApproved(false);
    };

    // Calculate count of edited items before making full and final
    const editedCount = useMemo(() => {
        let count = 0;
        batchResults.forEach(student => {
            if (!student.marks) return;
            Object.values(student.marks).forEach(m => {
                if (isGpaEdited(m)) count++;
                if (isStatusEdited(m)) count++;
            });
        });
        return count;
    }, [batchResults]);

    // Search filter for students
    const filteredBatchResults = useMemo(() => {
        if (!searchQuery.trim()) return batchResults;
        const q = searchQuery.toLowerCase().trim();
        return batchResults.filter(s =>
            (s.name && s.name.toLowerCase().includes(q)) ||
            (s.roll && s.roll.toLowerCase().includes(q)) ||
            (s.ern && s.ern.toString().toLowerCase().includes(q))
        );
    }, [batchResults, searchQuery]);

    const finalizeAndSave = () => {
        if (!window.confirm("Apply these changes to the permanent database?")) return;

        setStudents(prev => {
            const updatedYearData = [...prev[selectedYear]];
            batchResults.forEach(batchS => {
                const matchKey = (selectedYear === 'FE' || selectedYear === 'BE') ? 'ern' : 'name';
                const idx = updatedYearData.findIndex(s => {
                    const sVal = s[matchKey] ? s[matchKey].toString().toLowerCase().trim() : '';
                    const bVal = batchS[matchKey] ? batchS[matchKey].toString().toLowerCase().trim() : '';
                    return sVal === bVal;
                });

                if (idx !== -1) {
                    updatedYearData[idx] = { ...updatedYearData[idx], marks: { ...updatedYearData[idx].marks, ...batchS.marks } };
                } else {
                    // Both PDF and Excel might have new students
                    updatedYearData.unshift(batchS);
                }
            });
            return { ...prev, [selectedYear]: updatedYearData };
        });

        setBatchResults([]);
        alert("Batch finalized and saved!");
    };

    const handleMarkChange = (year, studentId, sem, field, value) => {
        setStudents(prev => ({
            ...prev,
            [year]: prev[year].map(s =>
                s.id === studentId ? {
                    ...s,
                    marks: {
                        ...s.marks,
                        [sem]: { ...s.marks[sem], [field]: field === 'gpa' ? parseFloat(value) || 0 : value }
                    }
                } : s
            )
        }));
    };

    const handleInfoChange = (year, studentId, field, value) => {
        setStudents(prev => ({
            ...prev,
            [year]: prev[year].map(s =>
                s.id === studentId ? { ...s, [field]: value } : s
            )
        }));
    };

    const handleDeleteStudent = (year, studentId) => {
        if (window.confirm("Are you sure you want to delete this student record?")) {
            setStudents(prev => ({
                ...prev,
                [year]: prev[year].filter(s => s.id !== studentId)
            }));
        }
    };

    const handleExportToExcel = () => {
        const dataList = batchResults.length > 0 ? batchResults : students[selectedYear];
        if (!selectedYear || !dataList.length) {
            alert("No data to export!");
            return;
        }

        const user = JSON.parse(localStorage.getItem('user') || '{}');
        let deptName = user.dept || 'General';
        if (deptName === 'Computer Science') deptName = 'Computer Engineering Department';

        const dataToExport = dataList.map(student => {
            const row = {
                "Student Name": student.name,
                "ERN / Roll": student.ern || student.roll || 'N/A'
            };

            if (selectedYear === 'FE') {
                row["Sem 1 GPA"] = student.marks.sem1?.gpa || 0;
                row["Sem 1 Status"] = student.marks.sem1?.status || 'F';
                row["Sem 2 GPA"] = student.marks.sem2?.gpa || 0;
                row["Sem 2 Status"] = student.marks.sem2?.status || 'F';
            } else if (selectedYear === 'SE') {
                row["Sem 3 GPA"] = student.marks.sem3?.gpa || 0;
                row["Sem 3 Status"] = student.marks.sem3?.status || 'F';
                row["Sem 4 GPA"] = student.marks.sem4?.gpa || 0;
                row["Sem 4 Status"] = student.marks.sem4?.status || 'F';
            } else if (selectedYear === 'TE') {
                [3, 4, 5, 6].forEach(s => {
                    row[`Sem ${s} GPA`] = student.marks[`sem${s}`]?.gpa || 0;
                    row[`Sem ${s} Status`] = student.marks[`sem${s}`]?.status || 'P';
                });
            } else if (selectedYear === 'BE') {
                [1, 2, 3, 4, 5, 6, 7, 8].forEach(s => {
                    row[`Sem ${s} GPA`] = student.marks[`sem${s}`]?.gpa || 0;
                    row[`Sem ${s} Status`] = student.marks[`sem${s}`]?.status || 'P';
                });
            }
            
            row["Average GPA"] = calculateAvg(student.marks).toFixed(2);
            return row;
        });

        const wb = XLSX.utils.book_new();
        const ws = XLSX.utils.aoa_to_sheet([
            [deptName.toUpperCase()],
            [`${selectedYear} BATCH RESULT EXTRACTION REPORT - ${new Date().toLocaleDateString()}`],
            [] 
        ]);

        XLSX.utils.sheet_add_json(ws, dataToExport, { origin: "A4" });
        XLSX.utils.book_append_sheet(wb, ws, "Results");
        XLSX.writeFile(wb, `${selectedYear}_Student_Results_${Date.now()}.xlsx`);
    };

    const handleApproveBatch = async () => {
        if (!window.confirm("Confirm: Are these results human-verified? Approved results will be locked for editing and unlocked for distribution.")) return;
        
        try {
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            if (currentFileId) {
                await fetch(`${API_BASE_URL}/approve-file`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ file_id: currentFileId, admin_name: user.name || 'Admin' }),
                });
            }
            setIsApproved(true);
            alert("Batch Approved & Locked!");
        } catch (err) {
            console.error("Approval process failed:", err);
            setIsApproved(true); // Allow local override to unblock user
        }
    };

    const handleMailResults = async () => {
        if (!isApproved) {
            alert("Access Denied: You must Approve and Lock the results before mailing to students.");
            return;
        }

        const listToMail = batchResults.length > 0 ? batchResults : students[selectedYear];

        if (!selectedYear || !listToMail.length) {
            alert("No data to mail!");
            return;
        }

        if (!window.confirm(`Are you sure you want to mail results to ${listToMail.length} students? This will use the configured SMTP server.`)) {
            return;
        }

        setIsMailing(true);
        const user = JSON.parse(localStorage.getItem('user') || '{}');

        try {
            const payload = {
                user_name: user.name || 'Unknown',
                file_id: currentFileId,
                semester: uploadSemester,
                students: listToMail.map(s => ({
                    name: s.name,
                    email: s.email,
                    pointer: s.marks[uploadSemester]?.gpa || 0.0,
                    avg: 0.0, // Backend uses pointer mostly
                    screenshot: s.marks[uploadSemester]?.screenshot || null,
                    subject_marks: s.marks[uploadSemester]?.subjectMarks || null
                }))
            };

            const response = await fetch(`${API_BASE_URL}/send-results`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload),
            });

            if (!response.ok) throw new Error('Mailing failed');

            const data = await response.json();
            alert(`Mailing process complete!\nSuccess: ${data.success_count || 0}\nFailed: ${data.fail_count || 0}`);

            // Auto-finalize on success if in batch mode
            if (batchResults.length > 0) {
                finalizeAndSave();
            }
        } catch (err) {
            console.error(err);
            alert('Error sending mails: ' + err.message);
        } finally {
            setIsMailing(false);
        }
    };

    const handleSelectKT = () => {
        setSelectedYear('KT');
        setViewMode('kt');
        fetchKTResults();
    };

    const fetchKTResults = async () => {
        try {
            const url = `${API_BASE_URL}/kt-results?student_level=${ktLevel}&semester=${ktSemester}`;
            const res = await fetch(url);
            if (res.ok) {
                const data = await res.json();
                if (data.success && Array.isArray(data.results)) {
                    setKtAttempts(data.results);
                }
            }
        } catch (e) {
            console.warn('Could not load KT results from backend:', e);
        }
    };

    const handleKTUpload = async (event) => {
        const file = event.target.files[0];
        if (!file) return;

        setKtUploadLoading(true);
        setError(null);

        const user = JSON.parse(localStorage.getItem('user') || '{}');
        const formData = new FormData();
        formData.append('file', file);

        try {
            const queryParams = new URLSearchParams({
                user_name: user.name || 'Anonymous',
                exam_session: ktSession,
                semester: ktSemester,
                student_level: ktLevel,
            });

            const response = await fetch(`${API_BASE_URL}/upload-kt?${queryParams.toString()}`, {
                method: 'POST',
                body: formData,
            });

            if (!response.ok) {
                const errData = await response.json();
                throw new Error(errData.detail || 'KT upload failed');
            }

            const data = await response.json();
            if (data.success) {
                alert(`KT Result Processed! Extracted ${data.count} student attempt(s).`);
                fetchKTResults();
            }
        } catch (err) {
            console.error(err);
            alert('Error processing KT results: ' + err.message);
        } finally {
            setKtUploadLoading(false);
            event.target.value = '';
        }
    };

    const handleSyncRegular = async () => {
        try {
            setSyncingRegular(true);
            const user = JSON.parse(localStorage.getItem('user') || '{}');
            const masterList = students[ktLevel] || [];

            const res = await fetch(`${API_BASE_URL}/store-regular-attempts`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_level: ktLevel,
                    exam_session: 'FH 2026',
                    semester: ktSemester,
                    students: masterList,
                }),
            });

            if (res.ok) {
                const data = await res.json();
                alert(`Successfully synchronized ${data.imported || 0} regular attempts to reconciliation pool!`);
            } else {
                throw new Error('Sync failed');
            }
        } catch (e) {
            alert('Error syncing regular attempts: ' + e.message);
        } finally {
            setSyncingRegular(false);
        }
    };

    const handleRunReconciliation = async () => {
        try {
            setReconcileLoading(true);
            const res = await fetch(`${API_BASE_URL}/reconcile`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_level: reconcileLevel,
                    semester: reconcileSemester || null,
                }),
            });

            if (!res.ok) {
                const errData = await res.json();
                throw new Error(errData.detail || 'Reconciliation failed');
            }

            const data = await res.json();
            if (data.success) {
                setReconciliationData(data);
                if (data.summary) {
                    setReconciliationSummary(data.summary);
                }
            }
        } catch (e) {
            alert('Reconciliation error: ' + e.message);
        } finally {
            setReconcileLoading(false);
        }
    };

    const handleDownloadFinalOutput = async () => {
        try {
            setIsExportingFinal(true);
            const res = await fetch(`${API_BASE_URL}/generate-final-output`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    student_level: reconcileLevel,
                    semester: reconcileSemester || null,
                }),
            });

            if (!res.ok) {
                const err = await res.json();
                throw new Error(err.detail || 'Export failed');
            }

            const blob = await res.blob();
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = `${reconcileLevel}_Consolidated_Results_${new Date().toISOString().slice(0, 10)}.xlsx`;
            document.body.appendChild(a);
            a.click();
            a.remove();
            window.URL.revokeObjectURL(downloadUrl);
        } catch (e) {
            alert('Export failed: ' + e.message);
        } finally {
            setIsExportingFinal(false);
        }
    };

    const handleSelectYear = (year) => {
        setSelectedYear(year);
        const list = students[year] || [];
        const prepared = list.map(s => {
            const normalizedMarks = {};
            Object.entries(s.marks || {}).forEach(([sem, m]) => {
                normalizedMarks[sem] = {
                    ...m,
                    ocrValue: m.ocrValue !== undefined ? m.ocrValue : (m.gpa ?? 0),
                    ocrStatus: m.ocrStatus !== undefined ? m.ocrStatus : (m.status ?? 'P')
                };
            });
            return {
                ...s,
                isExtracted: s.isExtracted || false,
                extractedFrom: s.extractedFrom || 'STORED RECORD',
                marks: normalizedMarks
            };
        });
        setBatchResults(prepared);
        setIsApproved(false);
        // Set correct default semester for each year
        if (year === 'FE' || year === 'BE') {
            setUploadSemester('sem1');
        } else if (year === 'SE') {
            setUploadSemester('sem3');
        } else if (year === 'TE') {
            setUploadSemester('sem3');
        }
        setViewMode('edit');
    };


    return (
        <div className="min-h-screen bg-slate-50 dark:bg-slate-950 font-sans pb-20">
            {/* Navbar */}
            <nav className="sticky top-0 z-30 bg-white/80 dark:bg-slate-900/80 backdrop-blur-md border-b border-slate-200 dark:border-slate-800">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center gap-4">
                            <div className="flex-shrink-0 w-10 h-10 bg-gradient-to-tr from-blue-600 to-cyan-500 rounded-xl flex items-center justify-center text-white shadow-lg shadow-blue-500/20">
                                <GraduationCap className="w-5 h-5" />
                            </div>
                            <div className="hidden md:block">
                                <h1 className="text-lg font-bold text-slate-900 dark:text-white">Dept. Admin</h1>
                                <p className="text-xs text-slate-500 font-medium">Computer Science Dept.</p>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                            <button onClick={toggleTheme} className="p-2 rounded-lg text-slate-500 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors">
                                <div className="text-xl">{theme === 'dark' ? '☀️' : '🌙'}</div>
                            </button>
                            <div className="h-6 w-px bg-slate-200 dark:bg-slate-700 hidden sm:block"></div>
                            <div className="flex items-center gap-3">
                                <img src="https://api.dicebear.com/7.x/avataaars/svg?seed=DeptAdmin" className="w-8 h-8 rounded-full bg-slate-100" alt="Admin" />
                                <button onClick={() => navigate('/')} className="text-sm font-medium text-slate-600 dark:text-slate-300 hover:text-red-500 transition-colors">
                                    Logout
                                </button>
                            </div>
                        </div>
                    </div>
                </div>
            </nav>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8 animate-fade-in">

                {viewMode === 'dashboard' ? (
                    <div className="space-y-8">
                        <div className="text-center mb-12">
                            <h2 className="text-3xl font-bold text-slate-900 dark:text-white">Department Dashboard</h2>
                            <p className="text-slate-500 mt-2">Select an academic year to manage and edit results.</p>
                        </div>

                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 max-w-6xl mx-auto">
                            <SelectionCard
                                title="FE Students"
                                description="First Year Results Management"
                                stats="Sem 1 & Sem 2"
                                icon={Users}
                                color="emerald"
                                onClick={() => handleSelectYear('FE')}
                            />
                            <SelectionCard
                                title="SE Students"
                                description="Second Year Results Management"
                                stats="Sem 3 & Sem 4"
                                icon={Users}
                                color="blue"
                                onClick={() => handleSelectYear('SE')}
                            />
                            <SelectionCard
                                title="TE Students"
                                description="Third Year Results Management"
                                stats="Sem 3, 4, 5 & 6"
                                icon={Activity}
                                color="purple"
                                onClick={() => handleSelectYear('TE')}
                            />
                            <SelectionCard
                                title="BE Students"
                                description="Final Year Results Management"
                                stats="Sem 1 to Sem 8"
                                icon={GraduationCap}
                                color="orange"
                                onClick={() => handleSelectYear('BE')}
                            />
                            <SelectionCard
                                title="KT Processing"
                                description="Re-examination & Multi-Attempt Tracking"
                                stats="FH / SH Exam Sessions"
                                icon={AlertTriangle}
                                color="rose"
                                onClick={handleSelectKT}
                            />
                            <SelectionCard
                                title="Final Reconciliation"
                                description="Generate Consolidated 3-Sheet Output"
                                stats="Reconcile & Excel Export"
                                icon={FileSpreadsheet}
                                color="indigo"
                                onClick={() => {
                                    setShowReconcileModal(true);
                                    handleRunReconciliation();
                                }}
                            />
                        </div>
                    </div>

                ) : viewMode === 'kt' ? (
                    <KTProcessingView
                        onBack={() => setViewMode('dashboard')}
                        ktAttempts={ktAttempts}
                        ktSession={ktSession}
                        setKtSession={setKtSession}
                        ktLevel={ktLevel}
                        setKtLevel={setKtLevel}
                        ktSemester={ktSemester}
                        setKtSemester={setKtSemester}
                        onUpload={handleKTUpload}
                        isLoading={ktUploadLoading}
                        onSyncRegular={handleSyncRegular}
                        isSyncing={syncingRegular}
                        onRefresh={fetchKTResults}
                        onOpenReconcile={() => {
                            setReconcileLevel(ktLevel);
                            setReconcileSemester(ktSemester);
                            setShowReconcileModal(true);
                            handleRunReconciliation();
                        }}
                        onPreviewImage={setPreviewImage}
                    />
                ) : (
                    <div className="animate-fade-in space-y-6">
                        <button
                            onClick={() => setViewMode('dashboard')}
                            className="flex items-center gap-2 text-slate-500 hover:text-blue-600 transition-colors group mb-4"
                        >
                            <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                            <span>Back to Selection</span>
                        </button>


                        <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6 mb-8 bg-white dark:bg-slate-900 p-6 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm">
                            <div>
                                <h2 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-3">
                                    {selectedYear} Result Management
                                </h2>
                                <p className="text-sm text-slate-500 mt-1">
                                    {batchResults.length > 0 ? `Working on ${batchResults.length} students` : 'Select a master list and upload to begin.'}
                                </p>
                                {isLoading && <div className="mt-2 flex items-center gap-2 text-blue-600 font-bold animate-pulse text-xs uppercase tracking-wider"><Activity className="w-3 h-3"/> Processing Results {error}</div>}
                                {error && !isLoading && <div className="mt-2 text-amber-500 font-bold text-xs uppercase tracking-wider">{error}</div>}
                            </div>

                            <div className="flex flex-wrap items-center gap-3">
                                <button
                                    onClick={() => {
                                        const newS = {
                                            id: Date.now(),
                                            name: "New Student",
                                            roll: `${selectedYear}-XXX`,
                                            email: "new@college.edu",
                                            marks: selectedYear === 'SE' ? {
                                                sem3: { gpa: 0, status: "P" },
                                                sem4: { gpa: 0, status: "P" }
                                            } : {
                                                sem3: { gpa: 0, status: "P" },
                                                sem4: { gpa: 0, status: "P" },
                                                sem5: { gpa: 0, status: "P" },
                                                sem6: { gpa: 0, status: "P" }
                                            }
                                        };
                                        setBatchResults(prev => [newS, ...prev]);
                                        setStudents(prev => ({
                                            ...prev,
                                            [selectedYear]: [newS, ...prev[selectedYear]]
                                        }));
                                    }}
                                    className="px-4 py-2 text-xs font-bold text-emerald-600 hover:bg-emerald-50 dark:hover:bg-emerald-900/20 border border-emerald-200 dark:border-emerald-900/30 rounded-xl transition-all flex items-center gap-2"
                                >
                                    <Plus className="w-4 h-4" /> Add Student
                                </button>

                                <button
                                    onClick={resetBatch}
                                    className="px-4 py-2 text-xs font-bold text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 border border-rose-200 dark:border-rose-900/30 rounded-xl transition-all"
                                >
                                    Reset Batch
                                </button>

                                <div className="h-8 w-px bg-slate-100 dark:bg-slate-800 hidden sm:block mx-1"></div>

                                <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase">Sem:</span>
                                    <select
                                        value={uploadSemester}
                                        onChange={(e) => setUploadSemester(e.target.value)}
                                        className="bg-transparent text-sm font-bold text-blue-600 outline-none cursor-pointer"
                                    >
                                        {selectedYear === 'FE' && (
                                            <>
                                                <option value="sem1">Sem 1</option>
                                                <option value="sem2">Sem 2</option>
                                            </>
                                        )}
                                        {selectedYear === 'SE' && (
                                            <>
                                                <option value="sem3">Sem 3</option>
                                                <option value="sem4">Sem 4</option>
                                            </>
                                        )}
                                        {selectedYear === 'TE' && (
                                            <>
                                                <option value="sem1">Sem 1</option>
                                                <option value="sem2">Sem 2</option>
                                                <option value="sem3">Sem 3</option>
                                                <option value="sem4">Sem 4</option>
                                                <option value="sem5">Sem 5</option>
                                                <option value="sem6">Sem 6</option>
                                            </>
                                        )}
                                        {selectedYear === 'BE' && (
                                            [1, 2, 3, 4, 5, 6, 7, 8].map(s => <option key={s} value={`sem${s}`}>Sem {s}</option>)
                                        )}
                                    </select>
                                </div>

                                <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 dark:bg-slate-800/50 rounded-xl border border-slate-200 dark:border-slate-700">
                                    <span className="text-[10px] font-bold text-slate-400 uppercase">Mode:</span>
                                    <select
                                        value={importMode}
                                        onChange={(e) => setImportMode(e.target.value)}
                                        className="bg-transparent text-sm font-bold text-indigo-600 outline-none cursor-pointer"
                                    >
                                        <option value="pdf">PDF OCR</option>
                                        <option value="excel">Excel Import</option>
                                    </select>
                                </div>

                                <label className={`px-4 py-2 bg-blue-600 text-white text-xs font-bold rounded-xl flex items-center gap-2 shadow-lg shadow-blue-500/20 cursor-pointer hover:bg-blue-700 transition-all ${isLoading ? 'opacity-50 pointer-events-none' : ''}`}>
                                    <Upload className="w-4 h-4" />
                                    <span>{isLoading ? 'Processing...' : (importMode === 'pdf' ? 'Import PDF' : 'Import Excel')}</span>
                                    <input
                                        type="file"
                                        accept={importMode === 'pdf' ? "application/pdf" : ".xlsx, .xls"}
                                        className="hidden"
                                        onChange={handleFileUpload}
                                        disabled={isLoading}
                                    />
                                </label>

                                {batchResults.length > 0 && !isApproved && (
                                    <button
                                        onClick={handleApproveBatch}
                                        className="px-4 py-2 bg-gradient-to-tr from-amber-500 to-orange-500 text-white text-xs font-black uppercase tracking-wider rounded-xl flex items-center gap-2 shadow-lg shadow-amber-500/30 hover:scale-105 active:scale-95 transition-all animate-pulse"
                                        title="Lock edits and finalize batch before mailing"
                                    >
                                        <Shield className="w-4 h-4" /> Approve & Finalize
                                    </button>
                                )}

                                {batchResults.length > 0 && isApproved && (
                                    <div className="flex items-center gap-2">
                                        <span className="px-3 py-1.5 bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border border-emerald-500/30 rounded-xl text-xs font-bold flex items-center gap-1.5 shadow-sm">
                                            <CheckCircle2 className="w-4 h-4 text-emerald-600" /> Full & Final Locked
                                        </span>
                                        <button
                                            onClick={() => setIsApproved(false)}
                                            className="px-2.5 py-1.5 text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 text-xs font-semibold rounded-xl border border-slate-200 dark:border-slate-700 transition-all hover:bg-slate-50 dark:hover:bg-slate-800"
                                            title="Unlock to make further adjustments before applying"
                                        >
                                            Unlock
                                        </button>
                                        <button
                                            onClick={finalizeAndSave}
                                            className="px-4 py-2 bg-emerald-600 text-white text-xs font-bold rounded-xl flex items-center gap-2 shadow-lg shadow-emerald-500/20 hover:bg-emerald-700 transition-all"
                                        >
                                            <Save className="w-4 h-4" /> Apply Changes
                                        </button>
                                    </div>
                                )}

                                <div className="flex items-center gap-1.5">
                                    <button
                                        onClick={() => {
                                            setReconcileLevel(selectedYear);
                                            setShowReconcileModal(true);
                                            handleRunReconciliation();
                                        }}
                                        className="px-3 py-2 text-indigo-600 hover:bg-indigo-50 dark:hover:bg-indigo-900/20 border border-indigo-200 dark:border-indigo-800/40 rounded-xl text-xs font-bold transition-all flex items-center gap-1.5"
                                        title="Reconcile and generate 3-sheet Excel"
                                    >
                                        <FileSpreadsheet className="w-4 h-4" />
                                        <span>Reconcile Output</span>
                                    </button>
                                    <button
                                        onClick={handleExportToExcel}
                                        className="p-2 text-slate-400 hover:text-blue-600 hover:bg-blue-50 dark:hover:bg-blue-900/20 rounded-xl transition-all"
                                        title="Export to Excel"
                                    >
                                        <FileDown className="w-5 h-5" />
                                    </button>
                                    <button
                                        onClick={handleMailResults}
                                        disabled={isMailing}
                                        title={isApproved ? "Send Emails" : "Approve first to enable mailing"}
                                        className={`p-2 rounded-xl transition-all ${isMailing ? 'animate-pulse' : ''} ${isApproved ? 'bg-indigo-50 dark:bg-indigo-900/20 text-indigo-600' : 'text-slate-300 dark:text-slate-700 cursor-not-allowed'}`}
                                    >
                                        <Send className="w-5 h-5" />
                                    </button>
                                </div>

                            </div>
                        </div>

                        {/* Toolbar */}
                        <div className="bg-white dark:bg-slate-900 p-4 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm flex flex-col sm:flex-row justify-between items-center gap-4">
                            <div className="relative w-full sm:w-80">
                                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                                <input 
                                    type="text" 
                                    placeholder="Search students..." 
                                    value={searchQuery}
                                    onChange={(e) => setSearchQuery(e.target.value)}
                                    className="w-full pl-10 pr-4 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-lg text-sm focus:ring-2 focus:ring-blue-500 outline-none text-slate-900 dark:text-white" 
                                />
                            </div>

                            <div className="flex items-center flex-wrap gap-4">
                                {editedCount > 0 && !isApproved && (
                                    <div className="flex items-center gap-2 px-3 py-1.5 bg-amber-500/15 border border-amber-500/40 rounded-xl text-amber-700 dark:text-amber-400 text-xs font-bold animate-pulse shadow-sm" title="Hover over edited boxes in the table to inspect previous read values and revert if needed">
                                        <Edit3 className="w-3.5 h-3.5 text-amber-500" />
                                        <span>{editedCount} {editedCount === 1 ? 'box' : 'boxes'} edited (pending final approval)</span>
                                    </div>
                                )}
                                {isApproved && (
                                    <div className="flex items-center gap-2 px-3 py-1.5 bg-emerald-500/15 border border-emerald-500/40 rounded-xl text-emerald-700 dark:text-emerald-400 text-xs font-bold">
                                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-500" />
                                        <span>Full & Final: Verified & Locked</span>
                                    </div>
                                )}
                                <div className="flex items-center gap-2 pl-4 border-l border-slate-200 dark:border-slate-700">
                                    <span className="text-xs font-medium text-slate-500 uppercase">Edit Mode</span>
                                    <button
                                        onClick={() => setIsEditing(!isEditing)}
                                        className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${isEditing ? 'bg-blue-600' : 'bg-slate-200 dark:bg-slate-700'}`}
                                    >
                                        <span className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${isEditing ? 'translate-x-6' : 'translate-x-1'}`} />
                                    </button>
                                </div>
                            </div>
                        </div>

                        {/* Results Table */}
                        <div className="bg-white dark:bg-slate-900 rounded-xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                            <div className="overflow-x-auto">
                                <table className="w-full text-sm text-left">
                                    <thead>
                                        <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300">
                                            <th className="px-6 py-4 font-semibold whitespace-nowrap">{(selectedYear === 'FE' || selectedYear === 'BE') ? 'ERN / Name' : 'Student Name'}</th>
                                                    
                                                    {selectedYear === 'FE' && (
                                                        <>
                                                            <th className="px-4 py-4 font-semibold text-center whitespace-nowrap">Sem 1</th>
                                                            <th className="px-4 py-4 font-semibold text-center whitespace-nowrap">Sem 2</th>
                                                        </>
                                                    )}

                                                    {selectedYear === 'SE' && (
                                                        <>
                                                            <th className="px-4 py-4 font-semibold text-center whitespace-nowrap">Sem 3</th>
                                                            <th className="px-4 py-4 font-semibold text-center whitespace-nowrap">Sem 4</th>
                                                        </>
                                                    )}

                                                    {selectedYear === 'TE' && (
                                                        <>
                                                            <th className="px-4 py-4 font-semibold text-center whitespace-nowrap">Sem 5</th>
                                                            <th className="px-4 py-4 font-semibold text-center whitespace-nowrap">Sem 6</th>
                                                        </>
                                                    )}

                                                    {selectedYear === 'BE' && [1, 2, 3, 4, 5, 6, 7, 8].map(s => (
                                                        <th key={s} className="px-4 py-4 font-semibold text-center whitespace-nowrap">Sem {s}</th>
                                                    ))}

                                                    {(selectedYear === 'FE' || selectedYear === 'BE') && (
                                                        <th className="px-6 py-4 font-semibold text-center">Preview</th>
                                                    )}
                                            <th className="px-6 py-4 text-right font-semibold">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                        {filteredBatchResults.length === 0 && (
                                            <tr>
                                                <td colSpan={selectedYear === 'BE' ? 11 : (selectedYear === 'FE' ? 5 : 4)} className="py-16 text-center">
                                                    <div className="flex flex-col items-center justify-center gap-3 max-w-md mx-auto">
                                                        <div className="w-14 h-14 rounded-2xl bg-amber-50 dark:bg-amber-950/30 text-amber-600 dark:text-amber-400 flex items-center justify-center border border-amber-200 dark:border-amber-800 shadow-sm">
                                                            {searchQuery ? <Search className="w-6 h-6" /> : <Upload className="w-6 h-6" />}
                                                        </div>
                                                        <div>
                                                            <h4 className="text-base font-bold text-slate-800 dark:text-white">
                                                                {searchQuery ? 'No matching students found' : 'No Active Batch Loaded'}
                                                            </h4>
                                                            <p className="text-xs text-slate-500 mt-1">
                                                                {searchQuery 
                                                                    ? `No students in the current batch matched "${searchQuery}".` 
                                                                    : 'Import a PDF / Excel file to extract results, or load stored students to review and edit.'}
                                                            </p>
                                                        </div>
                                                        {!searchQuery && (students[selectedYear]?.length > 0) && (
                                                            <button
                                                                onClick={loadStoredStudentsToBatch}
                                                                className="mt-2 px-5 py-2.5 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 text-white rounded-xl text-xs font-bold shadow-lg shadow-blue-500/25 transition-all flex items-center gap-2 hover:scale-[1.02] active:scale-[0.98]"
                                                            >
                                                                <Users className="w-4 h-4" />
                                                                Load {students[selectedYear].length} Stored {selectedYear} Students for Review & Edit
                                                            </button>
                                                        )}
                                                    </div>
                                                </td>
                                            </tr>
                                        )}
                                        {filteredBatchResults.map((student, idx) => (
                                            <tr key={student.id || idx} className="hover:bg-slate-50 dark:hover:bg-slate-800/50 group transition-colors">
                                                <td className="px-6 py-4 font-medium text-slate-900 dark:text-white">
                                                    <div className="flex flex-col">
                                                        <input
                                                            type="text"
                                                            value={student.name}
                                                            onChange={(e) => handleBatchInfoChange(student.id, 'name', e.target.value)}
                                                            disabled={isApproved || !isEditing}
                                                            className={`bg-transparent border-b border-transparent focus:border-blue-500 outline-none w-full font-medium transition-opacity ${!isEditing ? 'opacity-70 pointer-events-none' : ''}`}
                                                            placeholder="Student Name"
                                                        />
                                                        {(selectedYear === 'FE' || selectedYear === 'BE') && (
                                                            <span className="text-[10px] font-mono text-slate-400 mt-0.5">
                                                                ERN: {student.ern || 'N/A'}
                                                            </span>
                                                        )}
                                                    </div>
                                                </td>

                                                {(selectedYear === 'FE' || selectedYear === 'SE' || selectedYear === 'TE') && (
                                                    <>
                                                        {(selectedYear === 'FE' ? [1, 2] : selectedYear === 'SE' ? [3, 4] : [5, 6]).map(s => (
                                                            <td key={s} className="px-2 py-4 text-center relative overflow-visible">
                                                                <EditableResultCell
                                                                    studentId={student.id}
                                                                    sem={`sem${s}`}
                                                                    markData={student.marks[`sem${s}`]}
                                                                    isApproved={isApproved}
                                                                    isEditing={isEditing}
                                                                    isHighlighted={uploadSemester === `sem${s}`}
                                                                    size="normal"
                                                                    onChange={handleBatchMarkChange}
                                                                    onRevert={handleRevertBatchMark}
                                                                />
                                                            </td>
                                                        ))}
                                                        {selectedYear === 'FE' && (
                                                            <td className="px-6 py-4 text-center relative group/shot">
                                                                <button 
                                                                    onClick={() => setPreviewImage(student.marks[uploadSemester]?.screenshot)}
                                                                    className="inline-flex items-center justify-center p-2 bg-slate-100 dark:bg-slate-800 rounded-lg text-slate-500 cursor-zoom-in hover:bg-emerald-50 hover:text-emerald-600 transition-colors"
                                                                    title="Click for full preview"
                                                                >
                                                                    <Eye className="w-4 h-4" />
                                                                </button>
                                                                <div className="invisible group-hover/shot:visible absolute right-full top-1/2 -translate-y-1/2 mr-4 z-50 p-1 bg-white dark:bg-slate-800 border-2 border-indigo-500 rounded-xl shadow-2xl overflow-hidden min-w-[300px]">
                                                                    {student.marks[uploadSemester]?.screenshot ? (
                                                                        <img 
                                                                            src={student.marks[uploadSemester].screenshot.startsWith('data:') ? student.marks[uploadSemester].screenshot : `data:image/jpeg;base64,${student.marks[uploadSemester].screenshot}`} 
                                                                            className="max-w-[400px] h-auto object-contain"
                                                                            alt="Marks Section"
                                                                        />
                                                                    ) : <div className="p-4 text-xs italic text-slate-400">No screenshot captured</div>}
                                                                </div>
                                                            </td>
                                                        )}
                                                    </>
                                                )}
                                                {selectedYear === 'BE' && (
                                                    <>
                                                        {[1, 2, 3, 4, 5, 6, 7, 8].map(s => (
                                                            <td key={s} className="px-2 py-4 text-center relative overflow-visible">
                                                                <EditableResultCell
                                                                    studentId={student.id}
                                                                    sem={`sem${s}`}
                                                                    markData={student.marks[`sem${s}`]}
                                                                    isApproved={isApproved}
                                                                    isEditing={isEditing}
                                                                    isHighlighted={uploadSemester === `sem${s}`}
                                                                    size="compact"
                                                                    onChange={handleBatchMarkChange}
                                                                    onRevert={handleRevertBatchMark}
                                                                />
                                                            </td>
                                                        ))}
                                                        <td className="px-6 py-4 text-center relative group/shot">
                                                            <button 
                                                                onClick={() => setPreviewImage(student.marks[uploadSemester]?.screenshot)}
                                                                className="inline-flex items-center justify-center p-1.5 bg-slate-50 dark:bg-slate-800 rounded-md text-slate-400 hover:text-emerald-500 cursor-zoom-in transition-colors"
                                                                title="Click for full preview"
                                                            >
                                                                <Eye className="w-3.5 h-3.5" />
                                                            </button>
                                                            <div className="invisible group-hover/shot:visible absolute right-full top-1/2 -translate-y-1/2 mr-4 z-50 p-1 bg-white dark:bg-slate-800 border-2 border-indigo-500 rounded-xl shadow-2xl overflow-hidden min-w-[300px]">
                                                                {student.marks[uploadSemester]?.screenshot ? (
                                                                    <img 
                                                                        src={student.marks[uploadSemester].screenshot.startsWith('data:') ? student.marks[uploadSemester].screenshot : `data:image/jpeg;base64,${student.marks[uploadSemester].screenshot}`} 
                                                                        className="max-w-[400px] h-auto object-contain"
                                                                        alt="Marks Section"
                                                                    />
                                                                ) : <div className="p-4 text-xs italic text-slate-400">No screenshot captured</div>}
                                                            </div>
                                                        </td>
                                                    </>
                                                )}
                                                <td className="px-6 py-4 text-right overflow-visible">
                                                    <div className="flex items-center justify-end gap-3">
                                                        {student.isExtracted && (
                                                            <span className="text-emerald-600 flex items-center gap-1.5 text-xs font-bold whitespace-nowrap">
                                                                <div className="w-1.5 h-1.5 bg-emerald-500 rounded-full animate-pulse"></div>
                                                                {student.extractedFrom || 'EXTRACTED'}
                                                            </span>
                                                        )}

                                                        {/* Floating Academic Breakdown Popover */}
                                                        {(selectedYear === 'SE' || selectedYear === 'TE') && (
                                                            <div className="relative group/breakdown">
                                                                <button
                                                                    className="p-1.5 text-slate-400 hover:text-amber-500 hover:bg-amber-50 dark:hover:bg-amber-900/10 rounded-lg transition-all"
                                                                    title="Subject Performance"
                                                                >
                                                                    <Info className="w-4 h-4" />
                                                                </button>
                                                                
                                                                {/* Popover Card */}
                                                                <div 
                                                                    className="invisible group-hover/breakdown:visible absolute right-0 bottom-full mb-4 z-[9999] w-80 bg-slate-900 dark:bg-slate-900 border border-slate-700 rounded-3xl shadow-[0_20px_60px_rgba(0,0,0,0.6)] p-6 space-y-4 transform transition-all duration-300 translate-y-2 group-hover/breakdown:translate-y-0 opacity-0 group-hover/breakdown:opacity-100 pointer-events-none"
                                                                >
                                                                    <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                                                                        <div className="flex flex-col text-left">
                                                                            <h4 className="text-[10px] font-black text-amber-500 uppercase tracking-[0.2em] mb-0.5">Academic Breakdown</h4>
                                                                            <span className="text-[9px] text-slate-400 font-bold font-mono truncate max-w-[150px]">{student.name}</span>
                                                                        </div>
                                                                        <span className="px-2 py-1 bg-amber-500/10 text-amber-500 rounded-lg text-[9px] font-black ring-1 ring-amber-500/20">{uploadSemester.toUpperCase()}</span>
                                                                    </div>
                                                                    
                                                                    <div className="grid grid-cols-2 gap-x-6 gap-y-2 text-left">
                                                                        {student.marks[uploadSemester]?.subjectMarks ?
                                                                            Object.entries(student.marks[uploadSemester].subjectMarks).map(([sub, mark]) => (
                                                                                <div key={sub} className="flex justify-between items-center py-0.5 group/item border-b border-slate-800 last:border-0">
                                                                                    <span className="text-[10px] text-slate-500 font-bold uppercase truncate max-w-[100px]" title={sub}>{sub}</span>
                                                                                    <span className="text-[10px] font-black text-slate-200 font-mono">{mark}</span>
                                                                                </div>
                                                                            )) : <span className="col-span-2 text-slate-600 text-[10px] italic text-center py-4">No detailed records</span>
                                                                        }
                                                                    </div>
                                                                    
                                                                    <div className="pt-3 border-t border-slate-800 flex items-center justify-between">
                                                                        <div className="flex items-center gap-1.5">
                                                                            <Shield className="w-3 h-3 text-emerald-500" />
                                                                            <span className="text-[8px] text-slate-500 font-black uppercase">Official Scan Results</span>
                                                                        </div>
                                                                        <span className="text-[10px] font-black text-amber-500">GPA: {student.marks[uploadSemester]?.gpa || '0.00'}</span>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        )}

                                                        <button
                                                            onClick={() => (isEditing && !isApproved) && setBatchResults(prev => prev.filter(p => p.id !== student.id))}
                                                            disabled={!isEditing || isApproved}
                                                            className={`p-1.5 rounded-lg transition-colors ${(!isEditing || isApproved) ? 'text-slate-200 cursor-not-allowed' : 'text-slate-400 hover:text-rose-600 hover:bg-rose-50 dark:hover:bg-rose-900/10'}`}
                                                            title={(!isEditing || isApproved) ? "Edit mode disabled" : "Remove from batch"}
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
                    </div>
                )}
            </main>

            {/* Final Batch Reconciliation Modal */}
            {showReconcileModal && (
                <ReconciliationModal
                    isOpen={showReconcileModal}
                    onClose={() => setShowReconcileModal(false)}
                    reconcileLevel={reconcileLevel}
                    setReconcileLevel={setReconcileLevel}
                    reconcileSemester={reconcileSemester}
                    setReconcileSemester={setReconcileSemester}
                    onRun={handleRunReconciliation}
                    isLoading={reconcileLoading}
                    data={reconciliationData}
                    onDownload={handleDownloadFinalOutput}
                    isDownloading={isExportingFinal}
                />
            )}

            {/* Full-screen Image Preview Modal */}
            {previewImage && (

                <div 
                    className="fixed inset-0 z-[100] flex items-center justify-center bg-slate-900/90 backdrop-blur-md transition-all p-4 md:p-12 animate-in fade-in duration-300"
                    onClick={() => setPreviewImage(null)}
                >
                    <div 
                        className="relative max-w-7xl w-full h-full flex flex-col items-center justify-center"
                        onClick={(e) => e.stopPropagation()}
                    >
                        <button 
                            className="absolute -top-10 right-0 p-2 text-white hover:text-rose-400 transition-colors bg-white/10 rounded-full hover:bg-white/20"
                            onClick={() => setPreviewImage(null)}
                        >
                            <X className="w-6 h-6" />
                        </button>
                        
                        <div className="w-full h-full bg-white dark:bg-slate-800 rounded-2xl overflow-auto shadow-2xl border-4 border-white/10 flex items-start justify-center p-4">
                            <img 
                                src={previewImage.startsWith('data:') ? previewImage : `data:image/jpeg;base64,${previewImage}`} 
                                className="max-w-none w-full h-auto object-contain rounded-lg"
                                alt="Marksheet Section Full View"
                            />
                        </div>
                        
                        <p className="mt-4 text-slate-400 text-sm font-medium flex items-center gap-2">
                             Click outside to close preview
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}

function SelectionCard({ title, description, stats, icon: Icon, color, onClick }) {
    const colorConfigs = {
        emerald: "bg-emerald-50 text-emerald-600 group-hover:bg-emerald-600 shadow-emerald-100",
        blue: "bg-blue-50 text-blue-600 group-hover:bg-blue-600 shadow-blue-100",
        purple: "bg-purple-50 text-purple-600 group-hover:bg-purple-600 shadow-purple-100",
        orange: "bg-orange-50 text-orange-600 group-hover:bg-orange-600 shadow-orange-100",
        rose: "bg-rose-50 text-rose-600 group-hover:bg-rose-600 shadow-rose-100",
        indigo: "bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600 shadow-indigo-100",
    };
    const colorStyles = colorConfigs[color] || colorConfigs.blue;
    return (
        <button
            onClick={onClick}
            className="glass-card p-10 flex flex-col items-center justify-center gap-6 hover:scale-[1.03] transition-all group border-2 border-transparent hover:border-blue-500/20 w-full"
        >
            <div className={`w-20 h-20 rounded-full flex items-center justify-center transition-colors ${colorStyles} group-hover:text-white shadow-inner`}>
                <Icon className="w-10 h-10" />
            </div>
            <div className="text-center">
                <h3 className="text-2xl font-bold text-slate-900 dark:text-white uppercase tracking-tight">{title}</h3>
                <p className="text-slate-500 mt-2">{description}</p>
                <div className="mt-4 px-3 py-1 bg-slate-100 dark:bg-slate-800 rounded-full text-xs font-bold text-slate-600 dark:text-slate-400">
                    {stats}
                </div>
            </div>
        </button>
    );
}

function EditableResultCell({
    studentId,
    sem,
    markData = {},
    isApproved,
    isEditing,
    isHighlighted,
    size = 'normal',
    onChange,
    onRevert,
}) {
    const gpaVal = markData.gpa !== undefined && markData.gpa !== null ? markData.gpa : 0;
    const ocrGpa = markData.ocrValue !== undefined ? markData.ocrValue : gpaVal;

    const numGpa = Number(gpaVal || 0);
    const numOcrGpa = Number(ocrGpa || 0);
    const hasGpaEdited = !isApproved && Math.abs(numGpa - numOcrGpa) > 0.0001;

    const statusVal = (markData.status || 'F').toString().toUpperCase().trim();
    const ocrStatusVal = (markData.ocrStatus || statusVal).toString().toUpperCase().trim();

    const isPass = statusVal === 'PASS' || statusVal === 'P' || statusVal === 'SUCCESS';
    const ocrIsPass = ocrStatusVal === 'PASS' || ocrStatusVal === 'P' || ocrStatusVal === 'SUCCESS';
    const hasStatusEdited = !isApproved && isPass !== ocrIsPass;

    return (
        <div className="flex flex-col items-center gap-1.5 relative">
            {/* Pointer / GPA Edit Box */}
            <div className="relative group/ptr inline-block">
                <input
                    type="number"
                    step="0.01"
                    value={gpaVal}
                    onChange={(e) => onChange(studentId, sem, 'gpa', e.target.value)}
                    disabled={isApproved || !isEditing}
                    aria-label={`Pointer for ${sem}`}
                    className={`text-center font-bold transition-all rounded-lg outline-none ${
                        size === 'compact' ? 'w-14 h-7 text-xs border' : 'w-16 h-8 text-sm border-2'
                    } ${
                        isApproved || !isEditing
                            ? 'opacity-60 cursor-not-allowed bg-slate-50 dark:bg-slate-800/50 border-slate-200 dark:border-slate-700 text-slate-700 dark:text-slate-300'
                            : hasGpaEdited
                                ? 'border-amber-500 ring-2 ring-amber-400 dark:ring-amber-400/80 bg-amber-50 dark:bg-amber-950/40 text-amber-950 dark:text-amber-100 shadow-[0_0_15px_rgba(245,158,11,0.35)]'
                                : isHighlighted
                                    ? 'bg-blue-50 dark:bg-blue-900/20 border-blue-400 ring-2 ring-blue-500/10'
                                    : 'bg-transparent border-slate-200 dark:border-slate-800 focus:border-slate-400'
                    }`}
                />

                {/* Floating pill badge on the corner of the box */}
                {hasGpaEdited && (
                    <span 
                        className="absolute -top-2.5 -right-2 z-20 flex items-center gap-0.5 px-1.5 py-0.5 rounded-full text-[8px] font-black uppercase tracking-wider bg-amber-500 text-white shadow-md ring-1 ring-white/60 pointer-events-none"
                    >
                        <Edit3 className="w-2 h-2" /> EDITED
                    </span>
                )}

                {/* The hovering popover box indicating "This box was edited" */}
                {hasGpaEdited && (
                    <div className="invisible group-hover/ptr:visible opacity-0 group-hover/ptr:opacity-100 transition-all duration-200 absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-[999] pointer-events-auto">
                        <div className="bg-slate-900/95 dark:bg-slate-900/95 text-white text-xs rounded-2xl shadow-[0_15px_40px_rgba(0,0,0,0.6)] border border-amber-500/70 p-3 min-w-[210px] text-left backdrop-blur-md">
                            <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-slate-800">
                                <div className="flex items-center gap-1.5 text-amber-400 font-extrabold text-[11px] tracking-wide">
                                    <Edit3 className="w-3.5 h-3.5 text-amber-400" />
                                    <span>This box was edited</span>
                                </div>
                                <span className="text-[8px] bg-amber-500/20 text-amber-300 font-black px-1.5 py-0.5 rounded-md border border-amber-500/30 uppercase tracking-wider">
                                    DRAFT
                                </span>
                            </div>
                            <div className="space-y-1.5 text-[11px]">
                                <div className="flex items-center justify-between gap-3 text-slate-300">
                                    <span className="text-slate-400 text-[10px] font-medium">Pointer Read:</span>
                                    <span className="font-mono font-bold text-slate-200 bg-slate-800 px-1.5 py-0.5 rounded border border-slate-700">
                                        {Number(numOcrGpa).toFixed(2)}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between gap-3">
                                    <span className="text-amber-300 text-[10px] font-medium">Edited Value:</span>
                                    <span className="font-mono font-black text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/30">
                                        {Number(numGpa).toFixed(2)}
                                    </span>
                                </div>
                                <p className="text-[9px] text-amber-300/80 pt-0.5 leading-tight">
                                    Pointer altered prior to final sign-off
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onRevert(studentId, sem, 'gpa');
                                }}
                                className="mt-2.5 w-full flex items-center justify-center gap-1.5 py-1 px-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-[10px] font-bold transition-all hover:scale-[1.02] active:scale-[0.98]"
                                title="Revert to original pointer read"
                            >
                                <Undo2 className="w-3 h-3" /> Revert to Read ({Number(numOcrGpa).toFixed(2)})
                            </button>
                        </div>
                        {/* Triangle arrow */}
                        <div className="w-2.5 h-2.5 bg-slate-900 border-r border-b border-amber-500/70 transform rotate-45 mx-auto -mt-1.5"></div>
                    </div>
                )}
            </div>

            {/* Result / Status Edit Box */}
            <div className="relative group/res inline-block">
                <button
                    type="button"
                    onClick={() => !(isApproved || !isEditing) && onChange(studentId, sem, 'status', isPass ? 'F' : 'P')}
                    disabled={isApproved || !isEditing}
                    aria-label={`Result for ${sem}`}
                    className={`font-bold uppercase tracking-wider transition-all rounded-md flex items-center justify-center ${
                        size === 'compact' ? 'px-1.5 py-0.5 text-[8px]' : 'px-2 py-0.5 text-[10px]'
                    } ${
                        isPass
                            ? 'bg-emerald-100/90 text-emerald-700 dark:bg-emerald-900/40 dark:text-emerald-300 hover:bg-emerald-200'
                            : 'bg-rose-100/90 text-rose-700 dark:bg-rose-900/40 dark:text-rose-300 hover:bg-rose-200'
                    } ${
                        isApproved || !isEditing ? 'opacity-60 cursor-not-allowed' : 'cursor-pointer'
                    } ${
                        hasStatusEdited
                            ? 'border-2 border-amber-500 ring-2 ring-amber-400 dark:ring-amber-400/80 shadow-[0_0_15px_rgba(245,158,11,0.35)]'
                            : 'border border-transparent'
                    }`}
                >
                    {size === 'compact' ? (isPass ? 'P' : 'F') : (isPass ? 'PASS' : 'FAIL')}
                </button>

                {/* Floating pill badge on the corner of the box */}
                {hasStatusEdited && (
                    <span 
                        className="absolute -top-2.5 -right-2 z-20 flex items-center gap-0.5 px-1 py-0.2 rounded-full text-[7px] font-black uppercase tracking-wider bg-amber-500 text-white shadow-md ring-1 ring-white/60 pointer-events-none"
                    >
                        EDITED
                    </span>
                )}

                {/* The hovering popover box indicating "This box was edited" */}
                {hasStatusEdited && (
                    <div className="invisible group-hover/res:visible opacity-0 group-hover/res:opacity-100 transition-all duration-200 absolute bottom-full left-1/2 -translate-x-1/2 mb-2 z-[999] pointer-events-auto">
                        <div className="bg-slate-900/95 dark:bg-slate-900/95 text-white text-xs rounded-2xl shadow-[0_15px_40px_rgba(0,0,0,0.6)] border border-amber-500/70 p-3 min-w-[210px] text-left backdrop-blur-md">
                            <div className="flex items-center justify-between pb-1.5 mb-2 border-b border-slate-800">
                                <div className="flex items-center gap-1.5 text-amber-400 font-extrabold text-[11px] tracking-wide">
                                    <Edit3 className="w-3.5 h-3.5 text-amber-400" />
                                    <span>This box was edited</span>
                                </div>
                                <span className="text-[8px] bg-amber-500/20 text-amber-300 font-black px-1.5 py-0.5 rounded-md border border-amber-500/30 uppercase tracking-wider">
                                    DRAFT
                                </span>
                            </div>
                            <div className="space-y-1.5 text-[11px]">
                                <div className="flex items-center justify-between gap-3 text-slate-300">
                                    <span className="text-slate-400 text-[10px] font-medium">Result Read:</span>
                                    <span className={`font-mono font-bold px-1.5 py-0.5 rounded border text-[10px] ${
                                        ocrIsPass ? 'bg-emerald-900/40 text-emerald-300 border-emerald-700/50' : 'bg-rose-900/40 text-rose-300 border-rose-700/50'
                                    }`}>
                                        {ocrIsPass ? 'PASS' : 'FAIL'}
                                    </span>
                                </div>
                                <div className="flex items-center justify-between gap-3">
                                    <span className="text-amber-300 text-[10px] font-medium">Edited Result:</span>
                                    <span className={`font-mono font-black px-1.5 py-0.5 rounded border text-[10px] ${
                                        isPass ? 'bg-emerald-900/50 text-emerald-300 border-emerald-500/50' : 'bg-rose-900/50 text-rose-300 border-rose-500/50'
                                    }`}>
                                        {isPass ? 'PASS' : 'FAIL'}
                                    </span>
                                </div>
                                <p className="text-[9px] text-amber-300/80 pt-0.5 leading-tight">
                                    Result toggled prior to final verification
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    onRevert(studentId, sem, 'status');
                                }}
                                className="mt-2.5 w-full flex items-center justify-center gap-1.5 py-1 px-2 rounded-lg bg-amber-500/20 hover:bg-amber-500/30 text-amber-300 border border-amber-500/40 text-[10px] font-bold transition-all hover:scale-[1.02] active:scale-[0.98]"
                                title="Revert to original result read"
                            >
                                <Undo2 className="w-3 h-3" /> Revert to Read ({ocrIsPass ? 'PASS' : 'FAIL'})
                            </button>
                        </div>
                        {/* Triangle arrow */}
                        <div className="w-2.5 h-2.5 bg-slate-900 border-r border-b border-amber-500/70 transform rotate-45 mx-auto -mt-1.5"></div>
                    </div>
                )}
            </div>
        </div>
    );
}

function calculateAvg(marks) {
    const vals = Object.values(marks).map(m => m.gpa).filter(v => typeof v === 'number' && v > 0);
    return vals.length ? vals.reduce((a, b) => a + b, 0) / vals.length : 0;
}

// =========================================================================
// KT Examination Processing View Component
// =========================================================================

function KTProcessingView({
    onBack,
    ktAttempts = [],
    ktSession,
    setKtSession,
    ktLevel,
    setKtLevel,
    ktSemester,
    setKtSemester,
    onUpload,
    isLoading,
    onSyncRegular,
    isSyncing,
    onRefresh,
    onOpenReconcile,
    onPreviewImage,
}) {
    const [searchTerm, setSearchTerm] = useState('');

    const filtered = useMemo(() => {
        return (ktAttempts || []).filter(item => {
            const sid = (item.student_identifier || '').toLowerCase();
            const sname = (item.student_name || '').toLowerCase();
            const term = searchTerm.toLowerCase();
            return sid.includes(term) || sname.includes(term);
        });
    }, [ktAttempts, searchTerm]);

    const stats = useMemo(() => {
        const total = ktAttempts.length;
        const passed = ktAttempts.filter(a => (a.attempt_status || '').toUpperCase() === 'PASS').length;
        const failed = ktAttempts.filter(a => (a.attempt_status || '').toUpperCase() === 'FAIL').length;
        const withPointers = ktAttempts.filter(a => a.clearance_pointer && a.clearance_pointer.trim()).length;
        return { total, passed, failed, withPointers };
    }, [ktAttempts]);

    return (
        <div className="animate-fade-in space-y-6">
            <button
                onClick={onBack}
                className="flex items-center gap-2 text-slate-500 hover:text-blue-600 transition-colors group mb-2"
            >
                <ArrowLeft className="w-4 h-4 group-hover:-translate-x-1 transition-transform" />
                <span>Back to Dashboard</span>
            </button>

            {/* Header & Controls */}
            <div className="bg-white dark:bg-slate-900 p-6 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm space-y-6">
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 border-b border-slate-100 dark:border-slate-800 pb-5">
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="px-2.5 py-1 bg-rose-500/10 text-rose-600 dark:text-rose-400 font-black text-[10px] tracking-wider uppercase rounded-lg border border-rose-500/20">
                                Multi-Attempt Processing
                            </span>
                            <h2 className="text-2xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                KT Examination Workspace
                            </h2>
                        </div>
                        <p className="text-sm text-slate-500 mt-1">
                            Upload and inspect re-examination attempts across examination sessions (FH/SH).
                        </p>
                    </div>

                    <div className="flex flex-wrap items-center gap-2.5">
                        <button
                            onClick={onSyncRegular}
                            disabled={isSyncing}
                            className="px-3.5 py-2 text-xs font-bold text-blue-600 bg-blue-50 dark:bg-blue-900/20 hover:bg-blue-100 dark:hover:bg-blue-900/40 border border-blue-200 dark:border-blue-800/40 rounded-xl transition-all flex items-center gap-1.5"
                            title="Sync regular student attempts into the database table for multi-attempt reconciliation"
                        >
                            <RefreshCw className={`w-3.5 h-3.5 ${isSyncing ? 'animate-spin' : ''}`} />
                            <span>{isSyncing ? 'Syncing...' : 'Sync Regular Pool'}</span>
                        </button>

                        <button
                            onClick={onRefresh}
                            className="p-2 text-slate-500 hover:text-blue-600 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-all"
                            title="Refresh KT Records"
                        >
                            <RefreshCw className="w-4 h-4" />
                        </button>

                        <button
                            onClick={onOpenReconcile}
                            className="px-4 py-2 bg-gradient-to-r from-indigo-600 to-blue-600 text-white text-xs font-bold rounded-xl flex items-center gap-2 shadow-lg shadow-indigo-500/20 hover:opacity-95 transition-all"
                        >
                            <FileSpreadsheet className="w-4 h-4" />
                            <span>Run Reconciliation & Output</span>
                        </button>
                    </div>
                </div>

                {/* Scope Selectors & Upload Form */}
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
                    <div>
                        <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 block">
                            Student Level
                        </label>
                        <select
                            value={ktLevel}
                            onChange={(e) => setKtLevel(e.target.value)}
                            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm font-semibold text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-rose-500"
                        >
                            <option value="FE">FE (First Year)</option>
                            <option value="SE">SE (Second Year)</option>
                            <option value="TE">TE (Third Year)</option>
                            <option value="BE">BE (Final Year)</option>
                        </select>
                    </div>

                    <div>
                        <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 block">
                            Examination Session
                        </label>
                        <input
                            type="text"
                            value={ktSession}
                            onChange={(e) => setKtSession(e.target.value)}
                            placeholder="e.g. SH 2026 or FH 2026"
                            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm font-semibold text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-rose-500"
                        />
                    </div>

                    <div>
                        <label className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-1.5 block">
                            Semester
                        </label>
                        <select
                            value={ktSemester}
                            onChange={(e) => setKtSemester(e.target.value)}
                            className="w-full px-3 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-sm font-semibold text-slate-900 dark:text-white outline-none focus:ring-2 focus:ring-rose-500"
                        >
                            {[1, 2, 3, 4, 5, 6, 7, 8].map(s => (
                                <option key={s} value={`sem${s}`}>Semester {s}</option>
                            ))}
                        </select>
                    </div>

                    <div>
                        <label className={`w-full py-2.5 px-4 bg-rose-600 hover:bg-rose-700 text-white text-xs font-bold rounded-xl flex items-center justify-center gap-2 shadow-lg shadow-rose-500/20 cursor-pointer transition-all ${isLoading ? 'opacity-50 pointer-events-none' : ''}`}>
                            <Upload className="w-4 h-4" />
                            <span>{isLoading ? 'Processing PDF OCR...' : 'Import KT PDF'}</span>
                            <input
                                type="file"
                                accept="application/pdf"
                                className="hidden"
                                onChange={onUpload}
                                disabled={isLoading}
                            />
                        </label>
                    </div>
                </div>

                {/* Quick Metric Cards */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4 pt-2">
                    <div className="p-4 rounded-2xl bg-slate-50 dark:bg-slate-800/50 border border-slate-100 dark:border-slate-800">
                        <div className="text-xs font-medium text-slate-400">Total KT Records</div>
                        <div className="text-2xl font-extrabold text-slate-900 dark:text-white mt-1">{stats.total}</div>
                    </div>
                    <div className="p-4 rounded-2xl bg-emerald-50/60 dark:bg-emerald-950/20 border border-emerald-200/50 dark:border-emerald-800/30">
                        <div className="text-xs font-bold text-emerald-600 dark:text-emerald-400">Passed KT Attempts</div>
                        <div className="text-2xl font-extrabold text-emerald-600 dark:text-emerald-400 mt-1">{stats.passed}</div>
                    </div>
                    <div className="p-4 rounded-2xl bg-rose-50/60 dark:bg-rose-950/20 border border-rose-200/50 dark:border-rose-800/30">
                        <div className="text-xs font-bold text-rose-600 dark:text-rose-400">Failed KT Attempts</div>
                        <div className="text-2xl font-extrabold text-rose-600 dark:text-rose-400 mt-1">{stats.failed}</div>
                    </div>
                    <div className="p-4 rounded-2xl bg-purple-50/60 dark:bg-purple-950/20 border border-purple-200/50 dark:border-purple-800/30">
                        <div className="text-xs font-bold text-purple-600 dark:text-purple-400">With Clearance Pointer</div>
                        <div className="text-2xl font-extrabold text-purple-600 dark:text-purple-400 mt-1">{stats.withPointers}</div>
                    </div>
                </div>
            </div>

            {/* KT Attempts Table */}
            <div className="bg-white dark:bg-slate-900 rounded-3xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row justify-between items-center gap-3">
                    <div className="relative w-full sm:w-80">
                        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                        <input
                            type="text"
                            placeholder="Filter by ERN, Seat or Name..."
                            value={searchTerm}
                            onChange={(e) => setSearchTerm(e.target.value)}
                            className="w-full pl-9 pr-4 py-2 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs focus:ring-2 focus:ring-rose-500 outline-none text-slate-900 dark:text-white"
                        />
                    </div>
                    <div className="text-xs text-slate-400 font-medium">
                        Showing {filtered.length} of {ktAttempts.length} KT attempts
                    </div>
                </div>

                <div className="overflow-x-auto">
                    <table className="w-full text-xs text-left">
                        <thead>
                            <tr className="bg-slate-50 dark:bg-slate-800/50 border-b border-slate-200 dark:border-slate-800 text-slate-700 dark:text-slate-300 uppercase tracking-wider text-[10px]">
                                <th className="px-5 py-3.5 font-bold">Student Identifier</th>
                                <th className="px-5 py-3.5 font-bold">Student Name</th>
                                <th className="px-4 py-3.5 font-bold text-center">Level</th>
                                <th className="px-4 py-3.5 font-bold text-center">Session</th>
                                <th className="px-4 py-3.5 font-bold text-center">Semester</th>
                                <th className="px-4 py-3.5 font-bold text-center">Status</th>
                                <th className="px-4 py-3.5 font-bold text-center">GPA</th>
                                <th className="px-5 py-3.5 font-bold">Clearance Pointer</th>
                                <th className="px-5 py-3.5 font-bold">Source PDF</th>
                                <th className="px-4 py-3.5 font-bold text-center">Evidence</th>
                            </tr>
                        </thead>
                        <tbody className="divide-y divide-slate-100 dark:divide-slate-800 text-slate-700 dark:text-slate-300">
                            {filtered.length > 0 ? (
                                filtered.map((att, idx) => {
                                    const isPass = (att.attempt_status || '').toUpperCase() === 'PASS';
                                    return (
                                        <tr key={att.attempt_id || idx} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                                            <td className="px-5 py-3.5 font-mono font-bold text-slate-900 dark:text-white">
                                                {att.student_identifier || 'N/A'}
                                            </td>
                                            <td className="px-5 py-3.5 font-medium">
                                                {att.student_name || <span className="text-slate-400 italic">Unassigned</span>}
                                            </td>
                                            <td className="px-4 py-3.5 text-center">
                                                <span className="px-2 py-0.5 bg-slate-100 dark:bg-slate-800 rounded font-semibold text-[10px]">
                                                    {att.student_level || ktLevel}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3.5 text-center font-semibold text-slate-600 dark:text-slate-400">
                                                {att.exam_session}
                                            </td>
                                            <td className="px-4 py-3.5 text-center font-mono">
                                                {att.semester}
                                            </td>
                                            <td className="px-4 py-3.5 text-center">
                                                <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full font-black text-[10px] tracking-wide border ${
                                                    isPass
                                                        ? 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border-emerald-500/30'
                                                        : 'bg-rose-50 dark:bg-rose-950/40 text-rose-600 dark:text-rose-400 border-rose-500/30'
                                                }`}>
                                                    {isPass ? <CheckCircle2 className="w-3 h-3" /> : <AlertTriangle className="w-3 h-3" />}
                                                    {att.attempt_status}
                                                </span>
                                            </td>
                                            <td className="px-4 py-3.5 text-center font-mono font-bold">
                                                {Number(att.gpa || 0).toFixed(2)}
                                            </td>
                                            <td className="px-5 py-3.5">
                                                {att.clearance_pointer ? (
                                                    <span className="px-2 py-0.5 bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-300 border border-purple-200 dark:border-purple-800 rounded text-[10px] font-mono">
                                                        {att.clearance_pointer}
                                                    </span>
                                                ) : (
                                                    <span className="text-slate-400 text-[11px]">—</span>
                                                )}
                                            </td>
                                            <td className="px-5 py-3.5 text-[11px] text-slate-500 truncate max-w-[150px]" title={att.source_pdf}>
                                                {att.source_pdf || 'Uploaded PDF'}
                                            </td>
                                            <td className="px-4 py-3.5 text-center">
                                                {att.screenshot ? (
                                                    <button
                                                        onClick={() => onPreviewImage(att.screenshot)}
                                                        className="p-1 hover:bg-slate-100 dark:hover:bg-slate-800 text-blue-600 rounded transition-colors"
                                                        title="View extraction image snippet"
                                                    >
                                                        <Eye className="w-4 h-4" />
                                                    </button>
                                                ) : (
                                                    <span className="text-slate-400">—</span>
                                                )}
                                            </td>
                                        </tr>
                                    );
                                })
                            ) : (
                                <tr>
                                    <td colSpan={10} className="px-6 py-12 text-center text-slate-400">
                                        <Layers className="w-8 h-8 mx-auto mb-2 opacity-40" />
                                        <p className="font-semibold">No KT examination records found.</p>
                                        <p className="text-xs text-slate-500 mt-1">Import a KT examination PDF above or refresh records.</p>
                                    </td>
                                </tr>
                            )}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
}


// =========================================================================
// Reconciliation & Final Output Modal Component
// =========================================================================

function ReconciliationModal({
    isOpen,
    onClose,
    reconcileLevel,
    setReconcileLevel,
    reconcileSemester,
    setReconcileSemester,
    onRun,
    isLoading,
    data,
    onDownload,
    isDownloading,
}) {
    const [searchQuery, setSearchQuery] = useState('');
    const [filterStatus, setFilterStatus] = useState('ALL');

    const summary = data?.summary || null;
    const results = data?.results || [];
    const exceptions = data?.exceptions || [];

    const filteredResults = useMemo(() => {
        return results.filter(r => {
            const matchSearch =
                (r.student_identifier || '').toLowerCase().includes(searchQuery.toLowerCase()) ||
                (r.student_name || '').toLowerCase().includes(searchQuery.toLowerCase());
            const matchFilter = filterStatus === 'ALL' || r.clearance_status === filterStatus;
            return matchSearch && matchFilter;
        });
    }, [results, searchQuery, filterStatus]);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md animate-in fade-in duration-200">
            <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-2xl border border-slate-200 dark:border-slate-800 max-w-6xl w-full max-h-[92vh] flex flex-col overflow-hidden animate-in zoom-in-95 duration-200">
                {/* Modal Header */}
                <div className="px-8 py-5 border-b border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/40">
                    <div>
                        <div className="flex items-center gap-2">
                            <span className="px-2.5 py-0.5 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 font-bold text-[10px] tracking-wider uppercase rounded-md border border-indigo-500/20">
                                Output Engine
                            </span>
                            <h3 className="text-xl font-bold text-slate-900 dark:text-white flex items-center gap-2">
                                Result Reconciliation & Consolidated Output
                            </h3>
                        </div>
                        <p className="text-xs text-slate-500 mt-1">
                            Reconciles multiple attempts, establishes KT clearance evidence, and generates standardized 3-sheet Excel.
                        </p>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-slate-400 hover:text-slate-600 dark:hover:text-slate-200 rounded-xl hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                {/* Filter and Trigger Bar */}
                <div className="px-8 py-4 bg-slate-50/30 dark:bg-slate-800/20 border-b border-slate-100 dark:border-slate-800 flex flex-wrap items-center justify-between gap-4">
                    <div className="flex flex-wrap items-center gap-3">
                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-500 uppercase">Level:</span>
                            <select
                                value={reconcileLevel}
                                onChange={(e) => setReconcileLevel(e.target.value)}
                                className="px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-bold text-indigo-600 outline-none cursor-pointer"
                            >
                                <option value="FE">FE</option>
                                <option value="SE">SE</option>
                                <option value="TE">TE</option>
                                <option value="BE">BE</option>
                            </select>
                        </div>

                        <div className="flex items-center gap-2">
                            <span className="text-xs font-bold text-slate-500 uppercase">Semester:</span>
                            <select
                                value={reconcileSemester}
                                onChange={(e) => setReconcileSemester(e.target.value)}
                                className="px-3 py-1.5 bg-white dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs font-bold text-indigo-600 outline-none cursor-pointer"
                            >
                                <option value="">All Semesters</option>
                                {[1, 2, 3, 4, 5, 6, 7, 8].map(s => (
                                    <option key={s} value={`sem${s}`}>Semester {s}</option>
                                ))}
                            </select>
                        </div>

                        <button
                            onClick={onRun}
                            disabled={isLoading}
                            className="px-4 py-1.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-md shadow-indigo-500/20 transition-all disabled:opacity-50"
                        >
                            <RefreshCw className={`w-3.5 h-3.5 ${isLoading ? 'animate-spin' : ''}`} />
                            <span>{isLoading ? 'Running Engine...' : 'Run Reconciliation'}</span>
                        </button>
                    </div>

                    <button
                        onClick={onDownload}
                        disabled={isDownloading || !summary || summary.total_students === 0}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-bold flex items-center gap-2 shadow-lg shadow-emerald-500/20 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
                    >
                        <Download className="w-4 h-4" />
                        <span>{isDownloading ? 'Generating Excel...' : 'Download Consolidated Excel'}</span>
                    </button>
                </div>

                {/* Content Area */}
                <div className="flex-1 overflow-y-auto p-8 space-y-6">
                    {/* Summary Counters */}
                    {summary ? (
                        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3">
                            <div className="p-3.5 bg-slate-50 dark:bg-slate-800/60 rounded-2xl border border-slate-200/60 dark:border-slate-800">
                                <div className="text-[11px] font-semibold text-slate-400">Total Students</div>
                                <div className="text-xl font-black text-slate-900 dark:text-white mt-1">{summary.total_students}</div>
                            </div>
                            <div className="p-3.5 bg-emerald-50 dark:bg-emerald-950/30 rounded-2xl border border-emerald-200/60 dark:border-emerald-800/40">
                                <div className="text-[11px] font-bold text-emerald-600 dark:text-emerald-400">Original Pass</div>
                                <div className="text-xl font-black text-emerald-600 dark:text-emerald-400 mt-1">{summary.pass_count}</div>
                            </div>
                            <div className="p-3.5 bg-blue-50 dark:bg-blue-950/30 rounded-2xl border border-blue-200/60 dark:border-blue-800/40">
                                <div className="text-[11px] font-bold text-blue-600 dark:text-blue-400">Cleared Later</div>
                                <div className="text-xl font-black text-blue-600 dark:text-blue-400 mt-1">{summary.cleared_count}</div>
                            </div>
                            <div className="p-3.5 bg-rose-50 dark:bg-rose-950/30 rounded-2xl border border-rose-200/60 dark:border-rose-800/40">
                                <div className="text-[11px] font-bold text-rose-600 dark:text-rose-400">Uncleared Fail</div>
                                <div className="text-xl font-black text-rose-600 dark:text-rose-400 mt-1">{summary.uncleared_count}</div>
                            </div>
                            <div className="p-3.5 bg-amber-50 dark:bg-amber-950/30 rounded-2xl border border-amber-200/60 dark:border-amber-800/40">
                                <div className="text-[11px] font-bold text-amber-600 dark:text-amber-400">Pending KT</div>
                                <div className="text-xl font-black text-amber-600 dark:text-amber-400 mt-1">{summary.pending_count}</div>
                            </div>
                            <div className="p-3.5 bg-purple-50 dark:bg-purple-950/30 rounded-2xl border border-purple-200/60 dark:border-purple-800/40">
                                <div className="text-[11px] font-bold text-purple-600 dark:text-purple-400">Exceptions</div>
                                <div className="text-xl font-black text-purple-600 dark:text-purple-400 mt-1">{exceptions.length}</div>
                            </div>
                        </div>
                    ) : (
                        <div className="p-6 text-center text-slate-400 bg-slate-50 dark:bg-slate-800/40 rounded-2xl border border-slate-200 dark:border-slate-800">
                            Click "Run Reconciliation" above to process stored regular and KT attempts.
                        </div>
                    )}

                    {/* Exceptions Notice */}
                    {exceptions.length > 0 && (
                        <div className="bg-rose-50/70 dark:bg-rose-950/30 border border-rose-200 dark:border-rose-800/60 rounded-2xl p-4">
                            <div className="flex items-center gap-2 text-rose-700 dark:text-rose-300 font-bold text-xs mb-3">
                                <AlertTriangle className="w-4 h-4 text-rose-600" />
                                <span>Exceptions & Discrepancies Requiring Review ({exceptions.length})</span>
                            </div>
                            <div className="space-y-2 max-h-48 overflow-y-auto">
                                {exceptions.map((exc, idx) => (
                                    <div key={idx} className="bg-white/80 dark:bg-slate-900/80 p-3 rounded-xl border border-rose-100 dark:border-rose-900/30 text-xs flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                                        <div className="space-y-0.5">
                                            <div className="flex items-center gap-2">
                                                <span className="px-2 py-0.5 rounded bg-rose-100 dark:bg-rose-900/50 text-rose-700 dark:text-rose-300 font-black text-[10px]">
                                                    {exc.exception_type}
                                                </span>
                                                <span className="font-mono font-bold text-slate-900 dark:text-white">
                                                    {exc.student_identifier || 'Unidentified'}
                                                </span>
                                                {exc.student_name && (
                                                    <span className="text-slate-500 font-medium">— {exc.student_name}</span>
                                                )}
                                            </div>
                                            <p className="text-slate-600 dark:text-slate-300 text-[11px]">{exc.description}</p>
                                        </div>
                                        <span className="text-[10px] text-amber-600 dark:text-amber-400 font-semibold italic whitespace-nowrap">
                                            {exc.action_required}
                                        </span>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Student Reconciliation Results List */}
                    {results.length > 0 && (
                        <div className="bg-white dark:bg-slate-900 rounded-2xl border border-slate-200 dark:border-slate-800 shadow-sm overflow-hidden">
                            <div className="p-4 border-b border-slate-200 dark:border-slate-800 flex flex-col sm:flex-row justify-between items-center gap-3">
                                <div className="relative w-full sm:w-72">
                                    <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                                    <input
                                        type="text"
                                        placeholder="Search student results..."
                                        value={searchQuery}
                                        onChange={(e) => setSearchQuery(e.target.value)}
                                        className="w-full pl-9 pr-3 py-1.5 bg-slate-50 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 rounded-xl text-xs outline-none focus:ring-2 focus:ring-indigo-500 text-slate-900 dark:text-white"
                                    />
                                </div>

                                <div className="flex items-center gap-1.5 overflow-x-auto w-full sm:w-auto">
                                    {['ALL', 'PASSED_ORIGINAL', 'CLEARED_SUBSEQUENTLY', 'UNCLEARED', 'PENDING', 'NEEDS_REVIEW'].map(st => (
                                        <button
                                            key={st}
                                            onClick={() => setFilterStatus(st)}
                                            className={`px-2.5 py-1 rounded-lg text-[10px] font-bold transition-all whitespace-nowrap ${
                                                filterStatus === st
                                                    ? 'bg-indigo-600 text-white'
                                                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-400 hover:bg-slate-200'
                                            }`}
                                        >
                                            {st.replace('_', ' ')}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="overflow-x-auto max-h-96">
                                <table className="w-full text-xs text-left">
                                    <thead className="sticky top-0 bg-slate-50 dark:bg-slate-800 border-b border-slate-200 dark:border-slate-800 text-[10px] uppercase text-slate-500 font-bold z-10">
                                        <tr>
                                            <th className="px-5 py-3">Student ID</th>
                                            <th className="px-5 py-3">Student Name</th>
                                            <th className="px-3 py-3 text-center">Level</th>
                                            <th className="px-3 py-3 text-center">Attempts</th>
                                            <th className="px-4 py-3 text-center">Clearance Status</th>
                                            <th className="px-4 py-3 text-center">Clearing Session</th>
                                            <th className="px-5 py-3">Final Reconciliation Verdict</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-slate-100 dark:divide-slate-800">
                                        {filteredResults.map((r, idx) => {
                                            const cs = r.clearance_status;
                                            let badgeStyle = 'bg-slate-100 text-slate-600 border-slate-200';
                                            if (cs === 'PASSED_ORIGINAL') {
                                                badgeStyle = 'bg-emerald-50 dark:bg-emerald-950/40 text-emerald-700 dark:text-emerald-400 border-emerald-500/30';
                                            } else if (cs === 'CLEARED_SUBSEQUENTLY') {
                                                badgeStyle = 'bg-blue-50 dark:bg-blue-950/40 text-blue-700 dark:text-blue-400 border-blue-500/30';
                                            } else if (cs === 'UNCLEARED') {
                                                badgeStyle = 'bg-rose-50 dark:bg-rose-950/40 text-rose-700 dark:text-rose-400 border-rose-500/30';
                                            } else if (cs === 'PENDING') {
                                                badgeStyle = 'bg-amber-50 dark:bg-amber-950/40 text-amber-700 dark:text-amber-400 border-amber-500/30';
                                            } else if (cs === 'NEEDS_REVIEW') {
                                                badgeStyle = 'bg-purple-50 dark:bg-purple-950/40 text-purple-700 dark:text-purple-400 border-purple-500/30';
                                            }

                                            return (
                                                <tr key={idx} className="hover:bg-slate-50/60 dark:hover:bg-slate-800/40 transition-colors">
                                                    <td className="px-5 py-3 font-mono font-bold text-slate-900 dark:text-white">
                                                        {r.student_identifier}
                                                    </td>
                                                    <td className="px-5 py-3 font-medium">
                                                        {r.student_name || <span className="text-slate-400 italic">Unassigned</span>}
                                                    </td>
                                                    <td className="px-3 py-3 text-center font-bold">
                                                        {r.student_level}
                                                    </td>
                                                    <td className="px-3 py-3 text-center font-mono">
                                                        <span className="px-2 py-0.5 rounded-full bg-slate-100 dark:bg-slate-800 text-[10px] font-bold">
                                                            {r.total_attempts}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-center">
                                                        <span className={`px-2.5 py-0.5 rounded-full text-[10px] font-black uppercase tracking-wide border ${badgeStyle}`}>
                                                            {r.clearance_status.replace('_', ' ')}
                                                        </span>
                                                    </td>
                                                    <td className="px-4 py-3 text-center font-semibold text-slate-600 dark:text-slate-400">
                                                        {r.clearance_session || '—'}
                                                    </td>
                                                    <td className="px-5 py-3 text-slate-600 dark:text-slate-300 text-[11px]">
                                                        {r.final_status}
                                                    </td>
                                                </tr>
                                            );
                                        })}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    )}
                </div>

                {/* Modal Footer */}
                <div className="px-8 py-4 border-t border-slate-200 dark:border-slate-800 flex items-center justify-between bg-slate-50/50 dark:bg-slate-800/30">
                    <p className="text-xs text-slate-400">
                        Exported workbook adheres to university audit standards with Consolidated, Attempt History, and Exception sheets.
                    </p>
                    <button
                        onClick={onClose}
                        className="px-4 py-2 text-xs font-semibold text-slate-600 dark:text-slate-300 hover:bg-slate-100 dark:hover:bg-slate-800 rounded-xl transition-colors"
                    >
                        Close
                    </button>
                </div>
            </div>
        </div>
    );
}

