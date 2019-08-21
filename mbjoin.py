import sqlite3
import shutil
import argparse
from PIL import Image
from io import BytesIO
import os

#Setup arg parser
parser = argparse.ArgumentParser(description='Merges a series of raster MBTiles files.',
    epilog="Link to github#############")
parser.add_argument('-f', dest='format', metavar='format', const='jpg', nargs='?', help='Output format (PNG or JPEG)', choices=['png','jpg'])
parser.add_argument('-a', dest='action', metavar='merge action',const='blend', nargs='?', help='Merge action. blend () or alphacomposite (png only, replaces nodata from image 2 with nodata of image 1)', choices=['blend','alphacomposite'])
parser.add_argument('-p', dest='palette', metavar='palette colours',const=16, type=int, nargs='?',help='Number of output colours in the palette (png Only)')
parser.add_argument('out_file', metavar='output path',help='Output MBTiles file path')
parser.add_argument('in_files', nargs='+', metavar='input paths',help='List of MBTiles files to merge, in increasing order of importance (latter files will override earlier ones)')

#Parse args
try:
    args = parser.parse_args()
except BaseException as ex:
    print(ex)
    parser.print_help()
    raise SystemExit
#Get dataset 1
out = args.out_file
datasets = args.in_files
#Create output by copying dataset 1
print('Processing %s' % datasets[0])
if os.path.exists(out):
	os.remove(out)
shutil.copy2(datasets[0], out)
#Connect to master
master = sqlite3.connect(out)
#Loop through additional datasets
dataset_count = len(datasets)-1
for dataset in datasets[dataset_count:]:
	print('Processing %s' % dataset)
	#Attach dataset mbtiles
	sql = "ATTACH DATABASE ? AS child;"
	params = (dataset,)
	master.execute(sql, params)
	#Setup cursor
	c = master.cursor()
	#Update transparency table
	print('\tUpdate Transparency Table')
	sql = "INSERT INTO main.images_transparency (tile_id, transparency) SELECT tile_id, transparency FROM child.images_transparency WHERE tile_id NOT IN (SELECT tile_id FROM main.images_transparency);"
	c.execute(sql)
	#Update map table
	print('\tUpdate Map Table')
	sql = "INSERT INTO main.map (zoom_level, tile_column, tile_row, tile_id) SELECT zoom_level, tile_column, tile_row, tile_id FROM child.map WHERE tile_id NOT IN (SELECT tile_id FROM main.map);"
	c.execute(sql)
	#Get overlapping tiles
	print('\tUpdate Overlapping Tiles')
	sql = "SELECT i1.tile_id, i1.tile_data as png1, i2.tile_data as png2 FROM main.images i1 INNER JOIN child.images i2 ON i1.tile_id = i2.tile_id;"
	c.execute(sql)
	#Process overlapping tiles
	for row in c:
		#Get tiles
		img1 = Image.open(BytesIO(row[1]))
		img2 = Image.open(BytesIO(row[2]))
		if args.format == 'png':
			#Convert tile from pal to rgba
			img1 = img1.convert('RGBA')
			img2 = img2.convert('RGBA')
		else:
			img1 = img1.convert('RGB')
			img2 = img2.convert('RGB')
		#Merge tiles
		if args.format == 'png' and args.action == 'alphacomposite':
			img3 = Image.alpha_composite(img1, img2)
		else:
			img3 = Image.blend(img1, img2, 0.5)
		#Save image to buffer
		img3out = BytesIO()
		if args.format == 'png':
			img3compress = img3.convert('P', palette=Image.ADAPTIVE, colors=args.palette)
			img3compress.save(img3out, optimize=True, format='PNG')
		else:
			img3.save(img3out, optimize=True, format='JPEG')
		#Update tile
		u = master.cursor()
		sql = "UPDATE main.images SET tile_data = ? WHERE tile_id = ?;"
		params = (img3out.getvalue(),row[0],)
		u.execute(sql,params)
		u.close()
	#Append non-overlapping tiles
	print('\tUpdate Non Overlapping Tiles')
	sql = "INSERT INTO main.images (tile_id, tile_data) SELECT tile_id, tile_data FROM child.images WHERE tile_id NOT IN (SELECT tile_id FROM main.images);"
	c.execute(sql)
	#Close cursor
	c.close()
	#Commit changes
	master.commit()
	#detach database
	sql = "DETACH DATABASE child;"
	master.execute(sql)
#Close connection
master.close()
