/**
 * Centralized API Configuration
 * Supports dynamic backend URL via VITE_API_BASE_URL for deployment (e.g., Render, Railway, Hugging Face).
 * Defaults to http://localhost:8000 during local development.
 */
export const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/+$/, '');
