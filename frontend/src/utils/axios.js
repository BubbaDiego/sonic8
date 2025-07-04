/**
 * Axios instance with sensible defaults.
 * The baseURL is driven by VITE_APP_API_URL, falling back to localhost.
 */
import axios from 'axios';

const axiosServices = axios.create({
  baseURL: import.meta.env.VITE_APP_API_URL || 'http://localhost:5000'
});

// ==============================|| Request Interceptor ||============================== //
axiosServices.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('serviceToken');
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// ==============================|| Response Interceptor ||============================== //
axiosServices.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401 && !window.location.href.includes('/login')) {
      window.location.pathname = '/login';
    }
    return Promise.reject(error.response?.data || 'Service error');
  }
);

export default axiosServices;

// --- Helper for SWR / React‑Query etc. ---
export async function fetcher(args) {
  const [url, config] = Array.isArray(args) ? args : [args];
  const res = await axiosServices.get(url, { ...config });
  return res.data;
}
