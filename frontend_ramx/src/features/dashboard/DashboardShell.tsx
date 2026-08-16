import React, { useState } from 'react';
import plantImage from '../../assets/ramx_industrial_plant.png';

export const DashboardShell: React.FC = () => {
  // Accordion state
  const [expanded, setExpanded] = useState<string | null>('smart');

  // Radial stroke calculation
  const getStrokeOffset = (percentage: number) => {
    const radius = 20;
    const circumference = 2 * Math.PI * radius;
    return circumference - (percentage / 100) * circumference;
  };

  return (
    <div className="w-full max-w-6xl mx-auto text-[#111111] bg-transparent">
      
      {/* 3-Column main layout matching visual mockup */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-10 items-start select-none">
        
        {/* LEFT COLUMN: Title, Orange Alert Box, U3 Sector Widget (5 cols) */}
        <div className="lg:col-span-5 flex flex-col justify-between min-h-[500px] space-y-8">
          
          {/* Typographic Title block */}
          <div className="space-y-4">
            <h1 className="font-extrabold text-[5rem] leading-[0.85] tracking-tighter text-[#111111] font-sans uppercase">
              PLANT<br />OVERVIEW
            </h1>
            <div className="space-y-1">
              <div className="text-[14px] font-bold text-[#FF3B00] tracking-wider uppercase font-mono">BLOCK E5</div>
              <div className="text-[10px] text-neutral-500 uppercase tracking-widest font-extrabold">ALL SYSTEMS OPERATIONAL</div>
            </div>
          </div>

          {/* Vermilion Orange Alert Box */}
          <div className="border border-[#FF3B00]/25 rounded-[20px] overflow-hidden bg-white/70 backdrop-blur-sm shadow-md">
            {/* Header */}
            <div className="bg-[#FF3B00] text-white p-4 flex items-center justify-between font-mono font-bold text-[11px] tracking-wider">
              <div className="flex items-center gap-2">
                <span>FIRE DETECTED</span>
              </div>
              <div className="flex items-center gap-4">
                <span>CODE RED</span>
                <span>14:37:52</span>
                <span className="text-[13px]">↗</span>
              </div>
            </div>
            {/* Message Body */}
            <div className="p-4 space-y-4">
              <p className="text-[10px] text-neutral-500 uppercase tracking-wide leading-relaxed font-bold font-mono">
                A LARGE FIRE HAS BEEN DETECTED IN SECTOR F5. INITIATE PROTOCOLS IMMEDIATELY.
              </p>
              {/* Footer Button */}
              <button className="w-full pt-3.5 border-t border-neutral-200 flex items-center justify-between text-[11px] font-extrabold uppercase tracking-widest text-[#111111] hover:text-[#FF3B00] transition outline-none">
                <span>ACTIVATE ALARM PROTOCOL</span>
                <span className="text-sm">→</span>
              </button>
            </div>
          </div>

          {/* Sector info widget (U3 target circle) */}
          <div className="flex items-center gap-4">
            {/* Target icon */}
            <div className="w-14 h-14 rounded-full border border-neutral-300 flex items-center justify-center relative bg-white shadow-sm">
              <div className="w-10 h-10 rounded-full border border-neutral-200 bg-neutral-50 flex items-center justify-center font-bold text-xs text-neutral-500 font-mono">
                U3
              </div>
              {/* Target pin icon */}
              <div className="absolute top-0 right-1 w-2.5 h-2.5 bg-[#FF3B00] border-2 border-white rounded-full" />
            </div>
            
            {/* evals details */}
            <div className="space-y-0.5">
              <div className="text-[9px] font-bold text-[#FF3B00] tracking-wider uppercase font-mono">SECTOR F5</div>
              <div className="text-[10px] font-extrabold text-[#111111] uppercase tracking-wide leading-snug">
                EMERGENCY! THE EVACUATION HASN'T BEGUN YET!
              </div>
              <button className="text-[10px] text-neutral-400 hover:text-[#FF3B00] font-bold uppercase tracking-widest flex items-center gap-1 transition">
                <span>SWITCH TO UNIT</span>
                <span>↗</span>
              </button>
            </div>
          </div>

        </div>

        {/* CENTER COLUMN: B&W plant photo + Vermilion Diagonal Slash (4 cols) */}
        <div className="lg:col-span-4 relative h-[500px] w-full flex items-center justify-center overflow-hidden rounded-[24px]">
          
          {/* Bold Vermilion slash banner behind the plant */}
          <div className="absolute inset-0 bg-[#FF3B00] origin-top-left rotate-[28deg] -translate-x-[20%] translate-y-[22%] w-[130%] h-[32%] z-0 shadow-lg" />

          {/* Black and White generated plant image */}
          <img 
            src={plantImage} 
            alt="RAMX Industrial Plant" 
            className="w-full h-full object-cover relative z-10 brightness-[0.98] contrast-[1.05]"
          />
        </div>

        {/* RIGHT COLUMN: climate widget, Air sparkline, Reactor dials, Accordions (3 cols) */}
        <div className="lg:col-span-3 space-y-6 pl-0 lg:pl-6 border-l-0 lg:border-l border-neutral-300/40 min-h-[500px]">
          
          {/* Climate Control temperature */}
          <div className="space-y-1">
            <div className="text-[9px] font-extrabold uppercase tracking-wider text-neutral-400 font-mono">CLIMATE CONTROL</div>
            <div className="flex items-baseline gap-0.5 text-[#FF3B00] font-sans font-bold">
              <span className="text-[48px] leading-none tracking-tighter">67</span>
              <span className="text-[20px] leading-none">°</span>
              <span className="text-[18px] leading-none font-mono">.C</span>
            </div>
            <div className="text-[9px] font-extrabold uppercase tracking-wider text-[#FF3B00] font-mono">
              CRITICAL HIGH
            </div>
          </div>

          {/* Circulating Air line chart */}
          <div className="space-y-2">
            <div className="flex justify-between items-center text-[9px] font-bold uppercase tracking-wider text-neutral-400 font-mono">
              <span>CIRCULATING AIR</span>
              <span className="text-[#111111] font-mono">ON</span>
            </div>
            {/* Custom line chart */}
            <div className="h-14 w-full bg-neutral-200/40 rounded-xl border border-neutral-300/30 p-2 flex items-end relative overflow-hidden">
              <svg className="w-full h-full text-[#FF3B00]" viewBox="0 0 100 30" fill="none" stroke="currentColor" strokeWidth="1.6">
                <path 
                  d="M0,15 L15,22 L30,8 L45,18 L60,5 L75,15 L90,8 L100,18" 
                  fill="none" 
                  strokeLinecap="round"
                  strokeLinejoin="round"
                />
                <circle cx="90" cy="8" r="2.5" fill="#FF3B00" />
              </svg>
              {/* Scales */}
              <span className="absolute top-1.5 right-2 text-[7px] text-neutral-400 font-mono">80°</span>
              <span className="absolute top-4 right-2 text-[7px] text-neutral-400 font-mono">60°</span>
              <span className="absolute top-6.5 right-2 text-[7px] text-neutral-400 font-mono">40°</span>
              <span className="absolute bottom-1 right-2 text-[7px] text-neutral-400 font-mono">20°</span>
              
              <span className="absolute bottom-0.5 left-2 text-[7px] text-neutral-400 font-mono">12:00</span>
              <span className="absolute bottom-0.5 left-10 text-[7px] text-neutral-400 font-mono">13:00</span>
              <span className="absolute bottom-0.5 left-18 text-[7px] text-neutral-400 font-mono">14:00</span>
              <span className="absolute bottom-0.5 left-26 text-[7px] text-neutral-400 font-mono">15:00</span>
            </div>
          </div>

          {/* Reactor Status dials */}
          <div className="space-y-3">
            <div className="text-[9px] font-bold uppercase tracking-wider text-neutral-400 font-mono">REACTOR STATUS</div>
            <div className="flex items-center gap-6 justify-around">
              {/* Dial 1: NO2 */}
              <div className="flex flex-col items-center gap-1.5">
                <div className="radial-dial w-16 h-16 bg-neutral-100 border border-neutral-200/50 shadow-inner">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 50 50">
                    <circle cx="25" cy="25" r="20" stroke="#E2E2E1" strokeWidth="4.2" fill="none" />
                    <circle 
                      cx="25" 
                      cy="25" 
                      r="20" 
                      stroke="#FF3B00" 
                      strokeWidth="4.2" 
                      fill="none"
                      strokeDasharray={2 * Math.PI * 20}
                      strokeDashoffset={getStrokeOffset(67)}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute flex flex-col items-center justify-center z-10 text-center">
                    <span className="text-[12px] font-extrabold text-[#111111] font-mono leading-none">67</span>
                    <span className="text-[6px] text-neutral-400 uppercase tracking-widest font-mono mt-0.5">PPM</span>
                  </div>
                </div>
                <span className="text-[8.5px] font-extrabold text-neutral-400 uppercase tracking-widest font-mono">NO₂</span>
              </div>

              {/* Dial 2: CO */}
              <div className="flex flex-col items-center gap-1.5">
                <div className="radial-dial w-16 h-16 bg-neutral-100 border border-neutral-200/50 shadow-inner">
                  <svg className="w-full h-full transform -rotate-90" viewBox="0 0 50 50">
                    <circle cx="25" cy="25" r="20" stroke="#E2E2E1" strokeWidth="4.2" fill="none" />
                    <circle 
                      cx="25" 
                      cy="25" 
                      r="20" 
                      stroke="#111111" 
                      strokeWidth="4.2" 
                      fill="none"
                      strokeDasharray={2 * Math.PI * 20}
                      strokeDashoffset={getStrokeOffset(35)}
                      strokeLinecap="round"
                    />
                  </svg>
                  <div className="absolute flex flex-col items-center justify-center z-10 text-center">
                    <span className="text-[12px] font-extrabold text-[#111111] font-mono leading-none">35</span>
                    <span className="text-[6px] text-neutral-400 uppercase tracking-widest font-mono mt-0.5">PPM</span>
                  </div>
                </div>
                <span className="text-[8.5px] font-extrabold text-neutral-400 uppercase tracking-widest font-mono">CO</span>
              </div>
            </div>
          </div>

          {/* Accordion Expandables */}
          <div className="border-t border-neutral-300/40 pt-3 space-y-2">
            
            {/* Expandable 1 */}
            <div className="border-b border-neutral-200/40 pb-2">
              <button 
                onClick={() => setExpanded(expanded === 'smart' ? null : 'smart')}
                className="w-full flex items-center justify-between text-[10px] font-extrabold uppercase tracking-widest text-[#111111] hover:text-[#FF3B00] transition outline-none"
              >
                <span>SMART MONITORING</span>
                <span className="text-[#FF3B00] text-xs font-mono">{expanded === 'smart' ? '−' : '+'}</span>
              </button>
              {expanded === 'smart' && (
                <div className="mt-2 text-[9px] text-neutral-400 uppercase tracking-widest font-bold font-mono pl-1">
                  ACTIVE
                </div>
              )}
            </div>

            {/* Expandable 2 */}
            <div className="border-b border-neutral-200/40 pb-2">
              <button 
                onClick={() => setExpanded(expanded === 'incident' ? null : 'incident')}
                className="w-full flex items-center justify-between text-[10px] font-extrabold uppercase tracking-widest text-[#111111] hover:text-[#FF3B00] transition outline-none"
              >
                <span>INCIDENT REPORT</span>
                <span className="text-[#FF3B00] text-xs font-mono">{expanded === 'incident' ? '−' : '+'}</span>
              </button>
              {expanded === 'incident' && (
                <div className="mt-2 text-[9px] text-neutral-400 uppercase tracking-widest font-bold font-mono pl-1">
                  1 ACTIVE INCIDENT IN SECTOR F5
                </div>
              )}
            </div>

            {/* Expandable 3 */}
            <div className="pb-1">
              <button 
                onClick={() => setExpanded(expanded === 'logs' ? null : 'logs')}
                className="w-full flex items-center justify-between text-[10px] font-extrabold uppercase tracking-widest text-[#111111] hover:text-[#FF3B00] transition outline-none"
              >
                <span>SYSTEM LOGS</span>
                <span className="text-[#FF3B00] text-xs font-mono">{expanded === 'logs' ? '−' : '+'}</span>
              </button>
              {expanded === 'logs' && (
                <div className="mt-2 text-[9px] text-neutral-400 uppercase tracking-widest font-bold font-mono pl-1">
                  14:37:52 PROTOCOL ACTIVATED
                </div>
              )}
            </div>

          </div>

          {/* Footer Copyright */}
          <div className="text-[9px] text-neutral-400 font-bold uppercase tracking-widest font-mono text-center pt-2">
            © 2026 RAMX INDUSTRIES
          </div>

        </div>

      </div>

    </div>
  );
};
