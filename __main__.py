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
parser.add_argument('--buildangle', help='build the angle graphics lib', action='store_true')
parser.add_argument('--qtworkaround', help='apply a qt workaround', action='store_true')
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
    call(['curl', '-sL', '-o', ICON_FILE, 'https://github.com/minecraft-linux/mcpelauncher-proprietary/raw/master/minecraft.icns'])
copyfile(ICON_FILE, path.join(APP_OUTPUT_DIR, 'Contents', 'Resources', 'minecraft.icns'))

# Download the sources
def clone_repo(name, url, branch, orgurl = ""):
    display_stage("Cloning repository: " + url)
    directory = path.join(SOURCE_DIR, name)
    if not path.isdir(directory):
        call(['git', 'clone', '-b', branch, url, directory])
        if orgurl:
            call(['git', 'remote', 'set-url', 'origin', orgurl], cwd=directory)
            call(['git', 'submodule', 'sync'], cwd=directory)
    else:
        call(['git', 'pull'], cwd=directory)
    call(['git', 'submodule', 'update', '--init', '--recursive'], cwd=directory)

display_stage("Downloading sources")
clone_repo('msa', 'https://github.com/minecraft-linux/msa-manifest.git', 'master')
clone_repo('mcpelauncher', 'https://github.com/ChristopherHX/mcpelauncher-manifest.git', 'trmacOS', 'https://github.com/minecraft-linux/mcpelauncher-manifest.git')
clone_repo('mcpelauncher-ui', 'https://github.com/minecraft-linux/mcpelauncher-ui-manifest.git', 'ng')
#if args.buildangle:
#    clone_repo('osx-angle-ci', 'https://github.com/christopherhx/osx-angle-ci.git', 'master')

# Build
# QT_INSTALL_PATH = subprocess.check_output(['brew', '--prefix', 'qt']).decode('utf-8').strip()
QT_INSTALL_PATH = path.abspath(args.qt_path)
CMAKE_INSTALL_PREFIX = path.abspath(path.join(SOURCE_DIR, "install"))
CMAKE_QT_EXTRA_OPTIONS = ["-DCMAKE_PREFIX_PATH=" + QT_INSTALL_PATH, '-DCMAKE_INSTALL_RPATH_USE_LINK_PATH=ON']

if not path.isdir(CMAKE_INSTALL_PREFIX):
    makedirs(CMAKE_INSTALL_PREFIX)

def build_component(name, cmake_opts):
    display_stage("Building: " + name)
    source_dir = path.abspath(path.join(SOURCE_DIR, name))
    build_dir = path.join(SOURCE_DIR, "build", name)
    if not path.isdir(build_dir):
        makedirs(build_dir)
    call(['cmake', source_dir, '-DCMAKE_INSTALL_PREFIX=' + CMAKE_INSTALL_PREFIX] + cmake_opts, cwd=build_dir)
    call(['make', '-j' + str(cpu_count()), 'install'], cwd=build_dir)

def build_component32(name, cmake_opts):
    display_stage("Building: " + name)
    source_dir = path.abspath(path.join(SOURCE_DIR, name))
    build_dir = path.join(SOURCE_DIR, "build", name)
    if not path.isdir(build_dir):
        makedirs(build_dir)
    call(['cmake', source_dir, '-DCMAKE_INSTALL_PREFIX=' + CMAKE_INSTALL_PREFIX] + cmake_opts, cwd=build_dir)
    call(['make', '-j' + str(cpu_count())], cwd=build_dir)
    shutil.copy2(path.join(build_dir, 'mcpelauncher-client', 'mcpelauncher-client'), path.join(CMAKE_INSTALL_PREFIX, 'bin', 'mcpelauncher-client32'))

VERSION_OPTS = []
if args.update_url and args.build_id:
    VERSION_OPTS = ["-DENABLE_UPDATE_CHECK=ON", "-DUPDATE_CHECK_URL=" + args.update_url, "-DUPDATE_CHECK_BUILD_ID=" + args.build_id]

SPARKLE_OPTS = []
if args.update_sparkle_appcast:
    SPARKLE_OPTS = [ "-DENABLE_SPARKLE_UPDATE_CHECK=1", "-DSPARKLE_UPDATE_CHECK_URL=" + args.update_sparkle_appcast]

display_stage("Building")
build_component("msa", ['-DCMAKE_BUILD_TYPE=Release', '-DENABLE_MSA_QT_UI=ON', '-DMSA_UI_PATH_DEV=OFF', '-DCMAKE_CXX_FLAGS=-DNDEBUG  -Wl,-L' + path.abspath('libcxx-build') + ',-rpath,@loader_path/../Frameworks' +' -D_LIBCPP_DISABLE_AVAILABILITY=1 -I' + path.abspath('libcxx64-build/include/cxx/v1')] + CMAKE_QT_EXTRA_OPTIONS)
build_component("mcpelauncher", ['-DCMAKE_BUILD_TYPE=Release', '-DMSA_DAEMON_PATH=.', '-DENABLE_DEV_PATHS=OFF', '-DBUILD_FAKE_JNI_TESTS=OFF', '-DXAL_WEBVIEW_QT_PATH=.', '-DJNI_USE_JNIVM=ON', '-DOPENSSL_ROOT_DIR=' + path.abspath('ssl64'), '-DOPENSSL_CRYPTO_LIBRARY=' + path.abspath('ssl64/lib/libcrypto.dylib'), '-DBUILD_FAKE_JNI_EXAMPLES=OFF', '-DCMAKE_CXX_FLAGS=-DNDEBUG -Wl,-L' + path.abspath('libcxx-build') +',-rpath,@loader_path/../Frameworks -D_LIBCPP_DISABLE_AVAILABILITY=1 -I' + path.abspath('libcxx64-build/include/cxx/v1') + ' -I' + path.abspath('ssl64/include') + ' -L' + path.abspath('ssl64/lib')] + CMAKE_QT_EXTRA_OPTIONS)
build_component32("mcpelauncher", ['-DCMAKE_BUILD_TYPE=Release', '-DMSA_DAEMON_PATH=.', '-DENABLE_DEV_PATHS=OFF', '-DENABLE_QT_ERROR_UI=OFF', '-DBUILD_FAKE_JNI_TESTS=OFF', '-DOPENSSL_ROOT_DIR=' + path.abspath('ssl32'), '-DOPENSSL_CRYPTO_LIBRARY=' + path.abspath('ssl32/lib/libcrypto.dylib'), '-DBUILD_FAKE_JNI_EXAMPLES=OFF', '-DCMAKE_ASM_FLAGS=-m32', '-DCMAKE_C_FLAGS=-m32', '-DCMAKE_CXX_FLAGS=-m32 -DNDEBUG -Wl,-L' + path.abspath('libcxx-build') +',-rpath,@loader_path/../Frameworks -D_LIBCPP_DISABLE_AVAILABILITY=1 -I' + path.abspath('libcxx32-build/include/cxx/v1') + ' -I' + path.abspath('ssl32/include') + ' -L' + path.abspath('ssl32/lib'), '-DCMAKE_CXX_COMPILER_TARGET=i386-apple-darwin', '-DCMAKE_LIBRARY_ARCHITECTURE=i386-apple-darwin', '-DBUILD_WEBVIEW=OFF', '-DXAL_WEBVIEW_QT_PATH=.', '-DJNI_USE_JNIVM=ON'])
build_component("mcpelauncher-ui", ['-DCMAKE_BUILD_TYPE=Release', '-DGAME_LAUNCHER_PATH=.', '-DCMAKE_CXX_FLAGS=-DNDEBUG -Wl,-F'+ QT_INSTALL_PATH + '/lib/,-L' + path.abspath('libcxx-build') +',-rpath,@loader_path/../Frameworks -D_LIBCPP_DISABLE_AVAILABILITY=1 -I' + path.abspath('libcxx64-build/include/cxx/v1') + ((" -DLAUNCHER_VERSION_NAME=\"\\\"" + args.prettyversion + "\\\"\" ") if args.prettyversion else ' ') + (("-DLAUNCHER_VERSION_CODE=" + args.build_id + " ") if args.build_id else ' ') + "-DLAUNCHER_CHANGE_LOG=\"\\\"0.1b3 hotfix<br/>Launcher 0.1b2<br/>Added more verbose GUI errormessages<br/>For file-picking<br/>For pulseaudio<br/>For Gamepads<br/>For failing xal login window<br/><br/>Launcher 0.1-b1<br/>Launcher 0.1-b1<br/>1.16.200 now working<br/>ng ported to arm and arm64<br/>A lot of UI and launcher changes<br/>Fixed internal storage<br/>Modding support disabled again in this beta release<br/><br/>Technical changes to google play latest<br/>Fallback to launcher latest (beta) and hide latest,<br/>instead of disabling download and play<br/>if not found in the versionsdb<br/>allow incompatible => allowBeta, unsupported google play latest<br/>allowBeta only active if in beta program<br/><br/>Changes from 0.1.p2<br/>Remove gamepad input undefined behaviour, allways crashed if gamepad is connected<br/>Fix building for x86 32bit<br/>Fix changelog always shown (changed invalid type bool to int)<br/>Enhancement show arch in versionlist (Settings)<br/>Fix QSettings undefined behavior<br/>Enhancement keyboard navigation in versionslist (Settings)<br/>Fix cannot select google play latest anymore<br/>Changes from last preview<br/>Reenable hooking / modding support x86, x86_64 (new)<br/>Fix macOS 10.10 compatibility<br/>Fixed some crashs<br/>Fix gamepads<br/>Use same x11 window class for filepicker and gamewindow<br/>made x11 window class changeabi via cli<br/>Fix dlerror<br/>less linker logging<br/>Known issues:<br/><ul><li>msa-ui-qt doesn't get the correct window class yet, started by msa-daemon without `-name mcpelauncher` (Linux)</li><li>more crashs if gamepad is connected</li><li>resizeing the window lags</li><li>no visual errorreporting</li><li>crash if zenity isn't installed (Linux)</li><li>crash with random mutex lock fails (memory corruption)</li><li>apply glcorepatch on compatible versions with pattern / symbol, fallback to current behavior (primary macOS)</li><li>no armhf compat</li><li>No sound for aarch64, if you get that running</li><li>No sound for beta 1.16.0.67+, release 1.16.20+ (x86 / 32bit macOS)</li><li>a lot more..</li></ul><br/>Changes from flatpak-0.0.4><ul>    <li>Added Changelog</li>    <li>Fixed saving gamedata in Internal Storage. Please revert the previous workaround with 'flatpak --user --reset io.mrarm.mcpelauncher' or 'sudo flatpak --reset io.mrarm.mcpelauncher', then move the created '~/data/data/' folder to '~/.var/app/io.mrarm.mcpelauncher/data/mcpelauncher'</li>    <li>Minecraft 1.16.100.54 now working</li>    <li>Added Reset the Launcher via Settings</li>    <li>Added About Page with Version information</li>    <li>Added Compatibility report with more detailed Unsupported message</li>    <li>Extended the Troubleshooter to include more Items like the Compatibility Report</li>    <li>Moved again from fake-jni to libjnivm as fake java native interface</li>    <li>Also run 1.16.20 - 1.16.100 x86 variants</li>    <li>Block Google Play latest if it would be incompatible incl. Troubleshooter entry</li>    <li>Fix Google Play latest still hidden after login to the launcher</li>    <li>Improve integrated UpdateChecker to respond if you click on Check for Updates</li>    <li>Show error if update failed, instead of failing silently</li></ul>\\\"\"", "-DQt5QuickCompiler_FOUND=OFF"] + VERSION_OPTS + SPARKLE_OPTS + CMAKE_QT_EXTRA_OPTIONS)
#if args.buildangle:
#    call(['bash', '-c', './build.sh'], cwd=path.abspath(path.join(SOURCE_DIR, "osx-angle-ci")))

display_stage("Copying files")
def copy_installed_files(from_path, to_path):
    for f in listdir(from_path):
        print("Copying file: " + f)
        if path.isdir(path.join(from_path, f)):
            copytree(path.join(from_path, f), path.join(to_path, f), True)
        else:
            shutil.copy2(path.join(from_path, f), path.join(to_path, f), follow_symlinks = False)

copy_installed_files(path.join(CMAKE_INSTALL_PREFIX, 'bin'), path.join(APP_OUTPUT_DIR, 'Contents', 'MacOS'))
copy_installed_files(path.join(CMAKE_INSTALL_PREFIX, 'share'), path.join(APP_OUTPUT_DIR, 'Contents', 'Resources'))
copy_installed_files('libcxx-build', path.join(APP_OUTPUT_DIR, 'Contents', 'Frameworks'))
copy_installed_files('ssl/lib', path.join(APP_OUTPUT_DIR, 'Contents', 'Frameworks'))
# Workaround Qt 5.9.2
if args.qtworkaround:
    copy_installed_files(path.join(QT_INSTALL_PATH, 'qml', 'QtQuick'), path.join(APP_OUTPUT_DIR, 'Contents', 'Resources', 'qml', 'QtQuick'))
    copy_installed_files(path.join(QT_INSTALL_PATH, 'qml', 'QtQuick.2'), path.join(APP_OUTPUT_DIR, 'Contents', 'Resources', 'qml', 'QtQuick.2'))
if args.buildangle:
    copy_installed_files(path.abspath(path.join(SOURCE_DIR, "osx-angle-ci/artifacts")), path.join(APP_OUTPUT_DIR, 'Contents', 'Frameworks'))

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
