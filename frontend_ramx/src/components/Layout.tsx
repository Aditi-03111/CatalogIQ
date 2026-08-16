import React from 'react';
import { Outlet, Navigate, Link, useLocation } from 'react-router-dom';
import { useAuth, useUser, SignOutButton } from '@clerk/clerk-react';
import { Bell, LogOut, Loader2 } from 'lucide-react';

export const Layout: React.FC = () => {
  const location = useLocation();
  const { isSignedIn, isLoaded } = useAuth();
  const { user } = useUser();

  // Show loading state while Clerk is verifying auth status
  if (!isLoaded) {
    return (
      <div className="min-h-screen w-screen flex flex-col justify-center items-center bg-[#111111] text-white font-mono text-xs">
        <Loader2 className="w-6 h-6 animate-spin text-[#FF3B00] mb-2" />
        <p className="animate-pulse font-medium">Initializing RAMX console...</p>
      </div>
    );
  }

  // Auth Guard redirect check
  if (!isSignedIn) {
    return <Navigate to="/login" replace />;
  }

  const navLinks = [
    { name: 'OVERVIEW', path: '/dashboard' },
    { name: 'MANAGEMENT', path: '/catalog' },
    { name: 'REPORTS', path: '/unilog' },
    { name: 'ANALYTICS', path: '/jobs' },
  ];

  return (
    <div className="min-h-screen w-screen bg-[#111111] flex items-center justify-center p-4 lg:p-8 overflow-hidden relative font-sans bg-[radial-gradient(ellipse_at_left,_var(--tw-gradient-stops))] from-red-950/40 via-[#161616] to-[#0A0A0A]">
      
      {/* Sunlight beam cast overlay */}
      <div className="absolute top-0 right-0 w-[50%] h-[150%] bg-gradient-to-bl from-white/[0.04] to-transparent pointer-events-none z-0 transform rotate-12 origin-top-right" />

      {/* Floating White Dashboard Card matching reference photo */}
      <div className="w-full max-w-7xl h-[90vh] bg-[#F4F4F4] rounded-[36px] shadow-[0_30px_70px_rgba(0,0,0,0.65)] flex flex-col overflow-hidden relative z-10 border border-white/5">
        
        {/* Horizontal Nav Bar */}
        <header className="h-20 px-12 flex items-center justify-between shrink-0 bg-transparent border-b border-neutral-300/40">
          
          {/* Logo and Brand */}
          <Link to="/dashboard" className="flex items-center gap-2.5 outline-none text-[#111111]">
            <div className="w-5 h-5 flex items-center justify-center border-2 border-[#111111] rounded font-bold relative">
              <span className="text-[12px] absolute font-extrabold rotate-45">+</span>
            </div>
            <span className="font-extrabold tracking-widest text-[14px] uppercase font-mono">RAMX</span>
          </Link>

          {/* Center Navigation Links */}
          <nav className="flex items-center gap-8">
            {navLinks.map((link) => {
              const isActive = location.pathname.startsWith(link.path);
              return (
                <Link
                  key={link.name}
                  to={link.path}
                  className="group flex flex-col items-center py-2 text-[11px] font-bold tracking-wider transition outline-none"
                >
                  <span className={isActive ? 'text-[#FF3B00]' : 'text-neutral-500 hover:text-[#111111]'}>
                    {link.name}
                  </span>
                  <span 
                    className={`w-[5px] h-[5px] rounded-full mt-1.5 transition-all duration-300 ${
                      isActive ? 'bg-[#FF3B00] scale-100 opacity-100' : 'bg-transparent scale-0 opacity-0 group-hover:bg-neutral-400 group-hover:scale-75 group-hover:opacity-60'
                    }`}
                  />
                </Link>
              );
            })}
          </nav>

          {/* Action Button & User Actions */}
          <div className="flex items-center gap-5">
            
            <button 
              onClick={() => window.print()}
              className="bg-[#111111] hover:bg-neutral-800 text-white text-[10px] font-bold px-5 py-2.5 rounded-full flex items-center gap-1.5 transition shadow-sm"
            >
              <span>SAVE REPORT</span>
              <span className="font-semibold text-xs leading-none">↗</span>
            </button>

            <button className="text-neutral-500 hover:text-[#111111] transition relative">
              <Bell className="w-4 h-4" />
              <span className="absolute top-0 right-0 w-1 h-1 bg-[#FF3B00] rounded-full" />
            </button>

            {user?.imageUrl ? (
              <img 
                src={user.imageUrl} 
                alt={user.fullName || "User Avatar"} 
                className="w-8 h-8 rounded-full object-cover border border-neutral-300 shadow-sm" 
                referrerPolicy="no-referrer" 
              />
            ) : (
              <div className="w-8 h-8 rounded-full bg-neutral-200 border border-neutral-300 flex items-center justify-center font-bold text-xs">
                U
              </div>
            )}

            <SignOutButton redirectUrl="/login">
              <button
                onClick={() => localStorage.removeItem("token")}
                className="text-neutral-500 hover:text-[#FF3B00] transition flex items-center gap-1 text-[11px] font-bold uppercase tracking-wider"
                title="Sign out"
              >
                <LogOut className="w-4 h-4" />
              </button>
            </SignOutButton>

          </div>
        </header>

        {/* Floating Content Body */}
        <main className="flex-1 p-12 overflow-y-auto bg-transparent">
          <Outlet />
        </main>

      </div>
    </div>
  );
};
