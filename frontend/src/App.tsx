import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { ChatPage } from './pages/ChatPage';
import { MetricsPage } from './pages/MetricsPage';
import { LoginPage } from './pages/LoginPage';
import { RegisterPage } from './pages/RegisterPage';
import { AdminDashboard } from './pages/AdminDashboard';
import { ProfilePage } from './pages/ProfilePage';
import { AuthProvider, useAuth } from './context/AuthContext';

const ProtectedRoute: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const { isAuthenticated } = useAuth();
    return isAuthenticated ? <>{children}</> : <Navigate to="/login" />;
};

function App() {
    return (
        <AuthProvider>
            <Routes>
                <Route path="/login" element={<LoginPage />} />
                <Route path="/register" element={<RegisterPage />} />

                <Route path="/" element={
                    <ProtectedRoute>
                        <ChatPage />
                    </ProtectedRoute>
                } />

                <Route path="/chats/:id" element={
                    <ProtectedRoute>
                        <ChatPage />
                    </ProtectedRoute>
                } />

                <Route path="/metrics" element={
                    <ProtectedRoute>
                        <MetricsPage />
                    </ProtectedRoute>
                } />

                <Route path="/admin" element={
                    <ProtectedRoute>
                        <AdminDashboard />
                    </ProtectedRoute>
                } />

                <Route path="/profile" element={
                    <ProtectedRoute>
                        <ProfilePage />
                    </ProtectedRoute>
                } />
            </Routes>
        </AuthProvider>
    );
}

export default App;
