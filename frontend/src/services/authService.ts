import axios from 'axios';
import { User, LoginRequest, RegisterRequest, AuthResponse } from '../types/game';

const API_BASE_URL = process.env.REACT_APP_API_URL || 'http://localhost:8000/api';

// Create axios instance with interceptors
const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Response interceptor to handle auth errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      // Token expired or invalid
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export const authService = {
  async login(username: string, password: string): Promise<AuthResponse> {
    try {
      const response = await api.post<AuthResponse>('/auth/login', {
        username,
        password,
      });
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Login failed');
    }
  },

  async register(username: string, email: string, password: string): Promise<void> {
    try {
      await api.post('/auth/register', {
        username,
        email,
        password,
      });
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Registration failed');
    }
  },

  async logout(): Promise<void> {
    try {
      await api.post('/auth/logout');
    } catch (error) {
      // Logout can fail silently
      console.error('Logout error:', error);
    }
  },

  async getCurrentUser(): Promise<User> {
    try {
      const response = await api.get<User>('/auth/me');
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to get user data');
    }
  },

  async updateProfile(data: Partial<User>): Promise<User> {
    try {
      const response = await api.put<User>('/players/me', data);
      return response.data;
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Failed to update profile');
    }
  },
};

export default api;
