import React from 'react';
import { LayoutDashboard } from 'lucide-react';

export const DashboardShell: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <LayoutDashboard className="w-8 h-8 text-muted-foreground" />
        <div>
          <h2 className="text-3xl font-bold tracking-tight">Overview</h2>
          <p className="text-sm text-muted-foreground">Welcome to CatalogIQ. Monitor ingestion, quality metrics, and catalog health.</p>
        </div>
      </div>
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        {[
          { title: "Total Products", value: "0", sub: "0% verification rate" },
          { title: "Processing Jobs", value: "0", sub: "No active queue" },
          { title: "Review Backlog", value: "0", sub: "Fields requiring validation" },
          { title: "Catalog Quality", value: "--", sub: "Awaiting database load" }
        ].map((c, i) => (
          <div key={i} className="p-6 bg-card border rounded-xl shadow-sm space-y-2">
            <span className="text-xs font-semibold text-muted-foreground tracking-wider uppercase">{c.title}</span>
            <div className="text-3xl font-bold">{c.value}</div>
            <p className="text-xs text-muted-foreground">{c.sub}</p>
          </div>
        ))}
      </div>
      <div className="p-8 border border-dashed rounded-xl bg-card/50 flex flex-col items-center justify-center text-center space-y-4">
        <div className="w-12 h-12 rounded-full bg-secondary flex items-center justify-center text-muted-foreground">
          <LayoutDashboard className="w-6 h-6" />
        </div>
        <div className="max-w-sm space-y-1">
          <h3 className="font-semibold text-lg">Initial Setup Verified</h3>
          <p className="text-sm text-muted-foreground">CatalogIQ database and API shells are successfully running. Proceed to Phase 2 to wire up ingestion.</p>
        </div>
      </div>
    </div>
  );
};
