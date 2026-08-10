import React, { useState, useEffect } from 'react';
import { Search, Loader2, Sparkles, Filter, ExternalLink, AlertCircle, Database, CheckCircle2, ShieldAlert } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface AttributeItem {
  attribute_name: string;
  display_name: string;
  raw_value: string;
  unit?: string;
  confidence: number;
  status: string;
}

interface SearchResultItem {
  product_id: string;
  product_name: string;
  sku: string;
  category: string;
  manufacturer: string;
  model?: string;
  quality_score: number;
  similarity_score: number;
  status: string;
  commerce_description?: string;
  short_description?: string;
  features: string[];
  applications: string[];
  attributes: AttributeItem[];
}

interface SearchResponse {
  query: string;
  total: number;
  results: SearchResultItem[];
}

export const SearchShell: React.FC = () => {
  const navigate = useNavigate();
  const [query, setQuery] = useState<string>('industrial induction motors around 10 kW');
  const [categoryFilter, setCategoryFilter] = useState<string>('');
  const [brandFilter, setBrandFilter] = useState<string>('');
  const [limit, setLimit] = useState<number>(10);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [searchData, setSearchData] = useState<SearchResponse | null>(null);

  // Perform search
  const handleSearch = async (overrideQuery?: string) => {
    const q = overrideQuery !== undefined ? overrideQuery : query;
    if (!q.trim()) return;

    setLoading(true);
    setError(null);

    try {
      const params = new URLSearchParams();
      params.append('q', q.trim());
      params.append('limit', limit.toString());
      if (categoryFilter) params.append('category', categoryFilter);
      if (brandFilter) params.append('brand', brandFilter);

      const res = await fetch(`/api/v1/search?${params.toString()}`);
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || `Search failed with status ${res.status}`);
      }

      const data: SearchResponse = await res.json();
      setSearchData(data);
    } catch (err: any) {
      console.error('Semantic search error:', err);
      setError(err.message || 'An error occurred while connecting to the semantic search service.');
    } finally {
      setLoading(false);
    }
  };

  // Perform initial search on mount with default query
  useEffect(() => {
    handleSearch('industrial induction motors around 10 kW');
  }, []);

  const exampleQueries = [
    'industrial induction motors around 10 kW',
    'high RPM induction motors with IP55 protection',
    'motors suitable for continuous duty pumps',
  ];

  return (
    <div className="space-y-6 text-slate-100">
      {/* Header */}
      <div>
        <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
          <Sparkles className="w-7 h-7 text-indigo-400" />
          <span>Semantic Search & Vector Retrieval</span>
        </h2>
        <p className="text-sm text-slate-400 mt-1">
          Query validated catalog intelligence using natural language vector embeddings and Qdrant vector retrieval.
        </p>
      </div>

      {/* Search Bar & Controls */}
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-5 shadow-xl space-y-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search className="w-5 h-5 text-slate-400 absolute left-4 top-3.5" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter') handleSearch();
              }}
              placeholder="e.g. industrial induction motors around 10 kW for continuous operation"
              className="w-full pl-11 pr-4 py-3 bg-slate-950 border border-slate-700 rounded-lg text-sm text-slate-100 placeholder-slate-500 outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition font-medium"
            />
          </div>
          <button
            onClick={() => handleSearch()}
            disabled={loading}
            className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:opacity-50 text-white font-semibold rounded-lg text-sm transition shadow-lg flex items-center justify-center gap-2 min-w-[120px]"
          >
            {loading ? (
              <>
                <Loader2 className="w-4 h-4 animate-spin" />
                <span>Searching...</span>
              </>
            ) : (
              <>
                <Search className="w-4 h-4" />
                <span>Search</span>
              </>
            )}
          </button>
        </div>

        {/* Quick Example Query Pills */}
        <div className="flex flex-wrap items-center gap-2 pt-1 text-xs">
          <span className="text-slate-400 font-mono flex items-center gap-1">
            <span>Try:</span>
          </span>
          {exampleQueries.map((ex, idx) => (
            <button
              key={idx}
              onClick={() => {
                setQuery(ex);
                handleSearch(ex);
              }}
              className="px-3 py-1 bg-slate-800 hover:bg-slate-700 text-indigo-300 rounded-full border border-slate-700 transition font-mono text-[11px]"
            >
              "{ex}"
            </button>
          ))}
        </div>

        {/* Filters */}
        <div className="pt-3 border-t border-slate-800/80 flex flex-wrap items-center justify-between gap-4 text-xs">
          <div className="flex items-center gap-4 flex-wrap">
            <span className="text-slate-400 font-medium flex items-center gap-1.5">
              <Filter className="w-3.5 h-3.5 text-slate-400" /> Filters:
            </span>

            {/* Category Filter */}
            <input
              type="text"
              value={categoryFilter}
              onChange={(e) => setCategoryFilter(e.target.value)}
              placeholder="Category (e.g. Industrial Electric Motor)"
              className="bg-slate-950 border border-slate-700 text-slate-200 px-3 py-1.5 rounded text-xs outline-none focus:border-indigo-500 min-w-[180px]"
            />

            {/* Brand Filter */}
            <input
              type="text"
              value={brandFilter}
              onChange={(e) => setBrandFilter(e.target.value)}
              placeholder="Manufacturer / Brand"
              className="bg-slate-950 border border-slate-700 text-slate-200 px-3 py-1.5 rounded text-xs outline-none focus:border-indigo-500 min-w-[150px]"
            />
          </div>

          <div className="flex items-center gap-2">
            <span className="text-slate-400">Limit:</span>
            <select
              value={limit}
              onChange={(e) => setLimit(Number(e.target.value))}
              className="bg-slate-950 border border-slate-700 text-slate-200 px-2 py-1 rounded text-xs outline-none"
            >
              <option value={5}>5 results</option>
              <option value={10}>10 results</option>
              <option value={20}>20 results</option>
              <option value={50}>50 results</option>
            </select>
          </div>
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin" />
          <p className="text-sm font-medium">Generating query embedding & querying Qdrant vector index...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="bg-red-950/40 border border-red-800/80 rounded-xl p-6 text-red-200 flex items-start gap-4">
          <AlertCircle className="w-6 h-6 text-red-400 shrink-0 mt-0.5" />
          <div className="space-y-2">
            <h4 className="font-semibold text-red-100">Search Request Error</h4>
            <p className="text-xs text-red-300 font-mono">{error}</p>
            <button
              onClick={() => handleSearch()}
              className="mt-2 px-3 py-1.5 bg-red-900 hover:bg-red-800 text-red-100 text-xs font-semibold rounded transition border border-red-700"
            >
              Retry Search
            </button>
          </div>
        </div>
      )}

      {/* Results View */}
      {!loading && !error && searchData && (
        <div className="space-y-4">
          <div className="flex items-center justify-between px-1">
            <p className="text-xs text-slate-400 font-mono">
              Found <span className="text-indigo-400 font-bold">{searchData.total}</span> vector search match
              {searchData.total === 1 ? '' : 'es'} for query: <span className="text-slate-200">"{searchData.query}"</span>
            </p>
          </div>

          {searchData.results.length === 0 ? (
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
              <Database className="w-10 h-10 text-slate-600" />
              <h4 className="font-semibold text-slate-200 text-base">No Matching Products Found</h4>
              <p className="text-xs max-w-md text-slate-400">
                No vector search matches were retrieved. Ensure products are processed and indexed in Qdrant.
              </p>
            </div>
          ) : (
            <div className="space-y-4">
              {searchData.results.map((item) => {
                const simPct = Math.round(item.similarity_score * 100);

                return (
                  <div
                    key={item.product_id}
                    className="bg-slate-900 border border-slate-800 hover:border-indigo-500/50 rounded-xl p-6 shadow-xl transition space-y-4 group"
                  >
                    {/* Top Row: Title, SKU, Similarity Score */}
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800 font-mono">
                            {item.manufacturer}
                          </span>
                          <span className="text-xs text-slate-400 font-mono">SKU: {item.sku}</span>
                          <span className="text-xs text-slate-400 font-mono">Category: {item.category}</span>
                        </div>
                        <h3 className="text-xl font-bold text-white mt-1 group-hover:text-indigo-300 transition">
                          {item.product_name}
                        </h3>
                      </div>

                      <div className="text-right shrink-0">
                        <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-950 text-emerald-300 border border-emerald-800 rounded-full text-xs font-bold font-mono">
                          <Sparkles className="w-3.5 h-3.5 text-emerald-400" />
                          <span>Similarity: {simPct}%</span>
                        </div>
                        <div className="text-[11px] text-slate-400 font-mono mt-1">
                          Quality: <span className="text-emerald-400 font-bold">{item.quality_score}/100</span>
                        </div>
                      </div>
                    </div>

                    {/* Commerce Description */}
                    {item.commerce_description && (
                      <p className="text-xs text-slate-300 leading-relaxed bg-slate-950/60 p-3 rounded-lg border border-slate-800 font-sans">
                        {item.commerce_description}
                      </p>
                    )}

                    {/* Technical Specifications Preview */}
                    {item.attributes.length > 0 && (
                      <div className="space-y-1.5">
                        <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider font-mono">
                          Technical Specifications Preview
                        </span>
                        <div className="flex flex-wrap gap-2">
                          {item.attributes.slice(0, 6).map((attr, idx) => (
                            <span
                              key={idx}
                              className="px-2.5 py-1 bg-slate-950 border border-slate-800 text-slate-200 text-xs rounded font-mono flex items-center gap-1"
                            >
                              <span className="text-slate-400">{attr.display_name}:</span>
                              <span className="text-emerald-400 font-semibold">{attr.raw_value}</span>
                              {attr.unit && <span className="text-slate-400">{attr.unit}</span>}
                            </span>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Footer / Action */}
                    <div className="pt-3 border-t border-slate-800/80 flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        {item.status === 'verified' ? (
                          <span className="text-[11px] text-emerald-400 flex items-center gap-1 font-mono">
                            <CheckCircle2 className="w-3.5 h-3.5" /> Verified Catalog Record
                          </span>
                        ) : (
                          <span className="text-[11px] text-amber-400 flex items-center gap-1 font-mono">
                            <ShieldAlert className="w-3.5 h-3.5" /> Needs Review
                          </span>
                        )}
                      </div>

                      <button
                        onClick={() => navigate(`/catalog?product_id=${item.product_id}`)}
                        className="px-4 py-2 bg-slate-800 hover:bg-indigo-600 text-slate-200 hover:text-white text-xs font-semibold rounded-lg border border-slate-700 transition flex items-center gap-1.5 shadow-sm"
                      >
                        <span>View Product Intelligence</span>
                        <ExternalLink className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
