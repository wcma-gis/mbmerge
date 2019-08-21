# Wimmera CMA MBJOIN

Facilitates joining mbtiles files in jpg or png formats.

## Prerequisites

Python 3 with Pillow

```
python -m pip install Pillow
```

## Use

```
usage: mb-join.py [-h] [-f [format]] [-a [merge action]]
                  [-p [palette colours]]
                  output path input paths [input paths ...]

Merges a series of raster MBTiles files. Only works for PNG at the moment.

positional arguments:
  output path           Output MBTiles file path
  input paths           List of MBTiles files to merge, in increasing order of
                        importance (latter files will override earlier ones)

optional arguments:
  -h, --help            show this help message and exit
  -f [format]           Output format (PNG or JPEG)
  -a [merge action]     Merge action. blend () or alphacomposite (png only,
                        replaces nodata from image 2 with nodata of image 1)
  -p [palette colours]  Number of output colours in the palette (png only)
  ```

## Built With

* [Python](https://www.python.org/)
* [Pillow](https://pillow.readthedocs.io/en/stable/)

## Authors

* **Paul Skeen** - *Initial work* - [SkeenP](https://github.com/skeenp)

## License

This project is licensed under the MIT License - see the [LICENSE.md](LICENSE.md) file for details
