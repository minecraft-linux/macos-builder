from os import makedirs, path, popen
from shutil import rmtree
from jinja2 import Template

# Change for each release
VERSION = '0.0.1'

TEMPLATES_DIR = 'templates'
OUTPUT_DIR = 'output'
APP_OUTPUT_NAME = 'Minecraft Bedrock Launcher.app'

if path.exists(path.join(OUTPUT_DIR)):
  print('Removing `{}/`! Click enter to continue, or ^C to exit'.format(OUTPUT_DIR))
  input()
  rmtree(OUTPUT_DIR)

makedirs(path.join(OUTPUT_DIR, APP_OUTPUT_NAME, 'Contents', 'Resources'))
makedirs(path.join(OUTPUT_DIR, APP_OUTPUT_NAME, 'Contents', 'MacOS'))

# Download .icns file
popen(
  'wget https://github.com/minecraft-linux/mcpelauncher-proprietary/raw/master/minecraft.icns -q -o /dev/null -O "{}"'.format(
    path.join(OUTPUT_DIR, APP_OUTPUT_NAME, 'Contents', 'Resources', 'minecraft.icns')
  )
)

with open(path.join(TEMPLATES_DIR, 'Info.plist.tmpl'), 'r') as raw:
  info = Template(raw.read())
  output = info.render(
    cf_bundle_executable = 'mcpelauncher-ui-qt',
    cf_bundle_get_info_string = 'Minecraft Bedrock Launcher',
    cf_bundle_icon_file = 'minecraft',
    cf_bundle_name = 'Minecraft Bedrock Launcher',
    cf_bundle_version = VERSION
  )

  f = open(path.join(OUTPUT_DIR, APP_OUTPUT_NAME, 'Contents', 'Info.plist'), 'w')
  f.write(output)
  f.close()

print('App bundle has been built at {}!'.format(path.join(OUTPUT_DIR, APP_OUTPUT_NAME)))