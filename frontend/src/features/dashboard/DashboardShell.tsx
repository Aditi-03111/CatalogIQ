import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  LayoutDashboard,
  Database,
  UploadCloud,
  Activity,
  Search,
  CheckSquare,
  HeartPulse,
  AlertTriangle,
  ArrowRight,
  RefreshCw,
  FileText,
  ShieldCheck,
  Sparkles
} from 'lucide-react';

interface OverviewKpis {
  total_products: number;
  documents_processed: number;
  total_documents: number;
  active_processing_jobs: number;
  review_backlog: number;
  catalog_quality_score: number | null;
  verification_rate: number | null;
}

interface ProcessingActivityItem {
  id: string;
  filename: string;
  status: string;
  created_at: string;
  page_count: number | null;
  current_stage: string | null;
}

interface ReviewSummary {
  unresolved_validation_issues: number;
  conflicts_count: number;
  low_confidence_attributes: number;
  products_needing_review: number;
}

interface CatalogQualitySummary {
  overall_quality_score: number | null;
  completeness_rate: number | null;
  verified_products_count: number;
  needs_review_products_count: number;
  draft_products_count: number;
  evidence_coverage_rate: number | null;
  products_needing_attention: number;
}

interface RecentProductItem {
  id: string;
  product_name: string;
  brand: string;
  sku: string;
  category: string;
  status: string;
  quality_score: number;
  updated_at: string;
}

interface OverviewData {
  kpis: OverviewKpis;
  processing_activity: ProcessingActivityItem[];
  review_summary: ReviewSummary;
  catalog_quality_summary: CatalogQualitySummary;
  recent_products: RecentProductItem[];
}

export const DashboardShell: React.FC = () => {
  const navigate = useNavigate();
  const [data, setData] = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const fetchOverview = async () => {
    try {
      setLoading(true);
      setError(null);
      const res = await fetch('/api/v1/overview/summary');
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const summaryData: OverviewData = await res.json();
      setData(summaryData);
    } catch (err: any) {
      console.error('Failed to fetch Overview summary:', err);
      setError(err?.message || 'Failed to load Overview dashboard data');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchOverview();
  }, []);

  const formatTimestamp = (isoString?: string) => {
    if (!isoString) return '—';
    try {
      const d = new Date(isoString);
      return d.toLocaleDateString(undefined, {
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit',
      });
    } catch {
      return isoString;
    }
  };

  if (loading) {
    return (
      <div className="space-y-6 text-slate-100 animate-pulse">
        {/* Header Skeleton */}
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-8 w-48 bg-slate-800 rounded-lg"></div>
            <div className="h-4 w-96 bg-slate-800/60 rounded"></div>
          </div>
          <div className="h-9 w-24 bg-slate-800 rounded-lg"></div>
        </div>

        {/* KPI Cards Skeletons */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-3">
              <div className="h-3 w-24 bg-slate-800 rounded"></div>
              <div className="h-8 w-16 bg-slate-800 rounded"></div>
              <div className="h-3 w-28 bg-slate-800/60 rounded"></div>
            </div>
          ))}
        </div>

        {/* Quick Actions Skeleton */}
        <div className="h-16 bg-slate-900 border border-slate-800 rounded-xl"></div>

        {/* Main Content Grid Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-64 bg-slate-900 border border-slate-800 rounded-xl"></div>
          <div className="h-64 bg-slate-900 border border-slate-800 rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6 text-slate-100">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="w-8 h-8 text-slate-400" />
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Overview</h2>
            <p className="text-sm text-slate-400">Operational CatalogIQ dashboard</p>
          </div>
        </div>
        <div className="p-8 bg-red-950/40 border border-red-800/60 rounded-xl flex flex-col items-center justify-center text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-red-400" />
          <div className="max-w-md space-y-1">
            <h3 className="font-semibold text-lg text-red-200">Unable to Load Overview Summary</h3>
            <p className="text-sm text-red-300/80">{error}</p>
          </div>
          <button
            onClick={fetchOverview}
            className="px-4 py-2 bg-red-900 hover:bg-red-800 text-red-100 rounded-lg font-medium text-sm flex items-center gap-2 border border-red-700 transition"
          >
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      </div>
    );
  }

  const kpis = data?.kpis;
  const reviewSummary = data?.review_summary;
  const qualitySummary = data?.catalog_quality_summary;
  const activity = data?.processing_activity || [];
  const recentProducts = data?.recent_products || [];

  const isEmpty = (kpis?.total_products ?? 0) === 0 && (kpis?.total_documents ?? 0) === 0;

  return (
    <div className="space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-400">
            <LayoutDashboard className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
              Overview
            </h2>
            <p className="text-sm text-slate-400">
              Welcome to CatalogIQ. Live operational catalog health and ingestion intelligence.
            </p>
          </div>
        </div>

        <button
          onClick={fetchOverview}
          className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-lg border border-slate-800 transition flex items-center gap-2"
        >
          <RefreshCw className="w-3.5 h-3.5 text-slate-400" /> Refresh Data
        </button>
      </div>

      {/* TOP KPI CARDS */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
        {/* Total Products */}
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-2 hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold tracking-wider uppercase">Total Products</span>
            <Database className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-black text-white">{kpis?.total_products ?? 0}</div>
          <p className="text-xs text-slate-400">
            {kpis?.verification_rate != null ? `${kpis.verification_rate}% verified` : '0% verified'}
          </p>
        </div>

        {/* Documents Processed */}
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-2 hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold tracking-wider uppercase">Sources Processed</span>
            <FileText className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-3xl font-black text-white">{kpis?.documents_processed ?? 0}</div>
          <p className="text-xs text-slate-400">
            {kpis?.total_documents ?? 0} total documents uploaded
          </p>
        </div>

        {/* Active Jobs */}
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-2 hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold tracking-wider uppercase">Active Jobs</span>
            <Activity className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-black text-white">{kpis?.active_processing_jobs ?? 0}</div>
          <p className="text-xs text-slate-400">
            {(kpis?.active_processing_jobs ?? 0) > 0 ? 'Processing pipeline active' : 'No active queue'}
          </p>
        </div>

        {/* Review Backlog */}
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-2 hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold tracking-wider uppercase">Review Backlog</span>
            <CheckSquare className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-3xl font-black text-white">{kpis?.review_backlog ?? 0}</div>
          <p className="text-xs text-slate-400">Products needing review</p>
        </div>

        {/* Catalog Quality */}
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-2 hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold tracking-wider uppercase">Catalog Quality</span>
            <Sparkles className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-black text-emerald-400">
            {kpis?.catalog_quality_score != null ? `${kpis.catalog_quality_score}/100` : '--'}
          </div>
          <p className="text-xs text-slate-400">Overall health score</p>
        </div>

        {/* Verification Rate */}
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-2 hover:border-slate-700 transition">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold tracking-wider uppercase">Verification Rate</span>
            <ShieldCheck className="w-4 h-4 text-teal-400" />
          </div>
          <div className="text-3xl font-black text-teal-400">
            {kpis?.verification_rate != null ? `${kpis.verification_rate}%` : '--'}
          </div>
          <p className="text-xs text-slate-400">Verified products ratio</p>
        </div>
      </div>

      {/* QUICK ACTIONS BAR */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-wrap items-center justify-between gap-4">
        <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-slate-400 font-mono">
          <span>⚡ Quick Actions:</span>
        </div>
        <div className="flex flex-wrap items-center gap-3">
          <button
            onClick={() => navigate('/upload')}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold flex items-center gap-2 shadow-md transition"
          >
            <UploadCloud className="w-4 h-4" /> Upload Document
          </button>
          <button
            onClick={() => navigate('/catalog')}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-2 transition"
          >
            <Database className="w-4 h-4" /> Open Catalog
          </button>
          <button
            onClick={() => navigate('/search')}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-2 transition"
          >
            <Search className="w-4 h-4" /> Search Catalog
          </button>
          <button
            onClick={() => navigate('/reviews')}
            className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-2 transition"
          >
            <CheckSquare className="w-4 h-4" /> Review Issues
          </button>
        </div>
      </div>

      {/* EMPTY STATE IF DB HAS NO PRODUCTS / DOCUMENTS */}
      {isEmpty && (
        <div className="p-12 border border-dashed border-slate-800 rounded-xl bg-slate-900/60 flex flex-col items-center justify-center text-center space-y-4">
          <div className="w-16 h-16 rounded-full bg-indigo-950 border border-indigo-800 flex items-center justify-center text-indigo-400">
            <UploadCloud className="w-8 h-8" />
          </div>
          <div className="max-w-md space-y-1">
            <h3 className="font-bold text-xl text-white">No products yet</h3>
            <p className="text-sm text-slate-400">
              Upload a catalog document (e.g. PDF technical datasheet) to parse specifications, extract attributes, and build product intelligence.
            </p>
          </div>
          <button
            onClick={() => navigate('/upload')}
            className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-semibold text-sm flex items-center gap-2 shadow-lg transition"
          >
            <UploadCloud className="w-4 h-4" /> Upload Document to Begin
          </button>
        </div>
      )}

      {/* MAIN TWO-COLUMN DASHBOARD CONTENT */}
      {!isEmpty && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* REVIEW SUMMARY CARD */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2.5">
                  <CheckSquare className="w-5 h-5 text-orange-400" />
                  <h3 className="text-lg font-bold text-white">Review Summary</h3>
                </div>
                <span className="text-xs px-2.5 py-1 bg-amber-950/60 border border-amber-800/60 text-amber-300 rounded-full font-mono font-semibold">
                  {reviewSummary?.products_needing_review ?? 0} needing review
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-lg space-y-1">
                  <span className="text-[11px] text-slate-400 font-mono uppercase font-semibold">Unresolved Issues</span>
                  <div className="text-2xl font-black text-white">
                    {reviewSummary?.unresolved_validation_issues ?? 0}
                  </div>
                </div>

                <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-lg space-y-1">
                  <span className="text-[11px] text-slate-400 font-mono uppercase font-semibold">Validation Conflicts</span>
                  <div className="text-2xl font-black text-red-400">
                    {reviewSummary?.conflicts_count ?? 0}
                  </div>
                </div>

                <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-lg space-y-1">
                  <span className="text-[11px] text-slate-400 font-mono uppercase font-semibold">Low Confidence Fields</span>
                  <div className="text-2xl font-black text-amber-400">
                    {reviewSummary?.low_confidence_attributes ?? 0}
                  </div>
                </div>

                <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-lg space-y-1">
                  <span className="text-[11px] text-slate-400 font-mono uppercase font-semibold">Products Needing Action</span>
                  <div className="text-2xl font-black text-orange-400">
                    {reviewSummary?.products_needing_review ?? 0}
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between">
              <span className="text-xs text-slate-400">Resolve attribute conflicts & approval tasks</span>
              <button
                onClick={() => navigate('/reviews')}
                className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition"
              >
                View Reviews <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
            </div>
          </div>

          {/* CATALOG QUALITY SUMMARY CARD */}
          <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-5 flex flex-col justify-between">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-slate-800 pb-3">
                <div className="flex items-center gap-2.5">
                  <HeartPulse className="w-5 h-5 text-emerald-400" />
                  <h3 className="text-lg font-bold text-white">Catalog Quality Summary</h3>
                </div>
                <span className="text-xs px-2.5 py-1 bg-emerald-950/60 border border-emerald-800/60 text-emerald-300 rounded-full font-mono font-semibold">
                  Score: {qualitySummary?.overall_quality_score != null ? `${qualitySummary.overall_quality_score}/100` : '--'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-4">
                <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-lg space-y-1">
                  <span className="text-[11px] text-slate-400 font-mono uppercase font-semibold">Completeness Rate</span>
                  <div className="text-2xl font-black text-emerald-400">
                    {qualitySummary?.completeness_rate != null ? `${qualitySummary.completeness_rate}%` : '--'}
                  </div>
                </div>

                <div className="p-4 bg-slate-950/80 border border-slate-800/80 rounded-lg space-y-1">
                  <span className="text-[11px] text-slate-400 font-mono uppercase font-semibold">Evidence Coverage</span>
                  <div className="text-2xl font-black text-teal-400">
                    {qualitySummary?.evidence_coverage_rate != null ? `${qualitySummary.evidence_coverage_rate}%` : '--'}
                  </div>
                </div>
              </div>

              {/* Status Breakdown Bar */}
              <div className="space-y-1.5">
                <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                  <span>Product Validation Status Breakdown</span>
                  <span>{kpis?.total_products ?? 0} Total</span>
                </div>
                <div className="h-3 w-full bg-slate-950 rounded-full overflow-hidden flex border border-slate-800">
                  {qualitySummary?.verified_products_count ? (
                    <div
                      style={{
                        width: `${((qualitySummary.verified_products_count / (kpis?.total_products || 1)) * 100).toFixed(1)}%`,
                      }}
                      className="bg-emerald-500 h-full"
                      title={`Verified: ${qualitySummary.verified_products_count}`}
                    ></div>
                  ) : null}
                  {qualitySummary?.needs_review_products_count ? (
                    <div
                      style={{
                        width: `${((qualitySummary.needs_review_products_count / (kpis?.total_products || 1)) * 100).toFixed(1)}%`,
                      }}
                      className="bg-amber-500 h-full"
                      title={`Needs Review: ${qualitySummary.needs_review_products_count}`}
                    ></div>
                  ) : null}
                  {qualitySummary?.draft_products_count ? (
                    <div
                      style={{
                        width: `${((qualitySummary.draft_products_count / (kpis?.total_products || 1)) * 100).toFixed(1)}%`,
                      }}
                      className="bg-slate-600 h-full"
                      title={`Draft: ${qualitySummary.draft_products_count}`}
                    ></div>
                  ) : null}
                </div>
                <div className="flex items-center justify-between text-[11px] text-slate-400 font-mono pt-1">
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-emerald-500"></span> Verified ({qualitySummary?.verified_products_count ?? 0})
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-amber-500"></span> Review ({qualitySummary?.needs_review_products_count ?? 0})
                  </span>
                  <span className="flex items-center gap-1">
                    <span className="w-2 h-2 rounded-full bg-slate-600"></span> Draft ({qualitySummary?.draft_products_count ?? 0})
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-2 border-t border-slate-800/60 flex items-center justify-between">
              <span className="text-xs text-slate-400">
                {qualitySummary?.products_needing_attention ?? 0} products needing attention
              </span>
              <button
                onClick={() => navigate('/health')}
                className="px-3.5 py-1.5 bg-slate-800 hover:bg-slate-700 text-slate-200 rounded-lg text-xs font-semibold border border-slate-700 flex items-center gap-1.5 transition"
              >
                View Catalog Health <ArrowRight className="w-3.5 h-3.5 text-slate-400" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* PROCESSING ACTIVITY SECTION */}
      {!isEmpty && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2.5">
              <Activity className="w-5 h-5 text-blue-400" />
              <h3 className="text-lg font-bold text-white">Recent Ingestion & Processing Activity</h3>
            </div>
            <button
              onClick={() => navigate('/jobs')}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1"
            >
              View Jobs Queue <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {activity.length === 0 ? (
            <p className="text-xs text-slate-500 italic py-4 text-center">No processing activity recorded yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs font-semibold uppercase text-slate-400 font-mono">
                    <th className="py-2.5 px-3">Document / Source Name</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Stage</th>
                    <th className="py-2.5 px-3">Pages</th>
                    <th className="py-2.5 px-3">Upload / Processed Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {activity.map((item) => (
                    <tr key={item.id} className="hover:bg-slate-800/40 transition">
                      <td className="py-3 px-3 font-medium text-slate-200 flex items-center gap-2">
                        <FileText className="w-4 h-4 text-slate-400 shrink-0" />
                        <span className="truncate max-w-xs" title={item.filename}>{item.filename}</span>
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`text-[11px] font-semibold px-2 py-0.5 rounded border uppercase font-mono ${
                            item.status === 'processed' || item.status === 'completed'
                              ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                              : item.status === 'failed'
                              ? 'bg-red-950 text-red-300 border-red-800'
                              : item.status === 'parsing' || item.status === 'processing'
                              ? 'bg-blue-950 text-blue-300 border-blue-800 animate-pulse'
                              : 'bg-amber-950 text-amber-300 border-amber-800'
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-xs text-slate-300 capitalize">
                        {item.current_stage || '—'}
                      </td>
                      <td className="py-3 px-3 font-mono text-xs text-slate-400">
                        {item.page_count != null ? item.page_count : '—'}
                      </td>
                      <td className="py-3 px-3 font-mono text-xs text-slate-400">
                        {formatTimestamp(item.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* RECENT PRODUCTS SECTION */}
      {!isEmpty && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <div className="flex items-center gap-2.5">
              <Database className="w-5 h-5 text-indigo-400" />
              <h3 className="text-lg font-bold text-white">Recent Catalog Products</h3>
            </div>
            <button
              onClick={() => navigate('/catalog')}
              className="text-xs text-indigo-400 hover:text-indigo-300 font-semibold flex items-center gap-1"
            >
              Open Product Catalog <ArrowRight className="w-3.5 h-3.5" />
            </button>
          </div>

          {recentProducts.length === 0 ? (
            <p className="text-xs text-slate-500 italic py-4 text-center">No products found in catalog.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs font-semibold uppercase text-slate-400 font-mono">
                    <th className="py-2.5 px-3">Product Name</th>
                    <th className="py-2.5 px-3">Brand</th>
                    <th className="py-2.5 px-3">SKU</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Quality Score</th>
                    <th className="py-2.5 px-3">Last Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {recentProducts.map((prod) => (
                    <tr
                      key={prod.id}
                      onClick={() => navigate(`/catalog?product_id=${prod.id}`)}
                      className="cursor-pointer hover:bg-slate-800/50 transition"
                    >
                      <td className="py-3 px-3 font-semibold text-slate-100">{prod.product_name}</td>
                      <td className="py-3 px-3 text-slate-300">
                        <span className="px-2 py-0.5 rounded bg-slate-800 border border-slate-700 text-xs font-mono">
                          {prod.brand}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-xs text-slate-400">{prod.sku}</td>
                      <td className="py-3 px-3">
                        <span
                          className={`text-[11px] font-semibold px-2 py-0.5 rounded border uppercase font-mono ${
                            prod.status === 'verified'
                              ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                              : prod.status === 'needs_review'
                              ? 'bg-amber-950 text-amber-300 border-amber-800'
                              : 'bg-slate-800 text-slate-300 border-slate-700'
                          }`}
                        >
                          {prod.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono font-bold text-emerald-400 text-xs">
                        {prod.quality_score}/100
                      </td>
                      <td className="py-3 px-3 font-mono text-xs text-slate-400">
                        {formatTimestamp(prod.updated_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
