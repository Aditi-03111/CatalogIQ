import React, { useEffect } from 'react';
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

const queryClient = new QueryClient();

const DEFAULT_CLERK_KEY = "pk_test_Y2xlcmsuY2F0YWxvZ2lxLmRldiQ";

function App() {
  // Resolve publishable key synchronously
  const envKey = import.meta.env.VITE_CLERK_PUBLISHABLE_KEY;
  const savedKey = localStorage.getItem("clerk_publishable_key_override");
  
  const publishableKey = (envKey && envKey !== 'your_clerk_publishable_key_here') 
    ? envKey 
    : (savedKey || DEFAULT_CLERK_KEY);

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
