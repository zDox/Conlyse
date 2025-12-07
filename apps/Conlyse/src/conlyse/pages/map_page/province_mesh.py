import numpy as np
from conflict_interface.data_types.map_state.static_province import StaticProvince
import mapbox_earcut as earcut


def prepare_provinces(locations: list[StaticProvince]):
    """
    Prepare VBO data for provinces
    Returns:
        [np.ndarray, np.ndarray]: Vertex data and province color index data
    """
    vertex_data = []
    province_color_index_data = []
    max_province_id = 0
    for location in locations:
        # random color for province
        color_index = location.id
        max_province_id = max(max_province_id, color_index)
        border_points = location.borders
        # Skip if less than 3 points
        if len(border_points) < 3:
            continue

        # Flatten coordinates for earcut

        vertices = np.array([[p.x, p.y] for p in border_points], dtype=np.float32)

        # ring_end_indices specifies where each ring ends (for holes)
        # For a single polygon with no holes, it's just [len(border_points)]
        ring_end_indices = np.array([len(vertices)], dtype=np.uint32)

        # Triangulate using earcut
        tri_indices = earcut.triangulate_float32(vertices, ring_end_indices)

        # Convert indices to triangles
        # tri_indices contains indices into the vertices array
        for i in range(0, len(tri_indices), 3):
            a, b, c = tri_indices[i:i + 3]
            triangle = [
                (vertices[a][0], vertices[a][1]),
                (vertices[b][0], vertices[b][1]),
                (vertices[c][0], vertices[c][1])
            ]
            vertex_data.extend(triangle)
            province_color_index_data.append(color_index)
            province_color_index_data.append(color_index)
            province_color_index_data.append(color_index)


    vertex_data = np.array(vertex_data, dtype=np.float32).flatten()
    province_color_index_data = np.array(province_color_index_data, dtype=np.int32)
    assert len(vertex_data) // 2 == len(province_color_index_data)
    print(f"Prepared mesh for {len(locations)} provinces with {len(vertex_data)//2} vertices.")
    return vertex_data, province_color_index_data, max_province_id

class ProvinceMesh:
    def __init__(self, locations: list[StaticProvince]):
        self.vertex_data, self.province_color_index_data, self.max_province_id = prepare_provinces(locations)