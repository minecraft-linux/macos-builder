from subprocess import check_call as call
from os import path, makedirs, symlink, rmdir, remove, rename
from shutil import copyfile, copytree
from ds_store import DSStore
from pprint import pprint
from mac_alias import Alias
import os

SOURCE_DIR = 'source'
OUTPUT_DIR = 'output'
DMG_OUTPUT_NAME = 'Minecraft Bedrock Launcher.dmg'
DMG_OUTPUT_PATH = path.join(OUTPUT_DIR, DMG_OUTPUT_NAME)
DMG_MOUNT_PATH = '/Volumes/Minecraft Bedrock Launcher/'
APP_OUTPUT_NAME = 'Minecraft Bedrock Launcher.app'
APP_OUTPUT_DIR = path.join(OUTPUT_DIR, APP_OUTPUT_NAME)

VOL_NAME = 'Minecraft Bedrock Launcher'

if path.exists(DMG_OUTPUT_PATH):
    remove(DMG_OUTPUT_PATH)

BG_FILE = path.join(SOURCE_DIR, 'dmg-background.tif')
if not path.exists(BG_FILE):
    call(['curl', '-k', '-sL', '-o', BG_FILE, 'https://mrarm.io/u/dmg-background.tif'])

# we assume here that sectors are 512B
IMAGE_SECTOR_SIZE = 512


def calc_size(p):
    ret = 0
    for entry in os.scandir(p):
        if not entry.is_symlink():
            ret += (entry.stat().st_size + IMAGE_SECTOR_SIZE - 1) // IMAGE_SECTOR_SIZE
        ret += 16 + 4 * 8
        if entry.is_dir():
            ret += calc_size(entry.path)
    return ret

image_sectors = calc_size(APP_OUTPUT_DIR) + 1024 * 1024 * 4 // IMAGE_SECTOR_SIZE
try:
    makedirs('empty')
    call(['hdiutil', 'create', '-fs', 'HFS+', '-format', 'UDRW', '-sectors', str(image_sectors), '-volname', VOL_NAME,
          '-srcfolder', 'empty', '-quiet', DMG_OUTPUT_PATH])
finally:
    rmdir('empty')
call(['hdiutil', 'attach', '-noautoopen', '-mountpoint', DMG_MOUNT_PATH, '-quiet', DMG_OUTPUT_PATH])

symlink("/Applications", path.join(DMG_MOUNT_PATH, "Applications"))
copytree(APP_OUTPUT_DIR, path.join(DMG_MOUNT_PATH, APP_OUTPUT_NAME), symlinks=True)
copyfile(BG_FILE, path.join(DMG_MOUNT_PATH, ".background.tif"))

with DSStore.open(path.join(DMG_MOUNT_PATH, '.DS_Store'), 'w+') as d:
    d['Minecraft Bedrock Launcher.app']['Iloc'] = (152, 220 - 15)
    d['Applications']['Iloc'] = (488, 220 - 10)
    d['.']['bwsp'] = {
        'ShowStatusBar': False,
        'ShowPathbar': False,
        'ShowToolbar': False,
        'ShowTabView': False,
        'ContainerShowSidebar': False,
        'WindowBounds': '{{100, 350}, {640, 422}}',
        'ShowSidebar': False
    }
    d['.']['icvp'] = {
        'backgroundColorRed': 1.0,
        'backgroundColorGreen': 1.0,
        'backgroundColorBlue': 1.0,
        'iconSize': 64.0,
        'backgroundImageAlias': Alias.for_file(path.join(DMG_MOUNT_PATH, '.background.tif')).to_bytes(),
        'textSize': 13.0,
        'backgroundType': 2,
        'gridOffsetX': 0.0,
        'gridOffsetY': 0.0,
        'showItemInfo': False,
        'viewOptionsVersion': 1,
        'arrangeBy': 'none',
        'labelOnBottom': True,
        'showIconPreview': True,
        'gridSpacing': 50.0
    }

call(['hdiutil', 'detach', '-quiet', DMG_MOUNT_PATH])
rename(DMG_OUTPUT_PATH, DMG_OUTPUT_PATH + '.tmp')
call(['hdiutil', 'convert', '-format', 'UDZO', '-imagekey', 'zlib-level=6', '-o', DMG_OUTPUT_PATH, '-quiet',
      DMG_OUTPUT_PATH + '.tmp'])
remove(DMG_OUTPUT_PATH + '.tmp')
