import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Login from './pages/Login';
import SuperAdminDashboard from './pages/SuperAdmin';
import DeptAdminDashboard from './pages/DeptAdmin';

import { DataProvider } from './context/DataContext';

function App() {
  return (
    <ThemeProvider>
      <DataProvider>
        <Router>
          <Routes>
            <Route path="/" element={<Login />} />
            <Route path="/super-admin" element={<SuperAdminDashboard />} />
            <Route path="/dept-admin" element={<DeptAdminDashboard />} />
          </Routes>
        </Router>
      </DataProvider>
    </ThemeProvider>
  );
}

export default App;
