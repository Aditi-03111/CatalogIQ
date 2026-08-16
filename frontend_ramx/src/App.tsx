import React, { useState, useEffect } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ClerkProvider, useAuth } from '@clerk/clerk-react';
import { Layout } from './components/Layout';
import { LandingPage } from './features/landing/LandingPage';
import { LoginPage } from './features/landing/LoginPage';
import { DashboardShell } from './features/dashboard/DashboardShell';
import { ProductsShell } from './features/products/ProductsShell';
import { UploadShell } from './features/upload/UploadShell';
import { JobsShell } from './features/jobs/JobsShell';
import { SearchShell } from './features/search/SearchShell';
import { ReviewsShell } from './features/reviews/ReviewsShell';
import { HealthShell } from './features/health/HealthShell';
import { UnilogConsole } from './features/unilog/UnilogConsole';

// Stub route for settings
const SettingsStub = () => (
  <div className="space-y-4">
    <h2 className="text-3xl font-normal font-serif text-foreground">System Settings</h2>
    <p className="text-xs uppercase tracking-wider text-muted-foreground leading-relaxed">Configure threshold scores, API keys, worker concurrency, and LLM engines.</p>
  </div>
);

// Intercepts all window.fetch calls globally to attach the Clerk JWT Bearer token dynamically
const FetchInterceptor: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { getToken, isSignedIn } = useAuth();

  useEffect(() => {
    const originalFetch = window.fetch;
    
    window.fetch = async (input, init) => {
      let clonedInit = init;
      const requestUrl = typeof input === 'string'
        ? input
        : input instanceof URL
          ? input.toString()
          : input.url;
      const parsedUrl = new URL(requestUrl, window.location.origin);
      const isCatalogApiRequest = parsedUrl.origin === window.location.origin && parsedUrl.pathname.startsWith('/api/');

      if (isSignedIn && isCatalogApiRequest) {
        try {
          const token = await getToken();
          if (token) {
            clonedInit = { ...(init || {}) };
            const headers = new Headers(clonedInit.headers || {});
            headers.set('Authorization', `Bearer ${token}`);
            clonedInit.headers = headers;
          }
        } catch (e) {
          console.error("Failed to fetch Clerk token", e);
        }
      }
      return originalFetch(input, clonedInit);
    };

    return () => {
      window.fetch = originalFetch;
    };
  }, [getToken, isSignedIn]);

  return <>{children}</>;
};

// Falls back to a local storage override input in case key in .env file is missing/empty
const ClerkConfigPage = () => {
  const [customKeyInput, setCustomKeyInput] = useState('');
  
  const saveCustomPublishableKey = () => {
    const trimmed = customKeyInput.trim();
    if (!trimmed) return;
    localStorage.setItem("clerk_publishable_key_override", trimmed);
    localStorage.removeItem("token");
    window.location.reload();
  };

  return (
    <div className="min-h-screen w-screen flex flex-col justify-center items-center p-6 bg-background text-foreground relative overflow-hidden">
      <div className="absolute top-[-10%] right-[-10%] w-[50vw] h-[50vw] rounded-full glow-1 blur-[120px] pointer-events-none z-0" />
      <div className="absolute bottom-[-10%] left-[10%] w-[55vw] h-[55vw] rounded-full glow-2 blur-[150px] pointer-events-none z-0" />

      <div className="w-full max-w-sm bg-card border border-border p-8 z-10 shadow-2xl space-y-6 text-center">
        <div className="space-y-1">
          <h1 className="text-3xl font-normal font-serif">CatalogIQ</h1>
          <p className="text-xs text-muted-foreground">Configure Clerk Authentication to proceed.</p>
        </div>
        
        <div className="space-y-3 text-left">
          <label className="text-[10px] uppercase tracking-wider text-muted-foreground font-mono block">Clerk Publishable Key</label>
          <input
            type="text"
            placeholder="pk_test_..."
            value={customKeyInput}
            onChange={(e) => setCustomKeyInput(e.target.value)}
            className="w-full bg-background border border-border text-foreground px-3 py-2 text-xs outline-none focus:border-foreground transition font-mono animate-none"
          />
          <button
            onClick={saveCustomPublishableKey}
            disabled={!customKeyInput.trim()}
            className="w-full bg-foreground text-background text-xs font-semibold py-2.5 hover:opacity-90 transition disabled:opacity-50"
          >
            Apply Key & Initialize
          </button>
        </div>
      </div>
    </div>
  );
};

const queryClient = new QueryClient();

function App() {
  // Resolve publishable key synchronously
  const envKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
  const savedKey = localStorage.getItem("clerk_publishable_key_override");
  
  const publishableKey = (envKey && envKey !== 'your_clerk_publishable_key_here') 
    ? envKey 
    : savedKey;

  if (!publishableKey) {
    return <ClerkConfigPage />;
  }

  return (
    <ClerkProvider publishableKey={publishableKey}>
      <FetchInterceptor>
        <QueryClientProvider client={queryClient}>
          <BrowserRouter>
            <Routes>
              {/* Landing Page & Login */}
              <Route path="/" element={<LandingPage />} />
              <Route path="/login" element={<LoginPage />} />

              {/* Operational Console Wrapper */}
              <Route element={<Layout />}>
                <Route path="dashboard" element={<DashboardShell />} />
                <Route path="catalog" element={<ProductsShell />} />
                <Route path="products" element={<ProductsShell />} />
                <Route path="upload" element={<UploadShell />} />
                <Route path="jobs" element={<JobsShell />} />
                <Route path="search" element={<SearchShell />} />
                <Route path="reviews" element={<ReviewsShell />} />
                <Route path="health" element={<HealthShell />} />
                <Route path="unilog" element={<UnilogConsole />} />
                <Route path="settings" element={<SettingsStub />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </QueryClientProvider>
      </FetchInterceptor>
    </ClerkProvider>
  );
}

export default App;
