import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import { AuthProvider } from '@/auth/AuthContext';
import { AppErrorBoundary } from '@/components/AppErrorBoundary';
import { ToastProvider } from '@/components/ui/Toast';
import './index.css';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter>
            <App />
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </AppErrorBoundary>
  </StrictMode>,
);
