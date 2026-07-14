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

export default function CountryEliminationChart({ data, topN = 20 }: Props) {
  const chartData = data
    .sort((a, b) => b.elimination_rate - a.elimination_rate)
    .slice(0, topN)
    .map((c) => ({
      name: c.nation_name,
      elimination_rate: parseFloat((c.elimination_rate * 100).toFixed(1)),
      survival_days: parseFloat(c.avg_survival_days.toFixed(1)),
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
          domain={[0, 100]}
          tickFormatter={(v) => `${v}%`}
          tick={{ fontSize: 11, fill: 'var(--ifm-font-color-base)' }}
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
            `${value}% eliminated · ${props.payload.survival_days}d avg survival`,
            'Elimination rate',
          ]}
        />
        <Bar dataKey="elimination_rate" radius={[0, 3, 3, 0]}>
          {chartData.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={entry.elimination_rate < 25 ? '#50c878' : entry.elimination_rate < 50 ? '#f5a623' : '#e74c3c'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
