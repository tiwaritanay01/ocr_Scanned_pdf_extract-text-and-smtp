import React, { createContext, useContext, useState, useEffect } from 'react';

const DataContext = createContext();

export const useData = () => useContext(DataContext);

// Initial data structure matching mockData
const initialStudentsData = {
    FE: [
        {
            "id": 101,
            "name": "AARAV PATIL",
            "roll": "FE-101",
            "ern": "202401640001",
            "email": "aarav.patil@college.edu",
            "marks": {
                "sem1": { "gpa": 8.45, "status": "P", "ocrValue": 8.45, "ocrStatus": "P" },
                "sem2": { "gpa": 8.20, "status": "P", "ocrValue": 8.20, "ocrStatus": "P" }
            }
        },
        {
            "id": 102,
            "name": "DIYA SHARMA",
            "roll": "FE-102",
            "ern": "202401640002",
            "email": "diya.sharma@college.edu",
            "marks": {
                "sem1": { "gpa": 9.10, "status": "P", "ocrValue": 9.10, "ocrStatus": "P" },
                "sem2": { "gpa": 8.95, "status": "P", "ocrValue": 8.95, "ocrStatus": "P" }
            }
        },
        {
            "id": 103,
            "name": "ROHAN KULKARNI",
            "roll": "FE-103",
            "ern": "202401640003",
            "email": "rohan.kulkarni@college.edu",
            "marks": {
                "sem1": { "gpa": 6.85, "status": "P", "ocrValue": 6.85, "ocrStatus": "P" },
                "sem2": { "gpa": 0.00, "status": "F", "ocrValue": 0.00, "ocrStatus": "F" }
            }
        }
    ],
    SE: [
        {
            "id": 76,
            "name": "MAURYA SAHIL HARISHCHANDRA RAJKUMARI",
            "roll": "33077",
            "email": "maurya@college.edu",
            "marks": {
                "sem3": {
                    "gpa": 8.13,
                    "status": "P",
                    "ocrValue": 8.13,
                    "ocrStatus": "P",
                    "subjectMarks": {"CSC301": 84, "CSC302": 60, "CSC303": 67, "CSC304": 46, "CSC305": 64, "CSL301": 43, "CSL302": 19, "CSL303": 43, "CSL304": 66, "CSM301": 50}
                },
                "sem4": { "gpa": 0.0, "status": "P", "ocrValue": 0.0, "ocrStatus": "P" }
            }
        },
        {
            "id": 77,
            "name": "MAYATRA DEVANSH JITENDRA POOJA",
            "roll": "33078",
            "email": "mayatra@college.edu",
            "marks": {
                "sem3": {
                    "gpa": 9.22,
                    "status": "P",
                    "ocrValue": 9.22,
                    "ocrStatus": "P",
                    "subjectMarks": {"CSC301": 80, "CSC302": 72, "CSC303": 87, "CSC304": 67, "CSC305": 76, "CSL301": 48, "CSL302": 24, "CSL303": 46, "CSL304": 73, "CSM301": 41}
                },
                "sem4": { "gpa": 0.0, "status": "P", "ocrValue": 0.0, "ocrStatus": "P" }
            }
        },
        {
            "id": 78,
            "name": "MEJARI VISHAL GANESH GAYATRI",
            "roll": "33079",
            "email": "mejari@college.edu",
            "marks": {
                "sem3": {
                    "gpa": 8.83,
                    "status": "P",
                    "ocrValue": 8.83,
                    "ocrStatus": "P",
                    "subjectMarks": {"CSC301": 70, "CSC302": 80, "CSC303": 81, "CSC304": 52, "CSC305": 67, "CSL301": 47, "CSL302": 22, "CSL303": 43, "CSL304": 61, "CSM301": 44}
                },
                "sem4": { "gpa": 0.0, "status": "P", "ocrValue": 0.0, "ocrStatus": "P" }
            }
        },
        {
            "id": 79,
            "name": "MHATRE NISHANT SURENDRA",
            "roll": "33080",
            "email": "mhatre@college.edu",
            "marks": {
                "sem3": {
                    "gpa": 0.0,
                    "status": "F",
                    "ocrValue": 0.0,
                    "ocrStatus": "F",
                    "subjectMarks": {"CSC301": 26, "CSC302": 34, "CSC303": 53, "CSC304": 49, "CSC305": 49, "CSL301": 44, "CSL302": 20, "CSL303": 41, "CSL304": 56, "CSM301": 43}
                },
                "sem4": { "gpa": 0.0, "status": "P", "ocrValue": 0.0, "ocrStatus": "P" }
            }
        },
        {
            "id": 80,
            "name": "MHATRE SHRIYASH SANTOSH",
            "roll": "33081",
            "email": "mhatre@college.edu",
            "marks": {
                "sem3": {
                    "gpa": 7.87,
                    "status": "P",
                    "ocrValue": 7.87,
                    "ocrStatus": "P",
                    "subjectMarks": {"CSC301": 59, "CSC302": 69, "CSC303": 74, "CSC304": 50, "CSC305": 60, "CSL301": 42, "CSL302": 19, "CSL303": 44, "CSL304": 66, "CSM301": 41}
                },
                "sem4": { "gpa": 0.0, "status": "P", "ocrValue": 0.0, "ocrStatus": "P" }
            }
        }
    ],
    TE: [
        { id: 201, name: "Aditi Rao", roll: "TE-201", email: "aditi@college.edu", marks: { sem3: { gpa: 8.8, status: "P", ocrValue: 8.8, ocrStatus: "P" }, sem4: { gpa: 8.9, status: "P", ocrValue: 8.9, ocrStatus: "P" }, sem5: { gpa: 9.0, status: "P", ocrValue: 9.0, ocrStatus: "P" }, sem6: { gpa: 8.5, status: "P", ocrValue: 8.5, ocrStatus: "P" } } },
        { id: 202, name: "Vihaan Kumar", roll: "TE-202", email: "vihaan@college.edu", marks: { sem3: { gpa: 7.5, status: "P", ocrValue: 7.5, ocrStatus: "P" }, sem4: { gpa: 7.8, status: "P", ocrValue: 7.8, ocrStatus: "P" }, sem5: { gpa: 7.6, status: "F", ocrValue: 7.6, ocrStatus: "F" }, sem6: { gpa: 7.2, status: "P", ocrValue: 7.2, ocrStatus: "P" } } },
        { id: 203, name: "Ananya Mishra", roll: "TE-203", email: "ananya@college.edu", marks: { sem3: { gpa: 9.2, status: "P", ocrValue: 9.2, ocrStatus: "P" }, sem4: { gpa: 9.1, status: "P", ocrValue: 9.1, ocrStatus: "P" }, sem5: { gpa: 9.3, status: "P", ocrValue: 9.3, ocrStatus: "P" }, sem6: { gpa: 9.0, status: "P", ocrValue: 9.0, ocrStatus: "P" } } },
        { id: 204, name: "Arjun Reddy", roll: "TE-204", email: "arjun@college.edu", marks: { sem3: { gpa: 8.0, status: "P", ocrValue: 8.0, ocrStatus: "P" }, sem4: { gpa: 8.2, status: "P", ocrValue: 8.2, ocrStatus: "P" }, sem5: { gpa: 8.1, status: "P", ocrValue: 8.1, ocrStatus: "P" }, sem6: { gpa: 7.8, status: "P", ocrValue: 7.8, ocrStatus: "P" } } },
        { id: 205, name: "Sanya Mehta", roll: "TE-205", email: "sanya@college.edu", marks: { sem3: { gpa: 7.2, status: "P", ocrValue: 7.2, ocrStatus: "P" }, sem4: { gpa: 7.5, status: "P", ocrValue: 7.5, ocrStatus: "P" }, sem5: { gpa: 7.4, status: "P", ocrValue: 7.4, ocrStatus: "P" }, sem6: { gpa: 7.0, status: "F", ocrValue: 7.0, ocrStatus: "F" } } },
    ],
    BE: [
        {
            id: 401,
            name: "SIDDHARTH JOSHI",
            roll: "BE-401",
            ern: "202101640001",
            email: "siddharth.joshi@college.edu",
            marks: {
                sem1: { gpa: 8.50, status: "P", ocrValue: 8.50, ocrStatus: "P" },
                sem2: { gpa: 8.60, status: "P", ocrValue: 8.60, ocrStatus: "P" },
                sem3: { gpa: 8.75, status: "P", ocrValue: 8.75, ocrStatus: "P" },
                sem4: { gpa: 8.90, status: "P", ocrValue: 8.90, ocrStatus: "P" },
                sem5: { gpa: 9.10, status: "P", ocrValue: 9.10, ocrStatus: "P" },
                sem6: { gpa: 8.85, status: "P", ocrValue: 8.85, ocrStatus: "P" },
                sem7: { gpa: 9.25, status: "P", ocrValue: 9.25, ocrStatus: "P" },
                sem8: { gpa: 9.40, status: "P", ocrValue: 9.40, ocrStatus: "P" }
            }
        },
        {
            id: 402,
            name: "NEHA DESHMUKH",
            roll: "BE-402",
            ern: "202101640002",
            email: "neha.deshmukh@college.edu",
            marks: {
                sem1: { gpa: 7.90, status: "P", ocrValue: 7.90, ocrStatus: "P" },
                sem2: { gpa: 8.10, status: "P", ocrValue: 8.10, ocrStatus: "P" },
                sem3: { gpa: 7.80, status: "P", ocrValue: 7.80, ocrStatus: "P" },
                sem4: { gpa: 8.20, status: "P", ocrValue: 8.20, ocrStatus: "P" },
                sem5: { gpa: 8.40, status: "P", ocrValue: 8.40, ocrStatus: "P" },
                sem6: { gpa: 8.15, status: "P", ocrValue: 8.15, ocrStatus: "P" },
                sem7: { gpa: 8.50, status: "P", ocrValue: 8.50, ocrStatus: "P" },
                sem8: { gpa: 8.70, status: "P", ocrValue: 8.70, ocrStatus: "P" }
            }
        }
    ]
};

export const DataProvider = ({ children }) => {
    const [students, setStudents] = useState(() => {
        try {
            const saved = localStorage.getItem('global_students_data');
            if (saved) {
                const parsed = JSON.parse(saved);
                if (parsed && typeof parsed === 'object' && parsed.SE && parsed.SE.length) {
                    return {
                        FE: (parsed.FE && parsed.FE.length) ? parsed.FE : initialStudentsData.FE,
                        SE: (parsed.SE && parsed.SE.length) ? parsed.SE : initialStudentsData.SE,
                        TE: (parsed.TE && parsed.TE.length) ? parsed.TE : initialStudentsData.TE,
                        BE: (parsed.BE && parsed.BE.length) ? parsed.BE : initialStudentsData.BE,
                    };
                }
            }
        } catch (e) {
            console.warn('Failed to parse cached students:', e);
        }
        return initialStudentsData;
    });

    const [admins, setAdmins] = useState(() => {
        const saved = localStorage.getItem('global_admins_data');
        return saved ? JSON.parse(saved) : [
            { id: 1, name: "Dr. Sarah Wilson", dept: "Computer Science", email: "cs_admin@college.edu", status: "Active", lastActive: "Just now" },
            { id: 2, name: "Prof. James Miller", dept: "Mechanical Eng.", email: "mech_admin@college.edu", status: "Active", lastActive: "Just now" },
            { id: 3, name: "Dr. Emily Chen", dept: "Electrical Eng.", email: "ee_admin@college.edu", status: "Active", lastActive: "Just now" },
            { id: 4, name: "Prof. Rahul Verma", dept: "Civil Eng.", email: "civil_admin@college.edu", status: "Active", lastActive: "Just now" },
        ];
    });

    useEffect(() => {
        // Reset manual corrections tracking at the start of each browser session
        if (!sessionStorage.getItem('session_accuracy_synced')) {
            setStudents(prev => {
                const syncedData = { ...prev };
                Object.keys(syncedData).forEach(year => {
                    if (Array.isArray(syncedData[year])) {
                        syncedData[year] = syncedData[year].map(student => ({
                            ...student,
                            marks: student.marks ? Object.fromEntries(
                                Object.entries(student.marks).map(([sem, details]) => [
                                    sem,
                                    {
                                        ...details,
                                        ocrValue: details?.ocrValue !== undefined ? details.ocrValue : (details?.gpa ?? 0),
                                        ocrStatus: details?.ocrStatus !== undefined ? details.ocrStatus : (details?.status ?? 'P')
                                    }
                                ])
                            ) : {}
                        }));
                    }
                });
                return syncedData;
            });
            sessionStorage.setItem('session_accuracy_synced', 'true');
        }
    }, []);

    useEffect(() => {
        localStorage.setItem('global_students_data', JSON.stringify(students));
    }, [students]);

    useEffect(() => {
        localStorage.setItem('global_admins_data', JSON.stringify(admins));
    }, [admins]);

    return (
        <DataContext.Provider value={{ students, setStudents, admins, setAdmins }}>
            {children}
        </DataContext.Provider>
    );
};
