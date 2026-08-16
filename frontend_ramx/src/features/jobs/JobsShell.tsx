import React, { useState, useEffect } from 'react';
import { Activity, FileText, AlertTriangle, Eye, RefreshCw, Loader2 } from 'lucide-react';
import { formatApiDateTime, parseApiDate } from '../../lib/dates';

interface DocumentInfo {
  id: string;
  filename: string;
  storage_backend: string;
  storage_key: string;
  file_hash: string;
  content_hash: string | null;
  mime_type: string;
  file_size: number;
  page_count: number | null;
  status: string;
  parser_name: string | null;
  parser_version: string | null;
  parsed_at: string | null;
  created_at: string;
}

export const JobsShell: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // JSON Inspector Modal state
  const [selectedDocId, setSelectedDocId] = useState<string | null>(null);
  const [parsedData, setParsedData] = useState<any | null>(null);
  const [loadingParsed, setLoadingParsed] = useState(false);

  const fetchDocuments = async () => {
    try {
      setLoading(true);
      const res = await fetch("/api/v1/documents/");
      if (!res.ok) throw new Error("Failed to fetch documents list");
      const data: DocumentInfo[] = await res.json();
      // Sort by created_at desc
      data.sort((a, b) => (parseApiDate(b.created_at)?.getTime() || 0) - (parseApiDate(a.created_at)?.getTime() || 0));
      setDocuments(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments();
  }, []);

  const handleInspectJson = async (docId: string) => {
    setSelectedDocId(docId);
    setParsedData(null);
    setLoadingParsed(true);
    try {
      const res = await fetch(`/api/v1/documents/${docId}/parsed`);
      if (!res.ok) throw new Error("Failed to retrieve intermediate representation");
      const data = await res.json();
      setParsedData(data);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoadingParsed(false);
    }
  };

  const handleForceReprocess = async (docId: string) => {
    try {
      const res = await fetch(`/api/v1/documents/${docId}/reprocess`, { method: "POST" });
      if (!res.ok) throw new Error("Reprocess request failed");
      // Refresh documents list
      fetchDocuments();
    } catch (err: any) {
      setError(err.message);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Processing Logs</h2>
          <p className="text-sm text-muted-foreground">Monitor files, check parsing status logs, and inspect intermediate JSON documents.</p>
        </div>
        <button 
          onClick={fetchDocuments}
          className="px-4 py-2 border rounded-lg text-sm bg-background font-medium hover:bg-muted transition flex items-center space-x-1.5"
        >
          <RefreshCw className="w-4 h-4" />
          <span>Refresh</span>
        </button>
      </div>

      {error && (
        <div className="bg-destructive/10 border border-destructive/20 text-destructive text-sm rounded-lg p-4 flex items-center space-x-2">
          <AlertTriangle className="w-5 h-5 flex-shrink-0" />
          <span>{error}</span>
        </div>
      )}

      {loading ? (
        <div className="flex justify-center items-center py-20">
          <Loader2 className="w-8 h-8 text-primary animate-spin" />
        </div>
      ) : documents.length === 0 ? (
        <div className="bg-card border rounded-xl overflow-hidden shadow-sm">
          <div className="p-12 text-center text-muted-foreground flex flex-col items-center justify-center space-y-2">
            <Activity className="w-10 h-10 text-muted-foreground" />
            <h4 className="font-semibold text-foreground">No Documents Ingested</h4>
            <p className="text-sm max-w-xs">Upload technical catalogs to run parser workers and monitor processes.</p>
          </div>
        </div>
      ) : (
        <div className="bg-card border rounded-xl shadow-sm overflow-hidden">
          <table className="w-full text-left border-collapse">
            <thead>
              <tr className="bg-muted/40 border-b text-xs font-semibold text-muted-foreground uppercase">
                <th className="p-4">Document / File Details</th>
                <th className="p-4">Status</th>
                <th className="p-4">Page Count</th>
                <th className="p-4">Parser Details</th>
                <th className="p-4">Upload Date</th>
                <th className="p-4 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y text-sm">
              {documents.map((doc) => (
                <tr key={doc.id} className="hover:bg-muted/10 transition">
                  <td className="p-4">
                    <div className="flex items-center space-x-3">
                      <div className="w-10 h-10 rounded-lg bg-secondary flex items-center justify-center flex-shrink-0">
                        <FileText className="w-5 h-5 text-muted-foreground" />
                      </div>
                      <div>
                        <span className="font-semibold block truncate max-w-xs text-foreground">{doc.filename}</span>
                        <span className="text-xs text-muted-foreground block font-mono">{(doc.file_size / (1024 * 1024)).toFixed(2)} MB • {doc.file_hash.substring(0, 12)}...</span>
                      </div>
                    </div>
                  </td>
                  <td className="p-4">
                    <span className={`px-2.5 py-0.5 text-xs font-semibold rounded-full capitalize inline-block ${
                      doc.status === 'processed' ? 'bg-success/15 text-success' :
                      doc.status === 'failed' ? 'bg-destructive/15 text-destructive' :
                      'bg-warning/15 text-warning animate-pulse'
                    }`}>
                      {doc.status}
                    </span>
                  </td>
                  <td className="p-4 font-semibold">
                    {doc.page_count !== null ? `${doc.page_count} pages` : "N/A"}
                  </td>
                  <td className="p-4 font-mono text-xs">
                    {doc.parser_name ? (
                      <span>{doc.parser_name} v{doc.parser_version}</span>
                    ) : (
                      <span className="text-muted-foreground">-</span>
                    )}
                  </td>
                  <td className="p-4 text-xs text-muted-foreground">
                    {formatApiDateTime(doc.created_at)}
                  </td>
                  <td className="p-4 text-right">
                    <div className="flex justify-end space-x-2">
                      <button 
                        onClick={() => handleForceReprocess(doc.id)}
                        title="Force reprocess"
                        className="p-1.5 border rounded-lg hover:bg-muted text-muted-foreground hover:text-foreground transition"
                      >
                        <RefreshCw className="w-4 h-4" />
                      </button>
                      
                      {doc.status === 'processed' && (
                        <button 
                          onClick={() => handleInspectJson(doc.id)}
                          title="Inspect intermediate JSON"
                          className="p-1.5 bg-primary/10 border border-primary/20 rounded-lg hover:bg-primary/20 text-primary transition"
                        >
                          <Eye className="w-4 h-4" />
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* JSON Viewer Sidebar Modal */}
      {selectedDocId && (
        <div className="fixed inset-0 bg-background/80 backdrop-blur-sm z-50 flex justify-end">
          <div className="w-full max-w-2xl bg-card border-l h-full flex flex-col shadow-2xl p-6 space-y-4">
            <div className="flex justify-between items-center border-b pb-4">
              <div>
                <h4 className="font-bold text-lg">Intermediate JSON Viewer</h4>
                <p className="text-xs text-muted-foreground mt-0.5">Doc ID: {selectedDocId}</p>
              </div>
              <button 
                onClick={() => setSelectedDocId(null)}
                className="px-3 py-1.5 border rounded-lg text-xs hover:bg-muted font-medium transition"
              >
                Close Panel
              </button>
            </div>

            {loadingParsed ? (
              <div className="flex-1 flex justify-center items-center">
                <Loader2 className="w-8 h-8 text-primary animate-spin" />
              </div>
            ) : parsedData ? (
              <div className="flex-1 flex flex-col space-y-4 overflow-hidden">
                <div className="grid grid-cols-2 gap-4 text-sm bg-muted/40 p-4 rounded-lg">
                  <div>
                    <span className="text-xs text-muted-foreground block">Content Hash</span>
                    <span className="font-semibold text-foreground truncate block font-mono">{parsedData.content_hash}</span>
                  </div>
                  <div>
                    <span className="text-xs text-muted-foreground block">Parser Engine</span>
                    <span className="font-semibold text-foreground block font-mono">{parsedData.parser?.name} v{parsedData.parser?.version}</span>
                  </div>
                </div>

                <div className="flex-1 bg-muted p-4 rounded-lg overflow-y-auto text-xs font-mono">
                  <pre>{JSON.stringify(parsedData, null, 2)}</pre>
                </div>
              </div>
            ) : (
              <div className="text-center text-muted-foreground py-20">
                Failed to parse layout representation.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
