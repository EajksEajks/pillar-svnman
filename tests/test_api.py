import json

import requests
import responses

from .abstract_svnman_test import AbstractSVNManTest


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
    def test_create_repo_already_exists(self):
        from svnman.remote import CreateRepo
        from svnman.exceptions import RepoAlreadyExists

        responses.add(responses.POST, 'http://svnman_api_url/api/repo',
                      status=requests.codes.conflict)

        cr = CreateRepo(repo_id='UPPERCASE', project_id='someproject', creator='me <here@there>')
        with self.assertRaises(RepoAlreadyExists):
            self.remote.create_repo(cr)

    @responses.activate
    def test_delete_repo(self):
        responses.add(responses.DELETE,
                      'http://svnman_api_url/api/repo/repo-id',
                      status=requests.codes.no_content)
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

    @responses.activate
    def test_fetch_repo_internal_server_error(self):
        from svnman.exceptions import InternalAPIServerError

        responses.add(responses.GET, 'http://svnman_api_url/api/repo/repo-id', status=500)

        with self.assertRaises(InternalAPIServerError):
            self.remote.fetch_repo('repo-id')

    @responses.activate
    def test_fetch_repo_not_found(self):
        from svnman.exceptions import RepoNotFound

        responses.add(responses.GET, 'http://svnman_api_url/api/repo/repo-id', status=404)

        with self.assertRaises(RepoNotFound):
            self.remote.fetch_repo('repo-id')

    @responses.activate
    def test_fetch_repo_not_found(self):
        from svnman.exceptions import RemoteError

        responses.add(responses.GET, 'http://svnman_api_url/api/repo/repo-id',
                      status=requests.codes.im_a_teapot)

        with self.assertRaises(RemoteError):
            self.remote.fetch_repo('repo-id')

    @responses.activate
    def test_modify_access(self):
        def request_callback(request):
            payload = json.loads(request.body)
            # Both password hashes should use $2y$ type indication.
            self.assertEqual({
                'grant': [{'username': 'username', 'password': '$2y$1234'},
                          {'username': 'username2', 'password': '$2y$5555'},
                          ],
                'revoke': ['someone-else']
            }, payload)

            # Returns status code, headers, body
            return 204, {}, ''

        responses.add_callback(responses.POST, 'http://svnman_api_url/api/repo/repo-id/access',
                               callback=request_callback)

        self.remote.modify_access('repo-id',
                                  grant=[('username', '$2a$1234'), ('username2', '$2y$5555')],
                                  revoke=['someone-else'])
