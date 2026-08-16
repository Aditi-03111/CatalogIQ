import React from 'react';
import { Outlet, Navigate } from 'react-router-dom';
import { useAuth, useUser, SignOutButton } from '@clerk/clerk-react';
import { Bell, Command, Search, Sun, Moon, LogOut } from 'lucide-react';
import { Sidebar } from './Sidebar';
import { useTheme } from '../hooks/useTheme';

export const Layout: React.FC = () => {
  const { theme, toggleTheme } = useTheme();
  const { isSignedIn, isLoaded } = useAuth();
  const { user } = useUser();

  // Show loading state while Clerk is verifying auth status
  if (!isLoaded) {
    return (
      <div className="min-h-screen w-screen flex flex-col justify-center items-center bg-background text-foreground font-mono text-xs">
        <p className="animate-pulse">Loading CatalogIQ Operational Space...</p>
      </div>
    );
  }

  // Auth Guard redirect check
  if (!isSignedIn) {
    return <Navigate to="/login" replace />;
  }

  const userInitials = user?.fullName 
    ? user.fullName.split(' ').map((n: string) => n[0]).join('').substring(0, 2).toUpperCase() 
    : "CM";

  return (
    <div className="app-chrome mesh-grid flex h-screen w-screen overflow-hidden bg-background text-foreground rounded-none relative">
      
      {/* Background Ambient Glows */}
      <div className="absolute top-[-10%] right-[-10%] w-[45vw] h-[45vw] rounded-full glow-1 blur-[130px] pointer-events-none z-0" />
      <div className="absolute bottom-[-10%] left-[20%] w-[55vw] h-[55vw] rounded-full glow-2 blur-[160px] pointer-events-none z-0" />

      <Sidebar />
      
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto z-10 bg-transparent relative">
        <header className="h-16 border-b border-border px-8 flex items-center justify-between shrink-0 bg-background/80 backdrop-blur-md">
          <div className="flex items-center gap-3 min-w-0">
            <div className="hidden md:flex items-center gap-2 h-9 w-[360px] rounded-none border border-border bg-card px-3 text-muted-foreground">
              <Search className="w-4 h-4 text-foreground" />
              <span className="text-xs font-light tracking-wide truncate">Search products, SKUs, attributes...</span>
              <span className="ml-auto inline-flex items-center gap-1 rounded-none border border-border bg-background px-1.5 py-0.5 text-[9px] font-mono text-muted-foreground">
                <Command className="w-2.5 h-2.5" /> K
              </span>
            </div>
            <span className="text-[10px] uppercase tracking-widest px-2.5 py-1 rounded-none bg-[#9B8F77]/10 font-mono text-[#9B8F77] border border-[#9B8F77]/20">
              Live Beta
            </span>
          </div>
          <div className="flex items-center gap-3">
            {/* Theme Toggle Button */}
            <button 
              onClick={toggleTheme}
              className="w-9 h-9 rounded-none border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition flex items-center justify-center"
              title={`Switch to ${theme === 'dark' ? 'Light' : 'Dark'} Mode`}
            >
              {theme === 'dark' ? <Sun className="w-4 h-4" /> : <Moon className="w-4 h-4" />}
            </button>

            <button className="w-9 h-9 rounded-none border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition flex items-center justify-center">
              <Bell className="w-4 h-4" />
            </button>
            
            {user?.imageUrl ? (
              <img 
                src={user.imageUrl} 
                alt={user.fullName || "User"} 
                className="w-9 h-9 rounded-none border border-border object-cover" 
                referrerPolicy="no-referrer" 
              />
            ) : (
              <div className="w-9 h-9 rounded-none border border-foreground bg-card flex items-center justify-center font-mono text-foreground text-xs font-medium">
                {userInitials}
              </div>
            )}
            
            <span className="hidden sm:inline text-xs uppercase tracking-widest font-light text-muted-foreground">
              {user?.fullName || "Catalog Manager"}
            </span>

            <SignOutButton redirectUrl="/login">
              <button
                onClick={() => localStorage.removeItem("token")}
                className="h-9 px-3 rounded-none border border-border bg-card text-muted-foreground hover:text-foreground hover:bg-accent transition flex items-center gap-2 text-[9px] uppercase tracking-widest font-semibold"
                title="Sign out"
              >
                <LogOut className="w-3.5 h-3.5" />
                <span className="hidden lg:inline">Sign Out</span>
              </button>
            </SignOutButton>
          </div>
        </header>
        <div className="flex-1 p-6 lg:p-8 overflow-y-auto bg-transparent">
          <Outlet />
        </div>
      </main>
    </div>
  );
};
