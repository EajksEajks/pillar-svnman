import copy
from unittest import mock

import pillarsdk
import pillar.tests
import werkzeug.exceptions as wz_exceptions

from abstract_svnman_test import AbstractSVNManTest


class TestPillarExtension(AbstractSVNManTest):
    def test_is_svnman_project(self):
        svn = self.svnman
        sdk_project = None

        def conv():
            nonlocal sdk_project
            sdk_project = pillarsdk.Project(pillar.tests.mongo_to_sdk(project))

        # Default just-created project
        project = copy.deepcopy(self.project)
        conv()
        self.assertFalse(svn.is_svnman_project(sdk_project))

        project['extension_props'] = None
        conv()
        self.assertFalse(svn.is_svnman_project(sdk_project))

        # With empty svnman extensions. We don't make any distinction between
        # 'set up for SVNman' or 'has an actual repository'; the former → false,
        # the latter → true.
        project['extension_props'] = {'svnman': {}}
        conv()
        self.assertFalse(svn.is_svnman_project(sdk_project))

        project['extension_props'] = {'svnman': {'repo_id': 'something-random'}}
        conv()
        self.assertTrue(svn.is_svnman_project(sdk_project))

    @mock.patch('svnman.remote.API.create_repo')
    @mock.patch('svnman._random_id')
    def test_create_repo_happy(self, mock_random_id, mock_create_repo):
        from svnman import EXTENSION_NAME
        from svnman.remote import CreateRepo
        from svnman.exceptions import RepoAlreadyExists

        self.enter_app_context()
        self.login_api_as(24 * 'a', roles={'admin'})

        mock_create_repo.side_effect = [RepoAlreadyExists('first-random-id'), 'new-repo-id']
        mock_random_id.side_effect = ['first-random-id', 'second-random-id']

        returned_repo_id = self.svnman.create_repo(
            self.sdk_project,
            'tester <tester@unittests.com>',
        )

        # Not checking for exact parameters for both calls, since the objects passed
        # to the calls are modified in-place anyway, and wouldn't match a check
        # after the fact.
        cr2 = CreateRepo(repo_id='second-random-id',
                         project_id=str(self.proj_id),
                         creator='tester <tester@unittests.com>')
        mock_create_repo.assert_called_with(cr2)

        # This is the important bit: the final repository ID returned to the system
        # and stored in the project document.
        self.assertEqual('new-repo-id', returned_repo_id)

        db_proj = self.fetch_project_from_db(self.proj_id)
        self.assertEqual('new-repo-id', db_proj['extension_props'][EXTENSION_NAME]['repo_id'])
