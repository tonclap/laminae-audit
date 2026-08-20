"""Whole-plane readers for one z of the CT and of the surface prediction.

The calibration itself never needs a plane — it walks rays and samples points, which
is why `absolute_winding_calibration.py` has no code like this. A picture does need
one: the claim being demonstrated is "the ray crosses these laminae in this order",
and that is only checkable against the image the ray was drawn on.

Two different storage layouts, so two readers:

- **CT** `20260411134726-2.400um-0.2m-78keV-masked.zarr`, level 2 — `compressor: null`,
  `|u1`, chunks 128^3. One z-plane of one chunk is 16 KB of contiguous bytes at a
  computable offset, so a window is a handful of Range requests and no decode at all.
- **prediction** `…-recto-2um-ps256-L0-th0.45.zarr`, level 2 — blosc, chunks 256^3.
  There is no way to read one plane without decoding the whole 16.8 MB chunk, so this
  costs ~1.3 MB of transfer and ~27 ms of decode per 256x256 tile of output. Ask for
  windows, not for the full 8174x8174 slice (that would be 1024 chunks).

Both readers cache raw chunk bytes on disk and both are keyed by the same level 2
frame, which is the frame the annotations live in.
"""
import concurrent.futures as futures
import json
import os
import urllib.error
import urllib.request

import numpy as np

S3 = 'https://vesuvius-challenge-open-data.s3.amazonaws.com/'
CT = 'PHercParis4/volumes/20260411134726-2.400um-0.2m-78keV-masked.zarr/'
PREDICTION = ('PHercParis4/representations/predictions/surfaces/'
              '20260411134726-surface-20260413141734-surface-recto-2um-ps256-'
              'L0-th0.45.zarr/')
LEVEL = '2'


def _get(url, byte_range=None, timeout=120, retries=4):
    request = urllib.request.Request(url)
    if byte_range:
        request.add_header('Range', 'bytes=%d-%d' % byte_range)
    for attempt in range(retries):
        try:
            return urllib.request.urlopen(request, timeout=timeout).read()
        except urllib.error.HTTPError as error:
            if error.code == 404:
                return None
            if attempt == retries - 1:
                raise
        except Exception:                                      # noqa: BLE001
            if attempt == retries - 1:
                raise
    return None


class CTPlane:
    """Byte-range reader over the uncompressed CT level."""

    def __init__(self, cache, level=LEVEL):
        self.cache = cache
        os.makedirs(cache, exist_ok=True)
        self.level = level
        meta = json.loads(_get(f'{S3}{CT}{level}/.zarray').decode())
        if meta['compressor'] is not None or meta['dtype'] != '|u1':
            raise RuntimeError('CT level is no longer raw uint8; the offset arithmetic '
                               f'below would read garbage: {meta}')
        self.shape = meta['shape']                             # z, y, x
        self.chunk = meta['chunks'][0]

    def _tile(self, cz, cy, cx, lz):
        """One z-plane of one chunk, `chunk` x `chunk` bytes."""
        path = os.path.join(self.cache, f'ct{self.level}_{cz}_{cy}_{cx}_{lz}.bin')
        if os.path.exists(path):
            with open(path, 'rb') as handle:
                buf = handle.read()
        else:
            size = self.chunk * self.chunk
            buf = _get(f'{S3}{CT}{self.level}/{cz}/{cy}/{cx}',
                       (lz * size, lz * size + size - 1))
            # A chunk never written is legitimately absent and reads as fill value 0;
            # a short read is not, and padding it would quietly fabricate tissue.
            if buf is None:
                buf = bytes(size)
            elif len(buf) != size:
                raise RuntimeError(f'short read on CT chunk {cz}/{cy}/{cx}: '
                                   f'{len(buf)} of {size} bytes')
            tmp = f'{path}.{os.getpid()}.part'
            with open(tmp, 'wb') as handle:
                handle.write(buf)
            os.replace(tmp, path)
        return np.frombuffer(buf, np.uint8).reshape(self.chunk, self.chunk)

    def window(self, z, y0, y1, x0, x1, workers=32):
        """[y0:y1, x0:x1] of plane z, as uint8. Out-of-volume reads as 0."""
        out = np.zeros((y1 - y0, x1 - x0), np.uint8)
        z = int(round(z))
        if not 0 <= z < self.shape[0]:
            raise ValueError(f'z={z} outside the volume {self.shape}')
        cz, lz = divmod(z, self.chunk)
        keys = [(cz, cy, cx, lz)
                for cy in range(max(0, y0) // self.chunk,
                                (min(y1, self.shape[1]) - 1) // self.chunk + 1)
                for cx in range(max(0, x0) // self.chunk,
                                (min(x1, self.shape[2]) - 1) // self.chunk + 1)]
        with futures.ThreadPoolExecutor(min(workers, max(1, len(keys)))) as pool:
            tiles = list(pool.map(lambda key: self._tile(*key), keys))
        for (_, cy, cx, _), tile in zip(keys, tiles):
            ty0, tx0 = cy * self.chunk, cx * self.chunk
            sy0, sx0 = max(y0, ty0), max(x0, tx0)
            sy1 = min(y1, ty0 + self.chunk, self.shape[1])
            sx1 = min(x1, tx0 + self.chunk, self.shape[2])
            if sy0 >= sy1 or sx0 >= sx1:
                continue
            out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = \
                tile[sy0 - ty0:sy1 - ty0, sx0 - tx0:sx1 - tx0]
        return out


class PredictionPlane:
    """One z-plane of the blosc-compressed binary surface prediction."""

    def __init__(self, cache, level=LEVEL):
        import numcodecs
        self.cache = cache
        os.makedirs(cache, exist_ok=True)
        self.level = level
        meta = json.loads(_get(f'{S3}{PREDICTION}{level}/.zarray').decode())
        self.shape = meta['shape']
        self.chunks = meta['chunks']
        self.codec = numcodecs.get_codec(meta['compressor'])

    def _raw(self, cz, cy, cx):
        # Same file name the calibration's own reader uses, so the two share one cache
        # instead of downloading every chunk twice.
        path = os.path.join(self.cache, f'{self.level}_{cz}_{cy}_{cx}')
        if os.path.exists(path):
            with open(path, 'rb') as handle:
                return handle.read()
        data = _get(f'{S3}{PREDICTION}{self.level}/{cz}/{cy}/{cx}', timeout=300)
        if data is None:
            return None
        tmp = f'{path}.{os.getpid()}.part'
        with open(tmp, 'wb') as handle:
            handle.write(data)
        os.replace(tmp, path)
        return data

    def _tile(self, cz, cy, cx, lz):
        raw = self._raw(cz, cy, cx)
        if raw is None:
            return np.zeros((self.chunks[1], self.chunks[2]), np.uint8)
        block = np.frombuffer(self.codec.decode(raw), np.uint8).reshape(self.chunks)
        return block[lz].copy()                                # drop the 16.8 MB block

    def window(self, z, y0, y1, x0, x1, workers=8):
        out = np.zeros((y1 - y0, x1 - x0), np.uint8)
        z = int(round(z))
        cz, lz = divmod(z, self.chunks[0])
        keys = [(cz, cy, cx, lz)
                for cy in range(max(0, y0) // self.chunks[1],
                                (min(y1, self.shape[1]) - 1) // self.chunks[1] + 1)
                for cx in range(max(0, x0) // self.chunks[2],
                                (min(x1, self.shape[2]) - 1) // self.chunks[2] + 1)]
        # Download in parallel first (pure waiting), then decode serially: eight
        # concurrent decodes of a 16.8 MB block is 134 MB of transient arrays for no
        # gain, the decode being CPU-bound and the GIL-holding part of numcodecs short.
        missing = [key[:3] for key in keys
                   if not os.path.exists(os.path.join(
                       self.cache, f'{self.level}_{key[0]}_{key[1]}_{key[2]}'))]
        if len(missing) > 1:
            with futures.ThreadPoolExecutor(min(workers, len(missing))) as pool:
                list(pool.map(lambda key: self._raw(*key), missing))
        for key in keys:
            tile = self._tile(*key)
            _, cy, cx, _ = key
            ty0, tx0 = cy * self.chunks[1], cx * self.chunks[2]
            sy0, sx0 = max(y0, ty0), max(x0, tx0)
            sy1 = min(y1, ty0 + self.chunks[1], self.shape[1])
            sx1 = min(x1, tx0 + self.chunks[2], self.shape[2])
            if sy0 >= sy1 or sx0 >= sx1:
                continue
            out[sy0 - y0:sy1 - y0, sx0 - x0:sx1 - x0] = \
                tile[sy0 - ty0:sy1 - ty0, sx0 - tx0:sx1 - tx0]
        return out
