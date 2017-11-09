import logging
import os.path
import string
from urllib.parse import urljoin

import flask
from werkzeug.local import LocalProxy
import werkzeug.exceptions as wz_exceptions

import pillarsdk
from pillar.extension import PillarExtension
from pillar.auth import current_user
from pillar.api.projects import utils as proj_utils
from pillar.api.utils import str2id
from pillar.api.utils.authorization import require_login
from pillar import current_app

EXTENSION_NAME = 'svnman'


# SVNman stores the following keys in the project extension properties:
# repo_id: the Subversion repository ID
# users: list of ObjectIDs of users having access to the project

class SVNManExtension(PillarExtension):
    user_caps = {
        'subscriber-pro': frozenset({'svn-use'}),
        'demo': frozenset({'svn-use'}),
    }

    def __init__(self):
        from . import remote

        self._log = logging.getLogger('%s.SVNManExtension' % __name__)
        self.remote: remote.API = None

    @property
    def name(self):
        return EXTENSION_NAME

    def flask_config(self):
        """Returns extension-specific defaults for the Flask configuration.

        Use this to set sensible default values for configuration settings
        introduced by the extension.

        :rtype: dict
        """

        # Just so that it registers the management commands.
        from . import cli

        return {
            'SVNMAN_REPO_URL': 'http://SVNMAN_REPO_URL/repo/',
            'SVNMAN_API_URL': 'http://SVNMAN_API_URL/api/',
            'SVNMAN_API_USERNAME': 'SVNMAN_API_USERNAME',
            'SVNMAN_API_PASSWORD': 'SVNMAN_API_PASSWORD',
        }

    def eve_settings(self):
        """Returns extensions to the Eve settings.

        Currently only the DOMAIN key is used to insert new resources into
        Eve's configuration.

        :rtype: dict
        """
        return {'DOMAIN': {}}

    def blueprints(self):
        """Returns the list of top-level blueprints for the extension.

        These blueprints will be mounted at the url prefix given to
        app.load_extension().

        :rtype: list of flask.Blueprint objects.
        """

        from . import routes

        return [
            routes.blueprint,
        ]

    def setup_app(self, app):
        from . import remote

        self.remote = remote.API(
            remote_url=app.config['SVNMAN_API_URL'],
            username=app.config['SVNMAN_API_USERNAME'],
            password=app.config['SVNMAN_API_PASSWORD'],
        )

    @property
    def template_path(self):
        return os.path.join(os.path.dirname(__file__), 'templates')

    @property
    def static_path(self):
        return os.path.join(os.path.dirname(__file__), 'static')

    def sidebar_links(self, project):
        if not current_user.has_cap('svn-use'):
            return ''
        if not self.is_svnman_project(project):
            return ''
        return flask.render_template('svnman/sidebar.html', project=project)

    @property
    def has_project_settings(self) -> bool:
        return current_user.has_cap('svn-use')

    @require_login(require_cap='svn-use', redirect_to_login=True)
    def project_settings(self, project: pillarsdk.Project, **template_args: dict) -> flask.Response:
        """Renders the project settings page for this extension.

        Set YourExtension.has_project_settings = True and Pillar will call this function.

        :param project: the project for which to render the settings.
        :param template_args: additional template arguments.
        :returns: a Flask HTTP response
        """

        from .routes import project_settings

        remote_url = current_app.config['SVNMAN_REPO_URL']

        if self.is_svnman_project(project):
            repo_id = project.extension_props[EXTENSION_NAME].repo_id
            svn_url = urljoin(remote_url, repo_id)
        else:
            svn_url = ''
            repo_id = ''

        return project_settings(project,
                                svn_url=svn_url,
                                repo_id=repo_id,
                                remote_url=remote_url,
                                **template_args)

    def is_svnman_project(self, project: pillarsdk.Project) -> bool:
        """Checks whether the project is correctly set up for SVNman."""

        try:
            if not project.extension_props:
                return False
        except AttributeError:
            self._log.warning("is_svnman_project: Project url=%r doesn't have"
                              " any extension properties.", project['url'])
            if self._log.isEnabledFor(logging.DEBUG):
                import pprint
                self._log.debug('Project: %s', pprint.pformat(project.to_dict()))
            return False

        try:
            pprops = project.extension_props[EXTENSION_NAME]
        except KeyError:
            return False

        if pprops is None:
            self._log.warning("is_svnman_project: Project url=%r doesn't have"
                              " %s extension properties.", EXTENSION_NAME, project['url'])
            return False

        return bool(pprops.repo_id)

    def create_repo(self, project: pillarsdk.Project, creator: str) -> str:
        """Creates a SVN repository with a random ID attached to the project.

        Saves the repository ID in the project. Is a no-op if the project
        already has a Subversion repository.
        """

        from . import remote, exceptions

        eprops, proj = self._get_prop_props(project)
        project_id = project['_id']

        repo_id = eprops.get('repo_id')
        if repo_id:
            self._log.warning('project %s already has a Subversion repository %r',
                              project_id, repo_id)
            return repo_id

        repo_info = remote.CreateRepo(
            repo_id='',
            project_id=str(project_id),
            creator=creator,
        )

        for _ in range(100):
            repo_info.repo_id = _random_id()
            self._log.info('creating new repository, trying out %s', repo_info)
            try:
                actual_repo_id = self.remote.create_repo(repo_info)
            except exceptions.RepoAlreadyExists:
                self._log.info('repo_id=%r already exists, trying random other one',
                               repo_info.repo_id)
            else:
                break
        else:
            self._log.error('unable to find unique random repository ID, giving up')
            raise ValueError('unable to find unique random repository ID, giving up')

        self._log.info('created new Subversion repository: %s', repo_info)

        # Update the project to include the repository ID.
        eprops['repo_id'] = actual_repo_id
        proj_utils.put_project(proj)

        return actual_repo_id

    def _get_prop_props(self, project: pillarsdk.Project) -> (dict, dict):
        """Gets the project as dictionary and the extension properties."""

        proj = project.to_dict()
        eprops = proj.setdefault('extension_props', {}).setdefault(EXTENSION_NAME, {})
        return eprops, proj

    def delete_repo(self, project: pillarsdk.Project, repo_id: str):
        """Deletes an SVN repository and detaches it from the project."""

        from . import remote, exceptions

        eprops, proj = self._get_prop_props(project)
        proj_repo_id = eprops.get('repo_id')
        if proj_repo_id != repo_id:
            self._log.warning('project %s is linked to repo %r, not to %r, refusing to delete',
                              proj['_id'], proj_repo_id, repo_id)
            raise ValueError()

        self.remote.delete_repo(repo_id)
        self._log.info('deleted Subversion repository %s', repo_id)

        # Update the project to remove the repository ID.
        eprops.pop('repo_id', None)
        eprops.pop('access', None)
        proj_utils.put_project(proj)

    def svnman_projects(self, *, projection: dict = None):
        """Returns projects with a Subversion repository.

        :returns: {'_items': [proj, proj, ...], '_meta': Eve metadata}
        """

        import pillarsdk
        from pillar.web.system_util import pillar_api

        api = pillar_api()

        # Find projects that have a repository.
        params = {'where': {f'extension_props.{EXTENSION_NAME}.repo_id': {'$exists': 1}}}
        if projection:
            params['projection'] = projection

        projects = pillarsdk.Project.all(params, api=api)
        return projects

    def grant_access(self, project: pillarsdk.Project, repo_id: str, user_id: str):
        """Grants access to the given user."""

        eprops, proj = self._get_prop_props(project)
        proj_repo_id = eprops.get('repo_id')
        if proj_repo_id != repo_id:
            self._log.warning('project %s is linked to repo %r, not to %r, '
                              'refusing to grant access',
                              proj['_id'], proj_repo_id, repo_id)
            raise ValueError()

        db_user = self._get_db_user(proj, repo_id, user_id)
        username = db_user['username']
        password = '$2y$10$password-not-yet-set'
        self._log.info('granting user %s (%r) access to repo %s of project %s',
                       user_id, username, repo_id, proj['_id'])

        self.remote.modify_access(repo_id, grant=[(username, password)], revoke=[])

    def _get_db_user(self, proj, repo_id, user_id) -> dict:
        """Returns the user from the database.

        Raises a ValueError if the user is not allowed to use svn.
        """

        from pillar.auth import UserClass

        user_oid = str2id(user_id)
        db_user = current_app.db('users').find_one({'_id': user_oid})
        if not db_user:
            self._log.warning('user %s not found, not modifying access to repo %s of project %s',
                              user_id, repo_id, proj['_id'])
            raise ValueError('User not found')

        thatuser = UserClass.construct('', db_user)
        if not thatuser.has_cap('svn-use'):
            self._log.warning('user %s has no svn-use cap, not modifying access to repo %s of'
                              ' project %s', user_id, repo_id, proj['_id'])
            raise wz_exceptions.UnavailableForLegalReasons('User is not allowed to use Subversion')

        return db_user


def _get_current_svnman() -> SVNManExtension:
    """Returns the SVNMan extension of the current application."""

    return flask.current_app.pillar_extensions[EXTENSION_NAME]


def _random_id(alphabet=string.ascii_letters + string.digits) -> str:
    """Returns a random repository ID.

    IDs start with a lowercase-letters-only prefix so that any
    prefix-based subdivision on the server doesn't need to
    distinguish between too many different prefixes. It's
    a bit ugly to do that here, but at least it works 🐙
    """
    import random

    prefix = ''.join([random.choice(string.ascii_lowercase) for _ in range(2)])
    return prefix + ''.join([random.choice(alphabet) for _ in range(22)])


current_svnman: SVNManExtension = LocalProxy(_get_current_svnman)
"""SVNMan extension of the current app."""
