"""Section 2.2b — clusters nations by build style (normalized building composition).

Restricted to nations with enough human-played games to stand in for the roster of
player-controlled nations, since the replay data has no explicit "is playable" flag.
"""
import numpy as np
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from sklearn.metrics import silhouette_score
from sklearn.preprocessing import StandardScaler

from ..models.aggregates import ClusterInfo, CountryAggregate, NationSimilarityAggregate

MIN_HUMAN_GAMES = 5
MIN_K, MAX_K = 3, 10
TOP_N_BUILDINGS = 3


class NationSimilarityAggregator:
    """Takes CountryAggregate output (not raw GameData) — building composition is
    already aggregated per nation by CountryAggregator."""

    def aggregate(
        self, country_aggs: list[CountryAggregate]
    ) -> tuple[list[NationSimilarityAggregate], list[ClusterInfo]]:
        nations = [c for c in country_aggs if c.human_games_played >= MIN_HUMAN_GAMES]
        if len(nations) < MIN_K + 1:
            return [], []

        building_ids = sorted({uid for c in nations for uid in c.avg_final_building_counts})
        if not building_ids:
            return [], []

        # Row-normalize each nation's building counts to proportions of its own total,
        # so build *style* is compared rather than raw build volume.
        raw = np.array(
            [[c.avg_final_building_counts.get(uid, 0.0) for uid in building_ids] for c in nations]
        )
        totals = raw.sum(axis=1, keepdims=True)
        proportions = np.divide(raw, totals, out=np.zeros_like(raw), where=totals > 0)

        scaled = StandardScaler().fit_transform(proportions)

        pca_coords = PCA(n_components=2, random_state=0).fit_transform(scaled)

        cluster_ids = _best_kmeans(scaled)

        pop_mean = proportions.mean(axis=0)
        pop_std = proportions.std(axis=0)
        pop_std[pop_std == 0] = 1.0

        nation_results: list[NationSimilarityAggregate] = []
        for i, c in enumerate(nations):
            z_scores = (proportions[i] - pop_mean) / pop_std
            top_idx = np.argsort(z_scores)[::-1][:TOP_N_BUILDINGS]
            nation_results.append(
                NationSimilarityAggregate(
                    nation_name=c.nation_name,
                    games_played=c.games_played,
                    human_games_played=c.human_games_played,
                    cluster_id=int(cluster_ids[i]),
                    pca_x=round(float(pca_coords[i, 0]), 4),
                    pca_y=round(float(pca_coords[i, 1]), 4),
                    top_buildings=[building_ids[j] for j in top_idx],
                )
            )

        clusters: list[ClusterInfo] = []
        for k in sorted(set(cluster_ids.tolist())):
            members = cluster_ids == k
            centroid = proportions[members].mean(axis=0)
            centroid_z = (centroid - pop_mean) / pop_std
            top_idx = np.argsort(centroid_z)[::-1][:TOP_N_BUILDINGS]
            top_buildings = [building_ids[j] for j in top_idx]
            clusters.append(
                ClusterInfo(
                    id=int(k),
                    label=" / ".join(top_buildings[:2]),
                    size=int(members.sum()),
                    top_buildings=top_buildings,
                )
            )

        return nation_results, clusters


def _best_kmeans(scaled: np.ndarray) -> np.ndarray:
    n = scaled.shape[0]
    best_labels = None
    best_score = -1.0
    max_k = min(MAX_K, n - 1)
    for k in range(MIN_K, max_k + 1):
        labels = KMeans(n_clusters=k, n_init=10, random_state=0).fit_predict(scaled)
        if len(set(labels)) < 2:
            continue
        score = silhouette_score(scaled, labels)
        if score > best_score:
            best_score = score
            best_labels = labels
    if best_labels is None:
        best_labels = KMeans(n_clusters=MIN_K, n_init=10, random_state=0).fit_predict(scaled)
    return best_labels
