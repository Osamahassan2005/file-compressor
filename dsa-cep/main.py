#!/usr/bin/env python3
import heapq
import struct
import time
from collections import Counter
from typing import Optional, Dict, Tuple

MAGIC = b'HUFF'  # file signature

# ---------------------------------
# Basic tree node (student style)
# ---------------------------------
class Node:
    def __init__(self, sym: Optional[int], freq: int):
        # sym: None for internal nodes, 0..255 for leaf nodes
        self.sym = sym
        self.freq = freq
        self.left: Optional['Node'] = None
        self.right: Optional['Node'] = None

    def __lt__(self, other: 'Node'):
        # needed so heapq works — compare by freq
        return self.freq < other.freq

# --------------------------------
# Convert Tree to Graphiz format
# --------------------------------

def tree_to_dot(node, max_depth=3):
    dot = "digraph G {\n"
    dot += "node [shape=circle, style=filled, color=lightblue];\n"

    def traverse(n, depth=0):
        nonlocal dot
        if not n or depth > max_depth:
            return
        if n.left:
            dot += f'"{n.freq}\\n{n.sym if n.sym is not None else ""}" -> "{n.left.freq}\\n{n.left.sym if n.left.sym is not None else ""}";\n'
            traverse(n.left, depth+1)
        if n.right:
            dot += f'"{n.freq}\\n{n.sym if n.sym is not None else ""}" -> "{n.right.freq}\\n{n.right.sym if n.right.sym is not None else ""}";\n'
            traverse(n.right, depth+1)

    traverse(node)
    dot += "}"
    return dot

# ------------------------------------
# 1) Read file and count bytes (freq)
# ------------------------------------
def read_file_bytes(path: str) -> bytes:
    with open(path, 'rb') as f:
        return f.read()

def build_freq_map(data: bytes) -> Dict[int, int]:
    # quick and dirty frequency count
    return dict(Counter(data))

# -------------------------------------
# 2) Make heap and build Huffman tree
# ------------------------------------
def heap_from_freq(freq_map: Dict[int, int]) -> list:
    h = []
    for sym, fr in freq_map.items():
        heapq.heappush(h, Node(sym, fr))
    return h

def build_tree(h: list) -> Optional[Node]:
    # if empty file -> no tree
    if not h:
        return None
    # if only one symbol, create a parent so codes aren't empty
    if len(h) == 1:
        single = heapq.heappop(h)
        parent = Node(None, single.freq)
        parent.left = single
        return parent
    while len(h) > 1:
        a = heapq.heappop(h)
        b = heapq.heappop(h)
        p = Node(None, a.freq + b.freq)
        p.left = a
        p.right = b
        heapq.heappush(h, p)
    return heapq.heappop(h)

# ---------------------------
# 3) Walk tree -> code map
# ---------------------------
def make_codes(root: Optional[Node]) -> Dict[int, str]:
    codes: Dict[int, str] = {}
    if root is None:
        return codes

    def walk(node: Node, prefix: str):
        if node.sym is not None:
            # leaf: assign code; single-symbol edge-case -> "0"
            codes[node.sym] = prefix if prefix != "" else "0"
            return
        if node.left:
            walk(node.left, prefix + "0")
        if node.right:
            walk(node.right, prefix + "1")

    walk(root, "")
    return codes

# ----------------------------------------------------------------------
# 4) Tree serialization (preorder): 0x00 = internal, 0x01 + byte = leaf
# ----------------------------------------------------------------------
def serialize(root: Optional[Node]) -> bytes:
    out = bytearray()
    if root is None:
        return bytes(out)

    def dfs(node: Node):
        if node.sym is not None:
            out.append(1)
            out.append(node.sym)
            return
        out.append(0)
        dfs(node.left)
        dfs(node.right)

    dfs(root)
    return bytes(out)

def deserialize(blob: bytes) -> Optional[Node]:
    # parse preorder serialization; raise ValueError on bad data
    if not blob:
        return None
    idx = 0
    n = len(blob)

    def dfs(i: int) -> Tuple[Node, int]:
        if i >= n:
            raise ValueError("Bad tree data: ran out")
        flag = blob[i]
        i += 1
        if flag == 1:
            if i >= n:
                raise ValueError("Bad tree: leaf missing byte")
            s = blob[i]
            i += 1
            return Node(s, 0), i
        if flag == 0:
            left_node, i = dfs(i)
            right_node, i = dfs(i)
            p = Node(None, 0)
            p.left = left_node
            p.right = right_node
            return p, i
        raise ValueError(f"Bad tree flag {flag} at {i-1}")

    root, next_i = dfs(0)
    if next_i != n:
        raise ValueError("Extra bytes after tree data")
    return root

# ----------------------------------------------
# 5) Encode bytes using codes -> big bitstring
# ----------------------------------------------

def encode_bytes(data: bytes, codes: Dict[int, str]) -> str:
    pieces = []
    for b in data:
        pieces.append(codes[b])
    return "".join(pieces)

def pad_bits(bits: str) -> Tuple[str, int]:
    # pad to full bytes; return padded string + pad count (0..7)
    if len(bits) == 0:
        return "", 0
    extra = (8 - (len(bits) % 8)) % 8
    return bits + ("0" * extra), extra

def bits_to_bytes(bits: str) -> bytes:
    arr = bytearray()
    for i in range(0, len(bits), 8):
        byte = bits[i:i+8]
        arr.append(int(byte, 2))
    return bytes(arr)

def bytes_to_bits(bts: bytes) -> str:
    return "".join(f"{x:08b}" for x in bts)

# -------------------------
# 6) Compressor
# -------------------------
#
def compress_file(src: str, dst: str) -> Tuple[Optional[Node], Dict[str, object]]:
    """
    Returns (root, stats). If compression is skipped (already compressed type, .huff,
    or compression would increase size), returns (None, stats) with stats['skipped']=True
    and stats['note'] explaining why.
    """
    import shutil

    # Convert path to clean string
    src_str = str(src).strip().lower()

    already_compressed_exts = (
        ".zip", ".gz", ".7z", ".rar", ".jpeg", ".jpg", ".png", ".gif",
        ".mp3", ".mp4", ".avi", ".mov", ".odt", ".docx", ".xlsx"
    )

    t0 = time.perf_counter()
    raw = read_file_bytes(src)
    t_read = time.perf_counter()

    original_bytes = len(raw)

    # 1) Already Huffman compressed?
    if raw.startswith(MAGIC) or src_str.endswith(".huff"):
        stats = {
            "input": src,
            "output": dst,
            "original_bytes": original_bytes,
            "compressed_bytes": len(raw),
            "unique_symbols": 0,
            "pad_count": None,
            "compression_ratio": None,
            "space_saved_percent": None,
            "skipped": True,
            "note": "Input file is already in .huff format (double-compression prevented).",
            "time_read": t_read - t0,
            "time_total": time.perf_counter() - t0,
        }
        return None, stats

    # 2) Already compressed file type?
    if any(src_str.endswith(ext) for ext in already_compressed_exts):
        stats = {
            "input": src,
            "output": dst,
            "original_bytes": original_bytes,
            "compressed_bytes": original_bytes,
            "unique_symbols": 0,
            "pad_count": None,
            "compression_ratio": 1.0,
            "space_saved_percent": 0.0,
            "skipped": True,
            "note": "This file type is likely already compressed (skipped compression).",
            "time_read": t_read - t0,
            "time_total": time.perf_counter() - t0,
        }
        return None, stats

    # --- Normal compression path ---
    freq = build_freq_map(raw)
    h = heap_from_freq(freq)
    root = build_tree(h)
    t_tree = time.perf_counter()

    codes = make_codes(root)
    t_codes = time.perf_counter()

    bitstr = encode_bytes(raw, codes) if root is not None else ""
    padded, pad_count = pad_bits(bitstr)
    compressed = bits_to_bytes(padded)
    t_pack = time.perf_counter()

    tree_blob = serialize(root)
    tree_len = len(tree_blob)

    # Write header + data
    with open(dst, 'wb') as out:
        out.write(MAGIC)
        out.write(struct.pack(">I", tree_len))
        out.write(tree_blob)
        out.write(struct.pack("B", pad_count))
        out.write(compressed)
    t_write = time.perf_counter()

    compressed_bytes_total = 4 + 4 + tree_len + 1 + len(compressed)

    # --- Post-compression check: skip if larger than original ---
    if compressed_bytes_total >= original_bytes:
        shutil.copy(src, dst)  # keep original
        stats = {
            "input": src,
            "output": dst,
            "original_bytes": original_bytes,
            "compressed_bytes": original_bytes,
            "unique_symbols": len(freq),
            "pad_count": pad_count,
            "compression_ratio": 1.0,
            "space_saved_percent": 0.0,
            "skipped": True,
            "note": "The uploaded file appears to be already compressed; compression cannot reduce its size.”",
            "time_read": t_read - t0,
            "time_tree_build": t_tree - t_read,
            "time_codes": t_codes - t_tree,
            "time_pack": t_pack - t_codes,
            "time_write": t_write - t_pack,
            "time_total": t_write - t0,
        }
        return None, stats

    # --- Normal stats ---
    if original_bytes > 0:
        compression_ratio = compressed_bytes_total / original_bytes
        space_saved_percent = ((original_bytes - compressed_bytes_total) / original_bytes) * 100.0
    else:
        compression_ratio = None
        space_saved_percent = None

    stats = {
        "input": src,
        "output": dst,
        "original_bytes": original_bytes,
        "compressed_bytes": compressed_bytes_total,
        "unique_symbols": len(freq),
        "pad_count": pad_count,
        "compression_ratio": compression_ratio,
        "space_saved_percent": space_saved_percent,
        "skipped": False,
        "note": None,
        "time_read": t_read - t0,
        "time_tree_build": t_tree - t_read,
        "time_codes": t_codes - t_tree,
        "time_pack": t_pack - t_codes,
        "time_write": t_write - t_pack,
        "time_total": t_write - t0,
    }
    return root,stats

# -------------------------
# 7) Decompressor
# -------------------------
def decompress_file(src: str, dst: str) -> Dict[str, object]:
    t0 = time.perf_counter()
    raw = read_file_bytes(src)
    t_read = time.perf_counter()

    if len(raw) < 9:
        raise ValueError("Not a valid .huff (too small)")

    if raw[:4] != MAGIC:
        raise ValueError("Not a .huff file (magic mismatch)")

    tree_len = struct.unpack(">I", raw[4:8])[0]
    cursor = 8
    if cursor + tree_len + 1 > len(raw):
        raise ValueError("Header tree length unrealistic")

    tree_blob = raw[cursor:cursor+tree_len]
    cursor += tree_len

    pad_count = raw[cursor]
    cursor += 1

    comp_bytes = raw[cursor:]
    bitstr = bytes_to_bits(comp_bytes) if comp_bytes else ""
    if pad_count > 0:
        if pad_count > len(bitstr):
            raise ValueError("Padding bigger than stream")
        bitstr = bitstr[:-pad_count]
    t_unpad = time.perf_counter()

    root = deserialize(tree_blob) if tree_len > 0 else None
    t_tree = time.perf_counter()

    # decode by walking the tree
    if root is None:
        decoded = b""
    else:
        out = bytearray()
        node = root
        i = 0
        n = len(bitstr)
        while i < n:
            bit = bitstr[i]
            node = node.left if bit == '0' else node.right
            if node is None:
                raise ValueError("Corrupt bitstream (walked to None)")
            if node.sym is not None:
                out.append(node.sym)
                node = root
            i += 1
        decoded = bytes(out)
    t_decode = time.perf_counter()

    with open(dst, 'wb') as f:
        f.write(decoded)
    t_write = time.perf_counter()

    stats = {
        "input_huff": src,
        "output": dst,
        "compressed_size": len(raw),
        "restored_size": len(decoded),
        "pad_count": pad_count,
        "time_read": t_read - t0,
        "time_unpad": t_unpad - t_read,
        "time_tree": t_tree - t_unpad,
        "time_decode": t_decode - t_tree,
        "time_write": t_write - t_decode,
        "time_total": t_write - t0,
    }
    return stats