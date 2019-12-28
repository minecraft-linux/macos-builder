from os import makedirs, path, cpu_count, listdir
from subprocess import check_call as call, check_output
import subprocess
from shutil import rmtree, copyfile, copytree
import shutil
import argparse
import json
from jinja2 import Template

# Change for each release
VERSION = '0.0.1'

TEMPLATES_DIR = 'templates'
OUTPUT_DIR = 'output'
SOURCE_DIR = 'source'
APP_OUTPUT_NAME = 'Minecraft Bedrock Launcher.app'
APP_OUTPUT_DIR = path.join(OUTPUT_DIR, APP_OUTPUT_NAME)

ENABLE_COLORS=True


def display_stage(name):
    if ENABLE_COLORS:
        print("\x1B[1m\x1B[32m=> " + name + "\x1B[0m")
    else:
        print(name)


parser = argparse.ArgumentParser()
parser.add_argument('--qt-path', help='Specify the Qt installation path', required=True)
parser.add_argument('--update-url', help='Enable checking updates in the metalauncher from the specified URL')
parser.add_argument('--build-id', help='Specify the build ID for update checking purposes')
parser.add_argument('--force', help='Always remove the output directory', action='store_true')
args = parser.parse_args()

if path.exists(path.join(OUTPUT_DIR)):
    if not args.force:
        print('Removing `{}/`! Click enter to continue, or ^C to exit'.format(OUTPUT_DIR))
        input()
    rmtree(OUTPUT_DIR)

display_stage("Initializing")
makedirs(path.join(APP_OUTPUT_DIR, 'Contents', 'Resources'))
makedirs(path.join(APP_OUTPUT_DIR, 'Contents', 'Frameworks'))
makedirs(path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS'))
if not path.isdir(SOURCE_DIR):
    makedirs(SOURCE_DIR)

# Download .icns file
ICON_FILE = path.join(SOURCE_DIR, 'minecraft.icns')
if not path.exists(ICON_FILE):
    display_stage("Downloading icons file")
    call(['curl', '-sL', '-o', ICON_FILE, 'https://github.com/minecraft-linux/mcpelauncher-proprietary/raw/master/minecraft.icns'])
copyfile(ICON_FILE, path.join(APP_OUTPUT_DIR, 'Contents', 'Resources', 'minecraft.icns'))

# Download the sources
def clone_repo(name, url):
    display_stage("Cloning repository: " + url)
    directory = path.join(SOURCE_DIR, name)
    if not path.isdir(directory):
        call(['git', 'clone', '--recursive', url, directory])
    else:
        call(['git', 'pull'], cwd=directory)
        call(['git', 'submodule', 'update'], cwd=directory)

display_stage("Downloading sources")
clone_repo('msa', 'https://github.com/minecraft-linux/msa-manifest.git')
clone_repo('mcpelauncher', 'https://github.com/minecraft-linux/mcpelauncher-manifest.git')
clone_repo('mcpelauncher-ui', 'https://github.com/minecraft-linux/mcpelauncher-ui-manifest.git')

# Build
# QT_INSTALL_PATH = subprocess.check_output(['brew', '--prefix', 'qt']).decode('utf-8').strip()
QT_INSTALL_PATH = path.abspath(args.qt_path)
CMAKE_INSTALL_PREFIX = path.abspath(path.join(SOURCE_DIR, "install"))
CMAKE_INSTALL_FRAMEWORK_DIR = path.join(CMAKE_INSTALL_PREFIX, 'Frameworks')
CMAKE_QT_EXTRA_OPTIONS = ["-DCMAKE_PREFIX_PATH=" + QT_INSTALL_PATH, '-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON']

if not path.isdir(CMAKE_INSTALL_PREFIX):
    makedirs(CMAKE_INSTALL_PREFIX)

if not path.isdir(CMAKE_INSTALL_FRAMEWORK_DIR):
    makedirs(CMAKE_INSTALL_FRAMEWORK_DIR)

latest = json.loads(check_output(['curl', '-L', 'https://api.github.com/repos/minecraft-linux/osx-angle-ci/releases/latest']))
for asset in latest['assets']:
    assetfile = path.join(CMAKE_INSTALL_FRAMEWORK_DIR, asset['name'])
    if not path.isfile(assetfile):
        print('Downloading ' + asset['name'])
        call(['curl', '-L', asset['browser_download_url'], '--output', assetfile])

def build_component(name, cmake_opts):
    display_stage("Building: " + name)
    source_dir = path.abspath(path.join(SOURCE_DIR, name))
    build_dir = path.join(SOURCE_DIR, "build", name)
    if not path.isdir(build_dir):
        makedirs(build_dir)
    call(['cmake', source_dir, '-DCMAKE_INSTALL_PREFIX=' + CMAKE_INSTALL_PREFIX] + cmake_opts, cwd=build_dir)
    call(['make', '-j' + str(cpu_count()), 'install'], cwd=build_dir)

VERSION_OPTS = []
if args.update_url and args.build_id:
    VERSION_OPTS = ["-DENABLE_UPDATE_CHECK=ON", "-DUPDATE_CHECK_URL=" + args.update_url, "-DUPDATE_CHECK_BUILD_ID=" + args.build_id]

display_stage("Building")
build_component("msa", ['-DENABLE_MSA_QT_UI=ON', '-DMSA_UI_PATH_DEV=OFF'] + CMAKE_QT_EXTRA_OPTIONS)
build_component("mcpelauncher", ['-DMSA_DAEMON_PATH=.', '-DENABLE_DEV_PATHS=OFF'])
build_component("mcpelauncher-ui", ['-DGAME_LAUNCHER_PATH=.'] + VERSION_OPTS + CMAKE_QT_EXTRA_OPTIONS)

display_stage("Copying files")
def copy_installed_files(from_path, to_path):
    for f in listdir(from_path):
        print("Copying file: " + f)
        if path.isdir(path.join(from_path, f)):
            copytree(path.join(from_path, f), path.join(to_path, f))
        else:
            shutil.copy2(path.join(from_path, f), path.join(to_path, f))

copy_installed_files(path.join(CMAKE_INSTALL_PREFIX, 'bin'), path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS'))
copy_installed_files(path.join(CMAKE_INSTALL_PREFIX, 'share'), path.join(APP_OUTPUT_DIR, 'Contents', 'Resources'))
copy_installed_files(path.join(CMAKE_INSTALL_PREFIX, 'Frameworks'), path.join(APP_OUTPUT_DIR, 'Contents', 'Frameworks'))

display_stage("Building Info.plist file")
with open(path.join(TEMPLATES_DIR, 'Info.plist.tmpl'), 'r') as raw:
    info = Template(raw.read())
    output = info.render(
        cf_bundle_identifier = 'io.mrarm.mcpelauncher.ui',
        cf_bundle_executable = 'mcpelauncher-ui-qt',
        cf_bundle_get_info_string = 'Minecraft Bedrock Launcher',
        cf_bundle_icon_file = 'minecraft',
        cf_bundle_name = 'Minecraft Bedrock Launcher',
        cf_bundle_version = VERSION
    )

    f = open(path.join(APP_OUTPUT_DIR, 'Contents', 'Info.plist'), 'w')
    f.write(output)
    f.close()

display_stage("Copying Qt libraries")
QT_DEPLOY_OPTIONS = [path.join(QT_INSTALL_PATH, 'bin', 'macdeployqt'),  APP_OUTPUT_DIR]
QT_DEPLOY_OPTIONS.append('-qmldir=' + path.join(SOURCE_DIR, 'mcpelauncher-ui', 'mcpelauncher-ui-qt'))
QT_DEPLOY_OPTIONS.append('-executable=' + path.abspath(path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS', 'mcpelauncher-ui-qt')))
QT_DEPLOY_OPTIONS.append('-executable=' + path.abspath(path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS', 'msa-ui-qt')))
call(QT_DEPLOY_OPTIONS)

display_stage('App bundle has been built at {}!'.format(path.join(OUTPUT_DIR, APP_OUTPUT_NAME)))
