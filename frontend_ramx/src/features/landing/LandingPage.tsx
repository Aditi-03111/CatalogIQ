import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Sparkles } from 'lucide-react';
import { SignIn, SignOutButton, useAuth, useUser } from '@clerk/clerk-react';
import plantImage from '../../assets/ramx_industrial_plant.png';

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { isSignedIn, isLoaded } = useAuth();
  const { user } = useUser();

  const navLinks = [
    { name: 'OVERVIEW', path: '/dashboard' },
    { name: 'MANAGEMENT', path: '/catalog' },
    { name: 'REPORTS', path: '/upload' },
    { name: 'ANALYTICS', path: '/jobs' },
  ];

  return (
    <div className="min-h-screen w-full bg-[#ECECEB] text-[#111111] flex flex-col justify-between selection:bg-[#FF3B00] selection:text-white relative overflow-hidden font-sans">
      
      {/* Top Header navbar matching RAMX */}
      <header className="w-full h-20 px-8 lg:px-12 flex items-center justify-between border-b border-neutral-300/40 bg-[#ECECEB] z-30">
        <div className="flex items-center gap-2.5">
          <div className="w-5 h-5 flex items-center justify-center border-2 border-[#111111] rounded font-bold relative">
            <span className="text-[12px] absolute font-extrabold rotate-45">+</span>
          </div>
          <span className="font-extrabold tracking-widest text-[14px] uppercase font-mono text-[#111111]">RAMX</span>
        </div>
        
        <nav className="flex items-center gap-8">
          {navLinks.map((link) => (
            <span 
              key={link.name}
              onClick={() => navigate(link.path)}
              className="text-[11px] font-bold tracking-wider text-neutral-500 hover:text-[#111111] cursor-pointer transition uppercase"
            >
              {link.name}
            </span>
          ))}

          {isLoaded && isSignedIn && user ? (
            <div className="flex items-center gap-3.5 pl-4 border-l border-neutral-300">
              {user.imageUrl ? (
                <img 
                  src={user.imageUrl} 
                  alt={user.fullName || "User"} 
                  className="w-7 h-7 rounded-full object-cover border border-neutral-300" 
                />
              ) : (
                <div className="w-7 h-7 rounded-full bg-neutral-200 border border-neutral-300 flex items-center justify-center font-bold text-[10px]">
                  U
                </div>
              )}
              <button
                onClick={() => navigate('/dashboard')}
                className="bg-[#111111] hover:bg-neutral-800 text-white text-[10px] font-bold px-4 py-2 rounded-full transition"
              >
                CONSOLE ↗
              </button>
              <SignOutButton redirectUrl="/login">
                <button
                  onClick={() => localStorage.removeItem("token")}
                  className="text-neutral-500 hover:text-[#FF3B00] text-[10px] font-bold transition uppercase"
                >
                  Sign Out
                </button>
              </SignOutButton>
            </div>
          ) : (
            <button
              onClick={() => navigate('/login')}
              className="bg-[#111111] hover:bg-neutral-800 text-white text-[10px] font-bold px-5 py-2.5 rounded-full transition"
            >
              SIGN IN ↗
            </button>
          )}
        </nav>
      </header>

      {/* Main Body Layout matching Dribbble spacing */}
      <main className="flex-1 w-full px-8 lg:px-12 py-12 lg:py-16 grid grid-cols-1 lg:grid-cols-12 gap-12 items-center z-20 max-w-7xl mx-auto">
        
        {/* Left Column: RAMX industrial hero text (7 cols) */}
        <div className="lg:col-span-7 space-y-10">
          <div className="space-y-6">
            <div className="inline-flex items-center gap-2 text-[10px] font-bold text-[#FF3B00] tracking-wider uppercase font-mono">
              <Sparkles className="w-3.5 h-3.5" />
              <span>Catalog Ingestion & Intelligence</span>
            </div>
            
            <h1 className="text-5xl sm:text-6xl lg:text-7xl font-bold leading-[0.9] tracking-tighter text-[#111111] uppercase font-sans">
              PRODUCT DATA<br />THAT EXPLAINS<br />ITSELF.
            </h1>
            
            <p className="text-[11px] uppercase tracking-wide leading-relaxed text-neutral-500 font-bold font-mono max-w-md">
              RAMX catalog intelligence transforms raw industrial datasheets into verified attributes, confidence metrics, and structured catalog specs.
            </p>
          </div>

          {/* Call to action buttons */}
          <div className="flex flex-wrap items-center gap-4">
            <button
              onClick={() => navigate(isSignedIn ? '/dashboard' : '/login')}
              className="h-12 px-8 bg-[#111111] hover:bg-neutral-800 text-white text-[10px] uppercase tracking-widest font-bold transition rounded-full flex items-center gap-2 shadow-sm"
            >
              <span>ENTER WORKSPACE</span>
              <span className="font-semibold text-xs leading-none">↗</span>
            </button>
            <button
              onClick={() => navigate('/catalog')}
              className="h-12 px-8 bg-transparent text-neutral-500 hover:text-[#111111] border border-neutral-300 hover:border-neutral-400 text-[10px] uppercase tracking-widest font-bold transition rounded-full"
            >
              EXPLORE CATALOG
            </button>
          </div>

          {/* Stages bar */}
          <div className="grid grid-cols-3 gap-6 pt-8 border-t border-neutral-300/60 max-w-lg">
            <div className="space-y-1">
              <span className="text-[9px] text-neutral-400 uppercase tracking-widest block font-bold font-mono">STAGE 01</span>
              <span className="text-[11px] text-[#111111] font-bold uppercase block">LAYOUT PARSING</span>
            </div>
            <div className="space-y-1">
              <span className="text-[9px] text-neutral-400 uppercase tracking-widest block font-bold font-mono">STAGE 02</span>
              <span className="text-[11px] text-[#111111] font-bold uppercase block">AI EXTRACTION</span>
            </div>
            <div className="space-y-1">
              <span className="text-[9px] text-neutral-400 uppercase tracking-widest block font-bold font-mono">STAGE 03</span>
              <span className="text-[11px] text-[#111111] font-bold uppercase block">VALIDATION RUNS</span>
            </div>
          </div>
        </div>

        {/* Right Column: Visual Frame with plant image and diagonal slash (5 cols) */}
        <div className="lg:col-span-5 w-full flex justify-center lg:justify-end">
          <div className="border border-neutral-300/40 p-5 bg-white rounded-[28px] shadow-lg max-w-md w-full relative z-20">
            {isLoaded && !isSignedIn ? (
              <div className="w-full flex flex-col items-center py-6">
                <div className="mb-6 text-center space-y-1.5">
                  <h2 className="text-lg font-bold text-[#111111] uppercase font-mono tracking-wide">SIGN IN TO RAMX</h2>
                  <p className="text-[10px] text-neutral-400 uppercase tracking-wider font-bold">ACCESS CONTROL CONSOLE</p>
                </div>
                <SignIn 
                  routing="hash"
                  fallbackRedirectUrl="/dashboard"
                  signUpUrl="/login"
                  appearance={{
                    elements: {
                      rootBox: "w-full",
                      card: "bg-transparent border-0 shadow-none p-0 text-[#111111] w-full",
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
                      socialButtonsBlockButton: "bg-neutral-50 border border-neutral-300 text-[#111111] hover:bg-neutral-100 transition rounded-full w-full py-3.5 flex justify-center items-center gap-3",
                      socialButtonsBlockButtonText: "text-[#111111] font-bold text-[10px] uppercase tracking-widest",
                      socialButtonsProviderIcon__google: "w-4 h-4",
                    }
                  }}
                />
              </div>
            ) : (
              <div className="space-y-4">
                {/* Visual plant frame */}
                <div className="aspect-square w-full overflow-hidden bg-neutral-100 rounded-[20px] relative flex items-center justify-center">
                  
                  {/* Diagonal vermilion banner */}
                  <div className="absolute inset-0 bg-[#FF3B00] origin-top-left rotate-[28deg] -translate-x-[25%] translate-y-[22%] w-[130%] h-[32%] z-0" />
                  
                  <img 
                    src={plantImage} 
                    alt="RAMX Industrial Plant" 
                    className="w-full h-full object-cover relative z-10 brightness-[0.98] contrast-[1.05]"
                  />
                </div>
                
                {/* Sub-label under picture */}
                <div className="flex items-center justify-between text-[9px] text-neutral-400 font-mono tracking-widest uppercase font-bold">
                  <span>RAMX DATA LABS</span>
                  <span>REF: RX-2026</span>
                </div>
              </div>
            )}
          </div>
        </div>

      </main>

      {/* Bottom Footer bar */}
      <footer className="w-full h-16 border-t border-neutral-300/40 px-8 lg:px-12 flex items-center justify-between text-[9px] text-neutral-400 uppercase tracking-widest font-bold font-mono z-30">
        <span>© 2026 RAMX INDUSTRIES</span>
        <span>GEOMETRIC LIGHT INDUSTRIAL DESIGN PLATFORM</span>
      </footer>

    </div>
  );
};
