"""
navgrid.py - read the game's navigation grid (Levels/<level>/Ai/aigrid.data).

The grid tells where characters can stand and how high the floor is there. It is
what check_waypoints.py verifies every waypoint against, and what survey.py draws.

The format is not documented. This reader was worked out from the files and
checked against the game: about 90% of the characters the game places in a level
stand within 0.3 m of a surface it decodes (the rest sit, fly or lie down).

  file:  u32 version (21), cstr guid, u32 tileCount, then per tile:
           u32 hash, u32 width, u32 height, f32 x, f32 y, f32 z   (world position of the tile's corner)
           cstr guid, cstr templateGuid
           u32 lz4Size, u32 zlibSize, zlib( lz4 block( cells ) )
  cells: width * height records of 16 bytes, row by row (index = cz * width + cx),
         each covering 0.5 m x 0.5 m:
           u64 flags, u16 height, u16 height2 (both in 2 cm steps above the tile's y), u32 extra
Tiles overlap: there is one per walkable layer (the floors of a tower, a bridge
over a road), so one x/z can have several surfaces.

Flags: the lowest three bits are clear on floor that is free to walk on. Bit 0 is
set where a tile has no surface at all; bits 1 and 2 where something stands on the
floor (walls, furniture, rock).
"""
from __future__ import annotations

import math
import struct
import zlib

VERSION = 21
CELL = 0.5            # metres per cell
HEIGHT_STEP = 0.02    # metres per height unit
NO_SURFACE = 0x1
BLOCKED = 0x7         # any of these bits: not free floor
BUCKET = 32.0         # metres, for the tile index


def lz4_block(src: bytes) -> bytes:
    """Decompress one raw LZ4 block."""
    out = bytearray()
    i, n = 0, len(src)
    while i < n:
        token = src[i]
        i += 1
        literals = token >> 4
        if literals == 15:
            while True:
                b = src[i]
                i += 1
                literals += b
                if b != 255:
                    break
        out += src[i:i + literals]
        i += literals
        if i >= n:
            break
        offset = src[i] | (src[i + 1] << 8)
        i += 2
        length = token & 15
        if length == 15:
            while True:
                b = src[i]
                i += 1
                length += b
                if b != 255:
                    break
        length += 4
        start = len(out) - offset
        if offset == 0 or start < 0:
            raise ValueError("corrupt LZ4 block")
        if offset >= length:
            out += out[start:start + length]
        else:  # overlapping copy
            for k in range(length):
                out.append(out[start + k])
    return bytes(out)


class Tile:
    __slots__ = ("w", "h", "x", "y", "z", "guid", "_blob", "_cells")

    def cells(self) -> bytes:
        if self._cells is None:
            self._cells = lz4_block(zlib.decompress(self._blob))
            if len(self._cells) != self.w * self.h * 16:
                raise ValueError("tile %s: %d bytes for %dx%d cells" % (self.guid, len(self._cells), self.w, self.h))
        return self._cells

    def cell(self, x: float, z: float):
        """(flags, height) of the cell at world x/z, or None outside the tile."""
        cx = math.floor((x - self.x) / CELL)
        cz = math.floor((z - self.z) / CELL)
        if not (0 <= cx < self.w and 0 <= cz < self.h):
            return None
        flags, height = struct.unpack_from("<QH", self.cells(), (cz * self.w + cx) * 16)
        return flags, self.y + height * HEIGHT_STEP


class NavGrid:
    def __init__(self, path: str):
        with open(path, "rb") as fh:
            data = fh.read()
        pos = 0

        def u32():
            nonlocal pos
            value = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            return value

        def f32():
            nonlocal pos
            value = struct.unpack_from("<f", data, pos)[0]
            pos += 4
            return value

        def cstr():
            nonlocal pos
            end = data.index(b"\0", pos)
            value = data[pos:end].decode("ascii", "replace")
            pos = end + 1
            return value

        self.version = u32()
        if self.version != VERSION:
            raise ValueError("%s: navigation grid version %d, this reader knows version %d" % (path, self.version, VERSION))
        self.guid = cstr()
        self.tiles = []
        for _ in range(u32()):
            tile = Tile()
            u32()  # hash
            tile.w, tile.h = u32(), u32()
            tile.x, tile.y, tile.z = f32(), f32(), f32()
            tile.guid = cstr()
            cstr()  # template guid
            u32()   # size of the LZ4 block
            size = u32()
            tile._blob = data[pos:pos + size]
            pos += size
            tile._cells = None
            self.tiles.append(tile)
        # Tiles by 32 m square, so a lookup only tests the few tiles that can contain the point.
        self._index = {}
        for tile in self.tiles:
            x0, z0 = math.floor(tile.x / BUCKET), math.floor(tile.z / BUCKET)
            x1 = math.floor((tile.x + tile.w * CELL) / BUCKET)
            z1 = math.floor((tile.z + tile.h * CELL) / BUCKET)
            for bx in range(x0, x1 + 1):
                for bz in range(z0, z1 + 1):
                    self._index.setdefault((bx, bz), []).append(tile)

    def surfaces(self, x: float, z: float):
        """Every surface at world x/z as (height, flags), lowest first."""
        found = []
        for tile in self._index.get((math.floor(x / BUCKET), math.floor(z / BUCKET)), ()):
            hit = tile.cell(x, z)
            if hit and not hit[0] & NO_SURFACE:
                found.append((hit[1], hit[0]))
        found.sort()
        return found

    def floor(self, x: float, z: float, near: float, tolerance: float = 2.0):
        """Height of the free floor at x/z that is closest to `near`, or None."""
        best = None
        for height, flags in self.surfaces(x, z):
            if flags & BLOCKED:
                continue
            distance = abs(height - near)
            if distance <= tolerance and (best is None or distance < best[0]):
                best = (distance, height)
        return best[1] if best else None


def cell_centre(v: float) -> float:
    """The centre of the grid cell that contains coordinate v."""
    return (math.floor(v / CELL) + 0.5) * CELL
