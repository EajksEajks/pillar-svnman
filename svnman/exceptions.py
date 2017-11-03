"""SVNMan-specific exceptions."""


class SVNManException(Exception):
    """Base exception for all SVNMan-specific exceptions."""


class RemoteError(SVNManException):
    """Errors sent to us by the remote SVNMan API.

    Note that not all errors that have anything to do with the remote server
    communication are wrapped in this error; it's very possible you can get
    exceptions from the Requests library, for example.
    """


class RepoAlreadyExists(RemoteError):
    def __init__(self, repo_id: str):
        self.repo_id = repo_id

    def __repr__(self):
        return f'RepoAlreadyExists({self.repo_id!r})'

