import type {
  BuildingAggregate,
  BuildingTimeSeriesPoint,
  ColumnarData,
  CountryAggregate,
  CountryTimeSeries,
  MoraleTimeSeriesPoint,
  PlayerActivityPoint,
  ProvinceAggregate,
  ProductionTimeSeriesPoint,
  TimeSeriesOutput,
} from './types';

export function deserializeCountries(raw: ColumnarData): CountryAggregate[] {
  const idx = Object.fromEntries(raw.columns.map((c, i) => [c, i]));
  return raw.rows.map((r) => ({
    nation_name:           r[idx.nation_name]           as string,
    games_played:          r[idx.games_played]          as number,
    wins:                  r[idx.wins]                  as number,
    win_rate:              r[idx.win_rate]              as number,
    avg_final_vp:          r[idx.avg_final_vp]          as number,
    avg_placement:         r[idx.avg_placement]         as number,
    median_placement:      r[idx.median_placement]      as number,
    avg_final_provinces:   r[idx.avg_final_provinces]   as number,
    avg_initial_provinces: r[idx.avg_initial_provinces] as number,
    avg_expansion:         r[idx.avg_expansion]         as number,
    avg_provinces_captured:r[idx.avg_provinces_captured]as number,
    avg_provinces_lost:    r[idx.avg_provinces_lost]    as number,
    elimination_rate:          r[idx.elimination_rate]          as number,
    avg_survival_days:         r[idx.avg_survival_days]         as number,
    avg_wars_declared:         r[idx.avg_wars_declared]         as number,
    avg_peace_treaties_signed: r[idx.avg_peace_treaties_signed] as number,
    avg_alliances_formed:      r[idx.avg_alliances_formed]      as number,
    avg_right_of_ways_signed:  r[idx.avg_right_of_ways_signed]  as number,
    avg_total_production:         (r[idx.avg_total_production]         as Record<string, number> | undefined) ?? {},
    avg_production_rate:          (r[idx.avg_production_rate]          as Record<string, number> | undefined) ?? {},
    avg_final_building_counts:    (r[idx.avg_final_building_counts]    as Record<string, number> | undefined) ?? {},
    avg_final_building_levels:    (r[idx.avg_final_building_levels]    as Record<string, number> | undefined) ?? {},
    avg_national_morale:          (r[idx.avg_national_morale]          as number | undefined) ?? 0,
    solo_wins:                    (r[idx.solo_wins]                    as number | undefined) ?? 0,
    coalition_wins:               (r[idx.coalition_wins]               as number | undefined) ?? 0,
    coalition_win_rate:           (r[idx.coalition_win_rate]           as number | undefined) ?? 0,
    avg_winning_coalition_size:   (r[idx.avg_winning_coalition_size]   as number | undefined) ?? 0,
    avg_elimination_pct:          (r[idx.avg_elimination_pct]          as number | null | undefined) ?? null,
  }));
}

export function deserializeProvinces(raw: ColumnarData): ProvinceAggregate[] {
  const idx = Object.fromEntries(raw.columns.map((c, i) => [c, i]));
  return raw.rows.map((r) => ({
    province_id:              r[idx.province_id]              as number,
    province_name:            r[idx.province_name]            as string,
    terrain_type:             r[idx.terrain_type]             as string,
    is_coastal:               r[idx.is_coastal]               as boolean,
    games_appeared:           r[idx.games_appeared]           as number,
    avg_ownership_changes:    r[idx.avg_ownership_changes]    as number,
    contest_frequency:        r[idx.contest_frequency]        as number,
    win_correlation:          r[idx.win_correlation]          as number,
    resource_production_type: r[idx.resource_production_type] as string | null,
    avg_resource_production:  r[idx.avg_resource_production]  as number,
    avg_money_production:     r[idx.avg_money_production]     as number,
    avg_morale:               r[idx.avg_morale]               as number,
    typical_buildings:        (r[idx.typical_buildings]       as Record<string, number> | undefined) ?? {},
  }));
}

export function deserializeBuildings(raw: ColumnarData): BuildingAggregate[] {
  const idx = Object.fromEntries(raw.columns.map((c, i) => [c, i]));
  return raw.rows.map((r) => ({
    upgrade_identifier: r[idx.upgrade_identifier] as string,
    games_appeared:     r[idx.games_appeared]     as number,
    avg_per_game:       r[idx.avg_per_game]       as number,
    avg_per_winner:     r[idx.avg_per_winner]     as number,
    avg_per_loser:      r[idx.avg_per_loser]      as number,
    avg_level:          r[idx.avg_level]          as number,
    avg_per_tier:       (r[idx.avg_per_tier] ?? {}) as Record<string, number>,
  }));
}

type BucketSeries = Record<string, { avg: (number | null)[]; n: (number | null)[] }>;
type ProdSeries = BucketSeries;
type BuildingTypeSeries = Record<string, BucketSeries>;

function _deserializeProdBuckets(
  series: ProdSeries,
  pct_buckets: number[],
): Record<string, ProductionTimeSeriesPoint[]> {
  const result: Record<string, ProductionTimeSeriesPoint[]> = {};
  for (const [rtype, s] of Object.entries(series)) {
    result[rtype] = pct_buckets
      .map((b, i) => s.avg[i] != null
        ? { bucket: b, avg_production: s.avg[i]!, games_sampled: s.n[i]! }
        : null)
      .filter((p): p is ProductionTimeSeriesPoint => p !== null);
  }
  return result;
}

function _deserializeProdDayBuckets(
  series: ProdSeries,
): Record<string, ProductionTimeSeriesPoint[]> {
  const result: Record<string, ProductionTimeSeriesPoint[]> = {};
  for (const [rtype, s] of Object.entries(series)) {
    result[rtype] = s.avg
      .map((v, i) => v != null
        ? { bucket: i, avg_production: v, games_sampled: s.n[i]! }
        : null)
      .filter((p): p is ProductionTimeSeriesPoint => p !== null);
  }
  return result;
}

function _deserializeBldBuckets(
  series: BucketSeries,
  pct_buckets: number[],
): Record<string, BuildingTimeSeriesPoint[]> {
  const result: Record<string, BuildingTimeSeriesPoint[]> = {};
  for (const [uid, s] of Object.entries(series)) {
    result[uid] = pct_buckets
      .map((b, i) => s.avg[i] != null
        ? { bucket: b, avg_count: s.avg[i]!, games_sampled: s.n[i]! }
        : null)
      .filter((p): p is BuildingTimeSeriesPoint => p !== null);
  }
  return result;
}

function _deserializeBldTypeBuckets(
  series: BuildingTypeSeries,
  pct_buckets: number[],
): Record<string, Record<string, BuildingTimeSeriesPoint[]>> {
  const result: Record<string, Record<string, BuildingTimeSeriesPoint[]>> = {};
  for (const [uid, tiers] of Object.entries(series)) {
    result[uid] = _deserializeBldBuckets(tiers, pct_buckets);
  }
  return result;
}

export function deserializeTimeSeries(raw: {
  pct_buckets: number[];
  max_game_days: number;
  generated_at: string;
  pct_alive?: (number | null)[];
  pct_active_human?: (number | null)[];
  pct_passive_human?: (number | null)[];
  pct_ai?: (number | null)[];
  pct_alive_n?: (number | null)[];
  day_alive?: (number | null)[];
  day_active_human?: (number | null)[];
  day_passive_human?: (number | null)[];
  day_ai?: (number | null)[];
  day_alive_n?: (number | null)[];
  countries: Array<{
    nation_name: string;
    games_played: number;
    pct_avg: (number | null)[];
    pct_n:   (number | null)[];
    pct_vp_avg?: (number | null)[];
    day_avg: (number | null)[];
    day_n:   (number | null)[];
    day_vp_avg?: (number | null)[];
    prod_pct?: ProdSeries;
    prod_day?: ProdSeries;
    bld_pct?: BucketSeries;
    bld_type_pct?: BuildingTypeSeries;
    morale_pct_avg?: (number | null)[];
    morale_pct_n?:   (number | null)[];
    morale_day_avg?: (number | null)[];
    morale_day_n?:   (number | null)[];
  }>;
}): TimeSeriesOutput {
  const player_activity_pct: PlayerActivityPoint[] = raw.pct_buckets
    .map((b, i) => raw.pct_alive?.[i] != null
      ? {
          bucket: b,
          avg_alive: raw.pct_alive![i]!,
          avg_active_human: raw.pct_active_human?.[i] ?? 0,
          avg_passive_human: raw.pct_passive_human?.[i] ?? 0,
          avg_ai: raw.pct_ai?.[i] ?? 0,
          games_sampled: (raw.pct_alive_n?.[i] ?? 0) as number,
        }
      : null)
    .filter((p): p is PlayerActivityPoint => p !== null);

  const player_activity_days: PlayerActivityPoint[] = (raw.day_alive ?? [])
    .map((v, i) => v != null
      ? {
          bucket: i,
          avg_alive: v,
          avg_active_human: raw.day_active_human?.[i] ?? 0,
          avg_passive_human: raw.day_passive_human?.[i] ?? 0,
          avg_ai: raw.day_ai?.[i] ?? 0,
          games_sampled: (raw.day_alive_n?.[i] ?? 0) as number,
        }
      : null)
    .filter((p): p is PlayerActivityPoint => p !== null);

  return {
    pct_buckets:  raw.pct_buckets,
    max_game_days: raw.max_game_days,
    generated_at:  raw.generated_at,
    player_activity_pct,
    player_activity_days,
    countries: raw.countries.map((c): CountryTimeSeries => ({
      nation_name:  c.nation_name,
      games_played: c.games_played,
      pct_game: raw.pct_buckets
        .map((b, i) => c.pct_avg[i] != null
          ? { bucket: b, avg_provinces: c.pct_avg[i]!, avg_vp: c.pct_vp_avg?.[i] ?? 0, games_sampled: c.pct_n[i]! }
          : null)
        .filter((p): p is NonNullable<typeof p> => p !== null),
      game_days: c.day_avg
        .map((v, i) => v != null
          ? { bucket: i, avg_provinces: v, avg_vp: c.day_vp_avg?.[i] ?? 0, games_sampled: c.day_n[i]! }
          : null)
        .filter((p): p is NonNullable<typeof p> => p !== null),
      production_pct_game: c.prod_pct
        ? _deserializeProdBuckets(c.prod_pct, raw.pct_buckets)
        : undefined,
      production_game_days: c.prod_day
        ? _deserializeProdDayBuckets(c.prod_day)
        : undefined,
      building_pct_game: c.bld_pct
        ? _deserializeBldBuckets(c.bld_pct, raw.pct_buckets)
        : undefined,
      building_type_pct_game: c.bld_type_pct
        ? _deserializeBldTypeBuckets(c.bld_type_pct, raw.pct_buckets)
        : undefined,
      morale_pct_game: c.morale_pct_avg
        ? raw.pct_buckets
            .map((b, i) => c.morale_pct_avg![i] != null
              ? { bucket: b, avg_morale: c.morale_pct_avg![i]!, games_sampled: (c.morale_pct_n?.[i] ?? 0) as number }
              : null)
            .filter((p): p is MoraleTimeSeriesPoint => p !== null)
        : undefined,
      morale_game_days: c.morale_day_avg
        ? c.morale_day_avg
            .map((v, i) => v != null
              ? { bucket: i, avg_morale: v, games_sampled: (c.morale_day_n?.[i] ?? 0) as number }
              : null)
            .filter((p): p is MoraleTimeSeriesPoint => p !== null)
        : undefined,
    })),
  };
}
