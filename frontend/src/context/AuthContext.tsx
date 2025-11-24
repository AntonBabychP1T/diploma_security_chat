import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, User } from '../api/client';

interface AuthContextType {
    user: User | null;
    token: string | null;
    login: (token: string) => void;
    logout: () => void;
    isAuthenticated: boolean;
    isAdmin: boolean;
}

const AuthContext = createContext<AuthContextType | null>(null);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
    const [user, setUser] = useState<User | null>(null);
    const [token, setToken] = useState<string | null>(() => {
        const savedToken = localStorage.getItem('token');
        console.log('🔑 Initial token from localStorage:', savedToken ? 'exists' : 'missing');
        return savedToken;
    });

    useEffect(() => {
        const initAuth = async () => {
            const savedToken = localStorage.getItem('token');
            if (savedToken) {
                try {
                    const res = await api.get<User>('/auth/me');
                    setUser(res.data);
                } catch (err) {
                    console.error("Token invalid or expired", err);
                    logout();
                }
            }
        };
        initAuth();
    }, []);

    const login = async (newToken: string) => {
        console.log('🔐 Login called, saving token to localStorage');
        localStorage.setItem('token', newToken);
        setToken(newToken);
        try {
            const res = await api.get<User>('/auth/me');
            setUser(res.data);
        } catch (e) {
            console.error("Failed to fetch user profile", e);
        }
    };

    const logout = () => {
        console.log('🚪 Logout called, clearing token');
        localStorage.removeItem('token');
        setToken(null);
        setUser(null);
    };

    return (
        <AuthContext.Provider value={{
            user,
            token,
            login,
            logout,
            isAuthenticated: !!token,
            isAdmin: user?.is_admin || false
        }}>
            {children}
        </AuthContext.Provider>
    );
};

export const useAuth = () => {
    const context = useContext(AuthContext);
    if (!context) throw new Error('useAuth must be used within AuthProvider');
    return context;
};
