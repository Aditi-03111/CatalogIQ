import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  CheckSquare,
  AlertTriangle,
  Search,
  RefreshCw,
  Database,
  HeartPulse,
  CheckCircle2,
  Sparkles,
  Layers,
  X
} from 'lucide-react';

interface EvidenceItem {
  id: string;
  attribute_id?: string;
  source_name: string;
  source_type: string;
  trust_level: number;
  document_filename?: string;
  page_number?: number;
  evidence_text: string;
  extraction_method: string;
}

interface ReviewItem {
  validation_id: string;
  product_id: string;
  product_name: string;
  brand: string;
  sku: string;
  category: string;
  attribute_id?: string;
  attribute_name?: string;
  display_name?: string;
  category_type: string;
  validation_type: string;
  status: string;
  severity: string;
  message: string;
  actual_value?: any;
  expected_value?: any;
  current_value?: any;
  confidence?: number;
  product_quality_score: number;
  created_at: string;
  resolved_at?: string;
  resolved_by?: string;
  evidence: EvidenceItem[];
  competing_claims: any[];
}

interface ReviewSummaryCounts {
  total_open_issues: number;
  cross_source_conflicts: number;
  low_confidence_issues: number;
  validation_issues: number;
  missing_required_attributes: number;
  products_needing_review: number;
}

interface ReviewsResponse {
  summary: ReviewSummaryCounts;
  items: ReviewItem[];
  total_items: number;
  page: number;
  limit: number;
  total_pages: number;
}

export const ReviewsShell: React.FC = () => {
  const navigate = useNavigate();

  const [data, setData] = useState<ReviewsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [statusFilter, setStatusFilter] = useState<string>('open');
  const [categoryFilter, setCategoryFilter] = useState<string>('all');
  const [severityFilter, setSeverityFilter] = useState<string>('all');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('newest');

  // Selected review for detail drawer / modal
  const [selectedReview, setSelectedReview] = useState<ReviewItem | null>(null);
  const [resolving, setResolving] = useState<boolean>(false);
  const [customValueInput, setCustomValueInput] = useState<string>('');
  const [showCustomInput, setShowCustomInput] = useState<boolean>(false);
  const [resolutionNotes, setResolutionNotes] = useState<string>('');
  const [resolutionSuccess, setResolutionSuccess] = useState<string | null>(null);

  const fetchReviews = async () => {
    try {
      setLoading(true);
      setError(null);

      const params = new URLSearchParams();
      params.set('status', statusFilter);
      if (categoryFilter !== 'all') params.set('issue_type', categoryFilter);
      if (severityFilter !== 'all') params.set('severity', severityFilter);
      if (searchQuery.trim()) params.set('search', searchQuery.trim());
      params.set('sort_by', sortBy);

      const res = await fetch(`/api/v1/reviews?${params.toString()}`);
      if (!res.ok) {
        throw new Error(`Server returned HTTP ${res.status}`);
      }
      const responseData: ReviewsResponse = await res.json();
      setData(responseData);

      // If selected review is open, update reference
      if (selectedReview) {
        const updated = responseData.items.find((i) => i.validation_id === selectedReview.validation_id);
        if (updated) setSelectedReview(updated);
      }
    } catch (err: any) {
      console.error('Failed to fetch reviews:', err);
      setError(err?.message || 'Failed to load reviews workspace');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchReviews();
  }, [statusFilter, categoryFilter, severityFilter, sortBy]);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    fetchReviews();
  };

  const handleResolve = async (review: ReviewItem, resolution: string, value?: any) => {
    try {
      setResolving(true);
      setResolutionSuccess(null);

      const res = await fetch(`/api/v1/products/${review.product_id}/validation/${review.validation_id}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resolution,
          resolved_value: value,
          notes: resolutionNotes || `Resolved via Review Workspace with ${resolution}`,
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || 'Resolution failed');
      }

      setResolutionSuccess(`Successfully resolved ${review.display_name || 'issue'}!`);
      setShowCustomInput(false);
      setCustomValueInput('');
      setResolutionNotes('');

      // Refresh list
      await fetchReviews();
    } catch (err: any) {
      console.error('Resolution error:', err);
      alert(`Resolution failed: ${err.message}`);
    } finally {
      setResolving(false);
    }
  };

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

  const getSeverityBadgeClass = (sev: string) => {
    switch (sev.toLowerCase()) {
      case 'critical':
        return 'bg-red-950 text-red-300 border-red-800';
      case 'error':
        return 'bg-orange-950 text-orange-300 border-orange-800';
      case 'warning':
        return 'bg-amber-950 text-amber-300 border-amber-800';
      default:
        return 'bg-blue-950 text-blue-300 border-blue-800';
    }
  };

  const getCategoryBadge = (cat: string) => {
    switch (cat) {
      case 'cross_source_conflict':
        return (
          <span className="px-2 py-0.5 rounded bg-red-950 text-red-300 border border-red-800 text-[11px] font-mono font-semibold">
            ⚔️ Conflict
          </span>
        );
      case 'low_confidence':
        return (
          <span className="px-2 py-0.5 rounded bg-amber-950 text-amber-300 border border-amber-800 text-[11px] font-mono font-semibold">
            ⚠️ Low Confidence
          </span>
        );
      case 'missing_attribute':
        return (
          <span className="px-2 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 text-[11px] font-mono font-semibold">
            ❓ Missing Field
          </span>
        );
      default:
        return (
          <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 border border-slate-700 text-[11px] font-mono font-semibold">
            🛡️ Rule Check
          </span>
        );
    }
  };

  const summary = data?.summary;
  const items = data?.items || [];
  const isEmpty = (summary?.total_open_issues ?? 0) === 0 && statusFilter === 'open';

  return (
    <div className="space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-orange-950 border border-orange-800 flex items-center justify-center text-orange-400">
            <CheckSquare className="w-6 h-6" />
          </div>
          <div>
            <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
              Review & Resolution Workspace
            </h2>
            <p className="text-sm text-slate-400">
              Resolve catalog issues, validate conflicting claims, and maintain product data quality.
            </p>
          </div>
        </div>

        <button
          onClick={fetchReviews}
          className="px-3.5 py-2 bg-slate-900 hover:bg-slate-800 text-slate-300 text-xs font-semibold rounded-lg border border-slate-800 transition flex items-center gap-2"
        >
          <RefreshCw className={`w-3.5 h-3.5 text-slate-400 ${loading ? 'animate-spin' : ''}`} /> Refresh Reviews
        </button>
      </div>

      {/* TOP KPI CARDS */}
      <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-5">
        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold tracking-wider uppercase">Open Reviews</span>
            <CheckSquare className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-3xl font-black text-white">{summary?.total_open_issues ?? 0}</div>
          <p className="text-xs text-slate-400">Total active review items</p>
        </div>

        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold tracking-wider uppercase">Cross-Source Conflicts</span>
            <AlertTriangle className="w-4 h-4 text-red-400" />
          </div>
          <div className="text-3xl font-black text-red-400">{summary?.cross_source_conflicts ?? 0}</div>
          <p className="text-xs text-slate-400">Competing claim discrepancies</p>
        </div>

        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold tracking-wider uppercase">Low Confidence</span>
            <Sparkles className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-black text-amber-400">{summary?.low_confidence_issues ?? 0}</div>
          <p className="text-xs text-slate-400">Confidence below threshold</p>
        </div>

        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold tracking-wider uppercase">Validation Issues</span>
            <Layers className="w-4 h-4 text-blue-400" />
          </div>
          <div className="text-3xl font-black text-white">{summary?.validation_issues ?? 0}</div>
          <p className="text-xs text-slate-400">Rule & format violations</p>
        </div>

        <div className="p-5 bg-slate-900 border border-slate-800 rounded-xl shadow-lg space-y-2">
          <div className="flex items-center justify-between text-slate-400">
            <span className="text-[11px] font-bold tracking-wider uppercase">Products Needing Review</span>
            <Database className="w-4 h-4 text-indigo-400" />
          </div>
          <div className="text-3xl font-black text-indigo-400">{summary?.products_needing_review ?? 0}</div>
          <p className="text-xs text-slate-400">Catalog products requiring action</p>
        </div>
      </div>

      {/* FILTER & SEARCH BAR */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-4 shadow-lg flex flex-wrap items-center justify-between gap-4">
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 min-w-[240px]">
          <div className="relative flex-1">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search by Product Name, SKU, Brand, or Attribute..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full bg-slate-950 border border-slate-800 text-slate-200 pl-9 pr-4 py-2 rounded-lg text-xs font-medium outline-none focus:border-indigo-500 transition"
            />
          </div>
          <button
            type="submit"
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition"
          >
            Search
          </button>
        </form>

        <div className="flex flex-wrap items-center gap-3">
          {/* Category filter */}
          <select
            value={categoryFilter}
            onChange={(e) => setCategoryFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 px-3 py-2 rounded-lg text-xs font-medium outline-none"
          >
            <option value="all">All Categories</option>
            <option value="cross_source_conflict">Cross-Source Conflicts</option>
            <option value="low_confidence">Low Confidence</option>
            <option value="validation_issue">Validation Issues</option>
            <option value="missing_attribute">Missing Attributes</option>
          </select>

          {/* Status filter */}
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 px-3 py-2 rounded-lg text-xs font-medium outline-none"
          >
            <option value="open">Status: Open</option>
            <option value="resolved">Status: Resolved</option>
            <option value="all">Status: All</option>
          </select>

          {/* Severity filter */}
          <select
            value={severityFilter}
            onChange={(e) => setSeverityFilter(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 px-3 py-2 rounded-lg text-xs font-medium outline-none"
          >
            <option value="all">All Severities</option>
            <option value="critical">Critical</option>
            <option value="error">Error</option>
            <option value="warning">Warning</option>
            <option value="info">Info</option>
          </select>

          {/* Sort selector */}
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-slate-950 border border-slate-800 text-slate-300 px-3 py-2 rounded-lg text-xs font-medium outline-none"
          >
            <option value="newest">Sort: Newest</option>
            <option value="oldest">Sort: Oldest</option>
            <option value="severity">Sort: Severity</option>
            <option value="confidence">Sort: Confidence</option>
          </select>
        </div>
      </div>

      {/* ERROR STATE */}
      {error && (
        <div className="p-8 bg-red-950/40 border border-red-800/60 rounded-xl flex flex-col items-center justify-center text-center space-y-4">
          <AlertTriangle className="w-12 h-12 text-red-400" />
          <div className="max-w-md space-y-1">
            <h3 className="font-semibold text-lg text-red-200">Unable to Load Review Workspace</h3>
            <p className="text-sm text-red-300/80">{error}</p>
          </div>
          <button
            onClick={fetchReviews}
            className="px-4 py-2 bg-red-900 hover:bg-red-800 text-red-100 rounded-lg font-medium text-sm flex items-center gap-2 border border-red-700 transition"
          >
            <RefreshCw className="w-4 h-4" /> Retry
          </button>
        </div>
      )}

      {/* HEALTHY / EMPTY STATE */}
      {isEmpty && !loading && !error && (
        <div className="p-12 border border-dashed border-emerald-900/60 bg-emerald-950/20 rounded-xl flex flex-col items-center justify-center text-center space-y-4 shadow-xl">
          <div className="w-16 h-16 rounded-full bg-emerald-950 border border-emerald-800 flex items-center justify-center text-emerald-400">
            <CheckCircle2 className="w-8 h-8" />
          </div>
          <div className="max-w-md space-y-1">
            <h3 className="font-bold text-xl text-white">Catalog is Healthy</h3>
            <p className="text-sm text-emerald-300/80">
              No unresolved validation issues require your attention right now.
            </p>
          </div>
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <button
              onClick={() => navigate('/catalog')}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-2 transition"
            >
              <Database className="w-4 h-4" /> Open Catalog
            </button>
            <button
              onClick={() => navigate('/health')}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-2 transition"
            >
              <HeartPulse className="w-4 h-4" /> Catalog Health
            </button>
            <button
              onClick={() => navigate('/search')}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold flex items-center gap-2 transition"
            >
              <Search className="w-4 h-4" /> Search Catalog
            </button>
          </div>
        </div>
      )}

      {/* MAIN REVIEWS TABLE LIST */}
      {!isEmpty && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
          <div className="flex items-center justify-between border-b border-slate-800 pb-3">
            <h3 className="text-lg font-bold text-white flex items-center gap-2">
              <span>📋</span> Review Queue Items ({data?.total_items ?? 0})
            </h3>
            <span className="text-xs text-slate-400 font-mono">
              Showing page {data?.page ?? 1} of {data?.total_pages ?? 1}
            </span>
          </div>

          {loading ? (
            <div className="py-12 text-center text-slate-400 font-medium animate-pulse">
              Loading Review Items...
            </div>
          ) : items.length === 0 ? (
            <p className="text-xs text-slate-500 italic py-8 text-center">No review items match your active filters.</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead>
                  <tr className="border-b border-slate-800 text-xs font-semibold uppercase text-slate-400 font-mono">
                    <th className="py-2.5 px-3">Product / SKU</th>
                    <th className="py-2.5 px-3">Attribute</th>
                    <th className="py-2.5 px-3">Issue Category</th>
                    <th className="py-2.5 px-3">Severity</th>
                    <th className="py-2.5 px-3">Extracted / Expected Value</th>
                    <th className="py-2.5 px-3">Confidence</th>
                    <th className="py-2.5 px-3">Status</th>
                    <th className="py-2.5 px-3">Created</th>
                    <th className="py-2.5 px-3 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-800/60">
                  {items.map((item) => (
                    <tr
                      key={item.validation_id}
                      onClick={() => setSelectedReview(item)}
                      className="cursor-pointer hover:bg-slate-800/50 transition"
                    >
                      <td className="py-3 px-3">
                        <div className="font-semibold text-slate-100">{item.product_name}</div>
                        <div className="flex items-center gap-1.5 mt-0.5">
                          <span className="px-1.5 py-0.5 rounded bg-slate-800 border border-slate-700 text-[10px] font-mono text-slate-300">
                            {item.brand}
                          </span>
                          <span className="text-[11px] font-mono text-slate-400">SKU: {item.sku}</span>
                        </div>
                      </td>
                      <td className="py-3 px-3">
                        <div className="font-medium text-slate-200">{item.display_name}</div>
                        <div className="text-[11px] font-mono text-slate-400">{item.attribute_name || '—'}</div>
                      </td>
                      <td className="py-3 px-3">{getCategoryBadge(item.category_type)}</td>
                      <td className="py-3 px-3">
                        <span
                          className={`text-[11px] font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wider font-mono ${getSeverityBadgeClass(
                            item.severity
                          )}`}
                        >
                          {item.severity}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-xs">
                        {item.actual_value !== undefined && item.actual_value !== null ? (
                          <div className="text-emerald-400 font-semibold">{String(item.actual_value)}</div>
                        ) : (
                          <div className="text-slate-400">—</div>
                        )}
                        {item.expected_value !== undefined && item.expected_value !== null && (
                          <div className="text-amber-400 text-[11px] line-through">vs {String(item.expected_value)}</div>
                        )}
                      </td>
                      <td className="py-3 px-3 font-mono text-xs">
                        {item.confidence != null ? `${Math.round(item.confidence * 100)}%` : '—'}
                      </td>
                      <td className="py-3 px-3">
                        <span
                          className={`text-[11px] font-semibold px-2 py-0.5 rounded border uppercase font-mono ${
                            item.status === 'resolved'
                              ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                              : 'bg-amber-950 text-amber-300 border-amber-800'
                          }`}
                        >
                          {item.status}
                        </span>
                      </td>
                      <td className="py-3 px-3 font-mono text-xs text-slate-400">{formatTimestamp(item.created_at)}</td>
                      <td className="py-3 px-3 text-right">
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setSelectedReview(item);
                          }}
                          className="px-3 py-1.5 bg-indigo-600 hover:bg-indigo-500 text-white rounded text-xs font-semibold transition"
                        >
                          Inspect & Resolve
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* REVIEW DETAIL MODAL / DRAWER */}
      {selectedReview && (
        <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-4">
          <div className="bg-slate-900 border border-slate-800 rounded-xl shadow-2xl max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 space-y-6 text-slate-100 relative">
            {/* Close Button */}
            <button
              onClick={() => {
                setSelectedReview(null);
                setResolutionSuccess(null);
                setShowCustomInput(false);
              }}
              className="absolute top-4 right-4 p-1.5 text-slate-400 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg transition"
            >
              <X className="w-5 h-5" />
            </button>

            {/* Modal Header */}
            <div className="space-y-2 border-b border-slate-800 pb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono">
                  {selectedReview.brand}
                </span>
                <span className="text-xs text-slate-400 font-mono">SKU: {selectedReview.sku}</span>
                {getCategoryBadge(selectedReview.category_type)}
              </div>
              <h3 className="text-2xl font-bold text-white">{selectedReview.product_name}</h3>
              <p className="text-xs text-slate-400 font-mono">
                Attribute: <span className="text-slate-200 font-semibold">{selectedReview.display_name}</span> ({selectedReview.attribute_name || 'N/A'})
              </p>
            </div>

            {/* Success notification alert */}
            {resolutionSuccess && (
              <div className="p-4 bg-emerald-950/80 border border-emerald-800 rounded-lg text-emerald-300 text-xs font-semibold flex items-center justify-between">
                <span>✓ {resolutionSuccess}</span>
                <button onClick={() => setResolutionSuccess(null)} className="underline">Dismiss</button>
              </div>
            )}

            {/* Issue Details Box */}
            <div className="bg-slate-950 border border-slate-800 rounded-lg p-4 space-y-2">
              <div className="flex items-center justify-between text-xs text-slate-400 font-mono">
                <span>Validation Rule: <strong className="text-slate-200">{selectedReview.validation_type}</strong></span>
                <span className={`px-2 py-0.5 rounded border uppercase text-[10px] ${getSeverityBadgeClass(selectedReview.severity)}`}>
                  {selectedReview.severity}
                </span>
              </div>
              <p className="text-sm text-slate-200 leading-relaxed font-medium">{selectedReview.message}</p>
            </div>

            {/* Competing Claims Comparison */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-mono">
                ⚔️ Source Claims & Values Comparison
              </h4>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {/* Canonical / Source A Claim */}
                <div className="bg-slate-950 border border-emerald-900/80 rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-emerald-400 font-mono font-semibold">
                    <span>Source Claim A (Extracted)</span>
                    <span>Trust: 95%</span>
                  </div>
                  <div className="text-2xl font-black text-emerald-400 font-mono">
                    {selectedReview.actual_value !== undefined && selectedReview.actual_value !== null
                      ? String(selectedReview.actual_value)
                      : String(selectedReview.current_value || '—')}
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Confidence: {selectedReview.confidence != null ? `${Math.round(selectedReview.confidence * 100)}%` : '100%'}
                  </p>
                </div>

                {/* Competing / Source B Claim */}
                <div className="bg-slate-950 border border-amber-900/80 rounded-lg p-4 space-y-2">
                  <div className="flex items-center justify-between text-xs text-amber-400 font-mono font-semibold">
                    <span>Source Claim B (Expected / Competing)</span>
                    <span>Trust: 70%</span>
                  </div>
                  <div className="text-2xl font-black text-amber-400 font-mono">
                    {selectedReview.expected_value !== undefined && selectedReview.expected_value !== null
                      ? String(selectedReview.expected_value)
                      : '—'}
                  </div>
                  <p className="text-[11px] text-slate-400">Distributor / Cross-Attribute Check</p>
                </div>
              </div>
            </div>

            {/* Evidence Provenance Section */}
            <div className="space-y-3">
              <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider font-mono">
                🔎 Document Evidence Provenance
              </h4>

              {selectedReview.evidence.length === 0 ? (
                <p className="text-xs text-slate-500 italic p-4 bg-slate-950 rounded-lg text-center">
                  No evidence quotes attached to this attribute.
                </p>
              ) : (
                <div className="space-y-3 max-h-48 overflow-y-auto pr-1">
                  {selectedReview.evidence.map((ev) => (
                    <div key={ev.id} className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-1.5 text-xs">
                      <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                        <span>📄 {ev.document_filename || ev.source_name} (Page {ev.page_number || 1})</span>
                        <span>Trust: {Math.round(ev.trust_level * 100)}%</span>
                      </div>
                      <blockquote className="bg-slate-900/90 border-l-2 border-emerald-500 p-2.5 rounded text-slate-200 italic font-mono text-[11px] leading-relaxed">
                        "{ev.evidence_text}"
                      </blockquote>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Resolution Actions Panel */}
            {selectedReview.status === 'open' && (
              <div className="pt-4 border-t border-slate-800 space-y-4">
                <h4 className="text-xs font-bold text-slate-300 uppercase tracking-wider font-mono">
                  ⚡ Human Resolution Action
                </h4>

                <div className="space-y-2">
                  <label className="text-xs text-slate-400 font-mono block">Reviewer Notes (Optional):</label>
                  <input
                    type="text"
                    placeholder="Add audit resolution notes..."
                    value={resolutionNotes}
                    onChange={(e) => setResolutionNotes(e.target.value)}
                    className="w-full bg-slate-950 border border-slate-800 text-slate-200 px-3 py-2 rounded-lg text-xs font-medium outline-none"
                  />
                </div>

                <div className="flex flex-wrap items-center gap-3">
                  <button
                    disabled={resolving}
                    onClick={() => handleResolve(selectedReview, 'accept_source_a', selectedReview.actual_value)}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50 flex items-center gap-1.5 shadow-md"
                  >
                    Accept Extracted Claim A ({String(selectedReview.actual_value || selectedReview.current_value || 'Extracted')})
                  </button>

                  {selectedReview.expected_value !== undefined && selectedReview.expected_value !== null && (
                    <button
                      disabled={resolving}
                      onClick={() => handleResolve(selectedReview, 'accept_source_b', selectedReview.expected_value)}
                      className="px-4 py-2 bg-amber-600 hover:bg-amber-500 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50 flex items-center gap-1.5 shadow-md"
                    >
                      Accept Expected Claim B ({String(selectedReview.expected_value)})
                    </button>
                  )}

                  <button
                    disabled={resolving}
                    onClick={() => setShowCustomInput(!showCustomInput)}
                    className="px-4 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 rounded-lg text-xs font-semibold transition disabled:opacity-50"
                  >
                    Set Custom Value...
                  </button>
                </div>

                {showCustomInput && (
                  <div className="p-4 bg-slate-950 border border-slate-800 rounded-lg flex items-center gap-3">
                    <input
                      type="text"
                      placeholder="Enter verified custom value..."
                      value={customValueInput}
                      onChange={(e) => setCustomValueInput(e.target.value)}
                      className="flex-1 bg-slate-900 border border-slate-700 text-slate-200 px-3 py-2 rounded-lg text-xs font-medium outline-none"
                    />
                    <button
                      disabled={resolving || !customValueInput.trim()}
                      onClick={() => handleResolve(selectedReview, 'custom_value', customValueInput.trim())}
                      className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg text-xs font-semibold transition disabled:opacity-50"
                    >
                      Submit Custom Value
                    </button>
                  </div>
                )}
              </div>
            )}

            {selectedReview.status === 'resolved' && (
              <div className="p-4 bg-emerald-950/60 border border-emerald-800 rounded-lg text-xs text-emerald-300 flex items-center justify-between font-mono">
                <span>✓ Resolved by {selectedReview.resolved_by || 'human_reviewer'} on {formatTimestamp(selectedReview.resolved_at)}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
