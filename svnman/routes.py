import logging

from flask import Blueprint, render_template, jsonify
import werkzeug.exceptions as wz_exceptions

from pillar.api.utils.authorization import require_login
from pillar.auth import current_user
from pillar.web.projects.routes import project_view
from pillar.web.utils import attach_project_pictures
from pillar.web.system_util import pillar_api
import pillarsdk

from svnman import current_svnman

blueprint = Blueprint('svnman', __name__)
log = logging.getLogger(__name__)


def require_project_put(projections: dict = None):
    """Endpoint decorator, translates project_url into an actual project and checks PUT access."""

    import functools

    if callable(projections):
        raise TypeError('Use with @require_project_put() <-- note the parentheses')

    def decorator(wrapped):
        @functools.wraps(wrapped)
        @project_view()
        def wrapper(project: pillarsdk.Project, *args, **kwargs):
            if 'PUT' not in project.allowed_methods:
                log.warning('User %s has no PUT access to project %s (id=%s) but wants to '
                            'manage a Subversion repository; denying access to %s',
                            current_user.user_id, project.url, project['_id'], request.url)
                raise wz_exceptions.Forbidden()

            return wrapped(project, *args, **kwargs)

        return wrapper

    return decorator


@blueprint.route('/')
def index():
    api = pillar_api()

    # FIXME Sybren: add permission check.
    # TODO: add projections.
    projects = current_svnman.svnman_projects()

    for project in projects['_items']:
        attach_project_pictures(project, api)

    return render_template('svnman/index.html',
                           projects=projects)


def error_project_not_available():
    import flask

    if flask.request.is_xhr:
        resp = flask.jsonify({'_error': 'Subversion service not available'})
        resp.status_code = 403
        return resp

    return render_template('svnman/errors/service_not_available.html')


@blueprint.route('/<project_url>/create-repo', methods=['POST'])
@require_login(require_cap='svn-use')
@require_project_put()
def create_repo(project: pillarsdk.Project):
    log.info('going to create repository for project url=%r on behalf of user %s (%s)',
             project.url, current_user.user_id, current_user.email)

    from . import exceptions

    try:
        current_svnman.create_repo(project, f'{current_user.full_name} <{current_user.email}>')
    except (OSError, IOError):
        log.exception('unable to reach SVNman API')
        resp = jsonify(_message='unable to reach SVNman API server')
        resp.status_code = 500
        return resp
    except exceptions.RemoteError as ex:
        log.error('API sent us an error: %s', ex)
        resp = jsonify(_message=str(ex))
        resp.status_code = 500
        return resp
    return '', 204


@blueprint.route('/<project_url>/delete-repo/<repo_id>', methods=['POST'])
@require_login(require_cap='svn-use')
@require_project_put()
def delete_repo(project: pillarsdk.Project, repo_id: str):
    log.info('going to delete repository %s for project url=%r on behalf of user %s (%s)',
             repo_id, project.url, current_user.user_id, current_user.email)

    from . import exceptions

    try:
        current_svnman.delete_repo(project, repo_id)
    except (OSError, IOError):
        log.exception('unable to reach SVNman API')
        resp = jsonify(_message='unable to reach SVNman API server')
        resp.status_code = 500
        return resp
    except exceptions.RemoteError as ex:
        log.error('API sent us an error: %s', ex)
        resp = jsonify(_message=str(ex))
        resp.status_code = 500
        return resp
    return '', 204


def project_settings(project: pillarsdk.Project, **template_args: dict):
    """Renders the project settings page for Subversion projects."""

    if not current_user.has_cap('svn-use'):
        raise wz_exceptions.Forbidden()

    # Based on the project state, we can render a different template.
    if not current_svnman.is_svnman_project(project):
        return render_template('svnman/project_settings/offer_create_repo.html',
                               project=project, **template_args)

    return render_template('svnman/project_settings/settings.html',
                           project=project,
                           **template_args)
