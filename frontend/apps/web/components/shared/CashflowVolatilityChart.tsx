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
import { useTheme } from '@/components/theme/ThemeProvider';

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
  const { theme } = useTheme();
  const isDark = theme === 'dark';

  const strokeColor = isDark ? '#FFFFFF' : '#472393';
  const gradientColor = isDark ? '#FFFFFF' : '#472393';
  const axisColor = isDark ? '#71717A' : '#94A3B8';
  const dotStroke = isDark ? '#08090A' : '#FFFFFF';
  const refLineColor = isDark ? '#71717A' : '#94A3B8';

  return (
    <Card className={className}>
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-2 pb-4">
        <div className="space-y-1">
          <div className="flex items-center gap-1.5 text-xs text-foreground-muted font-medium uppercase tracking-wider">
            <Activity className="size-3.5 opacity-70" />
            <span>Resilience Tracking</span>
          </div>
          <h3 className="text-base sm:text-lg font-semibold text-foreground tracking-tight">{title}</h3>
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
                <stop offset="5%" stopColor={gradientColor} stopOpacity={isDark ? 0.22 : 0.18} />
                <stop offset="95%" stopColor={gradientColor} stopOpacity={0.0} />
              </linearGradient>
            </defs>

            <XAxis
              dataKey="week"
              stroke={axisColor}
              fontSize={11}
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              stroke={axisColor}
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
                  <div className="rounded-xl bg-surface border border-border p-3 shadow-xl space-y-1 text-foreground">
                    <p className="text-[11px] font-semibold text-foreground-muted uppercase tracking-wider">
                      Week {pt.week}
                    </p>
                    <p className="text-sm font-semibold text-foreground font-mono">
                      Inflow: {formatCurrency(pt.inflow)}
                    </p>
                    <p className="text-xs text-foreground-secondary font-mono">
                      Obligations: {formatCurrency(pt.obligations)}
                    </p>
                    {pt.isDip && (
                      <span className="text-[10px] font-medium text-foreground-muted block pt-1">
                        Cyclical dip absorbed
                      </span>
                    )}
                    {pt.isRecovery && (
                      <span className="text-[10px] font-medium text-foreground block pt-1">
                        Rapid rebound confirmed
                      </span>
                    )}
                  </div>
                );
              }}
            />

            <ReferenceLine
              y={3500}
              stroke={refLineColor}
              strokeDasharray="4 4"
              strokeOpacity={0.6}
              label={{
                value: 'Fixed Obligations (₹3.5k)',
                fill: axisColor,
                fontSize: 10,
                position: 'insideTopRight',
              }}
            />

            <Area
              type="monotone"
              dataKey="inflow"
              stroke={strokeColor}
              strokeWidth={2}
              fill="url(#inflowGradient)"
              activeDot={{ r: 5, fill: strokeColor, stroke: dotStroke, strokeWidth: 2 }}
            />
          </AreaChart>
        </ResponsiveContainer>
      </div>

      {/* Footer Legend */}
      <div className="pt-3 border-t border-border flex items-center justify-between text-xs text-foreground-muted">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-foreground" />
            <span>Weekly Inflow</span>
          </div>
          <div className="flex items-center gap-1.5">
            <span className="size-2 rounded-full bg-foreground-muted/40" />
            <span>Obligation Threshold</span>
          </div>
        </div>

        <span className="text-[11px] text-foreground-secondary font-medium">Resilient Recovery Pattern</span>
      </div>
    </Card>
  );
}
