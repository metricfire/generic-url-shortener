"""Generators for various short URL formats."""

import uuid
import hashlib
import base64

class IDGenerators:
    @staticmethod
    def uuid(url):
        """A random UUID, with dashes."""
        return str(uuid.uuid4())

    @staticmethod
    def md5(url):
        """Hex representation of the MD5 hash of the URL."""
        return hashlib.md5(url).hexdigest()

    @staticmethod
    def b64_md5(url):
        """URL safe Base64 encoding of the MD5 hash of the URL."""
        return base64.urlsafe_b64encode(hashlib.md5(url).digest()).strip("=")

if __name__ == "__main__":
    # Provide a quick way of experimenting with individual ID generators
    # from a shell.
    import sys
    import json

    if len(sys.argv) < 3:
        print "Usage: %s <id_generator_func> <url> [json encoded dictionary of extra params]" % sys.argv[0]
        raise SystemExit(1)

    try:
        kwargs = json.loads(sys.argv[3])
    except IndexError:
        kwargs = {}

    print getattr(IDGenerators, sys.argv[1])(sys.argv[2], **kwargs)
