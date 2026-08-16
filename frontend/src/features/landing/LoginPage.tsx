import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { SignIn, useAuth } from '@clerk/clerk-react';
import { AlertCircle, Loader2, Sparkles, Key, Sun, Moon } from 'lucide-react';
import { useTheme } from '../../hooks/useTheme';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { isSignedIn, isLoaded } = useAuth();
  
  const [clerkKey, setClerkKey] = useState<string>('');
  const [loadingConfig, setLoadingConfig] = useState(true);
  const [error] = useState<string | null>(null);

  // Manual configuration inputs if key is empty
  const [customKeyInput, setCustomKeyInput] = useState('');
  const [showManualInput, setShowManualInput] = useState(false);

  // Redirect to dashboard if already authenticated
  useEffect(() => {
    if (isLoaded && isSignedIn) {
      navigate('/dashboard');
    }
  }, [isLoaded, isSignedIn, navigate]);

  // Fetch Clerk Publishable Key from backend config on mount
  useEffect(() => {
    const fetchConfig = async () => {
      try {
        const res = await fetch('/api/v1/health/ready');
        if (!res.ok) throw new Error("Failed to fetch connection details");
        const data = await res.json();
        
        const key = data.clerk_publishable_key;
        if (key && key !== 'your_clerk_publishable_key_here') {
          setClerkKey(key);
        } else {
          // If env has placeholder, check localStorage override
          const savedOverride = localStorage.getItem("clerk_publishable_key_override");
          if (savedOverride) {
            setClerkKey(savedOverride);
          } else {
            setShowManualInput(true);
          }
        }
      } catch (err) {
        console.error("Config fetch error:", err);
        setShowManualInput(true);
      } finally {
        setLoadingConfig(false);
      }
    };
    fetchConfig();
  }, []);

  const saveCustomPublishableKey = () => {
    const trimmed = customKeyInput.trim();
    if (!trimmed) return;
    localStorage.setItem("clerk_publishable_key_override", trimmed);
    localStorage.removeItem("token"); // clear old stub tokens
    window.location.reload();
  };

  return (
    <div className="app-chrome min-h-screen w-screen flex flex-col justify-center items-center p-6 bg-background text-foreground relative overflow-hidden">
      
      {/* Background Ambient Glows */}
      <div className="absolute top-[-10%] right-[-10%] w-[50vw] h-[50vw] rounded-full glow-1 blur-[120px] pointer-events-none z-0" />
      <div className="absolute bottom-[-10%] left-[10%] w-[55vw] h-[55vw] rounded-full glow-2 blur-[150px] pointer-events-none z-0" />

      {/* Theme Toggle Button */}
      <div className="absolute top-6 right-6 z-10 flex gap-2">
        <button 
          onClick={toggleTheme}
          className="w-10 h-10 border border-border bg-card hover:bg-accent flex items-center justify-center transition"
          title="Toggle Theme"
        >
          {theme === 'dark' ? <Sun className="w-4 h-4 text-foreground" /> : <Moon className="w-4 h-4 text-foreground" />}
        </button>
        <button 
          onClick={() => navigate('/')}
          className="px-4 py-2 border border-border bg-card hover:bg-accent text-xs font-semibold tracking-wider transition uppercase"
        >
          Exit to Landing
        </button>
      </div>

      <div className="w-full max-w-md bg-card border border-border p-8 z-10 shadow-2xl space-y-8 flex flex-col justify-center items-center text-center">
        
        {/* Brand Header */}
        <div className="space-y-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#9B8F77]/10 border border-[#9B8F77]/20 font-mono text-[#9B8F77] text-[10px] uppercase tracking-widest">
            <Sparkles className="w-3.5 h-3.5" />
            <span>Industrial Intelligence Portal</span>
          </div>
          <h1 className="text-4xl font-normal font-serif tracking-tight mt-2">CatalogIQ</h1>
          <p className="text-xs text-muted-foreground max-w-xs mx-auto leading-relaxed">
            AI-powered data enrichment, unit validation, and explainable product records.
          </p>
        </div>

        {error && (
          <div className="bg-destructive/10 border border-destructive/20 text-destructive text-xs p-4 flex items-start gap-2.5 text-left w-full">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-semibold block">Authentication Error</span>
              <span className="leading-relaxed">{error}</span>
            </div>
          </div>
        )}

        {/* Configuration loading or Clerk sign-in form */}
        {loadingConfig ? (
          <div className="flex flex-col items-center justify-center space-y-2 py-4">
            <Loader2 className="w-8 h-8 text-muted-foreground animate-spin" />
            <p className="text-xs text-muted-foreground font-mono">Fetching authentication configs...</p>
          </div>
        ) : showManualInput ? (
          <div className="w-full space-y-4 text-left border-t border-border pt-6">
            <div className="space-y-1.5">
              <h3 className="text-sm font-semibold flex items-center gap-1.5 text-foreground">
                <Key className="w-4 h-4 text-muted-foreground" />
                <span>Configure Clerk Key</span>
              </h3>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Clerk Publishable Key is not configured in your `.env` file yet. You can paste your Clerk Publishable Key (starts with `pk_test_`) here to test:
              </p>
            </div>
            
            <div className="space-y-3">
              <input
                type="text"
                placeholder="pk_test_..."
                value={customKeyInput}
                onChange={(e) => setCustomKeyInput(e.target.value)}
                className="w-full bg-background border border-border text-foreground px-3 py-2 text-xs outline-none focus:border-foreground transition font-mono"
              />
              <div className="flex gap-2">
                <button
                  onClick={saveCustomPublishableKey}
                  disabled={!customKeyInput.trim()}
                  className="flex-1 bg-foreground text-background text-xs font-semibold py-2 px-3 hover:opacity-90 transition disabled:opacity-50 flex items-center justify-center gap-1"
                >
                  Apply Key & Reload
                </button>
                {clerkKey && (
                  <button
                    onClick={() => setShowManualInput(false)}
                    className="border border-border text-xs px-3 py-2 hover:bg-accent"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="w-full flex flex-col items-center justify-center space-y-6 border-t border-border pt-6 py-2">
            <div className="w-full border border-border bg-background p-3">
              <div className="aspect-square w-full overflow-hidden bg-background relative">
                <img
                  src="/brand_hero.png"
                  alt="CatalogIQ Brand Symbol"
                  className="w-full h-full object-cover brightness-100 contrast-105"
                />
                <div className="absolute inset-0 border border-black/5 pointer-events-none" />
              </div>
              <div className="mt-3 flex items-center justify-between text-[9px] text-muted-foreground font-mono tracking-widest uppercase font-light">
                <span>CatalogIQ Identity System</span>
                <span>Ref: CL-00</span>
              </div>
            </div>

            <div className="text-center space-y-1">
              <h2 className="font-serif text-lg font-medium text-foreground">Continue to Console</h2>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-light">
                Google accounts only
              </p>
            </div>
            
            <div className="google-only-clerk w-full flex justify-center scale-95 overflow-hidden">
              <SignIn 
                routing="hash"
                fallbackRedirectUrl="/dashboard"
                signUpUrl="/login"
                appearance={{
                  elements: {
                    rootBox: "w-full",
                    card: "bg-transparent border-0 shadow-none p-0 text-foreground",
                    headerTitle: "text-foreground",
                    headerSubtitle: "text-muted-foreground",
                    dividerRow: "hidden",
                    form: "hidden",
                    formField: "hidden",
                    formFieldRow: "hidden",
                    formButtonPrimary: "hidden",
                    footer: "hidden",
                    footerActionText: "hidden",
                    footerActionLink: "hidden",
                    socialButtons: "w-full",
                    socialButtonsBlockButton: "bg-card border border-border text-foreground hover:bg-accent transition rounded-none w-full py-3.5 flex justify-center items-center gap-3",
                    socialButtonsBlockButtonText: "text-foreground font-semibold text-[10px] uppercase tracking-widest",
                    socialButtonsProviderIcon__google: "w-4 h-4"
                  }
                }}
              />
            </div>

            <button
              onClick={() => setShowManualInput(true)}
              className="text-[10px] text-muted-foreground hover:text-foreground font-mono transition mt-2"
            >
              Change Clerk Publishable Key
            </button>
          </div>
        )}

        {/* Footer */}
        <div className="text-[10px] font-mono text-muted-foreground leading-relaxed">
          <span>CatalogIQ is protected by enterprise Clerk auth controls.</span>
        </div>
      </div>
    </div>
  );
};
