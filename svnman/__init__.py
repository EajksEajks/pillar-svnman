import logging
import os.path

import bson
import flask
from werkzeug.local import LocalProxy

import pillarsdk
from pillar.extension import PillarExtension
from pillar.auth import current_user
from pillar.api.projects import utils as proj_utils

EXTENSION_NAME = 'svnman'


# SVNman stores the following keys in the project extension properties:
# repo_id: the Subversion repository ID
# users: list of ObjectIDs of users having access to the project

class SVNManExtension(PillarExtension):
    user_caps = {
        'subscriber-pro': frozenset({'svn-use'}),
        'demo': frozenset({'svn-use'}),
        'admin': frozenset({'svn-use', 'svn-admin'}),
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
            'SVNMAN_API_URL': 'http://configure-SVNMAN_API_URL/api/',
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
        return flask.render_template('svnman/sidebar.html', project=project)

    @property
    def has_project_settings(self) -> bool:
        return current_user.has_cap('svn-use')

    def project_settings(self, project: pillarsdk.Project, **template_args: dict) -> flask.Response:
        """Renders the project settings page for this extension.

        Set YourExtension.has_project_settings = True and Pillar will call this function.

        :param project: the project for which to render the settings.
        :param template_args: additional template arguments.
        :returns: a Flask HTTP response
        """

        from .routes import project_settings

        return project_settings(project, **template_args)

    def is_svnman_project(self, project: pillarsdk.Project) -> bool:
        """Checks whether the project is correctly set up for SVNman."""

        if not project.extension_props:
            return False

        try:
            pprops = project.extension_props[EXTENSION_NAME]
        except AttributeError:
            self._log.warning("is_svnman_project: Project url=%r doesn't have"
                              " any extension properties.", project['url'])
            if self._log.isEnabledFor(logging.DEBUG):
                import pprint
                self._log.debug('Project: %s', pprint.pformat(project.to_dict()))
            return False
        except KeyError:
            return False

        if pprops is None:
            self._log.warning("is_svnman_project: Project url=%r doesn't have"
                              " Flamenco extension properties.", project['url'])
            return False

        return bool(pprops.repo_id)

    def create_repo(self, project_url: str, creator: str) -> str:
        """Creates a SVN repository with a random ID attached to the project.

        Saves the repository ID in the project. Is a no-op if the project
        already has a Subversion repository.
        """

        import random
        import string

        from . import remote, exceptions

        alphabet = string.ascii_letters + string.digits

        proj = proj_utils.get_project(project_url)
        project_id = proj['_id']
        eprops = proj.setdefault('extension_props', {}).setdefault(EXTENSION_NAME, {})

        repo_id = eprops.get('repo_id')
        if repo_id:
            self._log.warning('project %s already has a Subversion repository %r',
                              project_id, repo_id)
            return repo_id

        def random_id():
            return ''.join([random.choice(alphabet) for _ in range(24)])

        repo_info = remote.CreateRepo(
            repo_id='',
            project_id=str(project_id),
            creator=creator,
        )

        for _ in range(100):
            repo_info.repo_id = random_id()
            self._log.info('creating new repository, trying out %s', repo_info)
            try:
                self.remote.create_repo(repo_info)
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
        eprops['repo_id'] = repo_info.repo_id
        proj_utils.put_project(proj)

        return repo_info.repo_id


def _get_current_svnman() -> SVNManExtension:
    """Returns the SVNMan extension of the current application."""

    return flask.current_app.pillar_extensions[EXTENSION_NAME]


current_svnman: SVNManExtension = LocalProxy(_get_current_svnman)
"""SVNMan extension of the current app."""
