"""Persistent storage for a URL shortener."""

import json
import hashlib
import time

import boto
from boto.s3.connection import S3Connection, Key
import graphiteudp

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
        start = time.time()
        obj = Key(self.bucket)
        obj.key = path

        try:
            content = obj.get_contents_as_string()
        except boto.exception.S3ResponseError as ex:
            # XXX This exception handler doesn't seem to catch 404s from S3.
            # Confused, but leaving it as is for now.
            if '404' in ex:
                graphiteudp.send("s3.error.404", 1)
                raise NotFoundException()
            elif '403' in ex:
                graphiteudp.send("s3.error.403", 1)
                raise PermissionDeniedException()
            else:
                graphiteudp.send("s3.error.unhandled", 1)
                raise
            
        graphiteudp.send("s3.get_time", time.time() - start)
        graphiteudp.send("s3.get_size", len(content))
        return content

    def put(self, path, content):
        start = time.time()
        obj = Key(self.bucket)
        obj.key = path
        obj.set_contents_from_string(content)
        graphiteudp.send("s3.put_time", time.time() - start)
        graphiteudp.send("s3.put_size", len(content))

class URLShortenerS3Store(S3Store):
    """For the URL shortener S3 storage, enforce a predictable path and
    JSON serialisation for content."""

    def _get_path(self, path):
        return "urls/%s.json" % hashlib.sha1(path).hexdigest()

    def get(self, path):
        return json.loads(S3Store.get(self, self._get_path(path)))
    
    def put(self, path, content):
        return S3Store.put(self, self._get_path(path), json.dumps(content))

