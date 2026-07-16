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
import { percentileRank, percentileToColor } from '../colorScale';

interface Props {
  data: CountryAggregate[];
  topN?: number;
}

export default function CountryWinRateChart({ data, topN = 20 }: Props) {
  const allWinRates = data.map((c) => c.win_rate);
  const chartData = data
    .sort((a, b) => b.win_rate - a.win_rate)
    .slice(0, topN)
    .map((c) => ({
      name: c.nation_name,
      win_rate: parseFloat((c.win_rate * 100).toFixed(1)),
      percentile: percentileRank(c.win_rate, allWinRates),
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
          domain={[0, (dataMax: number) => Math.ceil(dataMax / 5) * 5]}
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
          formatter={(value: number) => [`${value}%`, 'Win rate']}
        />
        <Bar dataKey="win_rate" radius={[0, 3, 3, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={percentileToColor(entry.percentile)} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
