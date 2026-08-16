import React from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight, Sparkles, Sun, Moon } from 'lucide-react';
import { SignIn, SignOutButton, useAuth, useUser } from '@clerk/clerk-react';
import { useTheme } from '../../hooks/useTheme';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { theme, toggleTheme } = useTheme();
  const { isSignedIn, isLoaded } = useAuth();
  const { user } = useUser();

  return (
    <div className="min-h-screen w-full bg-background text-foreground flex flex-col justify-between selection:bg-foreground selection:text-background relative overflow-hidden mesh-grid">
      
      {/* Background Ambient Glows */}
      <div className="absolute top-[-10%] right-[-10%] w-[50vw] h-[50vw] rounded-full glow-1 blur-[130px] pointer-events-none z-10" />
      <div className="absolute bottom-[-10%] left-[10%] w-[60vw] h-[60vw] rounded-full glow-2 blur-[160px] pointer-events-none z-10" />
      
      {/* Top Header */}
      <header className="w-full h-20 px-8 lg:px-12 flex items-center justify-between border-b border-border bg-background/80 backdrop-blur-xl z-30">
        <div className="flex items-center gap-3.5">
          <svg viewBox="0 0 100 100" className="w-6 h-6 text-foreground fill-current">
            <path d="M50 15 L85 85 L68 85 L50 45 L32 85 L15 85 Z" />
          </svg>
          <div>
            <span className="font-serif text-2xl font-medium tracking-normal text-foreground">CatalogIQ</span>
            <span className="hidden md:inline-block ml-3 text-[9px] font-light uppercase tracking-widest text-muted-foreground border-l border-border pl-3">
              Enterprise Catalog Intelligence
            </span>
          </div>
        </div>
        
        <nav className="flex items-center gap-6">
          <span className="hidden sm:inline-block text-[9px] uppercase tracking-widest text-muted-foreground hover:text-foreground cursor-pointer transition">Ingestion</span>
          <span className="hidden sm:inline-block text-[9px] uppercase tracking-widest text-muted-foreground hover:text-foreground cursor-pointer transition">Reconciliation</span>
          <span className="hidden sm:inline-block text-[9px] uppercase tracking-widest text-muted-foreground hover:text-foreground cursor-pointer transition">Provenance</span>
          
          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            className="w-9 h-9 border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition flex items-center justify-center rounded-none"
            title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
          >
            {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
          </button>

          {isLoaded && isSignedIn && user ? (
            <div className="flex items-center gap-2 border border-border bg-card px-3 py-1.5 rounded-none shrink-0">
              {user.imageUrl ? (
                <img 
                  src={user.imageUrl} 
                  alt={user.fullName || "User"} 
                  className="w-6 h-6 rounded-none object-cover border border-border" 
                />
              ) : (
                <div className="w-6 h-6 rounded-none bg-[#9B8F77]/10 flex items-center justify-center font-mono text-[9px] text-[#9B8F77] border border-[#9B8F77]/20">
                  {user.firstName?.[0] || "U"}
                </div>
              )}
              <span className="text-[9px] uppercase font-mono tracking-widest text-muted-foreground hidden md:inline truncate max-w-[100px] mr-1.5">
                {user.firstName || user.fullName || "User"}
              </span>
              <button
                onClick={() => navigate('/dashboard')}
                className="h-6 px-2.5 bg-foreground text-background hover:opacity-90 text-[8px] uppercase tracking-widest font-semibold transition rounded-none"
              >
                Console
              </button>
              <SignOutButton redirectUrl="/login">
                <button
                  onClick={() => localStorage.removeItem("token")}
                  className="h-6 px-2.5 bg-transparent text-muted-foreground hover:text-foreground border border-border hover:bg-accent text-[8px] uppercase tracking-widest font-semibold transition rounded-none"
                >
                  Sign Out
                </button>
              </SignOutButton>
            </div>
          ) : (
            <button
              onClick={() => navigate('/login')}
              className="h-9 px-5 bg-foreground text-background hover:bg-transparent hover:text-foreground border border-foreground text-[9px] uppercase tracking-widest font-semibold transition duration-200 rounded-none"
            >
              Sign In
            </button>
          )}
        </nav>
      </header>

      {/* Main Body Grid */}
      <main className="flex-1 w-full px-8 lg:px-12 py-12 lg:py-16 grid grid-cols-1 lg:grid-cols-2 gap-12 items-center z-20">
        
        {/* Left column: Typography & Call to Actions */}
        <div className="space-y-8 max-w-xl">
          <div className="space-y-5">
            <div className="inline-flex items-center gap-2 border border-border bg-card/60 px-3 py-1.5 text-[9px] uppercase tracking-widest font-medium text-foreground">
              <Sparkles className="w-3.5 h-3.5 text-[#9B8F77]" />
              Multi-Source Ingestion & Entity Resolution
            </div>
            
            <h1 className="text-4xl sm:text-5xl lg:text-6xl font-normal leading-tight font-serif text-foreground tracking-normal">
              Unifying competing data without compromising truth.
            </h1>
            
            <p className="text-xs uppercase tracking-wider leading-relaxed text-muted-foreground font-light max-w-md">
              CatalogIQ ingests unstructured supplier documentation, resolving attributes, validating claims, and establishing clear source evidence provenance.
            </p>
          </div>

          {/* Action buttons */}
          <div className="flex flex-wrap items-center gap-4">
            <button
              onClick={() => navigate(isSignedIn ? '/dashboard' : '/login')}
              className="h-12 px-8 bg-foreground text-background border border-foreground hover:bg-transparent hover:text-foreground text-[10px] uppercase tracking-widest font-semibold transition duration-200 rounded-none flex items-center gap-2.5"
            >
              {isSignedIn ? 'Enter Dashboard' : 'Get Started'} <ArrowRight className="w-4 h-4" />
            </button>
            <button
              onClick={() => navigate('/catalog')}
              className="h-12 px-8 bg-transparent text-muted-foreground hover:text-foreground border border-border hover:bg-card text-[10px] uppercase tracking-widest font-semibold transition duration-200 rounded-none flex items-center gap-2"
            >
              Explore Catalog
            </button>
          </div>

          {/* Minimal Key Indicators */}
          <div className="grid grid-cols-3 gap-6 pt-6 border-t border-border">
            <div className="space-y-1">
              <span className="text-[9px] text-muted-foreground uppercase tracking-widest block font-light">Stage 01</span>
              <span className="font-serif text-sm text-foreground font-medium block">OCR Ingestion</span>
            </div>
            <div className="space-y-1">
              <span className="text-[9px] text-muted-foreground uppercase tracking-widest block font-light">Stage 02</span>
              <span className="font-serif text-sm text-foreground font-medium block">LLM Parsing</span>
            </div>
            <div className="space-y-1">
              <span className="text-[9px] text-muted-foreground uppercase tracking-widest block font-light">Stage 03</span>
              <span className="font-serif text-sm text-foreground font-medium block">Provenance</span>
            </div>
          </div>
        </div>

        {/* Right column: Identity visual with auth action */}
        <div className="w-full flex items-center justify-center lg:justify-end">
          <div className="border border-border p-5 bg-card/85 backdrop-blur-md rounded-none max-w-md w-full relative z-20">
            <div>
              <div className="aspect-square w-full overflow-hidden bg-background relative">
                <img
                  src="/brand_hero.png"
                  alt="CatalogIQ Brand Symbol"
                  className="w-full h-full object-cover brightness-100 contrast-105"
                />
                <div className="absolute inset-0 border border-black/5 pointer-events-none" />
              </div>

              <div className="mt-3.5 flex items-center justify-between text-[9px] text-muted-foreground font-mono tracking-widest uppercase font-light">
                <span>CatalogIQ Identity System</span>
                <span>Ref: CL-00</span>
              </div>

              {isLoaded && !isSignedIn ? (
                <div className="mt-5 border-t border-border pt-5 space-y-4">
                  <div className="text-center">
                    <h2 className="font-serif text-lg font-medium text-foreground">Continue to Console</h2>
                    <p className="text-[10px] text-muted-foreground uppercase tracking-wider font-light">
                      Google accounts only
                    </p>
                  </div>

                  <div className="google-only-clerk w-full flex justify-center overflow-hidden">
                    <SignIn
                      routing="hash"
                      fallbackRedirectUrl="/dashboard"
                      signUpUrl="/login"
                      appearance={{
                        elements: {
                          rootBox: "w-full",
                          card: "bg-transparent border-0 shadow-none p-0 text-foreground w-full",
                          header: "hidden",
                          dividerRow: "hidden",
                          form: "hidden",
                          formField: "hidden",
                          formFieldRow: "hidden",
                          formButtonPrimary: "hidden",
                          footer: "hidden",
                          footerActionText: "hidden",
                          footerActionLink: "hidden",
                          socialButtons: "w-full",
                          socialButtonsBlockButton: "bg-foreground text-background border border-foreground hover:bg-transparent hover:text-foreground transition rounded-none w-full py-3.5 flex justify-center items-center gap-3",
                          socialButtonsBlockButtonText: "font-semibold text-[10px] uppercase tracking-widest",
                          socialButtonsProviderIcon__google: "w-4 h-4",
                        }
                      }}
                    />
                  </div>
                </div>
              ) : null}

              {isLoaded && isSignedIn && (
                <div className="mt-5 border-t border-border pt-5">
                  <button
                    onClick={() => navigate('/dashboard')}
                    className="w-full h-12 bg-foreground text-background border border-foreground hover:bg-transparent hover:text-foreground text-[10px] uppercase tracking-widest font-semibold transition duration-200 rounded-none flex items-center justify-center gap-2.5"
                  >
                    Continue to Dashboard <ArrowRight className="w-4 h-4" />
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>

      </main>

      {/* Bottom Footer bar */}
      <footer className="w-full h-16 border-t border-border px-8 lg:px-12 flex items-center justify-between text-[9px] text-muted-foreground uppercase tracking-widest font-light z-30">
        <span>© 2026 CatalogIQ Platform</span>
        <span>Geometric Restraint & Architect Visual Style</span>
      </footer>

    </div>
  );
};
