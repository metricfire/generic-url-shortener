"""Persistent storage for a URL shortener."""

import json
import hashlib

import boto
from boto.s3.connection import S3Connection, Key

class NotFoundException(Exception):
    pass

class PermissionDeniedException(Exception):
    pass

class S3Store(object):
    """A thin wrapper around boto to provide a cleaner API for S3"""

    def __init__(self, s3_bucket, aws_access, aws_secret):
        self.s3 = S3Connection(aws_access, aws_secret)
        self.bucket = self.s3.get_bucket(s3_bucket, validate = False)

    def get(self, path):
        obj = Key(self.bucket)
        obj.key = path

        try:
            content = obj.get_contents_as_string()
        except boto.exception.S3ResponseError as ex:
            # XXX This exception handler doesn't seem to catch 404s from S3.
            # Confused, but leaving it as is for now.
            if '404' in ex:
                raise NotFoundException()
            elif '403' in ex:
                raise PermissionDeniedException()
            else:
                raise
            
        return content

    def put(self, path, content):
        obj = Key(self.bucket)
        obj.key = path
        obj.set_contents_from_string(content)

class URLShortenerS3Store(S3Store):
    """For the URL shortener S3 storage, enforce a predictable path and
    JSON serialisation for content."""

    def _get_path(self, path):
        return "urls/%s.json" % hashlib.sha1(path).hexdigest()

    def get(self, path):
        return json.loads(S3Store.get(self, self._get_path(path)))
    
    def put(self, path, content):
        return S3Store.put(self, self._get_path(path), json.dumps(content))

