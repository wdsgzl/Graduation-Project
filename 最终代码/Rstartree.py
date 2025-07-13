import os
import struct
import random
import time
import pandas as pd
from typing import List, Tuple
from math import ceil
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from collections import Counter


POINT_STRUCT = "ddd"
POINT_SIZE = struct.calcsize(POINT_STRUCT)
MAX_ENTRIES = 4
MIN_ENTRIES = 2
NODE_FOLDER = "nodes"
BLOCK_FILES = [f"blocks/block_{i}.bin" for i in range(658)]


NUM_QUERIES = 100
PRECISION = 1e-3
os.makedirs(NODE_FOLDER, exist_ok=True)

#初始化生成立方体
class MBR:
    def __init__(self, minx, miny, minz, maxx, maxy, maxz):
        self.minx, self.miny, self.minz = minx, miny, minz
        self.maxx, self.maxy, self.maxz = maxx, maxy, maxz

    def extend(self, other):
        self.minx = min(self.minx, other.minx)
        self.miny = min(self.miny, other.miny)
        self.minz = min(self.minz, other.minz)
        self.maxx = max(self.maxx, other.maxx)
        self.maxy = max(self.maxy, other.maxy)
        self.maxz = max(self.maxz, other.maxz)

    def intersects(self, other):
        return not (self.maxx < other.minx or self.minx > other.maxx or
                    self.maxy < other.miny or self.miny > other.maxy or
                    self.maxz < other.minz or self.minz > other.maxz)

    def to_tuple(self):
        return (self.minx, self.miny, self.minz, self.maxx, self.maxy, self.maxz)

class LeafEntry:
    def __init__(self, mbr: MBR, block_id: int, index_in_block: int):
        self.mbr = mbr                 #当前条目的最小立方体
        self.block_id = block_id        #包含数据点所在数据块
        self.index = index_in_block     #块内位置

class InternalEntry:
    def __init__(self, mbr: MBR, child_page: int):
        self.mbr = mbr
        self.child = child_page         #孩子的节点号

def group_entries(items: List, max_per_group: int = MAX_ENTRIES) -> List[List]:
    n = len(items)
    if n == 0:                  #判空
        return []
    if n <= max_per_group:      #判非满
        return [items]
    # 判满
    G = ceil(n / max_per_group)
    max_groups = max(1, n // MIN_ENTRIES)
    G = min(G, max_groups)
    base = n // G
    extra = n % G
    groups = []
    idx = 0
    for i in range(G):
        size = base + (1 if i < extra else 0)
        groups.append(items[idx:idx + size])
        idx += size
    return groups

class RStarTreeDisk:
    def __init__(self):
        self.next_page_id = 0
        self.root_page = None

    def build_from_blocks(self, block_files: List[str]):
        leaf_entries = []
        #读取分块文件
        for block_id, file_path in enumerate(block_files):
            with open(file_path, "rb") as f:
                data = f.read()
            num_points = len(data)
            for i in range(num_points):
                lon, lat, alt = struct.unpack(POINT_STRUCT, data[i * POINT_SIZE:(i + 1) * POINT_SIZE])#按照经纬海拔读取数据
                mbr = MBR(lon, lat, alt, lon, lat, alt)#将每个点的坐标都作为立方体的上下界
                leaf_entries.append(LeafEntry(mbr, block_id, i))
        leaf_entries.sort(key=lambda e: (e.mbr.minx, e.mbr.miny, e.mbr.minz)) #相近的立方体划为一组
        leaf_pages = []
        for group in group_entries(leaf_entries):
            page = self._write_node(True, group)
            leaf_pages.append((self._compute_mbr(group), page))#将点扩展立方体
        self._build_internal(leaf_pages)

    #生成节点立方体
    def _compute_mbr(self, entries: List) -> MBR:
        mbr = MBR(*entries[0].mbr.to_tuple())
        for e in entries[1:]:
            mbr.extend(e.mbr)
        return mbr

    #构建R*树
    def _build_internal(self, nodes: List[Tuple[MBR, int]]):
        while len(nodes) > 1:
            nodes.sort(key=lambda x: (x[0].minx, x[0].miny, x[0].minz))
            next_level = []
            for group in group_entries(nodes):
                entries = [InternalEntry(mbr, pid) for mbr, pid in group]
                page = self._write_node(False, entries)
                next_level.append((self._compute_mbr(entries), page))
            nodes = next_level
        self.root_page = nodes[0][1]

    #索引写入文件
    def _write_node(self, is_leaf: bool, entries: List):
        page_id = self.next_page_id
        self.next_page_id += 1
        path = os.path.join(NODE_FOLDER, f"node_{page_id}.bin")
        #按照设计的索引结构把索引写入文件
        with open(path, "wb") as f:
            f.write(struct.pack("i", page_id))
            f.write(struct.pack("?", is_leaf))
            f.write(struct.pack("i", len(entries)))
            for entry in entries:
                f.write(struct.pack("6d", *entry.mbr.to_tuple()))
                if is_leaf:
                    f.write(struct.pack("ii", entry.block_id, entry.index))
                else:
                    f.write(struct.pack("i", entry.child))
        return page_id

#读取节点中的立方体范围
def get_tree_mbr(root_page_id: int) -> MBR:
    path = os.path.join(NODE_FOLDER, f"node_{root_page_id}.bin")
    with open(path, "rb") as f:
        f.read(4)
        is_leaf = struct.unpack("?", f.read(1))[0]
        count = struct.unpack("i", f.read(4))[0]
        bounds = [None] * 6
        for _ in range(count):
            m = struct.unpack("6d", f.read(48))
            bounds = [m[i] if bounds[i] is None else min(bounds[i], m[i]) if i < 3 else max(bounds[i], m[i]) for i in range(6)]
            f.read(8 if is_leaf else 4)
        return MBR(*bounds)#返回最大查询范围


#生成查询立方体
def generate_query_mbr(root_mbr: MBR, scale: float) -> MBR:
    # dx = (root_mbr.maxx - root_mbr.minx) * scale ** (1/3)
    # dy = (root_mbr.maxy - root_mbr.miny) * scale ** (1/3)
    # dz = (root_mbr.maxz - root_mbr.minz) * scale ** (1/3)
    # cx = random.uniform(root_mbr.minx + dx/2, root_mbr.maxx - dx/2)
    # cy = random.uniform(root_mbr.miny + dy/2, root_mbr.maxy - dy/2)
    # cz = random.uniform(root_mbr.minz + dz/2, root_mbr.maxz - dz/2)
    dx = (root_mbr.maxx - root_mbr.minx) * scale ** (1/3)
    dy = (root_mbr.maxy - root_mbr.miny) * scale ** (1/3)
    dz = (400 - (50)) * scale ** (1/3)
    cx = random.uniform(root_mbr.minx + dx/2, root_mbr.maxx - dx/2)
    cy = random.uniform(root_mbr.miny + dy/2, root_mbr.maxy - dy/2)
    cz = random.uniform(50 + dz/2, 400 - dz/2)
    return MBR(cx - dx/2, cy - dy/2, cz - dz/2, cx + dx/2, cy + dy/2, cz + dz/2)

#按照索引查询
def query_rstar_tree(page_id: int, query: MBR, node_io: Counter, block_io: Counter, hits: List[Tuple]):
    path = os.path.join(NODE_FOLDER, f"node_{page_id}.bin")
    if not os.path.exists(path):
        return
    node_io[page_id] += 1#统计IO次数
    with open(path, "rb") as f:
        f.read(4)
        is_leaf = struct.unpack("?", f.read(1))[0]
        count = struct.unpack("i", f.read(4))[0]
        for _ in range(count):
            mbr_vals = struct.unpack("6d", f.read(48))#读取节点所有条目
            mbr = MBR(*mbr_vals)
            if not mbr.intersects(query):#判无重叠
                f.read(8 if is_leaf else 4)
                continue
            if is_leaf:#判叶子节点，打开数据块，读取数据点
                block_id, idx = struct.unpack("ii", f.read(8))
                if 0 <= block_id < len(BLOCK_FILES):
                    block_io[block_id] += 1#统计I/o次数
                    with open(BLOCK_FILES[block_id], "rb") as b:
                        b.seek(idx * POINT_SIZE)
                        pt = struct.unpack(POINT_STRUCT, b.read(POINT_SIZE))
                        if all([query.minx <= pt[0] <= query.maxx,
                                query.miny <= pt[1] <= query.maxy,
                                query.minz <= pt[2] <= query.maxz]):
                            hits.append(pt)
            else:
                child_id = struct.unpack("i", f.read(4))[0]
                query_rstar_tree(child_id, query, node_io, block_io, hits)#递归寻找

#执行查询
def run_queries(root_page_id: int):
    root_mbr = get_tree_mbr(root_page_id)
    stats = []
    all_hits_sample = []

    for _ in range(NUM_QUERIES):
        q = generate_query_mbr(root_mbr, PRECISION)
        node_io, block_io, hits = Counter(), Counter(), []
        start = time.time()
        query_rstar_tree(root_page_id, q, node_io, block_io, hits)
        elapsed = (time.time() - start) * 1000
        stats.append((sum(node_io.values()), sum(block_io.values()), elapsed, len(hits)))
        #print(block_io)
        if not all_hits_sample and hits:
            all_hits_sample = hits[:]

    df = pd.DataFrame(stats, columns=["节点IO", "块IO", "响应时间", "命中情况"])
    df["总IO"] = df["节点IO"] + df["块IO"]
    print("\n总情况:")
    print(df.sum())
    return df.mean(), all_hits_sample

#查询结果可视化
def visualize_hits(hits):
    if not hits:
        print("无查找结果666")
        return

    x = [p[0] for p in hits]
    y = [p[1] for p in hits]
    z = [p[2] for p in hits]

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(x, y, z, c='red', marker='o', s=3)
    ax.xaxis.set_major_formatter(ticker.FormatStrFormatter('%.4f'))
    ax.yaxis.set_major_formatter(ticker.FormatStrFormatter('%.4f'))
    ax.zaxis.set_major_formatter(ticker.FormatStrFormatter('%.1f'))
    plt.tight_layout()
    plt.show()

if __name__ == "__main__":
    mode = "query" #设置程序执行模式
    #建立索引模式
    if mode == "build":
        tree = RStarTreeDisk()
        tree.build_from_blocks(BLOCK_FILES)
        print(f"[INFO] 构建完成，根节点为 node_{tree.root_page}.bin")
        with open("root_page.txt", "w") as f:
            f.write(str(tree.root_page))
    #空间查询模式
    elif mode == "query":
            avg_stats, samples = run_queries(74795)
            print("查询完成，平均统计如下：")
            print(avg_stats)
            print("查询结果:")
            for hit in samples:
                print(hit)
            visualize_hits(samples)

