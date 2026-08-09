import React from 'react';

interface EnrichmentData {
  commerce_description?: string;
  short_description?: string;
  features?: string[];
  applications?: string[];
  keywords?: string[];
  seo_title?: string;
  seo_description?: string;
  confidence?: number;
  model?: string;
  prompt_version?: string;
  status?: string;
  generated_value?: string;
}

interface EnrichmentPanelProps {
  enrichment?: EnrichmentData;
  onRerunEnrichment?: () => void;
}

export const EnrichmentPanel: React.FC<EnrichmentPanelProps> = ({
  enrichment,
  onRerunEnrichment,
}) => {
  if (!enrichment) {
    return (
      <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl text-center text-slate-400">
        <p>No AI commerce enrichment generated yet.</p>
        {onRerunEnrichment && (
          <button
            onClick={onRerunEnrichment}
            className="mt-4 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium text-sm transition"
          >
            Generate Commerce Intelligence
          </button>
        )}
      </div>
    );
  }

  let parsedGen: any = {};
  if (enrichment.generated_value) {
    try {
      parsedGen = typeof enrichment.generated_value === 'string'
        ? JSON.parse(enrichment.generated_value)
        : enrichment.generated_value;
    } catch {
      parsedGen = {};
    }
  }

  const commerceDescription = enrichment.commerce_description || parsedGen.commerce_description;
  const shortDescription = enrichment.short_description || parsedGen.short_description;
  const features: string[] = (enrichment.features && enrichment.features.length > 0)
    ? enrichment.features
    : (parsedGen.features || []);
  const applications: string[] = (enrichment.applications && enrichment.applications.length > 0)
    ? enrichment.applications
    : (parsedGen.applications || []);
  const seoTitle = enrichment.seo_title || parsedGen.seo_title;
  const seoDescription = enrichment.seo_description || parsedGen.seo_description;

  const rawConf = enrichment.confidence ?? parsedGen.confidence ?? 0;
  const confidencePct = Math.round(rawConf * 100);

  if (enrichment.status === 'failed') {
    return (
      <div className="bg-slate-900 border border-red-900/50 rounded-xl p-6 shadow-xl space-y-4">
        <div className="flex items-center justify-between border-b border-slate-800 pb-3">
          <h3 className="text-xl font-bold text-red-400 flex items-center gap-2">
            <span>⚠️</span> AI Commerce Enrichment Failed
          </h3>
          <span className="text-xs bg-red-950 text-red-300 border border-red-800 px-3 py-1.5 rounded-md font-mono uppercase">
            Status: Failed
          </span>
        </div>
        <p className="text-sm text-slate-300">
          AI enrichment generation encountered an error or failed quality safety checks.
        </p>
        {onRerunEnrichment && (
          <button
            onClick={onRerunEnrichment}
            className="px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg font-medium text-sm transition"
          >
            Retry Commerce Intelligence
          </button>
        )}
      </div>
    );
  }

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-slate-800 pb-4">
        <div>
          <h3 className="text-xl font-bold text-slate-100 flex items-center gap-2">
            <span>✨</span> AI Commerce Intelligence
          </h3>
          <p className="text-sm text-slate-400 mt-1">
            Evidence-constrained, AI-generated commerce description & B2B metadata
          </p>
        </div>
        <div className="flex items-center gap-3">
          <span className="text-xs bg-indigo-950 text-indigo-300 border border-indigo-800 px-3 py-1.5 rounded-md font-mono">
            Model: {enrichment.model || 'Gemini 3.6 Flash'}
          </span>
          <div className="bg-slate-800 px-3 py-1.5 rounded-md border border-slate-700 text-right">
            <span className="text-[10px] text-slate-400 block uppercase tracking-wider font-semibold">
              Confidence
            </span>
            <span className="text-sm font-bold text-indigo-400">{confidencePct}%</span>
          </div>
        </div>
      </div>

      {/* Commerce Description */}
      {commerceDescription && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Commerce Description
          </h4>
          <div className="bg-slate-950/80 border border-slate-800/80 rounded-lg p-4 text-slate-200 text-sm leading-relaxed font-sans">
            {commerceDescription}
          </div>
        </div>
      )}

      {/* Short Description */}
      {shortDescription && (
        <div className="space-y-2">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            Short Summary
          </h4>
          <p className="text-sm text-slate-300 italic bg-slate-950/40 p-3 rounded border border-slate-800">
            "{shortDescription}"
          </p>
        </div>
      )}

      {/* Features & Applications */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {features && features.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Validated Key Features
            </h4>
            <ul className="space-y-1.5 text-sm text-slate-300">
              {features.map((feat, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-emerald-400 text-xs mt-0.5">✓</span>
                  <span>{feat}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {applications && applications.length > 0 && (
          <div className="space-y-2">
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              Industrial Applications
            </h4>
            <ul className="space-y-1.5 text-sm text-slate-300">
              {applications.map((app, idx) => (
                <li key={idx} className="flex items-start gap-2">
                  <span className="text-cyan-400 text-xs mt-0.5">•</span>
                  <span>{app}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* SEO Metadata */}
      {(seoTitle || seoDescription) && (
        <div className="border-t border-slate-800 pt-4 space-y-3">
          <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
            SEO & Catalog Metadata
          </h4>
          <div className="bg-slate-950 p-3 rounded-lg border border-slate-800 space-y-1.5 text-xs font-mono">
            {seoTitle && (
              <div>
                <span className="text-indigo-400 font-semibold block">SEO Title:</span>
                <span className="text-slate-300">{seoTitle}</span>
              </div>
            )}
            {seoDescription && (
              <div>
                <span className="text-indigo-400 font-semibold block">Meta Description:</span>
                <span className="text-slate-400">{seoDescription}</span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
