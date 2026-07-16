import React from 'react';
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { CountryAggregate } from '../types';

interface Props {
  data: CountryAggregate[];
  topN?: number;
}

export default function CountryExpansionChart({ data, topN = 20 }: Props) {
  const chartData = data
    .sort((a, b) => b.avg_expansion - a.avg_expansion)
    .slice(0, topN)
    .map((c) => ({
      name: c.nation_name,
      expansion: parseFloat(c.avg_expansion.toFixed(1)),
      initial: parseFloat(c.avg_initial_provinces.toFixed(1)),
      final: parseFloat(c.avg_final_provinces.toFixed(1)),
    }));

  return (
    <ResponsiveContainer width="100%" height={Math.max(300, chartData.length * 26)}>
      <BarChart
        data={chartData}
        layout="vertical"
        margin={{ top: 8, right: 48, left: 4, bottom: 8 }}
      >
        <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-300)" horizontal={false} />
        <XAxis
          type="number"
          tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
          tickFormatter={(v) => (v > 0 ? `+${v}` : String(v))}
        />
        <YAxis
          type="category"
          dataKey="name"
          tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
          width={95}
        />
        <Tooltip
          contentStyle={{
            background: 'var(--ifm-background-surface-color)',
            border: '1px solid var(--ifm-color-emphasis-300)',
            borderRadius: 6,
            color: 'var(--ifm-font-color-base)',
          }}
          formatter={(value: number, _: string, props) => [
            `${value > 0 ? '+' : ''}${value} provinces (${props.payload.initial} → ${props.payload.final})`,
            'Avg expansion',
          ]}
        />
        <Bar dataKey="expansion" radius={[0, 3, 3, 0]}>
          {chartData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.expansion > 0 ? '#50c878' : '#e74c3c'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
