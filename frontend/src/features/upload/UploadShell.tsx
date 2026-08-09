import React, { useState, useEffect, useRef } from 'react';
import { UploadCloud, CheckCircle, AlertTriangle, RefreshCw, Eye, FileText, ArrowRight, Loader2 } from 'lucide-react';

interface JobStep {
  id: string;
  stage: string;
  status: string;
  attempt_count: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
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
  const [dragActive, setDragActive] = useState(false);
  const [file, setFile] = useState<File | null>(null);
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

    if (!file.name.toLowerCase().endsWith('.pdf')) {
      setError("Only PDF files are supported for ingestion in Phase 3.");
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
        const errData = await res.json();
        throw new Error(errData.detail || "Upload failed");
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

  // Trigger retry on failed job
  const handleRetry = async () => {
    if (!jobId) return;
    setError(null);
    try {
      const res = await fetch(`/api/v1/jobs/${jobId}/retry`, { method: "POST" });
      if (!res.ok) {
        const errData = await res.json();
        throw new Error(errData.detail || "Retry trigger failed");
      }
      // Re-trigger polling
      setJobDetail(prev => prev ? { ...prev, status: 'queued' } : null);
    } catch (err: any) {
      setError(err.message);
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
        <h2 className="text-3xl font-bold tracking-tight">Ingest Documents</h2>
        <p className="text-sm text-muted-foreground">Upload industrial PDFs to execute layout parsing and generate normalized intermediate structures.</p>
      </div>

      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive text-sm rounded-lg p-4 flex items-start space-x-3">
          <AlertTriangle className="w-5 h-5 flex-shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="font-semibold">Error:</span> {error}
          </div>
        </div>
      )}

      {/* Upload Dropzone */}
      {!jobId && !uploading && (
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
            accept=".pdf" 
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
              <h3 className="font-semibold text-lg">Drag & drop your PDF here</h3>
              <p className="text-sm text-muted-foreground">Supports engineering datasheets, drawings, or product specs up to 50MB</p>
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

      {/* Uploading Status */}
      {uploading && (
        <div className="bg-card border rounded-xl p-12 text-center flex flex-col items-center justify-center space-y-4">
          <Loader2 className="w-10 h-10 text-primary animate-spin" />
          <h3 className="font-semibold text-lg">Ingesting Document...</h3>
          <p className="text-sm text-muted-foreground">Validating signatures, calculating SHA-256 hash, and uploading original file to store.</p>
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
                  <span>{file?.name || "Catalog Document"}</span>
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
                    <h5 className="text-sm font-semibold text-foreground">File Ingestion & Storage</h5>
                    <p className="text-xs text-muted-foreground mt-0.5">SHA-256 registered, PDF signature verified, original stored in bucket.</p>
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
                    <h5 className="text-sm font-semibold text-foreground">Layout Parsing & Structured Output (Docling)</h5>
                    <p className="text-xs text-muted-foreground mt-0.5">Extract layout structure, preserve tabular matrices, output page text structures.</p>
                    
                    {jobDetail.error_message && (
                      <div className="bg-destructive/10 border border-destructive/20 text-destructive text-xs rounded p-3 mt-2 font-mono">
                        {jobDetail.error_message}
                      </div>
                    )}
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
                Upload Another File
              </button>

              <div className="flex space-x-2">
                {jobDetail.status === 'failed' && (
                  <button 
                    onClick={handleRetry}
                    className="px-4 py-2 bg-warning text-warning-foreground font-medium rounded-lg text-sm hover:opacity-90 flex items-center space-x-1.5 transition"
                  >
                    <RefreshCw className="w-4 h-4 animate-spin-reverse" />
                    <span>Retry Pipeline</span>
                  </button>
                )}

                {jobDetail.status === 'completed' && (
                  <>
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
                  </>
                )}
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
