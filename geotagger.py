from PIL import Image, ImageDraw
import math
import requests
from io import BytesIO
from dataclasses import dataclass
from pathlib import Path
import argparse
from glob import glob

GPS_INFO_TAG = 34853
GPS_LAT_REF_TAG = 1
GPS_LAT_TAG = 2
GPS_LON_REF_TAG = 3
GPS_LON_TAG = 4
GPS_DIF_REF_TAG = 16
GPS_DIR_TAG = 17
TILE_WIDTH = 256
TILE_HEIGHT = 256
HEADERS = {"User-Agent": "Geotagger/1.0"}

DEFAULT_ZOOM = 18
DEFAULT_AREA = 100
DEFAULT_SCALE = 100
DOT_SIZE = 8
LINE_IMG_FRAC = 0.5
FOV_ALPHA = 45
FOV_ARC_FRAC = 0.2


@dataclass(eq=True, frozen=True)
class TileRef:
    x: int
    y: int
    zoom: int


@dataclass
class GeoData:
    lat: float
    lon: float
    dir: float | None = None


@dataclass
class Point:
    x: float
    y: float


@dataclass
class Box:
    x_min: int
    y_min: int
    x_max: int
    y_max: int


def get_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Add location map to photo.\n'
        'You can specify level of details by zoom parameter.\n'
        'With area parameter you can control how big area will be rendered, it results in map size.\n'
        'You can scale generated map preview with scale parameter.')
    parser.add_argument('file_name', nargs='+')
    parser.add_argument('--zoom', type=int, choices=range(10, 20),
                        metavar='[10-19]', help=f'Map zoom, level of details (default: {DEFAULT_ZOOM})', default=DEFAULT_ZOOM)
    parser.add_argument('--area', type=int, choices=range(10, 501),
                        metavar='[10-500]', help=f'Area of the map in percentage (default: {DEFAULT_AREA})', default=DEFAULT_AREA)
    parser.add_argument('--scale', type=int, choices=range(10, 501),
                        metavar='[10,500]', help=f'Scale of the map in percentage (default: {DEFAULT_SCALE})', default=DEFAULT_SCALE)
    args = parser.parse_args()
    args.area /= 100.0
    args.scale /= 100.0
    args.file_names = []
    for f in args.file_name:
        args.file_names += glob(f)
    return args


args = get_args()
tiles_cache = {}


def get_geodata(image: Image) -> GeoData | None:
    exif_data = image._getexif()
    ret = None
    if exif_data and GPS_INFO_TAG in exif_data:
        gps_data = exif_data[GPS_INFO_TAG]
        if GPS_LAT_TAG in gps_data and GPS_LAT_REF_TAG in gps_data and GPS_LON_TAG in gps_data and GPS_LON_REF_TAG in gps_data:
            lat_coords = gps_data[GPS_LAT_TAG]
            lat = (-1 if gps_data[GPS_LAT_REF_TAG] == 'S' else 1) * \
                (lat_coords[0] + (lat_coords[1] + lat_coords[2] / 60.0) / 60.0)
            lon_coords = gps_data[GPS_LON_TAG]
            lon = (-1 if gps_data[GPS_LON_REF_TAG] == 'W' else 1) * \
                (lon_coords[0] + (lon_coords[1] + lon_coords[2] / 60.0) / 60.0)
            ret = GeoData(lat, lon)
            if GPS_DIR_TAG in gps_data:
                ret.dir = gps_data[GPS_DIR_TAG]
    return ret


def get_tile_coord(geodata: GeoData, zoom: float) -> Point:
    lat_rad = math.radians(geodata.lat)
    n = 2.0 ** zoom
    x = (geodata.lon + 180.0) / 360.0 * n
    y = (1.0 - math.log(math.tan(lat_rad) +
         (1 / math.cos(lat_rad))) / math.pi) / 2.0 * n
    return Point(x, y)


def download_tile(tile: TileRef) -> Image:
    img_data = requests.get(
        f'http://a.tile.openstreetmap.org/{tile.zoom}/{tile.x}/{tile.y}.png', headers=HEADERS)
    if img_data.status_code != 200:
        raise Exception(img_data.text)
    return Image.open(BytesIO(img_data.content))


def get_tile(tile: TileRef) -> Image:
    if tile not in tiles_cache:
        tiles_cache[tile] = download_tile(tile)
    return tiles_cache[tile]


def generate_map(geodata: GeoData, zoom: float, tile_area: float) -> Image:
    tile_coord = get_tile_coord(geodata, zoom)
    tile_box = Box(x_min=math.floor(tile_coord.x - tile_area / 2),
                   x_max=math.floor(tile_coord.x + tile_area / 2),
                   y_min=math.floor(tile_coord.y - tile_area / 2),
                   y_max=math.floor(tile_coord.y + tile_area / 2))
    map = Image.new('RGB', ((tile_box.x_max - tile_box.x_min + 1) *
                    TILE_WIDTH, (tile_box.y_max - tile_box.y_min + 1) * TILE_HEIGHT))
    for x in range(tile_box.x_min, tile_box.x_max + 1):
        for y in range(tile_box.y_min, tile_box.y_max + 1):
            tile_img = get_tile(TileRef(zoom=zoom, x=x, y=y))
            map.paste(tile_img, ((x - tile_box.x_min) * TILE_WIDTH,
                      (y - tile_box.y_min) * TILE_HEIGHT))
    crop_x = (tile_coord.x - tile_area / 2 - tile_box.x_min) * TILE_WIDTH
    crop_y = (tile_coord.y - tile_area / 2 - tile_box.y_min) * TILE_HEIGHT
    map = map.crop((crop_x, crop_y, crop_x + tile_area *
                   TILE_WIDTH, crop_y + tile_area * TILE_HEIGHT))
    draw = ImageDraw.Draw(map)
    draw.ellipse((int((map.width - DOT_SIZE) / 2), int((map.height - DOT_SIZE) / 2), int(
        (map.width + DOT_SIZE) / 2), int((map.height + DOT_SIZE) / 2)), outline='red', width=2)
    if geodata.dir:
        def draw_line(angle: float):
            angle = angle / 180.0 * math.pi
            draw.line([int(map.width / 2), int(map.height / 2), int(map.width * (1 + math.sin(angle) * LINE_IMG_FRAC) / 2),
                      int(map.height * (1 - math.cos(angle) * LINE_IMG_FRAC) / 2)], fill='red', width=2)
        draw_line(geodata.dir - FOV_ALPHA / 2)
        draw_line(geodata.dir + FOV_ALPHA / 2)
        draw.arc([int(map.width * (1 - FOV_ARC_FRAC) / 2), int(map.height * (1 - FOV_ARC_FRAC) / 2),
                 int(map.width * (1 + FOV_ARC_FRAC) / 2), int(map.height * (1 + FOV_ARC_FRAC) / 2)],
                 geodata.dir - FOV_ALPHA / 2 - 90, geodata.dir + FOV_ALPHA / 2 - 90, fill='red', width=2)
    return map


def add_map_to_image(path: Path, zoom: float, tile_area: float, scale: float) -> None:
    try:
        image = Image.open(path)
    except:
        print(f'File {path} is not an image')
        return
    geodata = get_geodata(image)
    if not geodata:
        print(f'Image {path} does not contain coordinates')
        return
    print(
        f'Generating map for {path}{"" if geodata.dir else " (direction not included)"}...')
    map = generate_map(geodata, zoom, tile_area)
    if scale != 1.0:
        map = map.resize(
            [int(map.width * scale), int(map.height * scale)], Image.Resampling.NEAREST)
    image.paste(map, (image.width - map.width, image.height - map.height))
    image.save((path.parent / (path.stem + '_map')).with_suffix(path.suffix))


if not args.file_names:
    print('No files found')
    exit(0)

for f in args.file_names:
    add_map_to_image(Path(f), args.zoom, args.area, args.scale)
