"""Generators for various short URL formats."""

import uuid
import hashlib
import base64

class IDGenerators:
    @staticmethod
    def uuid(seed):
        """A random UUID, with dashes."""
        return str(uuid.uuid4())

    @staticmethod
    def md5(seed):
        """Hex representation of the MD5 hash of the seed."""
        return hashlib.md5(seed).hexdigest()

    @staticmethod
    def b64_md5(seed):
        """URL safe Base64 encoding of the MD5 hash of the seed."""
        return base64.urlsafe_b64encode(hashlib.md5(seed).digest()).strip("=")

if __name__ == "__main__":
    # Provide a quick way of experimenting with individual ID generators
    # from a shell.
    import sys
    import json

    if len(sys.argv) < 3:
        print "Usage: %s <id_generator_func> <seed> [json encoded dictionary of extra params]" % sys.argv[0]
        raise SystemExit(1)

    try:
        kwargs = json.loads(sys.argv[3])
    except IndexError:
        kwargs = {}

    print getattr(IDGenerators, sys.argv[1])(sys.argv[2], **kwargs)
