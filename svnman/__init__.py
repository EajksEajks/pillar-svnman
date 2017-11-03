import logging
import os.path

import flask
from werkzeug.local import LocalProxy

import pillarsdk
from pillar.extension import PillarExtension
from pillar.auth import current_user

EXTENSION_NAME = 'svnman'


class SVNManExtension(PillarExtension):
    user_caps = {
        'subscriber-pro': frozenset({'svn-use'}),
        'demo': frozenset({'svn-use'}),
        'admin': frozenset({'svn-use', 'svn-admin'}),
    }

    def __init__(self):
        from . import remote

        self._log = logging.getLogger('%s.SVNManExtension' % __name__)
        self.remote: remote.Remote = None

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

        self.remote = remote.Remote(
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


def _get_current_svnman() -> SVNManExtension:
    """Returns the SVNMan extension of the current application."""

    return flask.current_app.pillar_extensions[EXTENSION_NAME]


current_svnman: SVNManExtension = LocalProxy(_get_current_svnman)
"""SVNMan extension of the current app."""
