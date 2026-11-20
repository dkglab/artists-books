# The one Apache Jena version pin, shared by tools/jena (the command-line
# tools) and tools/fuseki (the server). Apache ships them as two separate
# tarballs from one release, and both Makefiles include this file, so the two
# can't drift apart (#175). Renovate (renovate.json) watches the line below.
#
# archive.apache.org, not dlcdn.apache.org: the CDN keeps only the current
# Jena release, so a pinned version 404s there as soon as the next one ships
# (#139). The archive keeps every release; it is slower, but this is a
# one-time fetch.
JENA_HOST := https://archive.apache.org/dist/jena/binaries
JENA_VERSION := 6.2.0
