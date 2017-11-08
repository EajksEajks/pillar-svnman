import responses

from abstract_svnman_test import AbstractSVNManTest


class TestAPI(AbstractSVNManTest):
    @responses.activate
    def test_create_repo(self):
        from svnman.remote import CreateRepo
        responses.add(responses.POST,
                      'http://svnman_api_url/api/repo',
                      json={'repo_id': 'something-completely-different'},
                      status=201)

        cr = CreateRepo(repo_id='UPPERCASE', project_id='someproject', creator='me <here@there>')
        resp = self.remote.create_repo(cr)
        self.assertEqual('something-completely-different', resp)

    @responses.activate
    def test_delete_repo(self):
        responses.add(responses.DELETE,
                      'http://svnman_api_url/api/repo/repo-id',
                      status=204)
        self.remote.delete_repo('repo-id')

    @responses.activate
    def test_fetch_repo(self):
        from svnman.remote import RepoDescription
        responses.add(responses.GET,
                      'http://svnman_api_url/api/repo/repo-id',
                      json={
                          'repo_id': 'something-completely-different',
                          'access': ['someuser', 'otheruser'],
                      },
                      status=200)

        resp = self.remote.fetch_repo('repo-id')
        expect = RepoDescription(
            repo_id='something-completely-different',
            access=['someuser', 'otheruser'],
        )
        self.assertEqual(expect, resp)
