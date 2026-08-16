import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { SignIn, useAuth } from '@clerk/clerk-react';
import { AlertCircle, Loader2, Sparkles, Key } from 'lucide-react';

export const LoginPage: React.FC = () => {
  const navigate = useNavigate();
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
    <div className="min-h-screen w-screen flex flex-col justify-center items-center p-6 bg-[#ECECEB] text-[#111111] relative overflow-hidden font-sans">
      
      {/* Top Header navbar matching RAMX */}
      <div className="absolute top-6 left-6 z-10 flex items-center gap-2.5 select-none">
        <div className="w-5 h-5 flex items-center justify-center border-2 border-[#111111] rounded font-bold relative">
          <span className="text-[12px] absolute font-extrabold rotate-45">+</span>
        </div>
        <span className="font-extrabold tracking-widest text-[14px] uppercase font-mono text-[#111111]">RAMX</span>
      </div>

      {/* Theme/Navigation Action Buttons */}
      <div className="absolute top-6 right-6 z-10 flex gap-2.5">
        <button 
          onClick={() => navigate('/')}
          className="px-5 py-2.5 bg-transparent text-neutral-500 hover:text-[#111111] border border-neutral-300 hover:border-neutral-400 text-[10px] font-extrabold uppercase tracking-widest transition rounded-full"
        >
          Exit to Landing
        </button>
      </div>

      {/* Main Login Panel Card Container */}
      <div className="w-full max-w-md bg-white border border-neutral-300/40 p-10 rounded-[28px] shadow-lg space-y-8 flex flex-col justify-center items-center text-center relative z-10">
        
        {/* Brand Header */}
        <div className="space-y-3">
          <div className="inline-flex items-center gap-1.5 px-3 py-1 bg-[#FF3B00]/5 border border-[#FF3B00]/25 font-mono text-[#FF3B00] text-[10px] font-bold uppercase tracking-widest rounded-full">
            <Sparkles className="w-3.5 h-3.5 animate-pulse" />
            <span>Industrial Workspace Portal</span>
          </div>
          <h1 className="text-4xl font-extrabold tracking-tight mt-2 uppercase font-sans">LOG IN</h1>
          <p className="text-[11px] text-neutral-400 uppercase tracking-wide leading-relaxed font-bold font-mono max-w-xs mx-auto">
            AI-powered catalog validation, data enrichment, and explainable product records.
          </p>
        </div>

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-600 text-xs p-4 flex items-start gap-2.5 text-left w-full rounded-[14px]">
            <AlertCircle className="w-4 h-4 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold block uppercase tracking-wider">Authentication Error</span>
              <span className="leading-relaxed font-mono">{error}</span>
            </div>
          </div>
        )}

        {/* Configuration loading or Clerk sign-in form */}
        {loadingConfig ? (
          <div className="flex flex-col items-center justify-center space-y-2 py-6">
            <Loader2 className="w-8 h-8 text-[#FF3B00] animate-spin" />
            <p className="text-xs text-neutral-400 font-mono uppercase tracking-widest font-bold">Syncing auth gates...</p>
          </div>
        ) : showManualInput ? (
          <div className="w-full space-y-5 text-left border-t border-neutral-200 pt-6">
            <div className="space-y-1.5">
              <h3 className="text-xs font-extrabold flex items-center gap-1.5 text-[#111111] uppercase font-mono tracking-wider">
                <Key className="w-4 h-4 text-neutral-400" />
                <span>Configure Clerk Key</span>
              </h3>
              <p className="text-[10px] text-neutral-400 uppercase tracking-wide leading-relaxed font-bold font-mono">
                Clerk Publishable Key is not configured in your `.env` file yet. You can paste your Clerk Publishable Key (starts with `pk_test_`) here to test:
              </p>
            </div>
            
            <div className="space-y-4">
              <input
                type="text"
                placeholder="pk_test_..."
                value={customKeyInput}
                onChange={(e) => setCustomKeyInput(e.target.value)}
                className="w-full bg-neutral-50 border border-neutral-300 text-[#111111] px-4 py-3 text-xs outline-none focus:border-[#FF3B00] transition font-mono rounded-[12px]"
              />
              <div className="flex gap-2">
                <button
                  onClick={saveCustomPublishableKey}
                  disabled={!customKeyInput.trim()}
                  className="flex-1 bg-[#111111] hover:bg-neutral-800 text-white text-[10px] font-bold py-3 px-4 rounded-full transition disabled:opacity-50 uppercase tracking-widest"
                >
                  Apply Key & Reload
                </button>
                {clerkKey && (
                  <button
                    onClick={() => setShowManualInput(false)}
                    className="border border-neutral-300 text-[10px] font-bold px-4 py-3 rounded-full hover:bg-neutral-50 transition uppercase tracking-widest text-neutral-500"
                  >
                    Cancel
                  </button>
                )}
              </div>
            </div>
          </div>
        ) : (
          <div className="w-full flex flex-col items-center justify-center space-y-6 border-t border-neutral-200 pt-6 py-2">
            <div className="text-center space-y-1">
              <h2 className="text-sm font-extrabold text-[#111111] uppercase tracking-wider font-mono">Continue with Google</h2>
              <p className="text-[9px] text-neutral-400 uppercase tracking-widest font-bold font-mono">
                RAMX console access uses Google credentials
              </p>
            </div>
            
            <div className="w-full flex justify-center scale-95 overflow-hidden">
              <SignIn 
                routing="hash"
                fallbackRedirectUrl="/dashboard"
                signUpUrl="/login"
                appearance={{
                  elements: {
                    rootBox: "w-full",
                    card: "bg-transparent border-0 shadow-none p-0 text-[#111111]",
                    headerTitle: "text-[#111111]",
                    headerSubtitle: "text-neutral-400",
                    dividerRow: "hidden",
                    form: "hidden",
                    formField: "hidden",
                    formFieldRow: "hidden",
                    formButtonPrimary: "hidden",
                    footer: "hidden",
                    footerActionText: "hidden",
                    footerActionLink: "hidden",
                    socialButtons: "w-full",
                    socialButtonsBlockButton: "bg-neutral-50 border border-neutral-300 text-[#111111] hover:bg-neutral-100 transition rounded-full w-full py-3.5 flex justify-center items-center gap-3",
                    socialButtonsBlockButtonText: "text-[#111111] font-bold text-[10px] uppercase tracking-widest",
                    socialButtonsProviderIcon__google: "w-4 h-4"
                  }
                }}
              />
            </div>

            <button
              onClick={() => setShowManualInput(true)}
              className="text-[9px] text-neutral-400 hover:text-[#FF3B00] font-bold uppercase tracking-widest font-mono transition mt-2 outline-none"
            >
              Configure Custom API Credentials
            </button>
          </div>
        )}

        {/* Footer */}
        <div className="text-[9.5px] font-bold uppercase tracking-wider font-mono text-neutral-400 leading-relaxed border-t border-neutral-100 pt-4 w-full">
          <span>RAMX SECURITY GATEWAY AUTHENTICATION</span>
        </div>
      </div>
    </div>
  );
};
