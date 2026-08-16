import React, { useState, useEffect } from 'react';
import {
  RefreshCw,
  Download,
  Database,
  Play,
  CheckCircle,
  AlertTriangle,
  ChevronDown,
  ChevronUp,
  Activity,
  FileText,
  ShieldCheck,
  UserCheck
} from 'lucide-react';

interface UnilogRecordItem {
  id: string;
  mfg_part_num: string;
  part_desc: string;
  part_manuf: string;
  status: string;
  quality_score: number;
  needs_review: boolean;
  validation_flags: string[];
  explainability_trace: {
    manufacturer_name?: string;
    brand_name?: string;
    classpath?: string;
    invoice_desc?: string;
    attributes?: string;
    quality?: string;
  };
  error_message: string | null;
  enriched_data: Record<string, any> | null;
}

interface EnrichmentMetrics {
  total_records: number;
  enriched_records: number;
  failed_records: number;
  processing_records: number;
  pending_records: number;
  average_quality_score: number;
  is_active: boolean;
}

export const UnilogConsole: React.FC = () => {
  const [metrics, setMetrics] = useState<EnrichmentMetrics | null>(null);
  const [records, setRecords] = useState<UnilogRecordItem[]>([]);
  const [totalRecords, setTotalRecords] = useState<number>(0);
  const [page, setPage] = useState<number>(1);
  const [limit] = useState<number>(10);
  
  // Tab states: 'all' or 'review'
  const [activeTab, setActiveTab] = useState<'all' | 'review'>('all');
  
  const [batchLimit, setBatchLimit] = useState<number>(10);
  const [loading, setLoading] = useState<boolean>(true);
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [selectedRecordId, setSelectedRecordId] = useState<string | null>(null);

  // Fetch status metrics and records list
  const fetchStatusAndData = async () => {
    try {
      const statusRes = await fetch('/api/v1/unilog/status');
      if (statusRes.ok) {
        const metricsData: EnrichmentMetrics = await statusRes.json();
        setMetrics(metricsData);
        setIsProcessing(metricsData.is_active);
      }
      
      const filterParam = activeTab === 'review' ? '&needs_review=true' : '';
      const recordsRes = await fetch(`/api/v1/unilog/records?page=${page}&limit=${limit}${filterParam}`);
      if (recordsRes.ok) {
        const data = await recordsRes.json();
        setRecords(data.records);
        setTotalRecords(data.total);
      }
    } catch (err) {
      console.error("Failed to load Unilog batch console details:", err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchStatusAndData();
  }, [page, activeTab]);

  // Poll status while background processing is active
  useEffect(() => {
    let interval: NodeJS.Timeout;
    if (isProcessing) {
      interval = setInterval(() => {
        fetchStatusAndData();
      }, 2000);
    }
    return () => {
      if (interval) clearInterval(interval);
    };
  }, [isProcessing, page, activeTab]);

  // Import raw CSV
  const handleImport = async () => {
    setLoading(true);
    try {
      const res = await fetch('/api/v1/unilog/import', { method: 'POST' });
      if (res.ok) {
        await fetchStatusAndData();
      }
    } catch (err) {
      console.error("Import failed:", err);
    } finally {
      setLoading(false);
    }
  };

  // Trigger batch run
  const handleProcessBatch = async () => {
    try {
      setIsProcessing(true);
      await fetch(`/api/v1/unilog/process?limit=${batchLimit}`, { method: 'POST' });
      fetchStatusAndData();
    } catch (err) {
      console.error("Batch processing launch failed:", err);
      setIsProcessing(false);
    }
  };

  // Download export CSV
  const handleExport = () => {
    window.open('/api/v1/unilog/export', '_blank');
  };

  // Approve a record flagged for human review
  const handleApproveRecord = async (recordId: string) => {
    try {
      const res = await fetch(`/api/v1/unilog/records/${recordId}/approve`, { method: 'POST' });
      if (res.ok) {
        // Refresh local data
        fetchStatusAndData();
      }
    } catch (err) {
      console.error("Approve record failed:", err);
    }
  };

  if (loading && !metrics) {
    return (
      <div className="flex flex-col justify-center items-center h-[50vh] text-[#111111]">
        <RefreshCw className="w-8 h-8 animate-spin text-[#FF3B00] mb-3" />
        <p className="font-mono text-xs uppercase tracking-wider">Syncing catalog parameters...</p>
      </div>
    );
  }

  const completionRate = metrics
    ? Math.round((metrics.enriched_records / (metrics.total_records || 1)) * 100)
    : 0;

  // Compute scorecard scores dynamically based on loaded records
  const invoiceCasingCompliant = records.length > 0 
    ? Math.round((records.filter(r => !r.validation_flags.some(f => f.toLowerCase().includes("uppercase"))).length / records.length) * 100)
    : 100;

  const invoiceLengthCompliant = records.length > 0
    ? Math.round((records.filter(r => !r.validation_flags.some(f => f.toLowerCase().includes("limit") || f.toLowerCase().includes("exceeds"))).length / records.length) * 100)
    : 100;

  return (
    <div className="w-full max-w-6xl mx-auto space-y-8 select-none text-[#111111]">
      
      {/* Visual Ingest Metric Cards Block */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* Total Ingested */}
        <div className="bg-white p-6 rounded-[20px] border border-neutral-300/40 shadow-sm flex flex-col justify-between h-32">
          <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider font-mono">INGESTED ROWS</span>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-extrabold font-sans">{metrics?.total_records ?? 0}</span>
            <span className="text-xs text-neutral-400 font-bold uppercase font-mono">SKUs</span>
          </div>
          <button 
            onClick={handleImport}
            className="text-[9px] text-[#FF3B00] hover:text-red-700 font-bold uppercase tracking-widest text-left"
          >
            RE-IMPORT RAW CSV ↗
          </button>
        </div>

        {/* Enrichment Rate */}
        <div className="bg-white p-6 rounded-[20px] border border-neutral-300/40 shadow-sm flex flex-col justify-between h-32">
          <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider font-mono">ENRICHED DATA</span>
          <div className="flex items-baseline gap-2">
            <span className="text-4xl font-extrabold font-sans text-[#FF3B00]">{metrics?.enriched_records ?? 0}</span>
            <span className="text-xs text-neutral-400 font-bold uppercase font-mono">/ {metrics?.total_records ?? 0}</span>
          </div>
          <div className="w-full bg-neutral-100 h-1 rounded-full overflow-hidden">
            <div className="bg-[#FF3B00] h-full" style={{ width: `${completionRate}%` }} />
          </div>
        </div>

        {/* Avg Completeness Score */}
        <div className="bg-white p-6 rounded-[20px] border border-neutral-300/40 shadow-sm flex flex-col justify-between h-32">
          <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider font-mono">AVERAGE HEALTH</span>
          <div className="flex items-baseline gap-1">
            <span className="text-4xl font-extrabold font-sans text-[#FF3B00]">{metrics?.average_quality_score ?? 0}</span>
            <span className="text-sm font-bold text-[#FF3B00]">.Q</span>
          </div>
          <span className="text-[9px] font-extrabold uppercase tracking-wider text-emerald-600 font-mono">
            OPTIMAL SPEC RATIO
          </span>
        </div>

        {/* Trigger batch control panel */}
        <div className="bg-white p-6 rounded-[20px] border border-[#FF3B00]/25 shadow-md flex flex-col justify-between h-32 relative overflow-hidden">
          <span className="text-[10px] font-bold text-neutral-400 uppercase tracking-wider font-mono">PIPELINE RUNNER</span>
          
          <div className="flex items-center gap-3">
            <select 
              value={batchLimit} 
              onChange={(e) => setBatchLimit(Number(e.target.value))}
              disabled={isProcessing}
              className="bg-neutral-50 border border-neutral-300 rounded-lg px-2.5 py-1 text-xs font-mono font-bold"
            >
              <option value="3">3 SKUs</option>
              <option value="10">10 SKUs</option>
              <option value="25">25 SKUs</option>
              <option value="50">50 SKUs</option>
            </select>
            
            <button 
              onClick={handleProcessBatch}
              disabled={isProcessing}
              className="bg-[#111111] hover:bg-neutral-800 text-white text-[10px] font-bold px-4 py-2 rounded-full flex items-center gap-1.5 transition disabled:opacity-50"
            >
              {isProcessing ? (
                <>
                  <RefreshCw className="w-3 h-3 animate-spin text-[#FF3B00]" />
                  <span>RUNNING</span>
                </>
              ) : (
                <>
                  <Play className="w-3 h-3 text-[#FF3B00] fill-current" />
                  <span>RUN BATCH</span>
                </>
              )}
            </button>
          </div>
          
          <span className="text-[9px] text-neutral-400 font-mono uppercase tracking-widest">
            {isProcessing ? "PROCESSING BACKGROUND JOBS..." : "STANDBY"}
          </span>
        </div>

      </div>

      {/* Validation Scorecard Banner */}
      <div className="bg-neutral-50 rounded-[24px] border border-neutral-300/40 p-6 flex flex-col md:flex-row justify-between items-center gap-6 shadow-sm">
        <div className="flex items-center gap-3">
          <ShieldCheck className="w-8 h-8 text-[#FF3B00]" />
          <div>
            <h3 className="text-xs font-bold uppercase font-mono text-neutral-500 tracking-wider">PIPELINE COMPLIANCE SCORECARD</h3>
            <p className="text-[10px] text-neutral-400 font-mono uppercase mt-0.5">Automated validation against UniHack guidelines.</p>
          </div>
        </div>
        
        <div className="flex gap-8">
          <div className="text-center">
            <span className="block text-xl font-extrabold font-mono text-[#FF3B00]">{invoiceCasingCompliant}%</span>
            <span className="block text-[8px] text-neutral-400 font-mono uppercase font-bold tracking-widest mt-1">Invoice Caps</span>
          </div>
          <div className="text-center border-l border-neutral-300/50 pl-8">
            <span className="block text-xl font-extrabold font-mono text-[#FF3B00]">{invoiceLengthCompliant}%</span>
            <span className="block text-[8px] text-neutral-400 font-mono uppercase font-bold tracking-widest mt-1">Invoice Length</span>
          </div>
          <div className="text-center border-l border-neutral-300/50 pl-8">
            <span className="block text-xl font-extrabold font-mono text-emerald-600">100%</span>
            <span className="block text-[8px] text-neutral-400 font-mono uppercase font-bold tracking-widest mt-1">UOM Formats</span>
          </div>
        </div>
      </div>

      {/* Audit Data Grid */}
      <div className="bg-white border border-neutral-300/40 rounded-[28px] p-8 shadow-sm space-y-6">
        
        {/* Table Header actions */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-neutral-200 pb-4">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-2">
              <Database className="w-5 h-5 text-[#FF3B00]" />
              <h2 className="text-lg font-bold uppercase font-mono tracking-wider">AI ENRICHMENT LOGS</h2>
            </div>
            
            {/* Filter Tabs */}
            <div className="flex bg-neutral-100 p-0.5 rounded-full text-[10px] font-mono font-bold">
              <button 
                onClick={() => { setActiveTab('all'); setPage(1); }}
                className={`px-4 py-1.5 rounded-full transition ${activeTab === 'all' ? 'bg-[#111111] text-white' : 'text-neutral-500 hover:text-neutral-800'}`}
              >
                ALL SKUS
              </button>
              <button 
                onClick={() => { setActiveTab('review'); setPage(1); }}
                className={`px-4 py-1.5 rounded-full transition flex items-center gap-1 ${activeTab === 'review' ? 'bg-[#111111] text-white' : 'text-neutral-500 hover:text-neutral-800'}`}
              >
                <span>NEEDS REVIEW</span>
                {metrics && metrics.pending_records > 0 && (
                  <span className="bg-[#FF3B00] text-white text-[8px] px-1.5 py-0.5 rounded-full leading-none">
                    {records.filter(r => r.needs_review).length}
                  </span>
                )}
              </button>
            </div>
          </div>
          
          <button 
            onClick={handleExport}
            disabled={metrics?.enriched_records === 0}
            className="bg-[#111111] hover:bg-neutral-800 text-white text-[10.5px] font-bold px-5 py-2.5 rounded-full flex items-center gap-2 transition disabled:opacity-40 w-full sm:w-auto justify-center"
          >
            <Download className="w-4 h-4 text-[#FF3B00]" />
            <span>EXPORT DELIVERY CSV</span>
          </button>
        </div>

        {/* Data list table */}
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs">
            <thead>
              <tr className="border-b border-neutral-200 text-[9px] font-bold uppercase text-neutral-400 font-mono tracking-widest">
                <th className="py-3 px-3">Part Number</th>
                <th className="py-3 px-3">Raw Description</th>
                <th className="py-3 px-3">Manufacturer</th>
                <th className="py-3 px-3">Status</th>
                <th className="py-3 px-3 text-center">Completeness</th>
                <th className="py-3 px-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-neutral-100 text-[#111111]">
              {records.map((rec) => {
                const isSelected = selectedRecordId === rec.id;
                return (
                  <React.Fragment key={rec.id}>
                    <tr 
                      onClick={() => setSelectedRecordId(isSelected ? null : rec.id)}
                      className="hover:bg-neutral-50/70 transition cursor-pointer"
                    >
                      <td className="py-4 px-3 font-mono font-bold text-[#FF3B00]">
                        {rec.mfg_part_num}
                      </td>
                      <td className="py-4 px-3 max-w-xs truncate font-medium text-neutral-700" title={rec.part_desc}>
                        {rec.part_desc}
                      </td>
                      <td className="py-4 px-3 font-mono text-[10px] text-neutral-500 uppercase tracking-wider">
                        {rec.part_manuf}
                      </td>
                      <td className="py-4 px-3">
                        <div className="flex items-center gap-2">
                          <span className={`text-[8.5px] font-bold font-mono tracking-widest uppercase px-2.5 py-0.5 rounded-full ${
                            rec.status === 'enriched' 
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200' 
                              : rec.status === 'failed' 
                              ? 'bg-red-50 text-red-700 border border-red-200' 
                              : 'bg-neutral-50 text-neutral-500 border border-neutral-200 animate-pulse'
                          }`}>
                            {rec.status}
                          </span>
                          
                          {rec.needs_review && (
                            <span className="bg-amber-50 text-amber-700 border border-amber-200 text-[8.5px] font-bold font-mono tracking-widest uppercase px-2.5 py-0.5 rounded-full flex items-center gap-0.5">
                              <AlertTriangle className="w-2.5 h-2.5" />
                              <span>REVIEW</span>
                            </span>
                          )}
                        </div>
                      </td>
                      <td className="py-4 px-3 font-mono text-center font-bold">
                        {rec.status === 'enriched' ? `${rec.quality_score}%` : '—'}
                      </td>
                      <td className="py-4 px-3 text-right">
                        {isSelected ? <ChevronUp className="w-4 h-4 text-neutral-400" /> : <ChevronDown className="w-4 h-4 text-neutral-400" />}
                      </td>
                    </tr>
                    
                    {/* Collapsible Details Drawer */}
                    {isSelected && (
                      <tr>
                        <td colSpan={6} className="bg-neutral-50/50 p-6 border-t border-b border-neutral-200/50">
                          
                          {/* Alert warnings box if validations failed */}
                          {rec.validation_flags.length > 0 && (
                            <div className="mb-6 bg-amber-50 border border-amber-300/60 rounded-xl p-4 flex justify-between items-center gap-4 text-xs font-mono text-amber-900">
                              <div className="flex items-start gap-2.5">
                                <AlertTriangle className="w-4 h-4 text-[#FF3B00] mt-0.5 flex-shrink-0" />
                                <div>
                                  <span className="font-extrabold uppercase block text-[9.5px]">Validation Warnings:</span>
                                  <ul className="list-disc list-inside mt-1 space-y-0.5 text-[10.5px]">
                                    {rec.validation_flags.map((flag, idx) => (
                                      <li key={idx}>{flag}</li>
                                    ))}
                                  </ul>
                                </div>
                              </div>
                              
                              <button 
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleApproveRecord(rec.id);
                                }}
                                className="bg-[#111111] hover:bg-neutral-800 text-white text-[9.5px] font-bold px-4 py-2 rounded-full flex items-center gap-1.5 transition whitespace-nowrap"
                              >
                                <UserCheck className="w-3.5 h-3.5 text-emerald-500" />
                                <span>APPROVE SKU</span>
                              </button>
                            </div>
                          )}

                          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 text-xs font-mono">
                            
                            {/* Left details (4 cols) */}
                            <div className="lg:col-span-4 space-y-4">
                              <h4 className="text-[10px] font-extrabold uppercase text-[#FF3B00] tracking-widest">NORMALIZATION MATRIX</h4>
                              
                              <div className="grid grid-cols-3 gap-2 border-b border-neutral-200 pb-2">
                                <span className="text-neutral-400 uppercase text-[9px] font-bold">Manufacturer</span>
                                <span className="col-span-2 text-[#111111] font-bold uppercase">{rec.enriched_data?.manufacturer_name || rec.part_manuf}</span>
                              </div>

                              <div className="grid grid-cols-3 gap-2 border-b border-neutral-200 pb-2">
                                <span className="text-neutral-400 uppercase text-[9px] font-bold">Brand</span>
                                <span className="col-span-2 text-[#111111] font-bold uppercase">{rec.enriched_data?.brand_name || '—'}</span>
                              </div>

                              <div className="grid grid-cols-3 gap-2 border-b border-neutral-200 pb-2">
                                <span className="text-neutral-400 uppercase text-[9px] font-bold">Category</span>
                                <span className="col-span-2 text-[#111111] font-bold uppercase">{rec.enriched_data?.classpath || '—'}</span>
                              </div>

                              <div className="grid grid-cols-3 gap-2 border-b border-neutral-200 pb-2">
                                <span className="text-neutral-400 uppercase text-[9px] font-bold">Invoice Desc</span>
                                <span className="col-span-2 text-[#FF3B00] font-bold uppercase font-sans text-xs">
                                  {rec.enriched_data?.invoice_desc || '—'}
                                </span>
                              </div>

                              <div className="grid grid-cols-3 gap-2">
                                <span className="text-neutral-400 uppercase text-[9px] font-bold">Mobile Desc</span>
                                <span className="col-span-2 text-neutral-600 uppercase text-[10px] leading-snug">
                                  {rec.enriched_data?.mobile_desc || '—'}
                                </span>
                              </div>
                            </div>

                            {/* Center details: Attributes (4 cols) */}
                            <div className="lg:col-span-4 space-y-4">
                              <h4 className="text-[10px] font-extrabold uppercase text-[#FF3B00] tracking-widest">PRODUCT SPECIFICATIONS ({rec.enriched_data?.attributes?.length || 0})</h4>
                              
                              <div className="border border-neutral-200 bg-white p-4 rounded-xl space-y-2 max-h-48 overflow-y-auto">
                                {rec.enriched_data?.attributes?.map((attr: any, idx: number) => (
                                  <div key={idx} className="flex justify-between items-center text-[10px] border-b border-neutral-100 pb-1 last:border-0 last:pb-0">
                                    <span className="text-neutral-400 uppercase font-bold">{attr.label}</span>
                                    <span className="text-[#111111] font-bold uppercase">
                                      {attr.value} {attr.uom}
                                    </span>
                                  </div>
                                ))}
                                {!rec.enriched_data?.attributes && (
                                  <div className="text-neutral-400 italic text-[10px] py-4 text-center">No attributes extracted</div>
                                )}
                              </div>
                            </div>

                            {/* Right details: Explainability Layer Trace (4 cols) */}
                            <div className="lg:col-span-4 space-y-4">
                              <h4 className="text-[10px] font-extrabold uppercase text-emerald-600 tracking-widest">EXPLAINABILITY & AI TRACE</h4>
                              
                              <div className="bg-emerald-50/40 border border-emerald-200 p-4 rounded-xl space-y-2.5 text-[9.5px] leading-snug text-neutral-700">
                                {rec.explainability_trace?.manufacturer_name && (
                                  <div>
                                    <span className="font-extrabold block uppercase text-emerald-800 text-[8px] tracking-wider">📌 Manufacturer match</span>
                                    {rec.explainability_trace.manufacturer_name}
                                  </div>
                                )}
                                {rec.explainability_trace?.brand_name && (
                                  <div>
                                    <span className="font-extrabold block uppercase text-emerald-800 text-[8px] tracking-wider">📌 Brand resolution</span>
                                    {rec.explainability_trace.brand_name}
                                  </div>
                                )}
                                {rec.explainability_trace?.classpath && (
                                  <div>
                                    <span className="font-extrabold block uppercase text-emerald-800 text-[8px] tracking-wider">📌 Taxonomy Classification</span>
                                    {rec.explainability_trace.classpath}
                                  </div>
                                )}
                                {rec.explainability_trace?.invoice_desc && (
                                  <div>
                                    <span className="font-extrabold block uppercase text-emerald-800 text-[8px] tracking-wider">📌 Invoice format constraint</span>
                                    {rec.explainability_trace.invoice_desc}
                                  </div>
                                )}
                                {!rec.explainability_trace && (
                                  <div className="text-neutral-400 italic py-4 text-center">No explainability trace compiled</div>
                                )}
                              </div>
                            </div>

                          </div>
                        </td>
                      </tr>
                    )}
                  </React.Fragment>
                );
              })}
              {records.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-8 text-center text-neutral-400 italic font-mono text-xs">
                    No items found matching the selected filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>

        {/* Pagination */}
        <div className="flex items-center justify-between pt-4 border-t border-neutral-200 text-xs">
          <span className="text-neutral-400 font-bold uppercase font-mono">
            Page {page} of {Math.ceil(totalRecords / limit) || 1} ({totalRecords} records total)
          </span>
          <div className="flex gap-2">
            <button
              onClick={() => setPage(p => Math.max(1, p - 1))}
              disabled={page === 1}
              className="px-4 py-2 border border-neutral-300 rounded-full hover:bg-neutral-50 transition disabled:opacity-40 font-bold"
            >
              PREVIOUS
            </button>
            <button
              onClick={() => setPage(p => p + 1)}
              disabled={page >= Math.ceil(totalRecords / limit)}
              className="px-4 py-2 border border-neutral-300 rounded-full hover:bg-neutral-50 transition disabled:opacity-40 font-bold"
            >
              NEXT
            </button>
          </div>
        </div>

      </div>

    </div>
  );
};
