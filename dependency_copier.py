import subprocess
import os
from os import path
import shutil


def is_macho(bin_path):
    with open(bin_path, 'rb') as f:
        magic = f.read(4)
        return magic == b"\xcf\xfa\xed\xfe"


def get_dependencies(bin_path):
    proc = subprocess.Popen(['otool', '-L', bin_path], stdout=subprocess.PIPE)
    proc.stdout.readline() # ignore the first line
    ret = []
    for line in proc.stdout:
        dep_path, _, _ = line.decode('utf-8').strip().partition(' ')
        if dep_path.startswith("/usr/local/"):
            ret.append(dep_path)
    return ret


def extract_path_info(file, dst_dir):
    is_framework = False
    src_file = file
    dst_file = path.join(dst_dir, path.basename(file))
    if ".framework/" in file:
        base_path, base_path2, _ = file.rpartition(".framework/")
        is_framework = True
        src_file = os.path.normpath(base_path + base_path2)
        dst_file = path.join(dst_dir, path.basename(src_file))
    return is_framework, src_file, dst_file


def copy_framework(src_dir, dst_dir, local_path, path_prefix):
    os.mkdir(path.join(dst_dir, local_path))
    for file in os.listdir(path.join(src_dir, local_path)):
        src_file = path.join(src_dir, local_path, file)
        dst_file = path.join(dst_dir, local_path, file)
        if file == 'Headers' or (local_path.startswith("Qt") and path.basename(local_path) == 'Versions' and
                                 (file != '5' and file != 'Current')):
            continue
        if path.islink(src_file):
            dst_link = os.readlink(src_file)
            os.symlink(dst_link, dst_file)
            continue
        if path.isdir(src_file):
            copy_framework(src_dir, dst_dir, path.join(local_path, file), path_prefix)
            continue

        shutil.copyfile(src_file, dst_file)
        print("Copied " + src_file + " to " + dst_file)
        if is_macho(dst_file):
            _copy_dependencies(dst_file, path_prefix, dst_dir, path.join(path_prefix, local_path, file))


def copy_file_and_dependencies(file, path_prefix, dst_dir):
    is_framework, src_file, dst_file = extract_path_info(file, dst_dir)
    if path.exists(dst_file):
        return
    print("Copying " + src_file + " to " + dst_file + (" (framework)" if is_framework else ""))

    if is_framework:
        copy_framework(path.dirname(src_file), dst_dir, path.basename(dst_file), path_prefix)
    else:
        shutil.copyfile(src_file, dst_file)
        _copy_dependencies(dst_file, path_prefix, dst_dir, path.join(path_prefix, path.basename(dst_file)))


def _copy_dependencies(dst_file, path_prefix, dst_dir, set_id=None):
    print('Copying deps: ' + dst_file)
    name_tool_opt = ['install_name_tool']
    if set_id is not None:
        name_tool_opt.extend(['-id', set_id])
    for dep in get_dependencies(dst_file):
        copy_file_and_dependencies(dep, path_prefix, dst_dir)
        _, dep_src_file, _ = extract_path_info(dep, dst_dir)
        dep_rel_file = path.relpath(dep, path.dirname(dep_src_file))
        name_tool_opt.extend(['-change', dep, path.join(path_prefix, dep_rel_file)])
    name_tool_opt.append(dst_file)
    if len(name_tool_opt) > 2:
        print('Running: ' + ' '.join(name_tool_opt))
        os.chmod(dst_file, 0o664)
        subprocess.check_call(name_tool_opt)
        os.chmod(dst_file, 0o444)


def copy_dependencies(exec_file, dst_dir):
    path_prefix = path.join("@executable_path", path.relpath(dst_dir, path.dirname(exec_file)))
    _copy_dependencies(exec_file, path_prefix, dst_dir)
    os.chmod(exec_file, 0o555)

