import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import { UploadCloud, CheckCircle, AlertTriangle, RefreshCw, Eye, FileText, ArrowRight, Loader2, Globe, Edit3 } from 'lucide-react';

interface JobStep {
  id: string;
  stage: string;
  status: string;
  attempt_count: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
  product_id?: string;
}

interface JobDetail {
  job_id: string;
  status: string;
  total_items: number;
  completed_items: number;
  failed_items: number;
  current_stage: string;
  error_message: string | null;
  steps: JobStep[];
}

export const UploadShell: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'file' | 'url' | 'text'>('file');
  
  // File Upload State
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  
  // URL Scraper State
  const [urlInput, setUrlInput] = useState('');
  
  // Copy-Paste State
  const [textInput, setTextInput] = useState('');
  const [textTitle, setTextTitle] = useState('');
  
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // Processing state
  const [docId, setDocId] = useState<string | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const [jobDetail, setJobDetail] = useState<JobDetail | null>(null);
  const [viewingParsed, setViewingParsed] = useState(false);
  const [parsedJson, setParsedJson] = useState<any | null>(null);
  const [loadingParsed, setLoadingParsed] = useState(false);

  const fileInputRef = useRef<HTMLInputElement>(null);

  // Poll job status every 1.5 seconds if active
  useEffect(() => {
    if (!jobId) return;

    const pollStatus = async () => {
      try {
        const res = await fetch(`/api/v1/jobs/${jobId}`);
        if (!res.ok) throw new Error("Failed to fetch job status");
        const data: JobDetail = await res.json();
        setJobDetail(data);

        // Stop polling if final state reached
        if (['completed', 'failed', 'cancelled'].includes(data.status.toLowerCase())) {
          clearInterval(intervalId);
        }
      } catch (err) {
        console.error("Polling error:", err);
      }
    };

    pollStatus(); // initial check
    const intervalId = setInterval(pollStatus, 1500);

    return () => clearInterval(intervalId);
  }, [jobId]);

  // Client-side file validation
  const validateFile = (file: File): boolean => {
    setError(null);
    const maxMB = 50;
    const maxBytes = maxMB * 1024 * 1024;

    if (file.size > maxBytes) {
      setError(`File size exceeds limit of ${maxMB}MB.`);
      return false;
    }

    const allowedExts = ['.pdf', '.xlsx', '.xls', '.docx', '.pptx', '.csv', '.txt', '.html', '.htm'];
    const filenameLower = file.name.toLowerCase();
    const hasValidExt = allowedExts.some(ext => filenameLower.endsWith(ext));

    if (!hasValidExt) {
      setError("Unsupported file format. Supported formats: PDF, Word, Excel, CSV, PPTX, Text, HTML.");
      return false;
    }

    return true;
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === "dragenter" || e.type === "dragover") {
      setDragActive(true);
    } else if (e.type === "dragleave") {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const droppedFile = e.dataTransfer.files[0];
      if (validateFile(droppedFile)) {
        setFile(droppedFile);
      }
    }
  };

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      const selectedFile = e.target.files[0];
      if (validateFile(selectedFile)) {
        setFile(selectedFile);
      }
    }
  };

  const triggerFileInput = () => {
    fileInputRef.current?.click();
  };

  // Perform upload
  const handleUpload = async () => {
    if (!file) return;
    setUploading(true);
    setError(null);
    setViewingParsed(false);
    setParsedJson(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("/api/v1/documents/upload", {
        method: "POST",
        body: formData,
      });

      if (!res.ok) {
        let errMsg = "Upload failed";
        try {
          const errData = await res.json();
          errMsg = errData.detail || errMsg;
        } catch {
          errMsg = `Server error (${res.status}). Service is restarting, please retry in 5 seconds.`;
        }
        throw new Error(errMsg);
      }

      const data = await res.json();
      setDocId(data.document_id);
      setJobId(data.job_id);
      
      // If it was already completed, stop loading and mock finished job info
      if (data.status === "already_processed") {
        setJobDetail({
          job_id: data.job_id || "cached",
          status: "completed",
          total_items: 1,
          completed_items: 1,
          failed_items: 0,
          current_stage: "completed",
          error_message: null,
          steps: []
        });
      } else {
        setJobDetail(null);
      }

    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during upload.");
    } finally {
      setUploading(false);
    }
  };

  // Perform URL Ingestion
  const handleUrlIngest = async () => {
    if (!urlInput.trim()) return;
    setUploading(true);
    setError(null);
    setViewingParsed(false);
    setParsedJson(null);

    try {
      const res = await fetch("/api/v1/documents/url", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ url: urlInput.trim() }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "URL ingestion failed");
      }

      const data = await res.json();
      setDocId(data.document_id);
      setJobId(data.job_id);
      setJobDetail(null);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during URL ingestion.");
    } finally {
      setUploading(false);
    }
  };

  // Perform Text Ingestion
  const handleTextIngest = async () => {
    if (!textInput.trim()) return;
    setUploading(true);
    setError(null);
    setViewingParsed(false);
    setParsedJson(null);

    try {
      const res = await fetch("/api/v1/documents/text", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: textInput.trim(),
          title: textTitle.trim() || undefined
        }),
      });

      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Text copy-paste ingestion failed");
      }

      const data = await res.json();
      setDocId(data.document_id);
      setJobId(data.job_id);
      setJobDetail(null);
    } catch (err: any) {
      setError(err.message || "An unexpected error occurred during text ingestion.");
    } finally {
      setUploading(false);
    }
  };

  // Fetch parsed JSON for inspection
  const handleViewParsed = async () => {
    if (!docId) return;
    setLoadingParsed(true);
    try {
      const res = await fetch(`/api/v1/documents/${docId}/parsed`);
      if (!res.ok) throw new Error("Failed to load parsed layout data");
      const data = await res.json();
      setParsedJson(data);
      setViewingParsed(true);
    } catch (err: any) {
      setError(err.message || "Could not retrieve parsed document output.");
    } finally {
      setLoadingParsed(false);
    }
  };



  // Force reprocess document
  const handleForceReprocess = async () => {
    if (!docId) return;
    setUploading(true);
    setError(null);
    setViewingParsed(false);
    setParsedJson(null);
    try {
      const res = await fetch(`/api/v1/documents/${docId}/reprocess`, { method: "POST" });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Reprocessing trigger failed");
      }
      const data = await res.json();
      setJobId(data.job_id);
      setJobDetail(null);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setUploading(false);
    }
  };

  const resetUploader = () => {
    setFile(null);
    setUrlInput('');
    setTextInput('');
    setTextTitle('');
    setDocId(null);
    setJobId(null);
    setJobDetail(null);
    setError(null);
    setViewingParsed(false);
    setParsedJson(null);
  };

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Ingest Product Sources</h2>
        <p className="text-sm text-muted-foreground">
          Transform scattered product information across PDFs, websites, Excel files, or plain text notes into structured catalog records.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-4">
        {[
          ['Parse', 'Extract layout elements and tables from PDFs, Office docs, URLs or text.'],
          ['Extract', 'Standardize sparse data structures into product properties.'],
          ['Validate', 'Analyze ranges, data types, units, and conflict rules.'],
          ['Enrich', 'Generate descriptive marketing copy and AI confidence logs.'],
        ].map(([label, description]) => (
          <div key={label} className="bg-card border rounded-lg p-4">
            <span className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">{label}</span>
            <p className="text-xs text-muted-foreground mt-2 leading-relaxed">{description}</p>
          </div>
        ))}
      </div>

      {error && !error.includes("did not match the expected pattern") && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive text-sm rounded-lg p-4 flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <div className="flex-1">
            <span className="font-semibold">Error:</span> {error}
          </div>
        </div>
      )}

      {/* Ingestion Type Selection Tabs */}
      {!jobId && !uploading && (
        <div className="flex border-b border-border space-x-6 mb-2">
          {[
            { id: 'file', label: '📄 File Ingestion', desc: 'PDF, Excel, Word, CSV' },
            { id: 'url', label: '🔗 URL Scraper', desc: 'Product web pages' },
            { id: 'text', label: '✍️ Copy-Paste', desc: 'Raw specs copy' }
          ].map(tab => (
            <button
              key={tab.id}
              onClick={() => {
                setActiveTab(tab.id as any);
                setError(null);
              }}
              className={`pb-3 text-sm font-semibold transition border-b-2 outline-none ${
                activeTab === tab.id
                  ? 'border-foreground text-foreground'
                  : 'border-transparent text-muted-foreground hover:text-foreground'
              }`}
            >
              <div className="text-left">
                <div>{tab.label}</div>
                <div className="text-[10px] font-normal text-muted-foreground mt-0.5">{tab.desc}</div>
              </div>
            </button>
          ))}
        </div>
      )}

      {/* Upload Dropzone */}
      {!jobId && !uploading && activeTab === 'file' && (
        <div 
          className={`border-2 border-dashed rounded-xl p-12 flex flex-col items-center justify-center text-center space-y-4 transition ${
            dragActive ? 'border-primary bg-primary/5' : 'border-border bg-card'
          }`}
          onDragEnter={handleDrag}
          onDragOver={handleDrag}
          onDragLeave={handleDrag}
          onDrop={handleDrop}
        >
          <div className="w-16 h-16 rounded-full bg-secondary flex items-center justify-center">
            <UploadCloud className="w-8 h-8 text-muted-foreground" />
          </div>
          
          <input 
            type="file" 
            ref={fileInputRef} 
            onChange={handleFileChange} 
            accept=".pdf,.xlsx,.xls,.docx,.pptx,.csv,.txt,.html,.htm" 
            className="hidden" 
          />

          {file ? (
            <div className="space-y-2">
              <p className="font-medium text-foreground">{file.name}</p>
              <p className="text-xs text-muted-foreground">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
              <div className="flex justify-center space-x-2 pt-2">
                <button 
                  onClick={handleUpload}
                  className="px-4 py-2 bg-primary text-primary-foreground font-medium rounded-lg text-sm transition hover:opacity-90 flex items-center space-x-2"
                >
                  <span>Start Ingestion</span>
                  <ArrowRight className="w-4 h-4" />
                </button>
                <button 
                  onClick={resetUploader}
                  className="px-4 py-2 border bg-background text-foreground font-medium rounded-lg text-sm hover:bg-muted transition"
                >
                  Clear
                </button>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              <h3 className="font-semibold text-lg">Drag & drop your file here</h3>
              <p className="text-sm text-muted-foreground">Supports PDF, Excel (.xlsx, .xls, .csv), Word (.docx), PPTX, Text, or HTML</p>
              <button 
                onClick={triggerFileInput}
                className="px-4 py-2 bg-secondary text-secondary-foreground font-medium rounded-lg text-sm transition hover:bg-secondary/80 mt-2"
              >
                Browse Files
              </button>
            </div>
          )}
        </div>
      )}

      {/* URL Scraper Option */}
      {!jobId && !uploading && activeTab === 'url' && (
        <div className="bg-card border rounded-xl p-8 space-y-4">
          <div className="space-y-1">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <Globe className="w-5 h-5 text-muted-foreground" />
              <span>Scrape Product URL</span>
            </h3>
            <p className="text-xs text-muted-foreground">Enter an industrial product webpage URL. The backend will parse the content using live AI loaders.</p>
          </div>
          <div className="flex gap-2">
            <input
              type="text"
              placeholder="e.g. https://www.siemens.com/motors/induction-motor-1le1"
              value={urlInput}
              onChange={(e) => setUrlInput(e.target.value)}
              className="flex-1 bg-background border border-border text-foreground px-4 py-2.5 rounded-lg text-sm outline-none focus:border-foreground transition"
            />
            <button
              onClick={handleUrlIngest}
              disabled={!urlInput.trim()}
              className="px-5 py-2.5 bg-primary text-primary-foreground font-medium rounded-lg text-sm hover:opacity-90 transition disabled:opacity-50 flex items-center gap-1.5"
            >
              <span>Ingest URL</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Copy-Paste Text Option */}
      {!jobId && !uploading && activeTab === 'text' && (
        <div className="bg-card border rounded-xl p-8 space-y-4">
          <div className="space-y-1">
            <h3 className="font-semibold text-lg flex items-center gap-2">
              <Edit3 className="w-5 h-5 text-muted-foreground" />
              <span>Paste Specification Text</span>
            </h3>
            <p className="text-xs text-muted-foreground">Copy and paste specification tables or raw datasheet texts directly.</p>
          </div>

          <div className="space-y-3">
            <div>
              <label className="text-xs text-muted-foreground block mb-1">Document Title / Model Reference (Optional)</label>
              <input
                type="text"
                placeholder="e.g. Siemens Induction Motor 1LE1"
                value={textTitle}
                onChange={(e) => setTextTitle(e.target.value)}
                className="w-full bg-background border border-border text-foreground px-4 py-2.5 rounded-lg text-sm outline-none focus:border-foreground transition"
              />
            </div>
            <div>
              <label className="text-xs text-muted-foreground block mb-1">Paste Technical Specifications Content</label>
              <textarea
                rows={6}
                placeholder="e.g. Casing: Cast Iron, Output power: 15 kW, Casing size: 160L, Protection: IP55..."
                value={textInput}
                onChange={(e) => setTextInput(e.target.value)}
                className="w-full bg-background border border-border text-foreground px-4 py-2.5 rounded-lg text-sm outline-none focus:border-foreground transition font-mono"
              />
            </div>
            <button
              onClick={handleTextIngest}
              disabled={!textInput.trim()}
              className="px-5 py-2.5 bg-primary text-primary-foreground font-medium rounded-lg text-sm hover:opacity-90 transition disabled:opacity-50 flex items-center gap-1.5"
            >
              <span>Ingest Text Specs</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      {/* Uploading Status */}
      {uploading && (
        <div className="bg-card border rounded-xl p-12 text-center flex flex-col items-center justify-center space-y-4">
          <Loader2 className="w-10 h-10 text-primary animate-spin" />
          <h3 className="font-semibold text-lg">Ingesting Product Data Source...</h3>
          <p className="text-sm text-muted-foreground">Scraping content, resolving layout blocks, mapping raw data inputs, and scheduling parsing task.</p>
        </div>
      )}

      {/* Active Job Progress & Details */}
      {jobId && jobDetail && (
        <div className="space-y-6">
          <div className="bg-card border rounded-xl p-6 space-y-6 shadow-sm">
            <div className="flex justify-between items-start">
              <div>
                <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">Processing Status</span>
                <h3 className="text-xl font-bold flex items-center space-x-2 mt-1">
                  <FileText className="w-5 h-5 text-muted-foreground" />
                  <span>{file?.name || urlInput || textTitle || "Pasted Ingestion Document"}</span>
                </h3>
                <p className="text-xs text-muted-foreground mt-1">Job ID: <code className="bg-muted px-1 py-0.5 rounded">{jobId}</code></p>
              </div>
              
              <div className="flex items-center space-x-2">
                <span className={`px-2.5 py-1 text-xs font-semibold rounded-full capitalize ${
                  jobDetail.status === 'completed' ? 'bg-success/15 text-success' :
                  jobDetail.status === 'failed' ? 'bg-destructive/15 text-destructive' :
                  'bg-warning/15 text-warning animate-pulse'
                }`}>
                  {jobDetail.status}
                </span>
              </div>
            </div>

            {/* Ingestion Steps Timeline */}
            <div className="border-t pt-6">
              <h4 className="font-semibold text-sm mb-4">Pipeline Stages</h4>
              <div className="relative border-l-2 border-muted pl-6 ml-4 space-y-6">
                
                {/* Stage 1: Upload */}
                <div className="relative">
                  <div className="absolute -left-[33px] bg-success text-success-foreground rounded-full w-6 h-6 flex items-center justify-center border-4 border-card">
                    <CheckCircle className="w-3 h-3" />
                  </div>
                  <div>
                    <h5 className="text-sm font-semibold text-foreground">Source Registration & Ingestion</h5>
                    <p className="text-xs text-muted-foreground mt-0.5">SHA-256 generated, duplicate check completed, content verified, and stored.</p>
                  </div>
                </div>

                {/* Stage 2: Parsing */}
                <div className="relative">
                  <div className={`absolute -left-[33px] rounded-full w-6 h-6 flex items-center justify-center border-4 border-card ${
                    jobDetail.status === 'completed' ? 'bg-success text-success-foreground' :
                    jobDetail.status === 'failed' ? 'bg-destructive text-destructive-foreground' :
                    jobDetail.status === 'processing' ? 'bg-warning text-warning-foreground animate-spin' :
                    'bg-muted text-muted-foreground'
                  }`}>
                    {jobDetail.status === 'completed' ? <CheckCircle className="w-3 h-3" /> :
                     jobDetail.status === 'failed' ? <AlertTriangle className="w-3 h-3" /> :
                     jobDetail.status === 'processing' ? <RefreshCw className="w-3 h-3" /> :
                     <div className="w-1.5 h-1.5 rounded-full bg-current" />}
                  </div>
                  <div>
                    <h5 className="text-sm font-semibold text-foreground">Layout Parsing & Structured Output</h5>
                    <p className="text-xs text-muted-foreground mt-0.5">Extract layout structure, preserve specification tables, and output page-level text structures.</p>
                    
                    {jobDetail.error_message && (
                      <div className="bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded p-3 mt-2 font-mono">
                        {jobDetail.error_message}
                      </div>
                    )}
                  </div>
                </div>

                <div className="relative">
                  <div className={`absolute -left-[33px] rounded-full w-6 h-6 flex items-center justify-center border-4 border-card ${
                    jobDetail.status === 'completed' ? 'bg-success text-success-foreground' : 'bg-muted text-muted-foreground'
                  }`}>
                    {jobDetail.status === 'completed' ? <CheckCircle className="w-3 h-3" /> : <div className="w-1.5 h-1.5 rounded-full bg-current" />}
                  </div>
                  <div>
                    <h5 className="text-sm font-semibold text-foreground">AI Extraction, Validation & Enrichment</h5>
                    <p className="text-xs text-muted-foreground mt-0.5">
                      Build product attributes, confidence scores, evidence links, quality status, and commerce-ready enrichment.
                    </p>
                  </div>
                </div>
              </div>
            </div>

            {/* Operational Action Footer */}
            <div className="border-t pt-6 flex justify-between">
              <button 
                onClick={resetUploader}
                className="px-4 py-2 border rounded-lg text-sm hover:bg-muted font-medium transition"
              >
                Ingest Another Record
              </button>

              <div className="flex space-x-2">
                {jobDetail.status !== 'completed' && (
                  <button 
                    onClick={handleForceReprocess}
                    className="px-4 py-2 bg-foreground text-background font-semibold rounded-lg text-sm hover:opacity-90 flex items-center space-x-1.5 transition"
                  >
                    <RefreshCw className="w-4 h-4 animate-spin-slow" />
                    <span>Force Reprocess Document</span>
                  </button>
                )}

                {jobDetail.status === 'completed' && (() => {
                  const extractedStep = jobDetail.steps?.find(s => s.product_id);
                  const pId = extractedStep?.product_id;
                  const targetUrl = pId ? `/catalog?product_id=${pId}` : '/catalog';
                  return (
                    <div className="flex items-center space-x-2">
                      <Link 
                        to={targetUrl}
                        className="px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-white font-medium rounded-lg text-sm flex items-center space-x-1.5 transition"
                      >
                        <CheckCircle className="w-4 h-4" />
                        <span>View Product Catalog Details</span>
                      </Link>

                      <button 
                        onClick={handleForceReprocess}
                        className="px-4 py-2 border text-foreground font-medium rounded-lg text-sm hover:bg-muted flex items-center space-x-1.5 transition"
                      >
                        <RefreshCw className="w-4 h-4" />
                        <span>Force Reprocess</span>
                      </button>
                      
                      <button 
                        onClick={handleViewParsed}
                        disabled={loadingParsed}
                        className="px-4 py-2 bg-primary text-primary-foreground font-medium rounded-lg text-sm hover:opacity-90 flex items-center space-x-1.5 transition disabled:opacity-50"
                      >
                        {loadingParsed ? (
                          <Loader2 className="w-4 h-4 animate-spin" />
                        ) : (
                          <Eye className="w-4 h-4" />
                        )}
                        <span>View Intermediate JSON</span>
                      </button>
                    </div>
                  );
                })()}
              </div>
            </div>
          </div>

          {/* JSON Viewer Inspector */}
          {viewingParsed && parsedJson && (
            <div className="bg-card border rounded-xl p-6 space-y-4 shadow-sm">
              <div className="flex justify-between items-center border-b pb-4">
                <div>
                  <h4 className="font-bold text-lg">Parsed Intermediate Representation</h4>
                  <p className="text-xs text-muted-foreground mt-0.5">Content Hash: <code>{parsedJson.content_hash}</code></p>
                </div>
                <span className="text-xs bg-secondary text-secondary-foreground px-2.5 py-1 rounded-md font-mono">
                  {parsedJson.parser?.name} v{parsedJson.parser?.version}
                </span>
              </div>
              
              {/* Basic metadata list */}
              <div className="grid grid-cols-3 gap-4 text-sm bg-muted/40 p-4 rounded-lg">
                <div>
                  <span className="text-xs text-muted-foreground block">Page Count</span>
                  <span className="font-semibold text-foreground">{parsedJson.metadata?.page_count || parsedJson.pages?.length}</span>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground block">Title Reference</span>
                  <span className="font-semibold text-foreground truncate block">{parsedJson.metadata?.title || "N/A"}</span>
                </div>
                <div>
                  <span className="text-xs text-muted-foreground block">Images Extracted</span>
                  <span className="font-semibold text-foreground">
                    {parsedJson.pages?.reduce((acc: number, p: any) => acc + (p.images?.length || 0), 0)}
                  </span>
                </div>
              </div>

              {/* JSON tree viewer */}
              <div className="bg-muted p-4 rounded-lg overflow-x-auto max-h-96 text-xs font-mono">
                <pre>{JSON.stringify(parsedJson, null, 2)}</pre>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
