import os
import struct
from typing import List, Tuple

# 设置文件路径
file_path = "nodes/node_5.bin"


# 定义MBR结构
class MBR:
    def __init__(self, minx, miny, minz, maxx, maxy, maxz):
        self.minx = minx
        self.miny = miny
        self.minz = minz
        self.maxx = maxx
        self.maxy = maxy
        self.maxz = maxz

    def __repr__(self):
        return f"MBR(({self.minx:.6f}, {self.miny:.6f}, {self.minz:.1f}) → ({self.maxx:.6f}, {self.maxy:.6f}, {self.maxz:.1f}))"


# 解析函数
def parse_node_file(path: str) -> Tuple[int, bool, List[Tuple[MBR, int]]]:
    entries = []
    with open(path, "rb") as f:
        page_id = struct.unpack("i", f.read(4))[0]
        is_leaf = struct.unpack("?", f.read(1))[0]
        count = struct.unpack("i", f.read(4))[0]

        for _ in range(count):
            mbr_vals = struct.unpack("6d", f.read(48))
            mbr = MBR(*mbr_vals)
            if is_leaf:
                block_id, index = struct.unpack("ii", f.read(8))
                entries.append((mbr, (block_id, index)))
            else:
                child_id = struct.unpack("i", f.read(4))[0]
                entries.append((mbr, child_id))

    return page_id, is_leaf, entries


# 调用解析并展示内容
page_id, is_leaf, entries = parse_node_file(file_path)
entries_output = {
    "页号": page_id,
    "是否为叶节点": is_leaf,
    "索引条目": entries
}
print("页号:"+str(entries_output["页号"]))
print("是否是叶节点:"+str(entries_output["是否为叶节点"]))
print("索引条目:")
for i in range(len(entries_output["索引条目"])):
    print(entries_output["索引条目"][i])
