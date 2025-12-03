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
    province_colors = []
    max_province_id = 0
    for location in locations:
        if location.id not in (305, 5412):
            continue
        print(location.borders)
        print(location.id)
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
            province_color_index_data.append(color_index % 1000)
            # Print the triangle coordinates for inspection
            print(f"Triangle {i // 3}: {triangle}")

    for i in range(1000):
        color = (np.random.rand(), np.random.rand(), np.random.rand())
        province_colors.append(color)


    vertex_data = np.array(vertex_data, dtype=np.float32)
    province_color_index_data = np.array(province_color_index_data, dtype=np.int32)
    color_data = np.array(province_colors, dtype=np.float32).flatten()
    print(color_data[8: 8+3])
    print(f"Prepared {len(vertex_data)//3} triangles for provinces.")
    print(vertex_data)
    print(province_color_index_data)
    return vertex_data.flatten(), province_color_index_data, color_data, max_province_id