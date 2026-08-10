import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Database, AlertTriangle, FileText, CheckCircle2 } from 'lucide-react';
import { ValidationPanel } from './ValidationPanel';
import { MultiSourceReconciliationPanel } from './MultiSourceReconciliationPanel';
import { EnrichmentPanel } from './EnrichmentPanel';

interface ProductItem {
  id: string;
  sku: string;
  brand: string;
  product_name: string;
  model?: string;
  category: string;
  status: string;
  quality_score: number;
  description?: string;
  commerce_description?: string;
  features?: string[];
  applications?: string[];
  keywords?: string[];
}

interface ProductAttributeItem {
  id: string;
  attribute_name: string;
  display_name: string;
  raw_value: string;
  unit?: string;
  confidence: number;
  status: string;
}

interface EvidenceItem {
  id: string;
  attribute_id: string;
  page_number?: number;
  evidence_text: string;
  extraction_method: string;
}

export const ProductsShell: React.FC = () => {
  const [searchParams] = useSearchParams();
  const paramProductId = searchParams.get('product_id');

  const [products, setProducts] = useState<ProductItem[]>([]);
  const [selectedProduct, setSelectedProduct] = useState<ProductItem | null>(null);
  const [attributes, setAttributes] = useState<ProductAttributeItem[]>([]);
  useEffect(() => {
    console.log("REACT ATTRIBUTES:", attributes);
    console.log(
      "AMBIENT TEMP:",
      attributes.find(
        (a) => a.attribute_name === "ambient_temperature"
      )
    );
  }, [attributes]);
  const [evidenceList, setEvidenceList] = useState<EvidenceItem[]>([]);
  const [validationIssues, setValidationIssues] = useState<any[]>([]);
  const [enrichmentData, setEnrichmentData] = useState<any>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [selectedAttrId, setSelectedAttrId] = useState<string | null>(null);

  useEffect(() => {
    fetchProducts();
  }, [paramProductId]);

  const fetchProducts = async () => {
    try {
      setLoading(true);
      const res = await fetch('/api/v1/products');
      if (res.ok) {
        const data: ProductItem[] = await res.json();
        setProducts(data);
        if (data.length > 0) {
          let target = data[0];
          if (paramProductId) {
            const paramMatch = data.find((p) => p.id === paramProductId);
            if (paramMatch) target = paramMatch;
          } else if (selectedProduct) {
            const currentMatch = data.find((p) => p.id === selectedProduct.id);
            if (currentMatch) target = currentMatch;
          }
          selectProduct(target);
        }
      }
    } catch (err) {
      console.error('Failed to fetch products:', err);
    } finally {
      setLoading(false);
    }
  };

  const selectProduct = async (prod: ProductItem) => {
    setSelectedProduct(prod);
    setSelectedAttrId(null);
    try {
      const [attrRes, evidRes, valRes, enrichRes] = await Promise.all([
        fetch(`/api/v1/products/${prod.id}/attributes`),
        fetch(`/api/v1/products/${prod.id}/evidence`),
        fetch(`/api/v1/products/${prod.id}/validation`),
        fetch(`/api/v1/products/${prod.id}/enrichment`),
      ]);

      if (attrRes.ok) {
        const fetchedAttrs: ProductAttributeItem[] = await attrRes.json();
        setAttributes(fetchedAttrs);
      }
      if (evidRes.ok) {
        setEvidenceList(await evidRes.json());
      }
      if (valRes.ok) {
        const valData = await valRes.json();
        setValidationIssues(valData.issues || []);
      }
      if (enrichRes.ok) {
        setEnrichmentData(await enrichRes.json());
      }
    } catch (err) {
      console.error('Failed to fetch product details:', err);
    }
  };

  const handleRerunValidation = async () => {
    if (!selectedProduct) return;
    try {
      const res = await fetch(`/api/v1/products/${selectedProduct.id}/validate`, { method: 'POST' });
      if (res.ok) {
        fetchProducts();
      }
    } catch (err) {
      console.error('Failed to rerun validation:', err);
    }
  };

  const handleRerunEnrichment = async () => {
    if (!selectedProduct) return;
    try {
      const res = await fetch(`/api/v1/products/${selectedProduct.id}/enrich`, { method: 'POST' });
      if (res.ok) {
        fetchProducts();
      }
    } catch (err) {
      console.error('Failed to rerun enrichment:', err);
    }
  };

  if (loading) {
    return (
      <div className="p-12 text-center text-slate-400 font-medium">
        Loading CatalogIQ Product Intelligence...
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="space-y-6">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-3xl font-bold tracking-tight">Product Intelligence Dashboard</h2>
            <p className="text-sm text-slate-400">Validated, quality-scored, and evidence-backed product catalog.</p>
          </div>
        </div>
        <div className="bg-slate-900 border border-slate-800 rounded-xl p-12 text-center text-slate-400 flex flex-col items-center justify-center space-y-3">
          <Database className="w-12 h-12 text-slate-600" />
          <h4 className="font-semibold text-slate-200 text-lg">No Products in Database</h4>
          <p className="text-sm max-w-sm text-slate-400">
            Upload technical datasheets (such as synthetic_motor.pdf) to parse, extract, validate, and enrich product intelligence.
          </p>
        </div>
      </div>
    );
  }

  const selectedEvidence = evidenceList.filter(
    (e) => !selectedAttrId || e.attribute_id === selectedAttrId
  );

  return (
    <div className="space-y-6 text-slate-100">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-3xl font-bold tracking-tight text-white flex items-center gap-2">
            <span>⚡</span> Product Intelligence Dashboard
          </h2>
          <p className="text-sm text-slate-400">
            Validation, Conflict Resolution & Evidence-Backed AI Commerce Enrichment
          </p>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={selectedProduct?.id || ''}
            onChange={(e) => {
              const p = products.find((x) => x.id === e.target.value);
              if (p) selectProduct(p);
            }}
            className="bg-slate-800 border border-slate-700 text-slate-200 px-4 py-2 rounded-lg text-sm font-medium outline-none"
          >
            {products.map((p) => (
              <option key={p.id} value={p.id}>
                {p.product_name} ({p.sku})
              </option>
            ))}
          </select>
          <button
            onClick={handleRerunValidation}
            className="px-3.5 py-2 bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs font-semibold rounded-lg border border-slate-700 transition"
          >
            Re-validate
          </button>
          <button
            onClick={handleRerunEnrichment}
            className="px-3.5 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-xs font-semibold rounded-lg transition"
          >
            Re-enrich AI
          </button>
        </div>
      </div>

      {selectedProduct && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main Specs & Intelligence Column */}
          <div className="lg:col-span-2 space-y-6">
            {/* Product Banner */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl relative overflow-hidden">
              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-semibold px-2.5 py-0.5 rounded bg-indigo-950 text-indigo-300 border border-indigo-800">
                      {selectedProduct.brand}
                    </span>
                    <span className="text-xs text-slate-400 font-mono">SKU: {selectedProduct.sku}</span>
                  </div>
                  <h3 className="text-2xl font-black text-white mt-2">{selectedProduct.product_name}</h3>
                  <p className="text-xs text-slate-400 mt-1 font-mono">
                    Category: <span className="text-slate-200">{selectedProduct.category}</span>
                  </p>
                </div>

                <div className="text-right">
                  <div className="flex items-center gap-2 justify-end">
                    {selectedProduct.status === 'verified' ? (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-emerald-950 text-emerald-300 border border-emerald-800 rounded-full text-xs font-bold uppercase tracking-wider">
                        <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" /> Verified
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-amber-950 text-amber-300 border border-amber-800 rounded-full text-xs font-bold uppercase tracking-wider">
                        <AlertTriangle className="w-3.5 h-3.5 text-amber-400" /> Needs Review
                      </span>
                    )}
                  </div>
                  <div className="mt-3">
                    <span className="text-[10px] text-slate-400 block uppercase tracking-wider font-semibold">
                      Quality Score
                    </span>
                    <span className="text-3xl font-black text-emerald-400">
                      {selectedProduct.quality_score}/100
                    </span>
                  </div>
                </div>
              </div>

              {selectedProduct.description && (
                <div className="mt-4 pt-4 border-t border-slate-800 text-sm text-slate-300">
                  {selectedProduct.description}
                </div>
              )}
            </div>

            {/* Specifications Table */}
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4">
              <h4 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <FileText className="w-5 h-5 text-indigo-400" /> Technical Specifications
              </h4>
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead>
                    <tr className="border-b border-slate-800 text-xs font-semibold uppercase text-slate-400 font-mono">
                      <th className="py-2.5 px-3">Specification</th>
                      <th className="py-2.5 px-3">Value</th>
                      <th className="py-2.5 px-3">Unit</th>
                      <th className="py-2.5 px-3">Confidence</th>
                      <th className="py-2.5 px-3">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/60">
                    {attributes.map((attr) => (
                      <tr
                        key={attr.id}
                        onClick={() => setSelectedAttrId(attr.id)}
                        className={`cursor-pointer transition ${selectedAttrId === attr.id ? 'bg-indigo-950/40' : 'hover:bg-slate-800/40'
                          }`}
                      >
                        <td className="py-3 px-3 font-medium text-slate-200">{attr.display_name}</td>
                        <td className="py-3 px-3 font-semibold text-emerald-400">{attr.raw_value}</td>
                        <td className="py-3 px-3 font-mono text-slate-400">{attr.unit || '—'}</td>
                        <td className="py-3 px-3 font-mono text-xs">{Math.round(attr.confidence * 100)}%</td>
                        <td className="py-3 px-3">
                          <span
                            className={`text-[11px] font-semibold px-2 py-0.5 rounded border uppercase font-mono ${attr.status === 'verified'
                              ? 'bg-emerald-950 text-emerald-300 border-emerald-800'
                              : attr.status === 'conflicting'
                                ? 'bg-red-950 text-red-300 border-red-800'
                                : 'bg-amber-950 text-amber-300 border-amber-800'
                              }`}
                          >
                            {attr.status}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Validation Panel */}
            <ValidationPanel
              productId={selectedProduct.id}
              qualityScore={selectedProduct.quality_score}
              issues={validationIssues}
              onResolutionCompleted={fetchProducts}
            />

            {/* Multi-Source Reconciliation Panel */}
            <MultiSourceReconciliationPanel
              productId={selectedProduct.id}
              onRefreshRequested={fetchProducts}
            />

            {/* AI Commerce Enrichment Panel */}
            <EnrichmentPanel
              enrichment={enrichmentData}
              onRerunEnrichment={handleRerunEnrichment}
            />
          </div>

          {/* Evidence & Provenance Column */}
          <div className="space-y-6">
            <div className="bg-slate-900 border border-slate-800 rounded-xl p-6 shadow-xl space-y-4 sticky top-6">
              <h4 className="text-lg font-bold text-slate-100 flex items-center gap-2">
                <span>🔎</span> Evidence Provenance
              </h4>
              <p className="text-xs text-slate-400">
                {selectedAttrId
                  ? 'Showing evidence quotes for selected attribute'
                  : 'Click any specification to inspect original document evidence'}
              </p>

              <div className="space-y-3 max-h-[600px] overflow-y-auto pr-1">
                {selectedEvidence.length === 0 ? (
                  <p className="text-xs text-slate-500 italic p-4 text-center">
                    No evidence quotes recorded for selection.
                  </p>
                ) : (
                  selectedEvidence.map((ev) => (
                    <div
                      key={ev.id}
                      className="bg-slate-950 border border-slate-800 rounded-lg p-3 space-y-2 text-xs"
                    >
                      <div className="flex items-center justify-between text-slate-400 font-mono text-[11px]">
                        <span>Page {ev.page_number || 1}</span>
                        <span className="capitalize">{ev.extraction_method}</span>
                      </div>
                      <blockquote className="bg-slate-900/90 border-l-2 border-emerald-500 p-2.5 rounded text-slate-200 italic font-mono text-[11px] leading-relaxed">
                        "{ev.evidence_text}"
                      </blockquote>
                    </div>
                  ))
                )}
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
