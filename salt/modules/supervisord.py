# -*- coding: utf-8 -*-
'''
Provide the service module for system supervisord or supervisord in a
virtualenv
'''

# Import python libs
import os

from salt.states import state_std

# Import salt libs
from salt.exceptions import CommandNotFoundError


def _get_supervisorctl_bin(bin_env):
    '''
    Return supervisorctl command to call, either from a virtualenv, an argument
    passed in, or from the global modules options
    '''
    cmd = 'supervisorctl'
    if not bin_env:
        which_result = __salt__['cmd.which_bin']([cmd])
        if which_result is None:
            raise CommandNotFoundError(
                'Could not find a `{0}` binary'.format(cmd)
            )
        return which_result

    # try to get binary from env
    if os.path.isdir(bin_env):
        cmd_bin = os.path.join(bin_env, 'bin', cmd)
        if os.path.isfile(cmd_bin):
            return cmd_bin
        raise CommandNotFoundError('Could not find a `{0}` binary'.format(cmd))

    return bin_env


def _ctl_cmd(cmd, name, conf_file, bin_env):
    ret = [_get_supervisorctl_bin(bin_env)]
    if conf_file is not None:
        ret += ['-c', conf_file]
    ret.append(cmd)
    if name:
        ret.append(name)
    return ' ' .join(ret)


def _get_return(ret):
    if ret['retcode'] == 0:
        return ret['stdout']
    else:
        return ''


def start(name='all', user=None, conf_file=None, bin_env=None, **kwargs):
    '''
    Start the named service.
    Process group names should not include a trailing asterisk.

    user
        user to run supervisorctl as
    conf_file
        path to supervisorctl config file
    bin_env
        path to supervisorctl bin or path to virtualenv with supervisor
        installed

    CLI Example:

    .. code-block:: bash

        salt '*' supervisord.start <service>
        salt '*' supervisord.start <group>:
    '''
    ret = __salt__['cmd.run_all'](
        _ctl_cmd('start', name, conf_file, bin_env), runas=user
    )
    state_std(kwargs, ret)
    return _get_return(ret)


def restart(name='all', user=None, conf_file=None, bin_env=None, **kwargs):
    '''
    Restart the named service.
    Process group names should not include a trailing asterisk.

    user
        user to run supervisorctl as
    conf_file
        path to supervisorctl config file
    bin_env
        path to supervisorctl bin or path to virtualenv with supervisor
        installed

    CLI Example:

    .. code-block:: bash

        salt '*' supervisord.restart <service>
        salt '*' supervisord.restart <group>:
    '''
    ret = __salt__['cmd.run_all'](
        _ctl_cmd('restart', name, conf_file, bin_env), runas=user
    )
    state_std(kwargs, ret)
    return _get_return(ret)


def stop(name='all', user=None, conf_file=None, bin_env=None, **kwargs):
    '''
    Stop the named service.
    Process group names should not include a trailing asterisk.

    user
        user to run supervisorctl as
    conf_file
        path to supervisorctl config file
    bin_env
        path to supervisorctl bin or path to virtualenv with supervisor
        installed

    CLI Example:

    .. code-block:: bash

        salt '*' supervisord.stop <service>
        salt '*' supervisord.stop <group>:
    '''
    ret = __salt__['cmd.run_all'](
        _ctl_cmd('stop', name, conf_file, bin_env), runas=user
    )
    state_std(kwargs, ret)
    return _get_return(ret)


def add(name, user=None, conf_file=None, bin_env=None, **kwargs):
    '''
    Activates any updates in config for process/group.

    user
        user to run supervisorctl as
    conf_file
        path to supervisorctl config file
    bin_env
        path to supervisorctl bin or path to virtualenv with supervisor
        installed

    CLI Example:

    .. code-block:: bash

        salt '*' supervisord.add <name>
    '''
    if name.endswith(':'):
        name = name[:-1]
    ret = __salt__['cmd.run_all'](
        _ctl_cmd('add', name, conf_file, bin_env), runas=user
    )
    state_std(kwargs, ret)
    return _get_return(ret)


def remove(name, user=None, conf_file=None, bin_env=None, **kwargs):
    '''
    Removes process/group from active config

    user
        user to run supervisorctl as
    conf_file
        path to supervisorctl config file
    bin_env
        path to supervisorctl bin or path to virtualenv with supervisor
        installed

    CLI Example:

    .. code-block:: bash

        salt '*' supervisord.remove <name>
    '''
    if name.endswith(':'):
        name = name[:-1]
    ret = __salt__['cmd.run_all'](
        _ctl_cmd('remove', name, conf_file, bin_env), runas=user
    )
    state_std(kwargs, ret)
    return _get_return(ret)


def reread(user=None, conf_file=None, bin_env=None, **kwargs):
    '''
    Reload the daemon's configuration files

    user
        user to run supervisorctl as
    conf_file
        path to supervisorctl config file
    bin_env
        path to supervisorctl bin or path to virtualenv with supervisor
        installed

    CLI Example:

    .. code-block:: bash

        salt '*' supervisord.reread
    '''
    ret = __salt__['cmd.run_all'](
        _ctl_cmd('reread', None, conf_file, bin_env), runas=user
    )
    state_std(kwargs, ret)
    return _get_return(ret)


def update(user=None, conf_file=None, bin_env=None, **kwargs):
    '''
    Reload config and add/remove as necessary

    user
        user to run supervisorctl as
    conf_file
        path to supervisorctl config file
    bin_env
        path to supervisorctl bin or path to virtualenv with supervisor
        installed

    CLI Example:

    .. code-block:: bash

        salt '*' supervisord.update
    '''
    ret = __salt__['cmd.run_all'](
        _ctl_cmd('update', None, conf_file, bin_env), runas=user
    )
    state_std(kwargs, ret)
    return _get_return(ret)


def status(name=None, user=None, conf_file=None, bin_env=None):
    '''
    List programs and its state

    user
        user to run supervisorctl as
    conf_file
        path to supervisorctl config file
    bin_env
        path to supervisorctl bin or path to virtualenv with supervisor
        installed

    CLI Example:

    .. code-block:: bash

        salt '*' supervisord.status
    '''
    all_process = {}
    for line in status_raw(name, user, conf_file, bin_env).splitlines():
        if len(line.split()) > 2:
            process, state, reason = line.split(None, 2)
        else:
            process, state, reason = line.split() + ['']
        all_process[process] = {'state': state, 'reason': reason}
    return all_process


def status_raw(name=None, user=None, conf_file=None, bin_env=None):
    '''
    Display the raw output of status

    user
        user to run supervisorctl as
    conf_file
        path to supervisorctl config file
    bin_env
        path to supervisorctl bin or path to virtualenv with supervisor
        installed

    CLI Example:

    .. code-block:: bash

        salt '*' supervisord.status_raw
    '''
    ret = __salt__['cmd.run_all'](
        _ctl_cmd('status', name, conf_file, bin_env), runas=user
    )
    return _get_return(ret)


def custom(command, user=None, conf_file=None, bin_env=None, **kwargs):
    '''
    Run any custom supervisord command

    user
        user to run supervisorctl as
    conf_file
        path to supervisorctl config file
    bin_env
        path to supervisorctl bin or path to virtualenv with supervisor
        installed

    CLI Example:

    .. code-block:: bash

        salt '*' supervisord.custom "mstop '*gunicorn*'"
    '''
    ret = __salt__['cmd.run_all'](
        _ctl_cmd(command, None, conf_file, bin_env), runas=user
    )
    state_std(kwargs, ret)
    return _get_return(ret)