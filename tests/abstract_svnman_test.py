import pillarsdk
import pillar.tests
import pillar.auth

from pillar.tests import PillarTestServer, AbstractPillarTest


class SVNManTestServer(PillarTestServer):
    def __init__(self, *args, **kwargs):
        PillarTestServer.__init__(self, *args, **kwargs)

        from svnman import SVNManExtension
        self.load_extension(SVNManExtension(), '/svn')


class AbstractSVNManTest(AbstractPillarTest):
    pillar_server_class = SVNManTestServer

    def setUp(self, **kwargs):
        super().setUp(**kwargs)

        from svnman.remote import API

        self.remote: API = self.svnman.remote
        self.proj_id, self.project = self.ensure_project_exists(project_overrides={
            'picture_header': None,
            'picture_square': None,
        })

        self.sdk_project = pillarsdk.Project(pillar.tests.mongo_to_sdk(self.project))

    def tearDown(self):
        self.unload_modules('svnman')
        super().tearDown()

    @property
    def svnman(self):
        from svnman import SVNManExtension

        svnman: SVNManExtension = self.app.pillar_extensions['svnman']
        return svnman
