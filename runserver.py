#!/usr/bin/env python

from pillar import PillarServer
from svnman import SVNManExtension

app = PillarServer('.')
app.load_extension(SVNManExtension(), '/svn')
app.process_extensions()

if __name__ == '__main__':
    app.run('::0', 5000, debug=True)
