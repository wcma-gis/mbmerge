# mbmerge

Facilitates joining mbtiles files in jpg, webp or png formats.

## Prerequisites

Python 3 with Pillow

```
python -m pip install Pillow
```

## Use

```
usage: mbmerge.py [-h] [-n name] [-p [palette colours]]
                  output path input paths [input paths ...]

Merges a series of raster MBTiles files. jpg files will be blended, png and
webp files will be merged using alpha compositing.

positional arguments:
  output path           Output MBTiles file path
  input paths           List of MBTiles files to merge, in increasing order of
                        importance (latter files will override earlier ones)

optional arguments:
  -h, --help            show this help message and exit
  -n name               Name value for output mbtiles metadata
  -p palette  Number of output colours in the palette (png only, defaults to 16)
```

Sample usage:
```
python mbmerge.py -n "Wimmera CMA Flood Risk" -p 8 "master.mbtiles" "NatiTown13_FloodRisk.mbtiles" "Hors19_FloodRisk.mbtiles"  "Con15_FloodRisk.mbtiles" "Dunm17_FloodRisk.mbtiles" "HGap17_FloodRisk.mbtiles"
```

## Built With

* [Python](https://www.python.org/)
* [Pillow](https://pillow.readthedocs.io/en/stable/)

## Authors

* **Paul Skeen** - *Initial work* - [SkeenP](https://github.com/skeenp)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
