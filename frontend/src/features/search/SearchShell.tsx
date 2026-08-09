import React from 'react';
import { Search } from 'lucide-react';

export const SearchShell: React.FC = () => {
  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-3xl font-bold tracking-tight">Semantic Search</h2>
        <p className="text-sm text-muted-foreground">Find products naturally using LLM embeddings and structural metadata.</p>
      </div>
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="e.g. Find stainless steel bearings under 5kg for high-RPM applications"
          className="flex-1 px-4 py-3 bg-card border rounded-lg text-sm outline-none focus:ring-1 focus:ring-ring font-medium"
          disabled
        />
        <button className="px-5 py-3 bg-primary text-primary-foreground font-medium rounded-lg text-sm transition shadow-sm hover:opacity-90 flex items-center gap-2">
          <Search className="w-4 h-4" />
          <span>Search</span>
        </button>
      </div>
      <div className="p-12 text-center text-muted-foreground flex flex-col items-center justify-center space-y-2 border border-dashed rounded-xl bg-card/25">
        <p className="text-sm">Semantic search indexes will be constructed after Qdrant is connected.</p>
      </div>
    </div>
  );
};
