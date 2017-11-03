import functools
import logging

import bson
from flask import Blueprint, render_template, redirect, url_for
from flask_login import login_required
import werkzeug.exceptions as wz_exceptions

from pillar.auth import current_user as current_user
from pillar.api.utils.authentication import current_user_id
from pillar.web.utils import attach_project_pictures
from pillar.web.system_util import pillar_api
from pillar.web.projects.routes import project_view
import pillarsdk

from svnman import current_svnman

blueprint = Blueprint('svnman', __name__)
log = logging.getLogger(__name__)


@blueprint.route('/')
def index():
    api = pillar_api()

    # FIXME Sybren: add permission check.
    # TODO: add projections.
    projects = current_svnman.svnman_projects()

    for project in projects['_items']:
        attach_project_pictures(project, api)

    projs_with_summaries = [
        (proj, current_svnman.job_manager.job_status_summary(proj['_id']))
        for proj in projects['_items']
    ]

    return render_template('svnman/index.html',
                           projs_with_summaries=projs_with_summaries)


def error_project_not_setup_for_svnman():
    return render_template('svnman/errors/project_not_setup.html')


def error_project_not_available():
    import flask

    if flask.request.is_xhr:
        resp = flask.jsonify({'_error': 'project not available on Subversion'})
        resp.status_code = 403
        return resp

    return render_template('svnman/errors/project_not_available.html')


@blueprint.route('/setup-for-svn')
def setup_for_svnman(project_url):
    return f'yeah {project_url}'


def project_settings(project: pillarsdk.Project, **template_args: dict):
    """Renders the project settings page for Subversion projects."""

    if not current_user.has_cap('svn-use'):
        raise wz_exceptions.Forbidden()

    # Based on the project state, we can render a different template.
    # if not current_svnman.is_svnman_project(project):
    return render_template('svnman/project_settings/offer_setup.html',
                           project=project, **template_args)

    return render_template('svnman/project_settings/settings.html',
                           project=project,
                           **template_args)
