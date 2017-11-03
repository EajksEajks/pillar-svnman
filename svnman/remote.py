import typing

import attr
import requests

from pillar import attrs_extra

from . import exceptions


@attr.s
class RepoDescription:
    repo_id: str = attrs_extra.string()
    access: typing.List[str] = attrs_extra.string()


@attr.s
class CreateRepo:
    repo_id: str = attrs_extra.string()
    project_id: str = attrs_extra.string()
    creator: str = attrs_extra.string()


@attr.s
class API:
    # The remote URL and credentials are separate. This way we can log the
    # URL that is used in requests without worrying about leaking creds.
    remote_url: str = attr.ib(validator=attr.validators.instance_of(str))
    """URL of the remote SVNMan API.
    
    Should probably end in '/api/'.
    """

    username: str = attr.ib(validator=attr.validators.instance_of(str))
    """Username for authenticating ourselves with the API."""
    password: str = attr.ib(validator=attr.validators.instance_of(str), repr=False)
    """Password for authenticating ourselves with the API."""

    _log = attrs_extra.log('%s.Remote' % __name__)
    _session = requests.Session()

    def __attrs_post_init__(self):
        from requests.adapters import HTTPAdapter
        self._session.mount('/', HTTPAdapter(max_retries=10))

    def _request(self, method: str, rel_url: str, **kwargs) -> requests.Response:
        """Performs a HTTP request on the API server."""

        from urllib.parse import urljoin

        abs_url = urljoin(self.remote_url, rel_url)
        self._log.getChild('request').info('%s %s', method, abs_url)

        auth = (self.username, self.password) if self.username or self.password else None
        return self._session.request(method, abs_url, auth=auth, **kwargs)

    def _raise_for_status(self, resp: requests.Response):
        """Raises the appropriate exception for the given response."""

        if resp.status_code < 400:
            return

        exc_class = exceptions.http_error_map[resp.status_code]
        raise exc_class(resp.text)

    def fetch_repo(self, repo_id: str) -> RepoDescription:
        """Fetches repository information from the remote."""

        resp = self._request('GET', f'repo/{repo_id}')
        self._raise_for_status(resp)

        return RepoDescription(**resp.json())

    def create_repo(self, create_repo: CreateRepo):
        """Creates a new repository with the given ID.

        :param create_repo: info required by the API
        :raises svnman.exceptions.RepoAlreadyExists:
        """

        resp = self._request('POST', f'repo', json=attr.asdict(create_repo))
        if resp.status_code == requests.codes.conflict:
            raise exceptions.RepoAlreadyExists(create_repo.repo_id)
        self._raise_for_status(resp)

    def modify_access(self,
                      repo_id: str,
                      grant: typing.List[typing.Tuple[str, str]],
                      revoke: typing.List[str]):
        """Modifies user access to the repository.

        Does not return anything; no exception means exection was ok.

        :param repo_id: the repository ID
        :param grant: list of (username password) tuples. The passwords should be BCrypt-hashed.
        :param revoke: list of usernames.
        """

        grants = [{'username': u, 'password': p} for u, p in grant]

        resp = self._request('POST', f'repo/{repo_id}/access', json={
            'grant': grants,
            'revoke': revoke,
        })
        self._raise_for_status(resp)
