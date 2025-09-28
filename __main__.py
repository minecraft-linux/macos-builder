from os import makedirs, path, cpu_count, listdir, getenv
from subprocess import check_call as call
import subprocess
from shutil import rmtree, copyfile, copytree
import shutil
import argparse
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
parser.add_argument('--update-sparkle-appcast', help='Sparkle appcast URL')
parser.add_argument('--update-sparkle-ed-public-key', help='Enable checking updates in the metalauncher from the specified URL')
parser.add_argument('--version', help='App version')
parser.add_argument('--prettyversion', help='App pretty version in settings')
parser.add_argument('--force', help='Always remove the output directory', action='store_true')
parser.add_argument('--qtworkaround', help='apply a qt workaround', action='store_true')
parser.add_argument('--skip-sync-sources', help='skip sync-sources', action='store_true')
parser.add_argument('--use-own-curl', help='skip sync-sources', action='store_true')
parser.add_argument('--app-root', help='base folder of the Application before running macdeployqt')
args = parser.parse_args()

if(args.version):
    VERSION = args.version

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
    call(['curl', '-sL', '-o', ICON_FILE, 'https://github.com/minecraft-linux/mcpelauncher-ui-qt/raw/0b956a0fc816d900d5b3f2883c6a401330c50fab/Resources/mcpelauncher-icon.icns'])
copyfile(ICON_FILE, path.join(APP_OUTPUT_DIR, 'Contents', 'Resources', 'minecraft.icns'))

# Download the sources
def clone_repo(name, url, branch):
    display_stage("Cloning repository: " + url)
    directory = path.join(SOURCE_DIR, name)
    if not path.isdir(directory):
        makedirs(directory)
        call(['git', 'init'], cwd=directory)
        call(['git', 'remote', 'add', 'origin', url], cwd=directory)
        call(['git', 'fetch', 'origin', branch], cwd=directory)
        call(['git', 'reset', '--hard', 'FETCH_HEAD'], cwd=directory)
        call(['git', 'submodule', 'update', '--init', '--recursive'], cwd=directory)
    else:
        call(['git', 'pull'], cwd=directory)
        call(['git', 'submodule', 'update', '--init', '--recursive'], cwd=directory)

if not args.skip_sync_sources:
    display_stage("Downloading sources")

    with open('msa.commit', 'r') as file:
        clone_repo('msa', 'https://github.com/minecraft-linux/msa-manifest.git', file.read().replace('\n', ''))
    with open('mcpelauncher.commit', 'r') as file:
        clone_repo('mcpelauncher', 'https://github.com/minecraft-linux/mcpelauncher-manifest.git', file.read().replace('\n', ''))
    with open('mcpelauncher-ui.commit', 'r') as file:
        clone_repo('mcpelauncher-ui', 'https://github.com/minecraft-linux/mcpelauncher-ui-manifest.git', file.read().replace('\n', ''))

# Build
# QT_INSTALL_PATH = subprocess.check_output(['brew', '--prefix', 'qt']).decode('utf-8').strip()
QT_INSTALL_PATH = path.abspath(args.qt_path)
CMAKE_INSTALL_PREFIX = path.abspath(path.join(SOURCE_DIR, "install"))
CMAKE_QT_EXTRA_OPTIONS = ["-DCMAKE_PREFIX_PATH=" + QT_INSTALL_PATH, '-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON']

MCPELAUNCHER_EXTRA_OPTIONS = []
if args.use_own_curl:
    MCPELAUNCHER_EXTRA_OPTIONS += [ "-DUSE_OWN_CURL=ON" ]
else:
    MCPELAUNCHER_EXTRA_OPTIONS += [ "-DUSE_OWN_CURL=OFF" ]

if not path.isdir(CMAKE_INSTALL_PREFIX):
    makedirs(CMAKE_INSTALL_PREFIX)

def cmake_cmd(source_dir):
    return ['cmake', source_dir, '-DCMAKE_INSTALL_PREFIX=' + CMAKE_INSTALL_PREFIX, '-DCMAKE_POLICY_VERSION_MINIMUM=4.0']

def build_component(name, cmake_opts):
    display_stage("Building: " + name)
    source_dir = path.abspath(path.join(SOURCE_DIR, name))
    build_dir = path.join(SOURCE_DIR, "build", name)
    if not path.isdir(build_dir):
        makedirs(build_dir)
    call(cmake_cmd(source_dir) + cmake_opts, cwd=build_dir)
    call(['make', '-j' + str(cpu_count()), 'install'], cwd=build_dir)

def build_component32(name, cmake_opts):
    display_stage("Building: " + name)
    source_dir = path.abspath(path.join(SOURCE_DIR, name))
    build_dir = path.join(SOURCE_DIR, "build", name)
    if not path.isdir(build_dir):
        makedirs(build_dir)
    call(cmake_cmd(source_dir) + cmake_opts, cwd=build_dir)
    call(['make', '-j' + str(cpu_count())], cwd=build_dir)
    shutil.copy2(path.join(build_dir, 'mcpelauncher-client', 'mcpelauncher-client'), path.join(CMAKE_INSTALL_PREFIX, 'bin', 'mcpelauncher-client32'))

VERSION_OPTS = []
if args.update_url and args.build_id:
    VERSION_OPTS = ["-DENABLE_UPDATE_CHECK=ON", "-DUPDATE_CHECK_URL=" + args.update_url, "-DUPDATE_CHECK_BUILD_ID=" + args.build_id]

SPARKLE_OPTS = []
if args.update_sparkle_appcast:
    SPARKLE_OPTS = [ "-DENABLE_SPARKLE_UPDATE_CHECK=1", "-DSPARKLE_UPDATE_CHECK_URL=" + args.update_sparkle_appcast]

display_stage("Building")
OPENSSL64_OPTS = [ '-DOPENSSL_ROOT_DIR=' + path.abspath('ssl64'), '-DOPENSSL_CRYPTO_LIBRARY=' + path.abspath('ssl64/lib/libcrypto.dylib')]
OPENSSL64_INCLUDES = '-I' + path.abspath('ssl64/include') + ' -L' + path.abspath('ssl64/lib')
build_component("msa", ['-DENABLE_MSA_QT_UI=ON', '-DMSA_UI_PATH_DEV=OFF', '-DCMAKE_CXX_FLAGS=-DNDEBUG  -Wl,-L' + path.abspath('libcxx-build') + ',-rpath,@loader_path/../Frameworks' +' -D_LIBCPP_DISABLE_AVAILABILITY=1 -I' + path.abspath('libcxx64-build/include/cxx/v1')] + CMAKE_QT_EXTRA_OPTIONS)
build_component("mcpelauncher", ['-DMSA_DAEMON_PATH=.', '-DENABLE_DEV_PATHS=OFF', '-DBUILD_FAKE_JNI_TESTS=OFF', '-DXAL_WEBVIEW_QT_PATH=.', '-DJNI_USE_JNIVM=ON', '-DBUILD_FAKE_JNI_EXAMPLES=OFF', '-DCMAKE_CXX_FLAGS=-DNDEBUG -Wl,-L' + path.abspath('libcxx-build') +',-rpath,@loader_path/../Frameworks -D_LIBCPP_DISABLE_AVAILABILITY=1 -I' + path.abspath('libcxx64-build/include/cxx/v1') + ' ' + OPENSSL64_INCLUDES] + CMAKE_QT_EXTRA_OPTIONS + MCPELAUNCHER_EXTRA_OPTIONS + OPENSSL64_OPTS)
build_component32("mcpelauncher", ['-DMSA_DAEMON_PATH=.', '-DENABLE_DEV_PATHS=OFF', '-DENABLE_QT_ERROR_UI=OFF', '-DBUILD_FAKE_JNI_TESTS=OFF', '-DOPENSSL_ROOT_DIR=' + path.abspath('ssl32'), '-DOPENSSL_CRYPTO_LIBRARY=' + path.abspath('ssl32/lib/libcrypto.dylib'), '-DBUILD_FAKE_JNI_EXAMPLES=OFF', '-DCMAKE_ASM_FLAGS=-m32', '-DCMAKE_C_FLAGS=-m32', '-DCMAKE_CXX_FLAGS=-m32 -DNDEBUG -Wl,-L' + path.abspath('libcxx-build') +',-rpath,@loader_path/../Frameworks -D_LIBCPP_DISABLE_AVAILABILITY=1 -I' + path.abspath('libcxx32-build/include/cxx/v1') + ' -I' + path.abspath('ssl32/include') + ' -L' + path.abspath('ssl32/lib'), '-DCMAKE_CXX_COMPILER_TARGET=i386-apple-darwin', '-DCMAKE_LIBRARY_ARCHITECTURE=i386-apple-darwin', '-DBUILD_WEBVIEW=OFF', '-DXAL_WEBVIEW_QT_PATH=.', '-DJNI_USE_JNIVM=ON'] + MCPELAUNCHER_EXTRA_OPTIONS)
ADDITIONAL_UI_OPTS = []
if args.prettyversion:
    ADDITIONAL_UI_OPTS += [ "-DLAUNCHER_VERSION_NAME=" + args.prettyversion ]
if args.build_id:
    ADDITIONAL_UI_OPTS += [ "-DLAUNCHER_VERSION_CODE=" + args.build_id ]
changelog = ""
with open('changelog.txt', 'r') as file:
    changelog = file.read().replace('\n', '<br/>')
    ADDITIONAL_UI_OPTS += [ "-DLAUNCHER_CHANGE_LOG=" + changelog ]

with open('versionsdb.txt', 'r') as file:
    ref = file.read().replace('\n', '')
    clone_repo('versionsdb', 'https://github.com/minecraft-linux/mcpelauncher-versiondb.git', ref)
    ADDITIONAL_UI_OPTS += [ "-DLAUNCHER_VERSIONDB_PATH=" + path.abspath(path.join(SOURCE_DIR, 'versionsdb'))]

with open('versionsdbremote.txt', 'r') as file:
    ref = file.read().replace('\n', '')
    ADDITIONAL_UI_OPTS += [ "-DLAUNCHER_VERSIONDB_URL=https://raw.githubusercontent.com/minecraft-linux/mcpelauncher-versiondb/" + ref]

build_component("mcpelauncher-ui", ['-DGAME_LAUNCHER_PATH=.', '-DCMAKE_CXX_FLAGS=-DNDEBUG -Wl,-F'+ QT_INSTALL_PATH + '/lib/,-L' + path.abspath('libcxx-build') +',-rpath,@loader_path/../Frameworks -D_LIBCPP_DISABLE_AVAILABILITY=1 -I' + path.abspath('libcxx64-build/include/cxx/v1') + ' ' + OPENSSL64_INCLUDES, "-DQt5QuickCompiler_FOUND=OFF", "-DLAUNCHER_ENABLE_GOOGLE_PLAY_LICENCE_CHECK=ON", "-DLAUNCHER_DISABLE_DEV_MODE=ON"] + VERSION_OPTS + SPARKLE_OPTS + CMAKE_QT_EXTRA_OPTIONS + ADDITIONAL_UI_OPTS + OPENSSL64_OPTS)

display_stage("Copying files")
def copy_installed_files(from_path, to_path):
    for f in listdir(from_path):
        print("Copying file: " + f)
        if path.isdir(path.join(from_path, f)):
            copytree(path.join(from_path, f), path.join(to_path, f), True, dirs_exist_ok = True)
        else:
            shutil.copy2(path.join(from_path, f), path.join(to_path, f), follow_symlinks = False)

if path.exists(args.app_root):
    copy_installed_files(args.app_root, APP_OUTPUT_DIR)

copy_installed_files(path.join(CMAKE_INSTALL_PREFIX, 'bin'), path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS'))
copy_installed_files(path.join(CMAKE_INSTALL_PREFIX, 'share'), path.join(APP_OUTPUT_DIR, 'Contents', 'Resources'))
# Workaround Qt 5.9.2
if args.qtworkaround:
    copy_installed_files(path.join(QT_INSTALL_PATH, 'qml', 'QtQuick'), path.join(APP_OUTPUT_DIR, 'Contents', 'Resources', 'qml', 'QtQuick'))
    copy_installed_files(path.join(QT_INSTALL_PATH, 'qml', 'QtQuick.2'), path.join(APP_OUTPUT_DIR, 'Contents', 'Resources', 'qml', 'QtQuick.2'))

display_stage("Building Info.plist file")
with open(path.join(TEMPLATES_DIR, 'Info.plist.tmpl'), 'r') as raw:
    info = Template(raw.read())
    output = info.render(
        cf_bundle_identifier = 'io.mrarm.mcpelauncher.ui',
        cf_bundle_executable = 'mcpelauncher-ui-qt',
        cf_bundle_get_info_string = 'Minecraft Bedrock Launcher',
        cf_bundle_icon_file = 'minecraft',
        cf_bundle_name = 'Minecraft Bedrock Launcher',
        cf_bundle_version = VERSION,
        cf_sparkle_feed = args.update_sparkle_appcast,
        cf_sparkle_public_ed_key = args.update_sparkle_ed_public_key,
        cf_bundle_macos_min = getenv("MACOSX_DEPLOYMENT_TARGET", "10.7")
    )

    f = open(path.join(APP_OUTPUT_DIR, 'Contents', 'Info.plist'), 'w')
    f.write(output)
    f.close()

display_stage("Copying Qt libraries")
QT_DEPLOY_OPTIONS = [path.join(QT_INSTALL_PATH, 'bin', 'macdeployqt'),  APP_OUTPUT_DIR]
QT_DEPLOY_OPTIONS.append('-qmldir=' + path.join(SOURCE_DIR, 'mcpelauncher-ui', 'mcpelauncher-ui-qt'))
QT_DEPLOY_OPTIONS.append('-qmldir=' + path.join(SOURCE_DIR, 'mcpelauncher', 'mcpelauncher-webview'))
QT_DEPLOY_OPTIONS.append('-qmldir=' + path.join(SOURCE_DIR, 'mcpelauncher', 'mcpelauncher-errorwindow', 'src', 'qml'))
QT_DEPLOY_OPTIONS.append('-executable=' + path.abspath(path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS', 'mcpelauncher-ui-qt')))
QT_DEPLOY_OPTIONS.append('-executable=' + path.abspath(path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS', 'msa-ui-qt')))
QT_DEPLOY_OPTIONS.append('-executable=' + path.abspath(path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS', 'mcpelauncher-webview')))
QT_DEPLOY_OPTIONS.append('-executable=' + path.abspath(path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS', 'mcpelauncher-error')))
call(QT_DEPLOY_OPTIONS)
