import subprocess
import os
from os import path
import shutil


def get_dependencies(bin_path):
    proc = subprocess.Popen(['otool', '-L', bin_path], stdout=subprocess.PIPE)
    proc.stdout.readline() # ignore the first line
    ret = []
    for line in proc.stdout:
        dep_path, _, _ = line.decode('utf-8').strip().partition(' ')
        if dep_path.startswith("/usr/local/opt/"):
            ret.append(dep_path)
    return ret


def copy_file_and_dependencies(file, path_prefix, dest_dir):
    is_framework = False
    src_file = file
    dest_file = path.join(dest_dir, path.basename(file))
    if ".framework/" in file:
        base_path, base_path2, _ = file.rpartition(".framework/")
        is_framework = True
        src_file = os.path.normpath(base_path + base_path2)
        dest_file = path.join(dest_dir, path.basename(src_file))
    print("Copying " + src_file + " to " + dest_file)
    if path.exists(dest_file):
        return

    if is_framework:
        shutil.copytree(src_file, dest_file)
    else:
        shutil.copyfile(src_file, dest_file)

    for dep in get_dependencies(file):
        copy_file_and_dependencies(dep, path_prefix, dest_dir)


def copy_dependencies(exec_file, dest_dir):
    path_prefix = path.join("@executable_path", path.relpath(dest_dir, path.dirname(exec_file)))
    for dep in get_dependencies(exec_file):
        copy_file_and_dependencies(dep, path_prefix, dest_dir)

