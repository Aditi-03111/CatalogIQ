import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import {
  HeartPulse,
  Activity,
  CheckCircle2,
  AlertTriangle,
  RefreshCw,
  Layers,
  ShieldCheck,
  FileText,
  UploadCloud,
  HelpCircle,
  ChevronRight,
  TrendingUp
} from 'lucide-react';

export interface OverallHealth {
  quality_score: number;
  completeness_rate: number;
  verification_rate: number;
  evidence_coverage: number;
  total_products: number;
  total_attributes: number;
  total_documents: number;
}

export interface StatusBreakdown {
  verified: number;
  needs_review: number;
  draft: number;
}

export interface IssuesSummary {
  total_open_issues: number;
  cross_source_conflicts: number;
  low_confidence_attributes: number;
  validation_issues: number;
  missing_required_attributes: number;
}

export interface CategoryHealthItem {
  category: string;
  product_count: number;
  avg_quality_score: number;
  verification_rate: number;
  completeness_rate: number;
  open_issues_count: number;
  conflicts_count: number;
}

export interface BrandHealthItem {
  brand: string;
  product_count: number;
  avg_quality_score: number;
  verification_rate: number;
  completeness_rate: number;
  open_issues_count: number;
  conflicts_count: number;
}

export interface ProductAttentionItem {
  id: string;
  product_name: string;
  brand: string;
  sku: string;
  category: string;
  status: string;
  quality_score: number;
  open_issues_count: number;
  has_conflicts: boolean;
  missing_required_count: number;
  updated_at: string;
}

export interface CatalogHealthResponse {
  overall: OverallHealth;
  status_breakdown: StatusBreakdown;
  issues: IssuesSummary;
  category_health: CategoryHealthItem[];
  brand_health: BrandHealthItem[];
  products_needing_attention: ProductAttentionItem[];
  worst_products: ProductAttentionItem[];
}

export const HealthShell: React.FC = () => {
  const [catSortField, setCatSortField] = useState<'product_count' | 'avg_quality_score' | 'verification_rate' | 'open_issues_count'>('product_count');
  const [catSortDir, setCatSortDir] = useState<'asc' | 'desc'>('desc');

  const [brandSortField, setBrandSortField] = useState<'product_count' | 'avg_quality_score' | 'verification_rate' | 'open_issues_count'>('product_count');
  const [brandSortDir, setBrandSortDir] = useState<'asc' | 'desc'>('desc');

  const { data, isLoading, isError, error, refetch, isRefetching } = useQuery<CatalogHealthResponse>({
    queryKey: ['catalogHealth'],
    queryFn: async () => {
      const res = await fetch('/api/v1/health/catalog');
      if (!res.ok) {
        throw new Error(`Failed to fetch catalog health: ${res.statusText}`);
      }
      return res.json();
    },
  });

  const getQualityBadgeClass = (score: number) => {
    if (score >= 85) return 'bg-emerald-950/80 text-emerald-300 border-emerald-800/80';
    if (score >= 70) return 'bg-amber-950/80 text-amber-300 border-amber-800/80';
    return 'bg-rose-950/80 text-rose-300 border-rose-800/80';
  };

  const getStatusBadgeClass = (statusStr: string) => {
    switch (statusStr.toLowerCase()) {
      case 'verified':
        return 'bg-emerald-950 text-emerald-300 border-emerald-800';
      case 'needs_review':
        return 'bg-amber-950 text-amber-300 border-amber-800';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  if (isLoading) {
    return (
      <div className="p-6 space-y-6 max-w-7xl mx-auto">
        <div className="flex items-center justify-between">
          <div>
            <div className="h-8 w-48 bg-slate-800 animate-pulse rounded"></div>
            <div className="h-4 w-96 bg-slate-800/60 animate-pulse rounded mt-2"></div>
          </div>
          <div className="h-9 w-28 bg-slate-800 animate-pulse rounded"></div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-6 gap-4">
          {[...Array(6)].map((_, i) => (
            <div key={i} className="p-4 bg-slate-900 border border-slate-800 rounded-xl h-24 animate-pulse"></div>
          ))}
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl h-64 animate-pulse"></div>
          <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl h-64 lg:col-span-2 animate-pulse"></div>
        </div>
      </div>
    );
  }

  if (isError || !data) {
    return (
      <div className="p-6 max-w-7xl mx-auto">
        <div className="p-8 bg-slate-900 border border-rose-900/50 rounded-xl text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-rose-400 mx-auto" />
          <h3 className="text-lg font-bold text-slate-100">Catalog health data couldn't be loaded</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto font-mono">
            {error instanceof Error ? error.message : 'An error occurred while building the operational catalog health summary.'}
          </p>
          <button
            onClick={() => refetch()}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition inline-flex items-center gap-2"
          >
            <RefreshCw className="w-3.5 h-3.5" /> Retry Health Fetch
          </button>
        </div>
      </div>
    );
  }

  const { overall, status_breakdown, issues, category_health, brand_health, products_needing_attention, worst_products } = data;

  if (overall.total_products === 0) {
    return (
      <div className="p-6 max-w-7xl mx-auto space-y-6">
        <div className="flex items-center justify-between border-b border-slate-800 pb-4">
          <div>
            <h2 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2 font-mono">
              <HeartPulse className="w-6 h-6 text-rose-400" /> Catalog Health
            </h2>
            <p className="text-xs text-slate-400 mt-1 font-mono">
              Understand catalog quality, completeness, evidence coverage, and review risk.
            </p>
          </div>
        </div>

        <div className="p-12 bg-slate-900 border border-slate-800 rounded-xl text-center space-y-5">
          <div className="w-16 h-16 bg-slate-800 rounded-full flex items-center justify-center mx-auto text-slate-400">
            <Activity className="w-8 h-8 text-indigo-400" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-slate-100">Your catalog is empty</h3>
            <p className="text-xs text-slate-400 mt-1 max-w-md mx-auto font-mono">
              Upload a catalog document to start building product intelligence and health metrics.
            </p>
          </div>
          <div className="flex items-center justify-center gap-3 pt-2">
            <Link
              to="/upload"
              className="px-4 py-2.5 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition flex items-center gap-2 shadow-md"
            >
              <UploadCloud className="w-4 h-4" /> Upload Document
            </Link>
            <Link
              to="/catalog"
              className="px-4 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg transition border border-slate-700 flex items-center gap-2"
            >
              <Layers className="w-4 h-4" /> Open Catalog
            </Link>
          </div>
        </div>
      </div>
    );
  }

  // Sorted Category Health
  const sortedCategories = [...category_health].sort((a, b) => {
    const valA = a[catSortField];
    const valB = b[catSortField];
    return catSortDir === 'asc' ? (valA > valB ? 1 : -1) : (valA < valB ? 1 : -1);
  });

  // Sorted Brand Health
  const sortedBrands = [...brand_health].sort((a, b) => {
    const valA = a[brandSortField];
    const valB = b[brandSortField];
    return brandSortDir === 'asc' ? (valA > valB ? 1 : -1) : (valA < valB ? 1 : -1);
  });

  const toggleCatSort = (field: 'product_count' | 'avg_quality_score' | 'verification_rate' | 'open_issues_count') => {
    if (catSortField === field) {
      setCatSortDir(catSortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setCatSortField(field);
      setCatSortDir('desc');
    }
  };

  const toggleBrandSort = (field: 'product_count' | 'avg_quality_score' | 'verification_rate' | 'open_issues_count') => {
    if (brandSortField === field) {
      setBrandSortDir(brandSortDir === 'asc' ? 'desc' : 'asc');
    } else {
      setBrandSortField(field);
      setBrandSortDir('desc');
    }
  };

  return (
    <div className="p-6 space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 border-b border-slate-800 pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-slate-100 flex items-center gap-2 font-mono">
            <HeartPulse className="w-6 h-6 text-rose-400" /> Catalog Health Dashboard
          </h2>
          <p className="text-xs text-slate-400 mt-1 font-mono">
            Understand catalog quality, completeness, evidence coverage, and review risk.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <button
            onClick={() => refetch()}
            disabled={isRefetching}
            className="px-3 py-1.5 bg-slate-900 hover:bg-slate-800 border border-slate-700 text-slate-300 rounded-lg text-xs font-mono font-medium transition flex items-center gap-2 disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${isRefetching ? 'animate-spin' : ''}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Top KPI Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-6 gap-4">
        {/* 1. Catalog Quality */}
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl relative group">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
            <span>Catalog Quality</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-emerald-400">
            {overall.quality_score.toFixed(1)}
          </div>
          <p className="text-[10px] font-mono text-slate-400 mt-1">AVG(Product.quality_score)</p>
          <div className="absolute inset-x-0 bottom-0 h-1 bg-emerald-500 rounded-b-xl"></div>
        </div>

        {/* 2. Completeness Rate */}
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl relative group">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
            <span>Completeness</span>
            <Layers className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-indigo-400">
            {overall.completeness_rate.toFixed(1)}%
          </div>
          <p className="text-[10px] font-mono text-slate-400 mt-1">Required & optional coverage</p>
          <div className="absolute inset-x-0 bottom-0 h-1 bg-indigo-500 rounded-b-xl"></div>
        </div>

        {/* 3. Verification Rate */}
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl relative group">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
            <span>Verification Rate</span>
            <CheckCircle2 className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-cyan-400">
            {overall.verification_rate.toFixed(1)}%
          </div>
          <p className="text-[10px] font-mono text-slate-400 mt-1">{status_breakdown.verified} of {overall.total_products} verified</p>
          <div className="absolute inset-x-0 bottom-0 h-1 bg-cyan-500 rounded-b-xl"></div>
        </div>

        {/* 4. Evidence Coverage */}
        <div className="p-4 bg-slate-900 border border-slate-800 rounded-xl relative group">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
            <span>Evidence Coverage</span>
            <ShieldCheck className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-blue-400">
            {overall.evidence_coverage.toFixed(1)}%
          </div>
          <p className="text-[10px] font-mono text-slate-400 mt-1">Attributes backed by evidence</p>
          <div className="absolute inset-x-0 bottom-0 h-1 bg-blue-500 rounded-b-xl"></div>
        </div>

        {/* 5. Open Reviews */}
        <Link
          to="/reviews"
          className="p-4 bg-slate-900 border border-slate-800 hover:border-amber-700/60 rounded-xl relative group transition"
        >
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
            <span>Open Reviews</span>
            <AlertTriangle className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-amber-400">
            {issues.total_open_issues}
          </div>
          <p className="text-[10px] font-mono text-slate-400 mt-1 group-hover:text-amber-300 transition">Inspect review queue →</p>
          <div className="absolute inset-x-0 bottom-0 h-1 bg-amber-500 rounded-b-xl"></div>
        </Link>

        {/* 6. Cross-Source Conflicts */}
        <Link
          to="/reviews?issue_type=cross_source_conflict"
          className="p-4 bg-slate-900 border border-slate-800 hover:border-rose-700/60 rounded-xl relative group transition"
        >
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-1">
            <span>Conflicts</span>
            <TrendingUp className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-2xl font-bold font-mono text-rose-400">
            {issues.cross_source_conflicts}
          </div>
          <p className="text-[10px] font-mono text-slate-400 mt-1 group-hover:text-rose-300 transition">Resolve conflicts →</p>
          <div className="absolute inset-x-0 bottom-0 h-1 bg-rose-500 rounded-b-xl"></div>
        </Link>
      </div>

      {/* Section: Status Distribution & Issues Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Status Distribution */}
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
          <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono flex items-center justify-between">
            <span>Product Status Breakdown</span>
            <span className="text-xs font-normal text-slate-400">Total: {overall.total_products}</span>
          </h3>

          {/* Stacked Bar */}
          <div className="h-4 w-full bg-slate-950 rounded-full overflow-hidden flex border border-slate-800">
            <div
              style={{ width: `${(status_breakdown.verified / overall.total_products) * 100}%` }}
              className="bg-emerald-500 h-full transition-all"
              title={`Verified: ${status_breakdown.verified}`}
            ></div>
            <div
              style={{ width: `${(status_breakdown.needs_review / overall.total_products) * 100}%` }}
              className="bg-amber-500 h-full transition-all"
              title={`Needs Review: ${status_breakdown.needs_review}`}
            ></div>
            <div
              style={{ width: `${(status_breakdown.draft / overall.total_products) * 100}%` }}
              className="bg-slate-600 h-full transition-all"
              title={`Draft: ${status_breakdown.draft}`}
            ></div>
          </div>

          <div className="space-y-2.5 pt-2">
            <div className="flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-emerald-500"></span>
                <span className="text-slate-300">Verified</span>
              </div>
              <div className="font-semibold text-slate-200">
                {status_breakdown.verified} <span className="text-slate-400 font-normal">({((status_breakdown.verified / overall.total_products) * 100).toFixed(1)}%)</span>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-amber-500"></span>
                <span className="text-slate-300">Needs Review</span>
              </div>
              <div className="font-semibold text-slate-200">
                {status_breakdown.needs_review} <span className="text-slate-400 font-normal">({((status_breakdown.needs_review / overall.total_products) * 100).toFixed(1)}%)</span>
              </div>
            </div>

            <div className="flex items-center justify-between text-xs font-mono">
              <div className="flex items-center gap-2">
                <span className="w-2.5 h-2.5 rounded-full bg-slate-500"></span>
                <span className="text-slate-300">Draft</span>
              </div>
              <div className="font-semibold text-slate-200">
                {status_breakdown.draft} <span className="text-slate-400 font-normal">({((status_breakdown.draft / overall.total_products) * 100).toFixed(1)}%)</span>
              </div>
            </div>
          </div>
        </div>

        {/* Issue Cards Grid */}
        <div className="lg:col-span-2 grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Link
            to="/reviews"
            className="p-5 bg-slate-900 border border-slate-800 hover:border-slate-700 rounded-xl space-y-2 group transition flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold font-mono text-slate-300 uppercase tracking-wider">Open Reviews</span>
                <AlertTriangle className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-3xl font-bold font-mono text-slate-100 mt-2">{issues.total_open_issues}</div>
              <p className="text-xs text-slate-400 mt-1">Validation rules requiring approval or correction.</p>
            </div>
            <div className="text-xs font-mono text-indigo-400 flex items-center gap-1 group-hover:translate-x-0.5 transition pt-2">
              Filter review queue <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </Link>

          <Link
            to="/reviews?issue_type=cross_source_conflict"
            className="p-5 bg-slate-900 border border-slate-800 hover:border-rose-900/60 rounded-xl space-y-2 group transition flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold font-mono text-slate-300 uppercase tracking-wider">Cross-Source Conflicts</span>
                <TrendingUp className="w-4 h-4 text-rose-400" />
              </div>
              <div className="text-3xl font-bold font-mono text-rose-400 mt-2">{issues.cross_source_conflicts}</div>
              <p className="text-xs text-slate-400 mt-1">Inconsistent values extracted across multiple catalog sources.</p>
            </div>
            <div className="text-xs font-mono text-rose-400 flex items-center gap-1 group-hover:translate-x-0.5 transition pt-2">
              Filter conflicts <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </Link>

          <Link
            to="/reviews?issue_type=low_confidence"
            className="p-5 bg-slate-900 border border-slate-800 hover:border-amber-900/60 rounded-xl space-y-2 group transition flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold font-mono text-slate-300 uppercase tracking-wider">Low Confidence Fields</span>
                <HelpCircle className="w-4 h-4 text-amber-400" />
              </div>
              <div className="text-3xl font-bold font-mono text-amber-400 mt-2">{issues.low_confidence_attributes}</div>
              <p className="text-xs text-slate-400 mt-1">Extraction confidence below 75% requiring human verification.</p>
            </div>
            <div className="text-xs font-mono text-amber-400 flex items-center gap-1 group-hover:translate-x-0.5 transition pt-2">
              Filter low confidence <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </Link>

          <Link
            to="/reviews?issue_type=missing_attribute"
            className="p-5 bg-slate-900 border border-slate-800 hover:border-indigo-900/60 rounded-xl space-y-2 group transition flex flex-col justify-between"
          >
            <div>
              <div className="flex items-center justify-between">
                <span className="text-xs font-bold font-mono text-slate-300 uppercase tracking-wider">Missing Required Fields</span>
                <FileText className="w-4 h-4 text-indigo-400" />
              </div>
              <div className="text-3xl font-bold font-mono text-indigo-400 mt-2">{issues.missing_required_attributes}</div>
              <p className="text-xs text-slate-400 mt-1">Category-specific mandatory attributes missing from extraction.</p>
            </div>
            <div className="text-xs font-mono text-indigo-400 flex items-center gap-1 group-hover:translate-x-0.5 transition pt-2">
              Filter missing fields <ChevronRight className="w-3.5 h-3.5" />
            </div>
          </Link>
        </div>
      </div>

      {/* Category & Brand Health Tables */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Category Health Table */}
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono">
              Category Quality Health
            </h3>
            <span className="text-xs font-mono text-slate-400">{category_health.length} categories</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <th className="py-2 px-2">Category</th>
                  <th
                    className="py-2 px-2 cursor-pointer hover:text-slate-200"
                    onClick={() => toggleCatSort('product_count')}
                  >
                    Products {catSortField === 'product_count' ? (catSortDir === 'asc' ? '↑' : '↓') : ''}
                  </th>
                  <th
                    className="py-2 px-2 cursor-pointer hover:text-slate-200"
                    onClick={() => toggleCatSort('avg_quality_score')}
                  >
                    Avg Quality {catSortField === 'avg_quality_score' ? (catSortDir === 'asc' ? '↑' : '↓') : ''}
                  </th>
                  <th
                    className="py-2 px-2 cursor-pointer hover:text-slate-200"
                    onClick={() => toggleCatSort('verification_rate')}
                  >
                    Verified % {catSortField === 'verification_rate' ? (catSortDir === 'asc' ? '↑' : '↓') : ''}
                  </th>
                  <th className="py-2 px-2 text-right">Issues</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {sortedCategories.map((c) => (
                  <tr key={c.category} className="hover:bg-slate-800/40 transition">
                    <td className="py-2.5 px-2 font-semibold text-slate-200">{c.category}</td>
                    <td className="py-2.5 px-2 text-slate-300">{c.product_count}</td>
                    <td className="py-2.5 px-2">
                      <span className={`px-1.5 py-0.5 rounded border text-[11px] font-bold ${getQualityBadgeClass(c.avg_quality_score)}`}>
                        {c.avg_quality_score.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-2.5 px-2 text-slate-300">{c.verification_rate.toFixed(1)}%</td>
                    <td className="py-2.5 px-2 text-right">
                      {c.open_issues_count > 0 ? (
                        <span className="text-amber-400 font-semibold">{c.open_issues_count} open</span>
                      ) : (
                        <span className="text-emerald-400">0</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Brand Health Table */}
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-slate-200 uppercase tracking-wider font-mono">
              Brand Quality Health
            </h3>
            <span className="text-xs font-mono text-slate-400">{brand_health.length} brands</span>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <th className="py-2 px-2">Brand</th>
                  <th
                    className="py-2 px-2 cursor-pointer hover:text-slate-200"
                    onClick={() => toggleBrandSort('product_count')}
                  >
                    Products {brandSortField === 'product_count' ? (brandSortDir === 'asc' ? '↑' : '↓') : ''}
                  </th>
                  <th
                    className="py-2 px-2 cursor-pointer hover:text-slate-200"
                    onClick={() => toggleBrandSort('avg_quality_score')}
                  >
                    Avg Quality {brandSortField === 'avg_quality_score' ? (brandSortDir === 'asc' ? '↑' : '↓') : ''}
                  </th>
                  <th
                    className="py-2 px-2 cursor-pointer hover:text-slate-200"
                    onClick={() => toggleBrandSort('verification_rate')}
                  >
                    Verified % {brandSortField === 'verification_rate' ? (brandSortDir === 'asc' ? '↑' : '↓') : ''}
                  </th>
                  <th className="py-2 px-2 text-right">Issues</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {sortedBrands.map((b) => (
                  <tr key={b.brand} className="hover:bg-slate-800/40 transition">
                    <td className="py-2.5 px-2 font-semibold text-slate-200">{b.brand}</td>
                    <td className="py-2.5 px-2 text-slate-300">{b.product_count}</td>
                    <td className="py-2.5 px-2">
                      <span className={`px-1.5 py-0.5 rounded border text-[11px] font-bold ${getQualityBadgeClass(b.avg_quality_score)}`}>
                        {b.avg_quality_score.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-2.5 px-2 text-slate-300">{b.verification_rate.toFixed(1)}%</td>
                    <td className="py-2.5 px-2 text-right">
                      {b.open_issues_count > 0 ? (
                        <span className="text-amber-400 font-semibold">{b.open_issues_count} open</span>
                      ) : (
                        <span className="text-emerald-400">0</span>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Attention Queue ("Products Needing Attention") */}
      <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider font-mono flex items-center gap-2">
              <AlertTriangle className="w-4 h-4 text-amber-400" /> Products Needing Attention
            </h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">Top products prioritized by review status, conflicts, and quality risk.</p>
          </div>
          <span className="text-xs font-mono text-slate-400">{products_needing_attention.length} items</span>
        </div>

        {products_needing_attention.length === 0 ? (
          <div className="p-6 bg-slate-950/60 border border-slate-800 rounded-lg text-center text-xs font-mono text-emerald-400">
            ✓ All products are healthy. No items require immediate attention.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono">
              <thead>
                <tr className="border-b border-slate-800 text-slate-400 uppercase text-[10px]">
                  <th className="py-2.5 px-3">Product / SKU</th>
                  <th className="py-2.5 px-3">Brand</th>
                  <th className="py-2.5 px-3">Category</th>
                  <th className="py-2.5 px-3">Status</th>
                  <th className="py-2.5 px-3">Quality</th>
                  <th className="py-2.5 px-3">Issues</th>
                  <th className="py-2.5 px-3 text-right">Action</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {products_needing_attention.map((item) => (
                  <tr key={item.id} className="hover:bg-slate-800/40 transition">
                    <td className="py-3 px-3">
                      <div className="font-semibold text-slate-100">{item.product_name}</div>
                      <div className="text-[11px] text-slate-400 font-mono">SKU: {item.sku}</div>
                    </td>
                    <td className="py-3 px-3 text-slate-300">{item.brand}</td>
                    <td className="py-3 px-3 text-slate-300">{item.category}</td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 text-[10px] font-bold rounded border uppercase ${getStatusBadgeClass(item.status)}`}>
                        {item.status}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <span className={`px-2 py-0.5 rounded border text-[11px] font-bold ${getQualityBadgeClass(item.quality_score)}`}>
                        {item.quality_score.toFixed(1)}
                      </span>
                    </td>
                    <td className="py-3 px-3">
                      <div className="space-y-0.5 text-[11px]">
                        {item.open_issues_count > 0 && (
                          <div className="text-amber-400 font-semibold">{item.open_issues_count} open issues</div>
                        )}
                        {item.has_conflicts && (
                          <div className="text-rose-400 font-semibold">⚠ Conflict detected</div>
                        )}
                        {item.open_issues_count === 0 && !item.has_conflicts && (
                          <div className="text-slate-400">—</div>
                        )}
                      </div>
                    </td>
                    <td className="py-3 px-3 text-right space-x-2">
                      <Link
                        to="/reviews"
                        className="px-2.5 py-1 bg-amber-600/80 hover:bg-amber-500 text-white text-[11px] font-semibold rounded transition inline-flex items-center gap-1"
                      >
                        Review Issues
                      </Link>
                      <Link
                        to="/catalog"
                        className="px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 text-[11px] font-semibold rounded transition inline-flex items-center gap-1"
                      >
                        Catalog
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Worst Products ("Lowest Quality Products") */}
      <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl space-y-4">
        <div className="flex items-center justify-between">
          <div>
            <h3 className="text-sm font-bold text-slate-100 uppercase tracking-wider font-mono flex items-center gap-2">
              <TrendingUp className="w-4 h-4 text-rose-400" /> Lowest Quality Products
            </h3>
            <p className="text-xs text-slate-400 font-mono mt-0.5">Bottom 10 products sorted by persisted quality_score ASC.</p>
          </div>
          <span className="text-xs font-mono text-slate-400">{worst_products.length} items</span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {worst_products.map((item) => (
            <div key={item.id} className="p-4 bg-slate-950 border border-slate-800/80 rounded-lg flex items-center justify-between gap-4">
              <div className="min-w-0 flex-1">
                <div className="font-semibold text-slate-200 text-xs truncate">{item.product_name}</div>
                <div className="flex items-center gap-2 mt-1 text-[11px] font-mono text-slate-400">
                  <span>{item.brand}</span>
                  <span>•</span>
                  <span>SKU: {item.sku}</span>
                  <span>•</span>
                  <span>{item.category}</span>
                </div>
              </div>
              <div className="text-right">
                <div className={`px-2.5 py-1 rounded border text-xs font-bold font-mono inline-block ${getQualityBadgeClass(item.quality_score)}`}>
                  {item.quality_score.toFixed(1)}
                </div>
                <div className="mt-1">
                  <Link
                    to="/catalog"
                    className="text-[10px] font-mono text-indigo-400 hover:text-indigo-300 flex items-center justify-end gap-0.5"
                  >
                    Details <ChevronRight className="w-3 h-3" />
                  </Link>
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
