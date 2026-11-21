import React from 'react';
import { createRoot } from 'react-dom/client';
import App from './App';
import { ErrorBoundary, GlobalErrors } from './ErrorOverlay';
import { SelfTest } from './dev/SelfTest';
import './styles.css';

const params = new URLSearchParams(window.location.search);
const selfTest = params.get('selftest') === '1';

createRoot(document.getElementById('root')!).render(
  selfTest ? (
    <SelfTest />
  ) : (
    <React.StrictMode>
      <ErrorBoundary>
        <GlobalErrors>
          <App />
        </GlobalErrors>
      </ErrorBoundary>
    </React.StrictMode>
  ),
);
