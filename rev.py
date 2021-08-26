#!/usr/bin/python3

import argparse
import logging
import os
import shutil
import subprocess
import sys
import time
from distutils.dir_util import copy_tree

import psutil

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

h = logging.StreamHandler(sys.stderr)
h.setLevel(logging.DEBUG)
log.addHandler(h)

SCRIPT_DIR = os.path.dirname(__file__)


def tool(cmd):
    script_path = '%s/%s' % (SCRIPT_DIR, cmd.lstrip('./'))
    if cmd[0] not in './':
        script_path += '/run'
    return script_path


def run_cmd(*args, **kwargs):
    log.debug('running %s %s' % (args, kwargs))
    return subprocess.check_output(*args, **kwargs)


def user_answer(desc, allowed):
    try:
        while True:
            ans = input(desc)
            if ans in allowed:
                return ans
    except KeyboardInterrupt:
        log.info('cancelled.')
        exit(0)


def unzip(file, out_dir):
    log.debug('unzipping %s > %s' % (file, out_dir))
    return run_cmd(['unzip', '-n', file, '-d', out_dir])


def get_java_env(mem_pct):
    mem = psutil.virtual_memory()
    free_mem = mem.available
    max_java_mem_mb = mem_pct * (free_mem >> 20)
    return {
        '_JAVA_OPTIONS': '-Xmx%dM' % max_java_mem_mb
    }


def apk2smali(file, out_dir):
    log.debug('apk2smali %s > %s' % (file, out_dir))
    return run_cmd([tool('Apktool'), 'd', file, '-o', out_dir])


def apk2res(file, out_dir):
    return run_cmd([tool('Apktool'), 'd', '-s', file, '-o', out_dir])


def dex2smali(file, out_dir):
    return run_cmd([tool('./dex2jar/dex-tools/build/install/dex-tools/d2j-dex2smali.sh'), '-o', out_dir, file])


def dex2jar(file, out_file):
    log.debug('dex2jar %s > %s' % (file, out_file))
    return run_cmd([tool('dex2jar'), file, '-o', out_file])


def d_cfr(jar, out_dir, libraries=None, **kwargs):
    run = [tool('cfr')]

    if libraries:
        pathSeparatorChar = os.path.pathsep
        run += ['--extraclasspath', pathSeparatorChar.join(libraries)]
    run += ['--outputdir', out_dir, jar]
    return run_cmd(run)


def d_fernflower(jar, out_dir, libraries=None, **kwargs):
    tmp_dir = '%s/tmp-fernflower-%d' % (out_dir, time.time())
    os.makedirs(tmp_dir)

    run = [tool('fernflower'), '-ren=1', '-mpm=3']
    # effect from libs -- visible
    if libraries:
        for lib_file in libraries:
            run += ['-e=%s' % lib_file]
    run += [jar, tmp_dir]

    r1 = run_cmd(run)

    jar_filename = os.path.basename(jar)
    src_jar_file_path = '%s/%s' % (tmp_dir, jar_filename)
    r2 = unzip(src_jar_file_path, out_dir)
    shutil.rmtree(tmp_dir)
    return r1


def d_jadx(jar, out_dir, **kwargs):
    return run_cmd([tool('jadx'), '-r', '--show-bad-code', '--deobf', '-ds', out_dir, jar])


def d_jd(jar, out_dir, **kwargs):
    return run_cmd([tool('jd-cli'), '-sr', '-od', out_dir, jar])


def d_procyon(jar, out_dir, **kwargs):
    return run_cmd([tool('procyon2'), jar, '-ei', '--unicode', '-ss', '-o', out_dir])


def d_krakatau(jar, out_dir, libraries=None, **kwargs):
    run = [tool('Krakatau')]

    # effect from libs -- not visible
    if libraries:
        run += ['-nauto']
        for lib_file in libraries:
            run += ['-path', lib_file]
    run += ['-out', out_dir, jar]

    return run_cmd(run)


decompilers = {
    'cfr': d_cfr,
    'fernflower': d_fernflower,
    'jadx': d_jadx,
    'jd': d_jd,
    'procyon': d_procyon,
    'krakatau': d_krakatau,
}
decompilers_str = ', '.join(decompilers.keys())


def decompile(decompiler_name, jar, out_dir, **kwargs):
    decompile_fn = decompilers[decompiler_name]
    log.info('decompiling: %s: %s > %s..' % (decompiler_name, jar, out_dir))
    return decompile_fn(jar, out_dir, **kwargs)


def realpath(p):
    return os.path.realpath(os.path.expanduser(p))


supported_extensions = 'apk dex jar'.split()
supported_extensions_str = ', '.join(supported_extensions)


class CustomHelpFormatter(argparse.ArgumentDefaultsHelpFormatter, argparse.RawTextHelpFormatter):
    def _get_help_string(self, action):
        if action.default:
            return super()._get_help_string(action)
        return action.help


if __name__ == '__main__':
    p = argparse.ArgumentParser(formatter_class=CustomHelpFormatter)
    p.add_argument('file',
                   help='file to decompile. Supported extensions: %s' % supported_extensions_str)
    p.add_argument('-d', dest='decompiler', required=False,
                   help='decompiler name to use\n'
                        'one of: %s' % decompilers_str)
    # todo
    # p.add_argument('-r', dest='decompiler_only', default=False, required=False,
    #                help='reuse all except decompiler output')
    p.add_argument('-o', dest='output_dir', required=False,
                   help='dir to store results in, default=${file}.rev')
    p.add_argument('-e', dest='ext', required=False,
                   help='treat target file as specified extension\n'
                        'one of: %s' % supported_extensions_str)
    p.add_argument('-m', dest='max_mem_pct', required=False, type=float, default=0.75,
                   help='upper RAM limit for java programs, in percent of current free RAM')
    p.add_argument('-l', dest='library_files', required=False, action='append', default=[],
                   help='library file(s) (may be useful for decompiler); '
                        'example:\n'
                        '-l ~/Android/Sdk/platforms/android-28/android.jar\n'
                        '-l ~/Android/Sdk/platforms/android-28/optional/org.apache.http.legacy.jar')
    # todo pass rest args to decompiler

    options = p.parse_args()
    log.info('running with options: %s' % options)

    decompiler = options.decompiler
    if decompiler and decompiler not in decompilers:
        p.error('available decompilers: %s' % decompilers_str)

    file_path = options.file

    if options.ext:
        ext = options.ext
    else:
        _, ext = os.path.splitext(file_path)
        ext = ext.lstrip('.')

    if ext not in supported_extensions:
        ext_err = 'Unsupported input file extension, should be one of: %s.' % ', '.join(supported_extensions)
        if not options.ext:
            ext_err += ' Override with -e <ext> if needed'
        p.error(ext_err)

    file_path = realpath(file_path)
    if not (os.path.exists(file_path) and os.path.isfile(file_path)):
        p.error('file %s does not exist' % file_path)
    filename = os.path.basename(file_path)
    log.debug('will process file %s' % file_path)

    output_dir = options.output_dir
    if not output_dir:
        output_dir = file_path + '.rev'
    output_dir = realpath(output_dir)

    if os.path.exists(output_dir):
        if os.path.isdir(output_dir):
            log.info('target output dir (%s) exists.' % output_dir)
            act = user_answer('specify action: re[u]se/[r]emove and recreate? ', 'ur')
            if act == 'u':
                log.info('reusing output directory %s..' % output_dir)
            elif act == 'r':
                log.info('recreating output directory %s..' % output_dir)
                shutil.rmtree(output_dir)
        else:
            p.error('specified output directory is a file: %s' % output_dir)
    os.makedirs(output_dir, exist_ok=True)
    log.debug('will output to %s' % output_dir)

    java_opts = get_java_env(options.max_mem_pct)
    log.debug('setting java env to %s' % java_opts)
    os.environ.update(java_opts)

    apk_unpacked_dir = '%s/apk_unpacked' % output_dir
    res_dir = '%s/apk_resources' % output_dir
    smali_dir = '%s/smali' % output_dir

    jar_file = '%s/%s.classes.jar' % (output_dir, filename)
    jar_unpacked_dir = '%s/jar_unpacked' % output_dir
    src_dir = '%s/src_%s' % (output_dir, decompiler)

    library_files = list(map(realpath, options.library_files))

    def process_jar(jar):
        unzip(jar, jar_unpacked_dir)
        if decompiler:
            decompile(decompiler, jar, src_dir, libraries=library_files)
            if ext == 'apk':
                log.info('copying resources..')
                copy_tree(res_dir, src_dir)
        else:
            log.info('decompilation not requested.')

    if ext == 'apk':
        unzip(file_path, apk_unpacked_dir)
        apk2res(file_path, res_dir)
        apk2smali(file_path, smali_dir)
        dex2jar(file_path, jar_file)
        process_jar(jar_file)

    if ext == 'dex':
        dex2smali(file_path, smali_dir)
        dex2jar(file_path, jar_file)
        process_jar(jar_file)

    if ext == 'jar':
        process_jar(file_path)

    log.info('fin.')
