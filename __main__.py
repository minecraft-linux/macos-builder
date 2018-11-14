from os import makedirs, path, cpu_count
from subprocess import check_call as call
from shutil import rmtree, copyfile
from jinja2 import Template

# Change for each release
VERSION = '0.0.1'

TEMPLATES_DIR = 'templates'
OUTPUT_DIR = 'output'
SOURCE_DIR = 'source'
APP_OUTPUT_NAME = 'Minecraft Bedrock Launcher.app'
APP_OUTPUT_DIR = path.join(OUTPUT_DIR, APP_OUTPUT_NAME)

if path.exists(path.join(OUTPUT_DIR)):
  print('Removing `{}/`! Click enter to continue, or ^C to exit'.format(OUTPUT_DIR))
  input()
  rmtree(OUTPUT_DIR)

makedirs(path.join(APP_OUTPUT_DIR, 'Contents', 'Resources'))
makedirs(path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS'))
makedirs(path.join(SOURCE_DIR))

# Download .icns file
ICON_FILE = path.join(SOURCE_DIR, 'minecraft.icns')
if not path.exists(ICON_FILE):
    call(['curl', '-s', '-o', ICON_FILE, 'https://github.com/minecraft-linux/mcpelauncher-proprietary/raw/master/minecraft.icns'])
copyfile(ICON_FILE, path.join(APP_OUTPUT_DIR, 'Contents', 'Resources', 'minecraft.icns'))

# Download the sources
def clone_repo(name, url):
  directory = path.join(SOURCE_DIR, name)
  if not path.isdir(directory):
    call(['git', 'clone', '--recursive', url, directory])
  else:
    call(['git', 'pull'], cwd=directory)
    call(['git', 'submodule', 'update'], cwd=directory)

clone_repo('msa', 'https://github.com/minecraft-linux/msa-manifest.git')
clone_repo('mcpelauncher', 'https://github.com/minecraft-linux/mcpelauncher-manifest.git')
clone_repo('mcpelauncher-ui', 'https://github.com/minecraft-linux/mcpelauncher-ui-manifest.git')

# Build
CMAKE_INSTALL_PREFIX = path.abspath(path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS'))

def build_component(name, cmake_opts):
    source_dir = path.abspath(path.join(SOURCE_DIR, name))
    build_dir = path.join(SOURCE_DIR, "build", name)
    if not path.isdir(build_dir):
        makedirs(build_dir)
    call(['cmake', source_dir, '-DCMAKE_INSTALL_PREFIX=' + CMAKE_INSTALL_PREFIX] + cmake_opts, cwd=build_dir)
    call(['make', '-j' + str(cpu_count()), 'install'], cwd=build_dir)

build_component("msa", ['-DENABLE_MSA_QT_UI=ON', '-DMSA_UI_PATH_DEV=OFF'])
build_component("mcpelauncher", ['-DMSA_DAEMON_PATH=.', '-DUSE_OWN_CURL=ON', '-DENABLE_DEV_PATHS=OFF'])
build_component("mcpelauncher-ui", ['-DGAME_LAUNCHER_PATH=.'])

with open(path.join(TEMPLATES_DIR, 'Info.plist.tmpl'), 'r') as raw:
  info = Template(raw.read())
  output = info.render(
    cf_bundle_executable = 'bin/mcpelauncher-ui-qt',
    cf_bundle_get_info_string = 'Minecraft Bedrock Launcher',
    cf_bundle_icon_file = 'minecraft',
    cf_bundle_name = 'Minecraft Bedrock Launcher',
    cf_bundle_version = VERSION
  )

  f = open(path.join(APP_OUTPUT_DIR, 'Contents', 'Info.plist'), 'w')
  f.write(output)
  f.close()

print('App bundle has been built at {}!'.format(path.join(OUTPUT_DIR, APP_OUTPUT_NAME)))
