import React, { useMemo } from 'react';
import {
  CartesianGrid,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts';
import type { ClusterInfo, NationSimilarityAggregate } from '../types';

interface Props {
  data: NationSimilarityAggregate[];
  clusters: ClusterInfo[];
}

const CLUSTER_COLORS = [
  '#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f',
  '#edc948', '#b07aa1', '#ff9da7', '#9c755f', '#bab0ac',
];

function colorForCluster(clusterId: number): string {
  return CLUSTER_COLORS[clusterId % CLUSTER_COLORS.length];
}

interface ScatterPoint {
  name: string;
  x: number;
  y: number;
  humanGames: number;
  topBuildings: string[];
  fill: string;
}

function CustomDot(props: { cx?: number; cy?: number; payload?: ScatterPoint }) {
  const { cx = 0, cy = 0, payload } = props;
  if (!payload) return null;
  return <circle cx={cx} cy={cy} r={5} fill={payload.fill} fillOpacity={0.8} />;
}

function CustomTooltip({ active, payload }: { active?: boolean; payload?: { payload: ScatterPoint }[] }) {
  if (!active || !payload?.length) return null;
  const p = payload[0].payload;
  return (
    <div style={{
      background: 'var(--ifm-background-surface-color)',
      border: '1px solid var(--ifm-color-emphasis-300)',
      borderRadius: 6,
      padding: '6px 10px',
      fontSize: 12,
      color: 'var(--ifm-font-color-base)',
      lineHeight: 1.6,
    }}>
      <div style={{ fontWeight: 600 }}>{p.name}</div>
      <div>{p.humanGames} human games sampled</div>
      <div>Distinctive builds: {p.topBuildings.join(', ')}</div>
    </div>
  );
}

function ClusterLegend({ clusters }: { clusters: ClusterInfo[] }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px 14px', marginTop: 10, fontSize: 11, color: 'var(--ifm-font-color-base)' }}>
      {clusters.map((c) => (
        <span key={c.id} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          <span style={{ width: 8, height: 8, borderRadius: '50%', background: colorForCluster(c.id), display: 'inline-block' }} />
          {c.label} ({c.size})
        </span>
      ))}
    </div>
  );
}

export default function CountrySimilarityScatterChart({ data, clusters }: Props) {
  const points = useMemo<ScatterPoint[]>(
    () => data.map((n) => ({
      name: n.nation_name,
      x: n.pca_x,
      y: n.pca_y,
      humanGames: n.human_games_played,
      topBuildings: n.top_buildings,
      fill: colorForCluster(n.cluster_id),
    })),
    [data],
  );

  if (points.length === 0) return null;

  return (
    <div>
      <ResponsiveContainer width="100%" height={480}>
        <ScatterChart margin={{ top: 24, right: 24, left: 8, bottom: 24 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--ifm-color-emphasis-200)" />
          <XAxis
            type="number"
            dataKey="x"
            tick={false}
            label={{ value: 'Build style (PC1) — proximity = similarity', position: 'insideBottom', offset: -14, fontSize: 11, fill: 'var(--ifm-color-emphasis-500)' }}
          />
          <YAxis
            type="number"
            dataKey="y"
            tick={false}
            label={{ value: 'Build style (PC2)', angle: -90, position: 'insideLeft', offset: 14, fontSize: 11, fill: 'var(--ifm-color-emphasis-500)' }}
          />
          <Tooltip content={<CustomTooltip />} />
          <Scatter data={points} shape={CustomDot} />
        </ScatterChart>
      </ResponsiveContainer>
      <ClusterLegend clusters={clusters} />
    </div>
  );
}
