'use client';

import React from 'react';
import {
  ResponsiveContainer,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from 'recharts';
import { Card } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Activity, ShieldCheck } from 'lucide-react';
import { formatCurrency } from '@/lib/utils';

export interface CashflowDataPoint {
  week: string;
  inflow: number;
  obligations: number;
  isDip?: boolean;
  isRecovery?: boolean;
}

interface CashflowVolatilityChartProps {
  data?: CashflowDataPoint[];
  title?: string;
  recoveryRate?: number;
  className?: string;
}

const defaultData: CashflowDataPoint[] = [
  { week: 'W1', inflow: 11200, obligations: 3500 },
  { week: 'W2', inflow: 12400, obligations: 3500 },
  { week: 'W3', inflow: 14100, obligations: 3500 },
  { week: 'W4', inflow: 6800, obligations: 3500, isDip: true },
  { week: 'W5', inflow: 10900, obligations: 3500, isRecovery: true },
  { week: 'W6', inflow: 13500, obligations: 3500 },
  { week: 'W7', inflow: 15200, obligations: 3500 },
  { week: 'W8', inflow: 7400, obligations: 3500, isDip: true },
  { week: 'W9', inflow: 11800, obligations: 3500, isRecovery: true },
  { week: 'W10', inflow: 14200, obligations: 3500 },
  { week: 'W11', inflow: 16100, obligations: 3500 },
  { week: 'W12', inflow: 15400, obligations: 3500 },
];

export function CashflowVolatilityChart({
  data = defaultData,
  title = 'Volatility-Aware Cashflow & Rebound',
  recoveryRate = 94,
  className,
}: CashflowVolatilityChartProps) {
  return (
    <Card className={className}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground font-semibold uppercase tracking-wider">
            <Activity className="size-3.5 text-teal-400" />
            <span>Resilience Tracking</span>
          </div>
          <h3 className="text-lg font-bold text-white tracking-tight">{title}</h3>
        </div>

        <Badge variant="mint" className="text-xs">
          <ShieldCheck className="size-3" />
          <span>{recoveryRate}% Rebound Rate</span>
        </Badge>
      </div>

      {/* Chart Canvas */}
      <div className="h-64 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
            <defs>
              <linearGradient id="inflowGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%" stopColor="#2DD4BF" stopOpacity={0.35} />
                <stop offset="95%" stopColor="#2DD4BF" stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <XAxis
              dataKey="week"
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke="#64748B"
              fontSize={11}
              tickLine={false}
              axisLine={false}
              tickFormatter={(v) => `₹${v / 1000}k`}
            />

            <Tooltip
              content={({ active, payload }) => {
                if (!active || !payload || !payload.length) return null;
                const pt = payload[0].payload as CashflowDataPoint;

                return (
                  <div className="rounded-xl bg-[#0E1F3D] border border-white/[0.12] p-3 shadow-xl space-y-1">
                    <p className="text-[11px] font-bold text-muted-foreground uppercase">
                      Week {pt.week}
                    </p>
                    <p className="text-sm font-bold text-white font-mono">
                      Inflow: {formatCurrency(pt.inflow)}
                    </p>
                    <p className="text-xs text-muted-foreground font-mono">
                      Obligations: {formatCurrency(pt.obligations)}
                    </p>
                    {pt.isDip && (
                      <span className="text-[10px] font-semibold text-amber-300 block pt-1">
                        Cyclical dip absorbed
                      </span>
                    )}
                    {pt.isRecovery && (
                      <span className="text-[10px] font-semibold text-teal-300 block pt-1">
                        Rapid rebound confirmed
                      </span>
                    )}
                  </div>
                );
              }}
            />

            <ReferenceLine
              y={3500}
              stroke="#F87171"
              strokeDasharray="4 4"
              strokeOpacity={0.6}
              label={{
                value: 'Fixed Obligations (₹3.5k)',
                fill: '#94A3B8',
                fontSize: 10,
                position: 'insideTopRight',
              }}
            />

            <Area
              type="monotone"
              dataKey="inflow"
              stroke="#2DD4BF"
              strokeWidth={2.5}
              fill="url(#inflowGradient)"
              activeDot={{ r: 6, fill: '#2DD4BF', stroke: '#060D1F', strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Footer Legend */}
      <div className="pt-3 border-t border-white/[0.06] flex items-center justify-between text-xs text-muted-foreground">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-teal-400" />
            <span>Weekly Inflow</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-red-400/60" />
            <span>Obligation Threshold</span>
          </div>
        </div>

        <span className="text-[11px] text-teal-300">Resilient Recovery Pattern</span>
      </div>
    </Card>
  );
}
