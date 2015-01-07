"""Generators for various short URL formats."""

import uuid

class IDGenerators:
    @staticmethod
    def uuid(url):
        return str(uuid.uuid4())

