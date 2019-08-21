import sqlite3
import shutil
import argparse
from PIL import Image
from io import BytesIO
import os

# Setup arg parser
parser = argparse.ArgumentParser(
    description='Merges a series of raster MBTiles files. jpg files will be blended, png and webp files will be merged using alpha compositing.',
    epilog="https://github.com/wcma-gis/mbjoin")
parser.add_argument(
    '-n', dest='name', metavar='name',
    help='Name value for output mbtiles metadata')
parser.add_argument(
    '-p', dest='palette', const=16, type=int, nargs='?',
    help='Number of output colours in the palette (png only, defaults to 16)')
parser.add_argument(
    'out_file', metavar='output path',
    help='Output MBTiles file path')
parser.add_argument(
    'in_files', nargs='+', metavar='input paths',
    help='List of MBTiles files to merge, in increasing order of importance (latter files will override earlier ones)')

# Parse args
try:
    args = parser.parse_args()
except BaseException as ex:
    print(ex)
    parser.print_help()
    raise SystemExit
# Get dataset 1
out = args.out_file
datasets = args.in_files
# Setup output by copying the first dataset
if os.path.exists(out):
    os.remove(out)
shutil.copy2(datasets[0], out)
# Connect to master
master = sqlite3.connect(out)
m = master.cursor()
# Setup list of connected databases
children = []
# Get dataset count
dataset_count = len(datasets)-1
# Setup metadata collector


def get_meta(db, param):
    # Setup sql
    sql = "SELECT value FROM {db}.metadata WHERE name = '{param}';"
    # Return value
    return m.execute(sql.format(db=db, param=param)).fetchone()[0]


# Get master metadata
meta = {}
meta['name'] = args.name if args.name else 'Merged MBTiles'
meta['format'] = get_meta('main', 'format')
# Check format is raster
if meta['format'] not in ('png', 'jpg', 'webp'):
    msg = 'ERROR: Unsupported tile format {format}. Tile format must be one of jpg, png or webp'
    print(msg.format(format=meta['format']))
    exit()
meta['bounds'] = get_meta('main', 'bounds').split(',')
meta['minzoom'] = get_meta('main', 'minzoom')
meta['maxzoom'] = get_meta('main', 'maxzoom')
# Setup metadata checker


def check_meta(file, param, value, error=False):
    # Check value
    if meta[param] != value:
        # Setup check message
        msg = 'ERROR' if error else 'WARNING'
        msg += ': {param} of file {file}[{cvalue}] differs from master format [{mvalue}]. '
        msg += 'All mbtiles files {directive} have the same {param}.'
        print(msg.format(param=param.title(), file=file, cvalue=value,
                         mvalue=meta[param], directive='must' if error else 'should'))
        # Return result
        return False
    # Return result
    return True


# Loop through additional datasets
for i, dataset in enumerate(datasets[-dataset_count:]):
    # Setup alias
    alias = 'ds' + str(i)
    # Attach dataset mbtiles
    sql = "ATTACH DATABASE ? AS ?;"
    params = (dataset, alias,)
    m.execute(sql, params)
    # Check format
    fmt = get_meta(alias, 'format')
    if not check_meta(dataset, 'format', fmt, True):
        exit()
    # Check minzoom
    minzoom = get_meta(alias, 'minzoom')
    if not check_meta(dataset, 'minzoom', minzoom):
        # Update master metadata
        if meta['minzoom'] < minzoom:
            meta['minzoom'] = minzoom
    # Check maxzoom
    maxzoom = get_meta(alias, 'maxzoom')
    if not check_meta(dataset, 'maxzoom', maxzoom):
        # Update master metadata
        if meta['maxzoom'] > maxzoom:
            meta['maxzoom'] = maxzoom
    # Check bounds
    bounds = get_meta(alias, 'bounds').split(',')
    # Update metadata bounds
    if meta['bounds'][0] > bounds[0]:
        meta['bounds'][0] = bounds[0]
    if meta['bounds'][1] < bounds[1]:
        meta['bounds'][1] = bounds[1]
    if meta['bounds'][2] < bounds[2]:
        meta['bounds'][2] = bounds[2]
    if meta['bounds'][3] > bounds[3]:
        meta['bounds'][3] = bounds[3]
    # Update children
    children.append({'id': i, 'alias': alias, 'dataset': dataset})
# Process datasets
for child in children:
    # Setup cursor
    c = master.cursor()
    # Update transparency table
    sql = "INSERT INTO main.images_transparency (tile_id, transparency) SELECT tile_id, transparency FROM {alias}.images_transparency WHERE tile_id NOT IN (SELECT tile_id FROM main.images_transparency);"
    c.execute(sql.format(alias=child['alias']))
    # Update map table
    sql = "INSERT INTO main.map (zoom_level, tile_column, tile_row, tile_id) SELECT zoom_level, tile_column, tile_row, tile_id FROM {alias}.map WHERE tile_id NOT IN (SELECT tile_id FROM main.map);"
    c.execute(sql.format(alias=child['alias']))
    # Get overlapping tiles
    sql = "SELECT i1.tile_id, i1.tile_data as png1, i2.tile_data as png2 FROM main.images i1 INNER JOIN {alias}.images i2 ON i1.tile_id = i2.tile_id;"
    c.execute(sql.format(alias=child['alias']))
    # Process overlapping tiles
    for row in c:
        # Get tiles from sqlite
        img1 = Image.open(BytesIO(row[1]))
        img2 = Image.open(BytesIO(row[2]))
        # Convert images
        if meta['format'] == 'png' or meta['format'] == 'webp':
            # Convert tile from pal to rgba
            img1 = img1.convert('RGBA')
            img2 = img2.convert('RGBA')
            img3 = Image.alpha_composite(img1, img2)
        else:
            # Convert file to RGB
            img1 = img1.convert('RGB')
            img2 = img2.convert('RGB')
            img3 = Image.blend(img1, img2, 0.5)
        # Save image to buffer
        img3out = BytesIO()
        # Save image
        if meta['format'] == 'png':
            img3compress = img3.convert(
                'P', palette=Image.ADAPTIVE, colors=args.palette)
            img3compress.save(img3out, optimize=True, format='PNG')
        elif meta['format'] == 'webp':
            img3.save(img3out, format='WEBP')
        else:
            img3.save(img3out, optimize=True, format='JPEG')
        # Setup update cursor
        u = master.cursor()
        # Update tile in database
        sql = "UPDATE main.images SET tile_data = ? WHERE tile_id = ?;"
        params = (img3out.getvalue(), row[0],)
        u.execute(sql, params)
        # Close update cursor
        u.close()
    # Append non-overlapping tiles
    sql = "INSERT INTO main.images (tile_id, tile_data) SELECT tile_id, tile_data FROM {alias}.images WHERE tile_id NOT IN (SELECT tile_id FROM main.images);"
    c.execute(sql.format(alias=child['alias']))
    # Close cursor
    c.close()
    # Commit changes
    master.commit()
# Process datasets
for child in children:
    # Detach database
    sql = "DETACH DATABASE {alias};"
    m.execute(sql.format(alias=child['alias']))
# Purge old meta table
sql = "DELETE FROM main.metadata;"
m.execute(sql)
# Update meta table
sql = "INSERT INTO main.metadata (name, value) VALUES ('{name}','{value}');"
m.execute(sql.format(name='name',value=meta['name']))
m.execute(sql.format(name='format',value=meta['format']))
m.execute(sql.format(name='minzoom',value=meta['minzoom']))
m.execute(sql.format(name='maxzoom',value=meta['maxzoom']))
m.execute(sql.format(name='bounds',value=','.join(meta['bounds'])))
# Close m cursor
m.close()
# Commit changes
master.commit()
# Close connection
master.close()
