import { StrictMode } from 'react';
import { createRoot } from 'react-dom/client';
import { BrowserRouter } from 'react-router-dom';
import { App } from './App';
import { AuthProvider } from '@/auth/AuthContext';
import { AppErrorBoundary } from '@/components/AppErrorBoundary';
import { ToastProvider } from '@/components/ui/Toast';
import './index.css';

declare global {
  interface Window {
    __UI_SPA_BASENAME__?: string;
  }
}

const basename = window.__UI_SPA_BASENAME__ ?? '/ui';

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <AppErrorBoundary>
      <AuthProvider>
        <ToastProvider>
          <BrowserRouter basename={basename}>
            <App />
          </BrowserRouter>
        </ToastProvider>
      </AuthProvider>
    </AppErrorBoundary>
  </StrictMode>,
);
