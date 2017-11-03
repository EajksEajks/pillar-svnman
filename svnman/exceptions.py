"""SVNMan-specific exceptions."""

import collections


class SVNManException(Exception):
    """Base exception for all SVNMan-specific exceptions."""


class RemoteError(SVNManException):
    """Errors sent to us by the remote SVNMan API.

    Note that not all errors that have anything to do with the remote server
    communication are wrapped in this error; it's very possible you can get
    IO exceptions when the network fails, for example.
    """


class InternalAPIServerError(RemoteError):
    """Raised when we received a 500 Internal Server Error from the API."""


class BadAPIRequest(RemoteError):
    """Raised when we received a 400 Bad Request response from the API"""


class RepoAlreadyExists(RemoteError):
    def __init__(self, repo_id: str):
        self.repo_id = repo_id

    def __repr__(self):
        return f'RepoAlreadyExists({self.repo_id!r})'


class RepoNotFound(RemoteError):
    def __init__(self, repo_id: str):
        self.repo_id = repo_id

    def __repr__(self):
        return f'RepoNotFound({self.repo_id!r})'


http_error_map = collections.defaultdict(RemoteError)
http_error_map.update({
    400: BadAPIRequest,
    500: InternalAPIServerError,
})
