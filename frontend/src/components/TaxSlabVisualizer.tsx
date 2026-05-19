"use client";
// Tax Slab Visualizer — shows exactly how much tax falls in each slab
// Add to form/page.tsx: import TaxSlabVisualizer from "@/components/TaxSlabVisualizer"
// Usage: <TaxSlabVisualizer income={taxableIncome} regime="new" />

import { useState } from "react";

interface SlabBreakdown {
  label: string;
  from: number;
  to: number;
  rate: number;
  taxable: number;
  tax: number;
  color: string;
}

const NEW_SLABS = [
  { from: 0,       to: 300000,  rate: 0,  color: "#10b981", label: "Nil slab" },
  { from: 300000,  to: 600000,  rate: 5,  color: "#3b82f6", label: "5% slab" },
  { from: 600000,  to: 900000,  rate: 10, color: "#8b5cf6", label: "10% slab" },
  { from: 900000,  to: 1200000, rate: 15, color: "#f59e0b", label: "15% slab" },
  { from: 1200000, to: 1500000, rate: 20, color: "#ef4444", label: "20% slab" },
  { from: 1500000, to: Infinity, rate: 30, color: "#dc2626", label: "30% slab" },
];

const OLD_SLABS = [
  { from: 0,      to: 250000,  rate: 0,  color: "#10b981", label: "Nil slab" },
  { from: 250000, to: 500000,  rate: 5,  color: "#3b82f6", label: "5% slab" },
  { from: 500000, to: 1000000, rate: 20, color: "#f59e0b", label: "20% slab" },
  { from: 1000000, to: Infinity, rate: 30, color: "#ef4444", label: "30% slab" },
];

function computeSlabs(income: number, regime: "new" | "old"): SlabBreakdown[] {
  const slabs = regime === "new" ? NEW_SLABS : OLD_SLABS;
  return slabs.map(s => {
    const taxable = Math.max(0, Math.min(income, s.to === Infinity ? income : s.to) - s.from);
    return {
      label: s.label, from: s.from, to: s.to,
      rate: s.rate, taxable, tax: (taxable * s.rate) / 100, color: s.color,
    };
  }).filter(s => s.taxable > 0 || s.from < income);
}

function r(n: number) {
  return `₹${n.toLocaleString("en-IN")}`;
}

export default function TaxSlabVisualizer({
  income = 1000000,
  regime = "new",
}: {
  income?: number;
  regime?: "new" | "old";
}) {
  const [hover, setHover] = useState<number | null>(null);
  const slabs = computeSlabs(income, regime);
  const totalTax = slabs.reduce((s, b) => s + b.tax, 0);
  const maxTaxable = Math.max(...slabs.map(s => s.taxable), 1);

  return (
    <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <div className="text-xs text-slate-500 uppercase tracking-wider mb-1">Tax Slab Breakdown</div>
          <div className="text-sm text-slate-300">
            Total tax on {r(income)} = <span className="font-bold text-white">{r(totalTax)}</span>
            <span className="text-slate-500 ml-2">({((totalTax / income) * 100).toFixed(1)}% effective rate)</span>
          </div>
        </div>
        <div className="text-xs text-blue-400 bg-blue-500/10 border border-blue-500/20 rounded-full px-3 py-1 font-bold uppercase">
          {regime} regime
        </div>
      </div>

      <div className="space-y-3">
        {slabs.map((slab, i) => {
          const pct = (slab.taxable / maxTaxable) * 100;
          const isHover = hover === i;
          return (
            <div key={i}
              className={`rounded-xl p-3 border transition-all cursor-default
                ${isHover ? "border-white/20 bg-white/5" : "border-slate-800 bg-slate-800/30"}`}
              onMouseEnter={() => setHover(i)}
              onMouseLeave={() => setHover(null)}>
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <div className="w-2.5 h-2.5 rounded-full" style={{ background: slab.color }} />
                  <span className="text-xs font-medium text-slate-300">{slab.label} ({slab.rate}%)</span>
                </div>
                <div className="text-right">
                  <span className="text-xs text-slate-400">{r(slab.taxable)} × {slab.rate}% = </span>
                  <span className="text-sm font-bold text-white ml-1">{r(slab.tax)}</span>
                </div>
              </div>
              <div className="h-2 bg-slate-800 rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-500"
                  style={{ width: `${pct}%`, background: slab.color, opacity: slab.rate === 0 ? 0.3 : 0.8 }} />
              </div>
              {isHover && (
                <div className="mt-2 text-[10px] text-slate-500">
                  Slab range: {r(slab.from)} – {slab.to === Infinity ? "above" : r(slab.to)}
                  {slab.rate === 0 ? " (tax-free)" : ""}
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* 87A rebate note */}
      {totalTax > 0 && income <= (regime === "new" ? 700000 : 500000) && (
        <div className="mt-4 bg-green-500/10 border border-green-500/20 rounded-xl p-3 text-xs text-green-400">
          ✓ <strong>87A rebate applies</strong> — income within ₹{regime === "new" ? "7,00,000" : "5,00,000"} limit.
          Full tax of {r(totalTax)} is waived. Net tax = ₹0.
        </div>
      )}

      {/* Cess */}
      {totalTax > 0 && income > (regime === "new" ? 700000 : 500000) && (
        <div className="mt-3 bg-slate-800/50 rounded-xl p-3 flex justify-between text-xs">
          <span className="text-slate-400">+ Health & Education Cess @ 4%</span>
          <span className="font-bold text-white">{r(Math.round(totalTax * 0.04))}</span>
        </div>
      )}
    </div>
  );
}
