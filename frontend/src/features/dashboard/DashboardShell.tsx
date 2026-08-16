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
import { formatApiDateTime } from '../../lib/dates';

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

  if (loading) {
    return (
      <div className="space-y-6 text-foreground animate-pulse">
        {/* Header Skeleton */}
        <div className="flex items-center justify-between">
          <div className="space-y-2">
            <div className="h-8 w-48 bg-accent rounded-lg"></div>
            <div className="h-4 w-96 bg-accent/60 rounded"></div>
          </div>
          <div className="h-9 w-24 bg-accent rounded-lg"></div>
        </div>

        {/* KPI Cards Skeletons */}
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="p-5 bg-card border border-border rounded-xl space-y-3">
              <div className="h-3 w-24 bg-accent rounded"></div>
              <div className="h-8 w-16 bg-accent rounded"></div>
              <div className="h-3 w-28 bg-accent/60 rounded"></div>
            </div>
          ))}
        </div>

        {/* Quick Actions Skeleton */}
        <div className="h-16 bg-card border border-border rounded-xl"></div>

        {/* Main Content Grid Skeleton */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <div className="h-64 bg-card border border-border rounded-xl"></div>
          <div className="h-64 bg-card border border-border rounded-xl"></div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="space-y-6 text-foreground">
        <div className="flex items-center gap-3">
          <LayoutDashboard className="w-8 h-8 text-muted-foreground" />
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Overview</h2>
            <p className="text-sm text-muted-foreground">Operational CatalogIQ dashboard</p>
          </div>
        </div>
        <div className="p-8 bg-red-500/10/40 border border-red-500/20/60 rounded-xl flex flex-col items-center justify-center text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-red-400" />
          <div className="max-w-md space-y-1">
            <h3 className="font-semibold text-lg text-red-200">Unable to Load Overview Summary</h3>
            <p className="text-sm text-red-500/80">{error}</p>
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
  const primaryActions = [
    { label: 'Upload Source', icon: UploadCloud, to: '/upload', primary: true },
    { label: 'Review Issues', icon: CheckSquare, to: '/reviews' },
    { label: 'Search Catalog', icon: Search, to: '/search' },
  ];
  const kpiCards = [
    {
      label: 'Total Products',
      value: kpis?.total_products ?? 0,
      detail: kpis?.verification_rate != null ? `${kpis.verification_rate}% verified` : '0% verified',
      icon: Database,
      accent: 'text-cyan-300',
      bar: 'from-cyan-300 to-emerald-300',
    },
    {
      label: 'Sources Processed',
      value: kpis?.documents_processed ?? 0,
      detail: `${kpis?.total_documents ?? 0} total documents uploaded`,
      icon: FileText,
      accent: 'text-blue-300',
      bar: 'from-blue-300 to-cyan-300',
    },
    {
      label: 'Active Jobs',
      value: kpis?.active_processing_jobs ?? 0,
      detail: (kpis?.active_processing_jobs ?? 0) > 0 ? 'Processing pipeline active' : 'No active queue',
      icon: Activity,
      accent: 'text-amber-300',
      bar: 'from-amber-300 to-orange-300',
    },
    {
      label: 'Review Backlog',
      value: kpis?.review_backlog ?? 0,
      detail: 'Products needing review',
      icon: CheckSquare,
      accent: 'text-orange-300',
      bar: 'from-orange-300 to-rose-300',
    },
    {
      label: 'Catalog Quality',
      value: kpis?.catalog_quality_score != null ? `${kpis.catalog_quality_score}/100` : '--',
      detail: 'Overall health score',
      icon: Sparkles,
      accent: 'text-emerald-500',
      bar: 'from-emerald-300 to-lime-300',
    },
    {
      label: 'Verification Rate',
      value: kpis?.verification_rate != null ? `${kpis.verification_rate}%` : '--',
      detail: 'Verified products ratio',
      icon: ShieldCheck,
      accent: 'text-teal-300',
      bar: 'from-teal-300 to-cyan-300',
    },
  ];
  const intelligenceSteps = [
    { label: 'Ingest', value: kpis?.total_documents ?? 0, icon: UploadCloud, color: 'text-cyan-300' },
    { label: 'Extract', value: kpis?.documents_processed ?? 0, icon: FileText, color: 'text-blue-300' },
    { label: 'Validate', value: qualitySummary?.evidence_coverage_rate != null ? `${qualitySummary.evidence_coverage_rate}%` : '--', icon: ShieldCheck, color: 'text-emerald-500' },
    { label: 'Review', value: reviewSummary?.products_needing_review ?? 0, icon: CheckSquare, color: 'text-amber-300' },
  ];

  return (
    <div className="space-y-8 text-foreground rounded-none">
      {/* Hero Section */}
      <section className="border border-border bg-card p-8 rounded-none relative overflow-hidden">
        {/* Subtle grid accent */}
        <div className="absolute right-0 top-0 w-1/3 h-full opacity-[0.03] pointer-events-none mesh-grid border-l border-border" />
        
        <div className="grid gap-8 xl:grid-cols-[1.1fr_0.9fr]">
          <div className="flex flex-col justify-between gap-8 z-10">
            <div className="space-y-6">
              <div className="inline-flex items-center gap-2 border border-[#9B8F77]/30 bg-[#9B8F77]/5 px-3 py-1.5 text-[9px] uppercase tracking-widest font-medium text-[#9B8F77]">
                <Sparkles className="w-3.5 h-3.5" />
                Product Intelligence Engine
              </div>
              <div className="max-w-3xl space-y-4">
                <h2 className="text-foreground text-4xl lg:text-5xl font-normal leading-tight font-serif">
                  Product data that explains itself.
                </h2>
                <p className="text-xs uppercase tracking-wider text-muted-foreground leading-relaxed max-w-xl font-light">
                  CatalogIQ transforms raw industrial PDF specifications into structured attribute claims, confidence scores, evidence provenance, and verified catalog intelligence.
                </p>
              </div>
            </div>

            <div className="flex flex-wrap items-center gap-3">
              {primaryActions.map((action) => {
                const Icon = action.icon;
                return (
                  <button
                    key={action.label}
                    onClick={() => navigate(action.to)}
                    className={`h-10 px-5 text-xs uppercase tracking-widest font-medium transition duration-150 rounded-none border ${
                      action.primary
                        ? 'bg-foreground text-background border-foreground hover:bg-transparent hover:text-foreground'
                        : 'border-border bg-background text-muted-foreground hover:bg-card hover:text-foreground'
                    }`}
                  >
                    <Icon className="w-3.5 h-3.5 mr-2 inline" />
                    {action.label}
                  </button>
                );
              })}
              <button
                onClick={fetchOverview}
                className="h-10 border border-border bg-background px-5 text-xs uppercase tracking-widest font-medium text-muted-foreground hover:text-foreground hover:bg-card transition flex items-center gap-2"
              >
                <RefreshCw className="w-3.5 h-3.5 text-[#9B8F77]" /> Refresh
              </button>
            </div>
          </div>

          <div className="border border-border bg-background p-6 rounded-none relative">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[9px] uppercase tracking-widest text-[#9B8F77]">Intelligence Pipeline</p>
                <h3 className="mt-1.5 text-lg font-normal font-serif text-foreground">Source Ingestion Flow</h3>
              </div>
              <span className="border border-[#9B8F77]/30 bg-[#9B8F77]/5 px-2.5 py-1 text-[10px] font-mono text-[#9B8F77]">
                {kpis?.catalog_quality_score != null ? `Score: ${kpis.catalog_quality_score}/100` : 'Standby'}
              </span>
            </div>

            <div className="mt-6 grid grid-cols-4 gap-2">
              {intelligenceSteps.map((step) => {
                const Icon = step.icon;
                return (
                  <div key={step.label} className="border border-border bg-card p-3 rounded-none">
                    <div className="mb-2.5 flex h-8 w-8 items-center justify-center border border-border bg-background text-foreground">
                      <Icon className="w-3.5 h-3.5" />
                    </div>
                    <p className="text-[9px] uppercase tracking-widest text-muted-foreground font-light">{step.label}</p>
                    <p className="mt-1 text-base font-medium text-foreground font-mono">{step.value}</p>
                  </div>
                );
              })}
            </div>

            <div className="mt-5 border border-border bg-card p-4 rounded-none">
              <div className="mb-2.5 flex items-center justify-between text-[10px] uppercase tracking-wider">
                <span className="text-muted-foreground">Evidence Coverage Rate</span>
                <span className="font-mono text-[#9B8F77]">
                  {qualitySummary?.evidence_coverage_rate != null ? `${qualitySummary.evidence_coverage_rate}% Backed` : 'Awaiting data'}
                </span>
              </div>
              <div className="h-1 bg-border rounded-none overflow-hidden">
                <div
                  className="h-full bg-foreground rounded-none"
                  style={{ width: `${Math.max(4, qualitySummary?.evidence_coverage_rate ?? 0)}%` }}
                />
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* KPI Cards Grid */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 rounded-none">
        {kpiCards.map((card) => {
          const Icon = card.icon;
          return (
            <div key={card.label} className="border border-border bg-card p-4 transition-all hover:border-[#9B8F77]/40 rounded-none">
              <div className="flex items-center justify-between">
                <span className="text-[9px] font-medium tracking-widest uppercase text-muted-foreground">{card.label}</span>
                <Icon className="w-3.5 h-3.5 text-[#9B8F77]" />
              </div>
              <div className="mt-3.5 text-2xl font-normal text-foreground font-serif">{card.value}</div>
              <p className="mt-1 text-[10px] text-muted-foreground font-light truncate">{card.detail}</p>
              <div className="mt-4 h-[1px] bg-border rounded-none">
                <div className="h-full w-2/3 bg-[#9B8F77]" />
              </div>
            </div>
          );
        })}
      </div>

      {/* Quick Actions Bar */}
      <div className="border border-border bg-card p-4 flex flex-wrap items-center justify-between gap-4 rounded-none">
        <div className="flex items-center gap-2.5 text-[9px] font-medium uppercase tracking-widest text-muted-foreground font-mono">
          <span className="w-1.5 h-1.5 bg-[#9B8F77]" />
          <span>Quick Actions</span>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={() => navigate('/upload')}
            className="px-4 py-2 bg-foreground text-background text-[10px] uppercase tracking-wider font-semibold hover:bg-transparent hover:text-foreground border border-foreground transition duration-150 rounded-none"
          >
            <UploadCloud className="w-3.5 h-3.5 mr-1.5 inline" /> Upload Document
          </button>
          <button
            onClick={() => navigate('/catalog')}
            className="px-4 py-2 bg-transparent text-muted-foreground hover:text-foreground border border-border hover:bg-accent text-[10px] uppercase tracking-wider font-semibold transition duration-150 rounded-none"
          >
            <Database className="w-3.5 h-3.5 mr-1.5 inline" /> Open Catalog
          </button>
          <button
            onClick={() => navigate('/search')}
            className="px-4 py-2 bg-transparent text-muted-foreground hover:text-foreground border border-border hover:bg-accent text-[10px] uppercase tracking-wider font-semibold transition duration-150 rounded-none"
          >
            <Search className="w-3.5 h-3.5 mr-1.5 inline" /> Search Catalog
          </button>
          <button
            onClick={() => navigate('/reviews')}
            className="px-4 py-2 bg-transparent text-muted-foreground hover:text-foreground border border-border hover:bg-accent text-[10px] uppercase tracking-wider font-semibold transition duration-150 rounded-none"
          >
            <CheckSquare className="w-3.5 h-3.5 mr-1.5 inline" /> Review Issues
          </button>
        </div>
      </div>

      {/* Empty State */}
      {isEmpty && (
        <div className="p-12 border border-border bg-card flex flex-col items-center justify-center text-center space-y-4 rounded-none">
          <div className="w-12 h-12 border border-border bg-background flex items-center justify-center text-foreground">
            <UploadCloud className="w-5 h-5" />
          </div>
          <div className="max-w-md space-y-2">
            <h3 className="text-xl font-normal font-serif text-foreground">No products yet</h3>
            <p className="text-[11px] text-muted-foreground font-light leading-relaxed uppercase tracking-wider">
              Upload a catalog document (PDF technical datasheet) to parse specifications, extract attributes, and build product intelligence.
            </p>
          </div>
          <button
            onClick={() => navigate('/upload')}
            className="px-5 py-2.5 bg-foreground text-background hover:bg-transparent hover:text-foreground border border-foreground text-xs font-semibold uppercase tracking-widest transition duration-150 rounded-none"
          >
            <UploadCloud className="w-4 h-4 mr-2 inline" /> Upload Document to Begin
          </button>
        </div>
      )}

      {/* Two Column Grid */}
      {!isEmpty && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 rounded-none">
          {/* Review Summary */}
          <div className="border border-border bg-card p-6 space-y-6 flex flex-col justify-between rounded-none">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2.5">
                  <CheckSquare className="w-4 h-4 text-[#9B8F77]" />
                  <h3 className="text-lg font-normal font-serif text-foreground">Review Summary</h3>
                </div>
                <span className="text-[10px] px-2.5 py-1 border border-[#9B8F77]/30 bg-[#9B8F77]/5 text-[#9B8F77] font-mono font-medium uppercase tracking-widest">
                  {reviewSummary?.products_needing_review ?? 0} Backlog
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 bg-background border border-border space-y-1.5 rounded-none">
                  <span className="text-[9px] text-muted-foreground font-mono uppercase tracking-widest block">Unresolved Issues</span>
                  <div className="text-xl font-normal font-mono text-foreground">
                    {reviewSummary?.unresolved_validation_issues ?? 0}
                  </div>
                </div>

                <div className="p-4 bg-background border border-border space-y-1.5 rounded-none">
                  <span className="text-[9px] text-muted-foreground font-mono uppercase tracking-widest block">Validation Conflicts</span>
                  <div className="text-xl font-normal font-mono text-[#9B8F77]">
                    {reviewSummary?.conflicts_count ?? 0}
                  </div>
                </div>

                <div className="p-4 bg-background border border-border space-y-1.5 rounded-none">
                  <span className="text-[9px] text-muted-foreground font-mono uppercase tracking-widest block">Low Confidence Fields</span>
                  <div className="text-xl font-normal font-mono text-foreground">
                    {reviewSummary?.low_confidence_attributes ?? 0}
                  </div>
                </div>

                <div className="p-4 bg-background border border-border space-y-1.5 rounded-none">
                  <span className="text-[9px] text-muted-foreground font-mono uppercase tracking-widest block">Needs Human Action</span>
                  <div className="text-xl font-normal font-mono text-[#9B8F77]">
                    {reviewSummary?.products_needing_review ?? 0}
                  </div>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-border flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-light">Resolve attribute conflicts & review tags</span>
              <button
                onClick={() => navigate('/reviews')}
                className="px-3.5 py-1.5 bg-background hover:bg-accent text-foreground border border-border text-[10px] uppercase tracking-wider font-semibold flex items-center gap-1.5 transition rounded-none"
              >
                View Reviews <ArrowRight className="w-3 h-3 text-muted-foreground" />
              </button>
            </div>
          </div>

          {/* Catalog Quality Summary */}
          <div className="border border-border bg-card p-6 space-y-6 flex flex-col justify-between rounded-none">
            <div className="space-y-4">
              <div className="flex items-center justify-between border-b border-border pb-3">
                <div className="flex items-center gap-2.5">
                  <HeartPulse className="w-4 h-4 text-[#9B8F77]" />
                  <h3 className="text-lg font-normal font-serif text-foreground">Catalog Quality Summary</h3>
                </div>
                <span className="text-[10px] px-2.5 py-1 border border-[#9B8F77]/30 bg-[#9B8F77]/5 text-[#9B8F77] font-mono font-medium uppercase tracking-widest">
                  Score: {qualitySummary?.overall_quality_score != null ? `${qualitySummary.overall_quality_score}/100` : '--'}
                </span>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div className="p-4 bg-background border border-border space-y-1.5 rounded-none">
                  <span className="text-[9px] text-muted-foreground font-mono uppercase tracking-widest block">Completeness Rate</span>
                  <div className="text-xl font-normal font-mono text-foreground">
                    {qualitySummary?.completeness_rate != null ? `${qualitySummary.completeness_rate}%` : '--'}
                  </div>
                </div>

                <div className="p-4 bg-background border border-border space-y-1.5 rounded-none">
                  <span className="text-[9px] text-muted-foreground font-mono uppercase tracking-widest block">Evidence Coverage</span>
                  <div className="text-xl font-normal font-mono text-foreground">
                    {qualitySummary?.evidence_coverage_rate != null ? `${qualitySummary.evidence_coverage_rate}%` : '--'}
                  </div>
                </div>
              </div>

              {/* Status Breakdown Bar */}
              <div className="space-y-2">
                <div className="flex items-center justify-between text-[10px] uppercase tracking-wider text-muted-foreground">
                  <span>Product Validation State</span>
                  <span className="font-mono text-foreground">{kpis?.total_products ?? 0} Total Records</span>
                </div>
                <div className="h-1.5 w-full bg-border overflow-hidden flex rounded-none">
                  {qualitySummary?.verified_products_count ? (
                    <div
                      style={{
                        width: `${((qualitySummary.verified_products_count / (kpis?.total_products || 1)) * 100).toFixed(1)}%`,
                      }}
                      className="bg-foreground h-full"
                      title={`Verified: ${qualitySummary.verified_products_count}`}
                    ></div>
                  ) : null}
                  {qualitySummary?.needs_review_products_count ? (
                    <div
                      style={{
                        width: `${((qualitySummary.needs_review_products_count / (kpis?.total_products || 1)) * 100).toFixed(1)}%`,
                      }}
                      className="bg-[#9B8F77] h-full"
                      title={`Needs Review: ${qualitySummary.needs_review_products_count}`}
                    ></div>
                  ) : null}
                  {qualitySummary?.draft_products_count ? (
                    <div
                      style={{
                        width: `${((qualitySummary.draft_products_count / (kpis?.total_products || 1)) * 100).toFixed(1)}%`,
                      }}
                      className="bg-white/10 h-full"
                      title={`Draft: ${qualitySummary.draft_products_count}`}
                    ></div>
                  ) : null}
                </div>
                <div className="flex flex-wrap items-center justify-between text-[9px] text-muted-foreground uppercase tracking-widest pt-1 gap-2">
                  <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-foreground"></span> Verified ({qualitySummary?.verified_products_count ?? 0})
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-[#9B8F77]"></span> Needs Review ({qualitySummary?.needs_review_products_count ?? 0})
                  </span>
                  <span className="flex items-center gap-1.5">
                    <span className="w-1.5 h-1.5 bg-white/10"></span> Draft ({qualitySummary?.draft_products_count ?? 0})
                  </span>
                </div>
              </div>
            </div>

            <div className="pt-4 border-t border-border flex items-center justify-between">
              <span className="text-[10px] text-muted-foreground uppercase tracking-wider font-light">
                {qualitySummary?.products_needing_attention ?? 0} items at risk
              </span>
              <button
                onClick={() => navigate('/health')}
                className="px-3.5 py-1.5 bg-background hover:bg-accent text-foreground border border-border text-[10px] uppercase tracking-wider font-semibold flex items-center gap-1.5 transition rounded-none"
              >
                View Catalog Health <ArrowRight className="w-3 h-3 text-muted-foreground" />
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Processing Activity Table */}
      {!isEmpty && (
        <div className="border border-border bg-card p-6 space-y-4 rounded-none">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2.5">
              <Activity className="w-4 h-4 text-[#9B8F77]" />
              <h3 className="text-lg font-normal font-serif text-foreground">Ingestion & Processing Activity</h3>
            </div>
            <button
              onClick={() => navigate('/jobs')}
              className="text-[10px] uppercase tracking-widest text-foreground hover:text-[#9B8F77] font-semibold flex items-center gap-1"
            >
              View Queue <ArrowRight className="w-3 h-3 ml-0.5" />
            </button>
          </div>

          {activity.length === 0 ? (
            <p className="text-xs text-muted-foreground italic py-4 text-center">No processing activity recorded yet.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border text-[9px] font-medium uppercase text-muted-foreground font-mono tracking-widest">
                    <th className="py-3 px-3 font-light">Document / Source Name</th>
                    <th className="py-3 px-3 font-light">Status</th>
                    <th className="py-3 px-3 font-light">Stage</th>
                    <th className="py-3 px-3 font-light text-center">Pages</th>
                    <th className="py-3 px-3 font-light text-right">Upload / Processed Time</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50 text-foreground">
                  {activity.map((item) => (
                    <tr key={item.id} className="hover:bg-background/40 transition">
                      <td className="py-3.5 px-3 font-light text-sm flex items-center gap-2">
                        <FileText className="w-3.5 h-3.5 text-[#9B8F77] shrink-0" />
                        <span className="truncate max-w-xs" title={item.filename}>{item.filename}</span>
                      </td>
                      <td className="py-3.5 px-3">
                        <span
                          className={`text-[9px] font-mono tracking-widest uppercase px-2 py-0.5 border rounded-none ${
                            item.status === 'processed' || item.status === 'completed'
                              ? 'bg-foreground/5 text-foreground border-foreground/30'
                              : item.status === 'failed'
                              ? 'bg-red-500/10/20 text-red-400 border-red-900/40'
                              : item.status === 'parsing' || item.status === 'processing'
                              ? 'bg-[#9B8F77]/10 text-[#9B8F77] border-[#9B8F77]/30 animate-pulse'
                              : 'bg-border text-muted-foreground border-border'
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 font-mono text-[10px] text-muted-foreground uppercase tracking-wide">
                        {item.current_stage || '—'}
                      </td>
                      <td className="py-3.5 px-3 font-mono text-[10px] text-muted-foreground text-center">
                        {item.page_count != null ? item.page_count : '—'}
                      </td>
                      <td className="py-3.5 px-3 font-mono text-[10px] text-muted-foreground text-right">
                        {formatApiDateTime(item.created_at)}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* Recent Catalog Products */}
      {!isEmpty && (
        <div className="border border-border bg-card p-6 space-y-4 rounded-none">
          <div className="flex items-center justify-between border-b border-border pb-3">
            <div className="flex items-center gap-2.5">
              <Database className="w-4 h-4 text-[#9B8F77]" />
              <h3 className="text-lg font-normal font-serif text-foreground">Recent Catalog Products</h3>
            </div>
            <button
              onClick={() => navigate('/catalog')}
              className="text-[10px] uppercase tracking-widest text-foreground hover:text-[#9B8F77] font-semibold flex items-center gap-1"
            >
              Open Catalog <ArrowRight className="w-3 h-3 ml-0.5" />
            </button>
          </div>

          {recentProducts.length === 0 ? (
            <p className="text-xs text-muted-foreground italic py-4 text-center">No products found in catalog.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead>
                  <tr className="border-b border-border text-[9px] font-medium uppercase text-muted-foreground font-mono tracking-widest">
                    <th className="py-3 px-3 font-light">Product Name</th>
                    <th className="py-3 px-3 font-light">Brand</th>
                    <th className="py-3 px-3 font-light">SKU</th>
                    <th className="py-3 px-3 font-light">Status</th>
                    <th className="py-3 px-3 font-light text-center">Quality Score</th>
                    <th className="py-3 px-3 font-light text-right">Last Updated</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-border/50 text-foreground">
                  {recentProducts.map((prod) => (
                    <tr
                      key={prod.id}
                      onClick={() => navigate(`/catalog?product_id=${prod.id}`)}
                      className="cursor-pointer hover:bg-background/40 transition"
                    >
                      <td className="py-3.5 px-3 font-normal text-sm text-foreground">{prod.product_name}</td>
                      <td className="py-3.5 px-3">
                        <span className="px-2 py-0.5 bg-background border border-border text-[10px] text-muted-foreground font-mono tracking-wider rounded-none">
                          {prod.brand}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 font-mono text-[10px] text-muted-foreground">{prod.sku}</td>
                      <td className="py-3.5 px-3">
                        <span
                          className={`text-[9px] font-mono tracking-widest uppercase px-2 py-0.5 border rounded-none ${
                            prod.status === 'verified'
                              ? 'bg-foreground/5 text-foreground border-foreground/30'
                              : 'bg-[#9B8F77]/10 text-[#9B8F77] border-[#9B8F77]/30'
                          }`}
                        >
                          {prod.status}
                        </span>
                      </td>
                      <td className="py-3.5 px-3 font-mono text-center text-foreground">
                        {prod.quality_score}/100
                      </td>
                      <td className="py-3.5 px-3 font-mono text-[10px] text-muted-foreground text-right">
                        {formatApiDateTime(prod.updated_at)}
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

