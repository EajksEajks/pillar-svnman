"""Commandline interface for SVNMan."""

import logging

from flask import current_app
from flask_script import Manager

from pillar.cli import manager

log = logging.getLogger(__name__)

manager_svnman = Manager(current_app, usage="Perform SVNMan operations")


@manager_svnman.command
def info(repo_id):
    """Fetches repository information from the SVNMan API."""

    from . import current_svnman

    log.info('Fetching repository %r', repo_id)
    repoinfo = current_svnman.remote.fetch_repo(repo_id)

    log.info('Repo ID: %s', repoinfo.repo_id)
    log.info('Access : %s', sorted(repoinfo.access))


manager.add_command('svn', manager_svnman)
