#!/usr/bin/env python
"""truecolour.py -- cache the clearest spring Sentinel-2 true-colour scene for a window (EPSG:3577)."""
import os

import numpy as np


def truecolour(cx, cy, half_m, cache_dir, name, start="2024-08-01", end="2024-10-20", year=None):
    """Return (rgb uint8 HxWx3, extent (minx, maxx, miny, maxy)); cached as <cache_dir>/<name>.npz."""
    os.makedirs(cache_dir, exist_ok=True)
    path = f"{cache_dir}/{name}.npz"
    if os.path.exists(path):
        z = np.load(path)
        return z["rgb"], tuple(z["extent"])
    os.environ.setdefault("PROJ_NETWORK", "OFF")
    os.environ.setdefault("DATACUBE_CONFIG_PATH", "/g/data/v10/public/modules/dea/20231204/datacube.conf")
    import datacube
    if year:
        start, end = start.replace("2024", str(year)), end.replace("2024", str(year))
    dc = datacube.Datacube(app="truecolour")
    ds = dc.load(product=["ga_s2am_ard_3", "ga_s2bm_ard_3", "ga_s2cm_ard_3"],
                 x=(cx - half_m, cx + half_m), y=(cy - half_m, cy + half_m), crs="EPSG:3577",
                 time=(start, end), measurements=["nbart_red", "nbart_green", "nbart_blue", "oa_fmask"],
                 output_crs="EPSG:3577", resolution=(-10, 10), group_by="solar_day", skip_broken_datasets=True)
    clear = (ds.oa_fmask == 1).mean(("x", "y")).values
    k = int(np.argmax(clear))
    bands = [ds[b].isel(time=k).values.astype(float) for b in ("nbart_red", "nbart_green", "nbart_blue")]
    rgb = np.zeros(bands[0].shape + (3,), np.uint8)
    for i, b in enumerate(bands):
        b = np.where(b <= 0, np.nan, b)
        lo, hi = np.nanpercentile(b, 2), np.nanpercentile(b, 98)
        rgb[..., i] = np.nan_to_num(np.clip((b - lo) / max(hi - lo, 1), 0, 1) * 255).astype(np.uint8)
    x, y = ds.x.values, ds.y.values
    extent = (float(x.min() - 5), float(x.max() + 5), float(y.min() - 5), float(y.max() + 5))
    np.savez_compressed(path, rgb=rgb, extent=np.array(extent), date=str(ds.time.values[k])[:10], clear=clear[k])
    return rgb, extent
