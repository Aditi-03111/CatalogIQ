import React, { useState } from 'react';

interface ValidationIssue {
  id?: string;
  validation_type: string;
  severity: string;
  attribute_name?: string;
  message: string;
  expected_value?: any;
  actual_value?: any;
}

interface ValidationPanelProps {
  productId: string;
  qualityScore: number;
  completenessScore?: number;
  issues: ValidationIssue[];
  onResolutionCompleted?: () => void;
}

export const ValidationPanel: React.FC<ValidationPanelProps> = ({
  productId,
  qualityScore,
  completenessScore = 80,
  issues,
  onResolutionCompleted,
}) => {
  const [resolvingId, setResolvingId] = useState<string | null>(null);

  const handleResolve = async (issueId: string, resolution: string, value?: any) => {
    try {
      setResolvingId(issueId);
      const res = await fetch(`/api/v1/products/${productId}/validation/${issueId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          resolution,
          resolved_value: value,
          notes: `Resolved via UI with ${resolution}`,
        }),
      });

      if (res.ok) {
        if (onResolutionCompleted) {
          onResolutionCompleted();
        }
      }
    } catch (err) {
      console.error('Failed to resolve validation issue:', err);
    } finally {
      setResolvingId(null);
    }
  };

  const getSeverityBadgeClass = (severity: string) => {
    switch (severity.toLowerCase()) {
      case 'critical':
        return 'bg-red-900 text-red-200 border-red-700';
      case 'error':
        return 'bg-orange-900 text-orange-200 border-orange-700';
      case 'warning':
        return 'bg-amber-900 text-amber-200 border-amber-700';
      default:
        return 'bg-blue-900 text-blue-200 border-blue-700';
    }
  };

  return (
    <div className="bg-card border border-border rounded-xl p-6 shadow-xl space-y-6">
      {/* Header & Quality Score */}
      <div className="flex items-center justify-between border-b border-border pb-4">
        <div>
          <h3 className="text-xl font-bold text-foreground flex items-center gap-2">
            <span>🛡️</span> Validation & Intelligence Health
          </h3>
          <p className="text-sm text-muted-foreground mt-1">
            Deterministic rule checks, completeness scoring, and conflict management
          </p>
        </div>
        <div className="flex items-center gap-4">
          <div className="text-right">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">Completeness</span>
            <span className="text-lg font-bold text-cyan-400">{completenessScore}%</span>
          </div>
          <div className="text-right bg-accent px-4 py-2 rounded-lg border border-border">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider block">Quality Score</span>
            <span className="text-2xl font-black text-emerald-400">{qualityScore}/100</span>
          </div>
        </div>
      </div>

      {/* Issues List */}
      {issues.length === 0 ? (
        <div className="bg-emerald-500/10/30 border border-emerald-500/20/50 rounded-lg p-4 text-emerald-500 flex items-center gap-3">
          <span className="text-xl">✓</span>
          <div>
            <p className="font-semibold">No Validation Issues Detected</p>
            <p className="text-xs text-emerald-400/80">Product data is complete, verified, and conflict-free.</p>
          </div>
        </div>
      ) : (
        <div className="space-y-3">
          <h4 className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
            Unresolved Issues ({issues.length})
          </h4>
          {issues.map((issue, idx) => (
            <div
              key={issue.id || idx}
              className="bg-background/60 border border-border rounded-lg p-4 space-y-3"
            >
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <span
                    className={`text-xs px-2.5 py-0.5 rounded-full font-semibold border uppercase tracking-wider ${getSeverityBadgeClass(
                      issue.severity
                    )}`}
                  >
                    {issue.severity}
                  </span>
                  <span className="font-semibold text-foreground text-sm">
                    {issue.attribute_name ? `Attribute: ${issue.attribute_name}` : issue.validation_type}
                  </span>
                </div>
                <span className="text-xs text-muted-foreground font-mono">{issue.validation_type}</span>
              </div>

              <p className="text-sm text-foreground">{issue.message}</p>

              {(issue.expected_value || issue.actual_value) && (
                <div className="grid grid-cols-2 gap-4 bg-card/80 p-3 rounded border border-border/80 text-xs font-mono">
                  <div>
                    <span className="text-muted-foreground block">Expected Value:</span>
                    <span className="text-emerald-400">{String(issue.expected_value || 'N/A')}</span>
                  </div>
                  <div>
                    <span className="text-muted-foreground block">Actual Extracted:</span>
                    <span className="text-amber-400">{String(issue.actual_value || 'N/A')}</span>
                  </div>
                </div>
              )}

              {/* Conflict resolution actions */}
              {issue.id && (
                <div className="flex items-center gap-2 pt-2 border-t border-border/60">
                  <button
                    disabled={resolvingId === issue.id}
                    onClick={() => handleResolve(issue.id!, 'accept_source_a', issue.actual_value)}
                    className="px-3 py-1.5 bg-emerald-700 hover:bg-emerald-600 text-white rounded text-xs font-medium transition disabled:opacity-50"
                  >
                    Accept Extracted Value
                  </button>
                  {issue.expected_value && (
                    <button
                      disabled={resolvingId === issue.id}
                      onClick={() => handleResolve(issue.id!, 'accept_source_b', issue.expected_value)}
                      className="px-3 py-1.5 bg-cyan-700 hover:bg-cyan-600 text-white rounded text-xs font-medium transition disabled:opacity-50"
                    >
                      Accept Expected Value
                    </button>
                  )}
                  <button
                    disabled={resolvingId === issue.id}
                    onClick={() => {
                      const val = prompt('Enter custom resolution value:');
                      if (val !== null) {
                        handleResolve(issue.id!, 'custom_value', val);
                      }
                    }}
                    className="px-3 py-1.5 bg-accent hover:bg-card text-foreground rounded text-xs font-medium transition disabled:opacity-50"
                  >
                    Set Custom Value...
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
