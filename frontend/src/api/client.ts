import axios from 'axios';

export const api = axios.create({
    baseURL: '/api',
});

// Add request interceptor to attach token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('token');
        console.log('🔍 API Request:', {
            url: config.url,
            method: config.method,
            hasToken: !!token,
            tokenPreview: token ? `${token.substring(0, 20)}...` : 'none'
        });

        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => {
        console.error('❌ Request interceptor error:', error);
        return Promise.reject(error);
    }
);

// Add response interceptor to log responses
api.interceptors.response.use(
    (response) => {
        console.log('✅ API Response:', {
            url: response.config.url,
            status: response.status,
            data: response.data
        });
        return response;
    },
    (error) => {
        console.error('❌ API Error:', {
            url: error.config?.url,
            status: error.response?.status,
            message: error.response?.data?.detail || error.message
        });
        return Promise.reject(error);
    }
);

export interface User {
    id: number;
    email: string;
    is_admin: boolean;
    created_at: string;
}

export interface LoginResponse {
    access_token: string;
    token_type: string;
}

export interface Message {
    id: number;
    role: 'user' | 'assistant' | 'system';
    content: string;
    created_at: string;
    meta_data?: {
        latency?: number;
        masked_used?: boolean;
        provider?: string;
        style?: string;
        [key: string]: any;
    };
}

export interface Chat {
    id: number;
    title: string;
    created_at: string;
    updated_at: string;
    messages?: Message[];
}

export interface ChatCreate {
    title: string;
}

export interface ChatRequest {
    message: string;
    style?: string;
    provider?: string;
    model?: string;
}

export interface Metrics {
    total_messages: number;
    recent_avg_latency: number;
    recent_masked_count: number;
    sample_size: number;
}

export const deleteChat = (id: number) => api.delete(`/chats/${id}`);
export const updateChat = (id: number, title: string) => api.patch<Chat>(`/chats/${id}`, { title });
export const fetchCurrentUser = () => api.get<User>('/auth/me');
export const changePassword = (payload: { current_password: string; new_password: string }) =>
    api.post('/auth/change-password', payload);

// Memories
export interface MemoryItem {
    id: number;
    user_id: number;
    category: string;
    key: string;
    value: string;
    confidence: number;
    created_at: string;
    updated_at: string;
}

export const fetchMemories = () => api.get<MemoryItem[]>('/memories');
export const addMemory = (payload: { category: string; key: string; value: string; confidence?: number }) =>
    api.post<MemoryItem>('/memories', payload);
export const deleteMemory = (id: number) => api.delete(`/memories/${id}`);

export const transcribeAudio = (blob: Blob) => {
    const formData = new FormData();
    formData.append('file', blob, 'audio.webm');
    return api.post<{ text: string }>('/audio/transcribe', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
    });
};

export const askSecretary = (query: string) =>
    api.post<{ response: string }>('/secretary/ask', { query });
