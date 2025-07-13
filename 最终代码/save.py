import os
import struct

BLOCK_SIZE = 8192
FLOAT_SIZE = 8
POINT_SIZE = FLOAT_SIZE * 3


def parse_plt_file(file_path):
    points = []
    with open(file_path, 'r') as f:
        for line in f:
            try:
                parts = line.strip().split()
                if len(parts) != 3:
                    continue
                lat = float(parts[0])
                lon = float(parts[1])
                alt = float(parts[2])
                points.append((lat, lon, alt))
            except ValueError:
                continue
    return points


def pack_points_to_blocks(points):

    blocks = []
    block = []
    block_size = 0
    block_index = 0

    for pt in points:
        if block_size + POINT_SIZE > BLOCK_SIZE:
            blocks.append((block_index, block))
            block_index += 1
            block = []
            block_size = 0

        block.append(pt)
        block_size += POINT_SIZE

    if block:
        blocks.append((block_index, block))

    return blocks


def write_blocks_to_files(blocks, output_dir='blocks'):

    os.makedirs(output_dir, exist_ok=True)

    for block_index, block_points in blocks:
        file_path = os.path.join(output_dir, f"block_{block_index}.bin")
        with open(file_path, 'wb') as f:
            for pt in block_points:
                f.write(struct.pack('ddd', pt[0], pt[1], pt[2]))  # float64

        print(f" 写入块文件: {file_path}（包含 {len(block_points)} 个点）")


def main(plt_path):
    points = parse_plt_file(plt_path)
    print(f"Loaded {len(points)} points.")

    blocks = pack_points_to_blocks(points)
    print(f"Packed into {len(blocks)} blocks.")


    for block_index, block_points in blocks:
        mbr = compute_mbr(block_points)
        print(f"Block {block_index}: MBR = {mbr}")

    #写入文件
    write_blocks_to_files(blocks)


def compute_mbr(block_points):
    lats = [p[0] for p in block_points]
    lons = [p[1] for p in block_points]
    alts = [p[2] for p in block_points]
    return {
        'min_lat': min(lats),
        'max_lat': max(lats),
        'min_lon': min(lons),
        'max_lon': max(lons),
        'min_alt': min(alts),
        'max_alt': max(alts),
    }


if __name__ == '__main__':
    main("output.plt")
