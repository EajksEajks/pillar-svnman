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


@manager_svnman.command
def create(repo_id, project_url, creator):
    """Creates a new Subversion repository."""

    from pillar.api.projects.utils import project_id
    from . import current_svnman
    from .remote import CreateRepo

    pid = project_id(project_url)
    creation_info = CreateRepo(
        repo_id=repo_id,
        project_id=str(pid),
        creator=creator,
    )

    log.info('Creating repository %r', repo_id)
    current_svnman.remote.create_repo(creation_info)


@manager_svnman.command
def grant(repo_id, username, password):
    """Allows the user access to the repository."""

    import bcrypt
    from . import current_svnman

    hashed = bcrypt.hashpw(password.encode('utf8'), bcrypt.gensalt()).decode('ascii')

    log.info('Granting access to repo %r', repo_id)
    log.info('Hashed password: %r', hashed)
    current_svnman.remote.modify_access(repo_id, grant=[(username, hashed)], revoke=[])
    log.info('Done')


@manager_svnman.command
def revoke(repo_id, username):
    """Revokes the user access from the repository."""

    from . import current_svnman

    log.info('Revoking access from repo %r', repo_id)
    current_svnman.remote.modify_access(repo_id, grant=[], revoke=[username])
    log.info('Done')


@manager_svnman.command
def delete(repo_id):
    """Deletes a repository. This cannot be undone via the API."""

    from . import current_svnman

    log.info('Deleting repository %r', repo_id)
    input('Press ENTER to continue irrevocable repository deletion')

    current_svnman.remote.delete_repo(repo_id)
    log.info('Done')


manager.add_command('svn', manager_svnman)
