from invoke import task
from invoke import Collection

import json
import locale
import os
import os.path
import re
import shlex
import subprocess


@task
def _virtualenv(ctx, virtualenv_path=None):
    virtualenv_path = virtualenv_path or ctx.virtualenv_path
    selinux = ctx.get('selinux', False)
    python = ctx.get('python', '/usr/bin/python')
    if not check_virtualenv(ctx, virtualenv_path):
        if not os.path.exists(os.path.dirname(virtualenv_path)):
            os.makedirs(os.path.dirname(virtualenv_path))
        ctx.run(' '.join(['virtualenv', virtualenv_path]))
        if not check_virtualenv(ctx, virtualenv_path):
            raise Exception('python install fails')
    # symlink selinux system-packages in virtualenv if needed and selinux found
    if selinux:
        # check if selinux is available
        command = [python, '-c', 'import json; import selinux; print json.dumps(selinux.__file__)']
        try:
            output = subprocess.check_output(command).encode(locale.getdefaultlocale()[1])
            if not output:
                print('selinux detected but not found')
            else:
                location = json.loads(output)
                module_location = os.path.dirname(location)
                so_location = os.path.join(os.path.dirname(module_location), '_selinux.so')
                #print ('selinux detected here: {}'.format(location))
                # TODO: check python version
                target_module_location = os.path.join(virtualenv_path, 'lib', 'python2.7', 'site-packages', 'selinux')
                target_so_location = os.path.join(virtualenv_path, 'lib', 'python2.7', 'site-packages', '_selinux.so')
                if not os.path.exists(target_module_location):
                    os.symlink(module_location, target_module_location)
                if not os.path.exists(target_so_location):
                    os.symlink(so_location, target_so_location)
        except subprocess.CalledProcessError as e:
            # selinux not available, ignore it
            print('selinux not available, ignore it')


@task
def _ansible(ctx, virtualenv_path=None,
             skip=None, version=None):
    skip = skip if (skip is not None) \
        else ctx.ansible.skip
    dependencies = ctx.dependencies
    if not skip:
        virtualenv_path = virtualenv_path or ctx.virtualenv_path
        package = ctx.ansible.package_name
        version = version or ctx.ansible.version
        _pip_package(ctx, package, version)
        for dependency in dependencies:
            _pip_package(ctx, dependency['name'],
                         dependency.get('version', None))
    else:
        print('ansible not managed (ansible.skip: yes)')


def _pip_package(ctx, package, version=None, virtualenv_path=None):
    virtualenv_path = virtualenv_path or ctx.virtualenv_path
    if not check_pip(ctx, virtualenv_path, package, version):
        pip_install(ctx, virtualenv_path, package, version)
        if not check_pip(ctx, virtualenv_path, package, version):
            raise Exception('{} install fails'.format(package))


@task
def galaxy(ctx):
    virtualenv_path = ctx.virtualenv_path
    ctx.run(_vcommand(virtualenv_path, 'ansible-galaxy',
                      'install',
                      '-r', 'requirements.yml',
                      '--roles-path', 'dependencies/'))


@task(pre=[_virtualenv, _ansible, galaxy])
def configure(ctx):
    pass


def run_playbook(ctx, playbook=None,
                 ask_become_pass=False, ask_vault_pass=False,
                 check=False, diff=False,
                 verbose=False, debug=False, tags=None, ansible_args=''):
    virtualenv_path = ctx.virtualenv_path
    os.environ['PATH'] = \
        os.path.join(virtualenv_path, 'bin') + ':' + os.environ['PATH']
    os.environ['ANSIBLE_CONFIG'] = 'etc/ansible.cfg'
    if os.path.exists('.vault_pass.txt'):
        os.environ['ANSIBLE_VAULT_PASSWORD_FILE'] = '.vault_pass.txt'
        ask_vault_pass = False
    args = [playbook]
    if ask_become_pass:
        args.append('--ask-become-pass')
    if ask_vault_pass:
        args.append('--ask-vault-pass')
    if diff:
        args.append('--diff')
    if check:
        args.append('--check')
    if verbose:
        args.append('-v')
    if debug:
        args.append('-vvv')
    if tags:
        args.extend(['--tags', tags])
    args.extend(shlex.split(ansible_args))
    ctx.run(_vcommand(virtualenv_path, 'ansible-playbook', *args), pty=True)


@task(pre=[configure])
def run(ctx, playbook=None,
        ask_become_pass=False, ask_vault_pass=False,
        check=False, diff=False,
        verbose=False, debug=False, tags=None, ansible_args=''):
    run_playbook(ctx, playbook, ask_become_pass=ask_become_pass,
                 ask_vault_pass=ask_vault_pass,
                 check=check, diff=diff, verbose=verbose, debug=debug,
                 tags=tags, ansible_args=ansible_args)


# invoke target generator
def run_playbook_task(name, playbook, ansible_args=''):
    @task(pre=[configure], name=name)
    def inside_run(ctx,
                   ask_become_pass=False, ask_vault_pass=False,
                   check=False, diff=False, verbose=False, debug=False,
                   tags=None, ansible_args=ansible_args):
        run_playbook(ctx, playbook, ask_become_pass=ask_become_pass,
                     ask_vault_pass=ask_vault_pass, check=check,
                     diff=diff, verbose=verbose, debug=debug, tags=tags,
                     ansible_args=ansible_args)
    return inside_run


chocolatey = run_playbook_task('chocolatey', 'playbooks/chocolatey.yml')

def check_virtualenv(ctx, virtualenv_path):
    r = ctx.run(' '.join([
        os.path.join(virtualenv_path, 'bin/python'),
        '--version'
    ]), warn=True, hide='both')
    return r.ok


def check_pip(ctx, virtualenv_path, package, version):
    r = ctx.run(' '.join([
        os.path.join(virtualenv_path, 'bin/pip'),
        'show',
        package
    ]), hide='both', warn=True)
    if not r.ok:
        # pip show package error - package is not here
        return False
    if version is None:
        # no version check needed
        return True
    # package here, check version
    m = re.search(r'^Version: (.*)$', r.stdout, re.MULTILINE)
    result = m is not None and m.group(1).strip() == version
    return result


def pip_install(ctx, virtualenv_path, package, version):
    pkgspec = None
    if version is None:
        pkgspec = package
    else:
        pkgspec = '{}=={}'.format(package, version)
    ctx.run(' '.join([
        os.path.join(virtualenv_path, 'bin/pip'),
        'install',
        pkgspec
    ]))


def _vcommand(virtualenv_path, command, *args):
    cl = []
    cl.append(os.path.join(virtualenv_path, 'bin', command))
    cl.extend(args)
    return ' '.join(cl)


def _command(command, *args):
    cl = []
    cl.append(os.path.join(command))
    cl.extend(args)
    return ' '.join(cl)


ns = Collection(chocolatey)
ns.configure({
    'ansible': {
        'package_name': 'ansible'
    },
    'dependencies': []
})
