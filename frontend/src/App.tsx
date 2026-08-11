import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { DashboardShell } from './features/dashboard/DashboardShell';
import { ProductsShell } from './features/products/ProductsShell';
import { UploadShell } from './features/upload/UploadShell';
import { JobsShell } from './features/jobs/JobsShell';
import { SearchShell } from './features/search/SearchShell';
import { ReviewsShell } from './features/reviews/ReviewsShell';
import { HealthShell } from './features/health/HealthShell';

// Stub route for settings
const SettingsStub = () => (
  <div>
    <h2 className="text-3xl font-bold tracking-tight">System Settings</h2>
    <p className="text-muted-foreground mt-2">Configure threshold scores, API keys, worker concurrency, and LLM engines.</p>
  </div>
);

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<Layout />}>
            <Route index element={<DashboardShell />} />
            <Route path="catalog" element={<ProductsShell />} />
            <Route path="upload" element={<UploadShell />} />
            <Route path="jobs" element={<JobsShell />} />
            <Route path="search" element={<SearchShell />} />
            <Route path="reviews" element={<ReviewsShell />} />
            <Route path="health" element={<HealthShell />} />
            <Route path="settings" element={<SettingsStub />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
