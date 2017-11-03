import typing

import attr
import requests

from pillar import attrs_extra


@attr.s
class RepoDescription(object):
    repo_id: str = attr.ib(validator=attr.validators.instance_of(str))
    access: typing.List[str] = attr.ib(validator=attr.validators.instance_of(list))


@attr.s
class API(object):
    # The remote URL and credentials are separate. This way we can log the
    # URL that is used in requests without worrying about leaking creds.
    remote_url: str = attr.ib(validator=attr.validators.instance_of(str))
    """URL of the remote SVNMan API.
    
    Should probably end in '/api/'.
    """

    username: str = attr.ib(validator=attr.validators.instance_of(str))
    """Username for authenticating ourselves with the API."""
    password: str = attr.ib(validator=attr.validators.instance_of(str))
    """Password for authenticating ourselves with the API."""

    _log = attrs_extra.log('%s.Remote' % __name__)
    _session = requests.Session()

    def __attrs_post_init__(self):
        from requests.adapters import HTTPAdapter
        self._session.mount('/', HTTPAdapter(max_retries=10))

    def fetch_repo(self, repo_id: str) -> RepoDescription:
        """Fetches repository information from the remote."""

        resp = self._request('GET', f'repo/{repo_id}')
        resp.raise_for_status()
        return RepoDescription(**resp.json())

    def _request(self, method: str, rel_url: str, **kwargs) -> requests.Response:
        """Performs a HTTP request on the API server."""

        from urllib.parse import urljoin

        abs_url = urljoin(self.remote_url, rel_url)
        self._log.getChild('request').info('%s %s', method, abs_url)

        auth = (self.username, self.password) if self.username or self.password else None
        return self._session.request(method, abs_url, auth=auth, **kwargs)
