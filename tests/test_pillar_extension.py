import copy

import pillarsdk
import pillar.tests

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
