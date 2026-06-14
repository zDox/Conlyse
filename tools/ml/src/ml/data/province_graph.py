"""
Province adjacency graph for the GNN.

Each map province (land + sea) is a graph node. Edges come from
`StaticMapData.connections_b64` / `.graph` — the unit-movement connection graph
(the same data `Army.get_next_connections()` /
`Map.get_closest_point_on_nearest_connection()` use for pathfinding), NOT polygon
border-touching geometry.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

import numpy as np
from conflict_interface.data_types.newest.static_map_data import StaticMapData
from conflict_interface.data_types.newest.version import VERSION
from conflict_interface.replay.replay_timeline import ReplayTimeline

logger = logging.getLogger(__name__)


@dataclass
class ProvinceGraph:
    map_id: str
    node_ids: np.ndarray  # int64 [N] — node_ids[i] = province id for node index i
    edge_index: np.ndarray  # int64 [2, E] — COO, both directions

    @property
    def num_nodes(self) -> int:
        return len(self.node_ids)

    def id_to_index(self) -> dict[int, int]:
        return {int(pid): i for i, pid in enumerate(self.node_ids)}


def build_province_adjacency(static_map_data: StaticMapData) -> tuple[list[int], np.ndarray]:
    """Returns (node_ids, edge_index) over ALL provinces (land + sea).

    node_ids[i] = province id for node index i (sorted for determinism). edge_index
    is `[2, E]` int64 COO of *node indices* (0..N-1, PyG convention), both directions.
    """
    node_ids = sorted(province.id for province in static_map_data.locations)
    index_of = {province_id: i for i, province_id in enumerate(node_ids)}

    edges: set[tuple[int, int]] = set()
    for province_id in node_ids:
        points = static_map_data.get_points(province_id) or []
        for point in points:
            for neighbor_point in static_map_data.graph.get(point, []):
                neighbor_id = static_map_data.get_province(neighbor_point)
                if neighbor_id is None or neighbor_id == province_id:
                    continue
                edges.add((index_of[province_id], index_of[neighbor_id]))
                edges.add((index_of[neighbor_id], index_of[province_id]))

    if edges:
        edge_index = np.array(sorted(edges), dtype=np.int64).T
    else:
        edge_index = np.zeros((2, 0), dtype=np.int64)

    return node_ids, edge_index


def get_or_build_province_graph(map_id: str, maps_dir: Path, cache_dir: Path) -> ProvinceGraph:
    """Load the province graph for `map_id`, building and caching it if needed.

    Cache: `{cache_dir}/{map_id}.npz`. Missing `.bin` for a referenced `map_id` fails
    loudly — the node-index <-> province-id mapping is baked into every downstream
    tensor, so a silently-missing graph would corrupt training data.
    """
    cache_path = cache_dir / f"{map_id}.npz"
    if cache_path.exists():
        data = np.load(cache_path)
        return ProvinceGraph(map_id=map_id, node_ids=data["node_ids"], edge_index=data["edge_index"])

    bin_path = maps_dir / f"{map_id}.bin"
    if not bin_path.exists():
        raise FileNotFoundError(
            f"Static map data for map_id '{map_id}' not found at {bin_path}. "
            "All maps referenced by the dataset must have a .bin file in maps_dir."
        )

    static_map_data = ReplayTimeline.read_static_map_data(VERSION, bin_path)
    if static_map_data is None:
        raise ValueError(f"Failed to read static map data from {bin_path}")

    node_ids, edge_index = build_province_adjacency(static_map_data)
    node_ids_arr = np.array(node_ids, dtype=np.int64)

    cache_dir.mkdir(parents=True, exist_ok=True)
    np.savez(cache_path, node_ids=node_ids_arr, edge_index=edge_index)
    logger.info(
        "Built province graph for map_id=%s: %d nodes, %d directed edges (cached to %s)",
        map_id, len(node_ids_arr), edge_index.shape[1], cache_path,
    )
    return ProvinceGraph(map_id=map_id, node_ids=node_ids_arr, edge_index=edge_index)
