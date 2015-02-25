import os
import json
import hashlib
import time
import logging
import hmac

from flask import Flask, request, redirect
import requests

# Persistent storage.
import stores
from idgenerators import IDGenerators

app = Flask(__name__)

class Actions:

    @staticmethod
    def redirect(url_metadata):
        return redirect(url_metadata['url']) # 302, temporary
    
    @staticmethod
    def proxy(url_metadata):
        # TODO Consider the security (XSS/CSRF/etc) implications of this.

        # Mitigation points:
        # * No user-defined headers are sent with the request.
        # * It is forced to be a GET request.
        # * Only some of the response is returned:
        #   * Request body
        #   * HTTP response code
        #   * Content-type header
        #
        # Is this enough?

        response = requests.get(url_metadata['url'], timeout=30)
        return response.content, response.status_code, \
            {'Content-Type': response.headers.get('content-type', 'text/plain')}
    
    @staticmethod
    def preview(url_metadata):
        # TODO template etc
        return "Preview: This short URL points to %s" % url_metadata['url']

# Some default config settings.
default_config = {
        'max_url_length': 1024
    ,   'default_id_generator': 'b64_md5'
    ,   'default_action': 'redirect'
    ,   'log_level': 'DEBUG'
    }

# Load config from the environment, falling back to the defaults.
for k, v in default_config.iteritems():
    app.config[k] = os.environ.get(k, v)

# Set up logging.
app.logger.setLevel(getattr(logging, app.config['log_level']))
app.logger.addHandler(logging.StreamHandler())

# Config the user is required to provide because there are no sensible
# defaults.
required_config = [
        'api_secrets'
    ,   's3_bucket'
    ,   'aws_access'
    ,   'aws_secret'
    ]

for k in required_config:
    try:
        app.config[k] = os.environ[k]
    except KeyError:
        app.logger.error("Cannot start without an environment variable for '%s'" % k)
        raise Exception("Insufficient config, check your logs for detail.")

# Set up the persistent store.
storage = stores.URLShortenerS3Store(
        app.config['s3_bucket']
    ,   app.config['aws_access']
    ,   app.config['aws_secret']
    )

@app.route('/')
def root():
    return "OK"

def validate_auth_token():
    # Compute a HMAC auth token from what the request data and our shared
    # secret, using SHA1.
    valid_auth_tokens = []
    for shared_secret in app.config['api_secrets'].split(","):
        valid_auth_tokens.append(hmac.HMAC(shared_secret, request.data,
            hashlib.sha1).hexdigest())

    submitted_auth_token = request.headers.get('x-authtoken', None)

    for auth_token in valid_auth_tokens:
        app.logger.debug("calculated_auth_token=%s submitted_auth_token=%s "
            "match=%s", auth_token, submitted_auth_token, \
            auth_token in submitted_auth_token)

    # Look for the auth token we calculated to appear in what the user
    # submitted. We're not strict about where exactly the auth token appears
    # in an attempt to not burden the user with getting the whitespace exactly
    # correct. Once the right token is in there somewhere, it's fine.
    return any(map(lambda at: at in submitted_auth_token, valid_auth_tokens))

def validate_add(request_data):
    try:
        request_data['url']
    except KeyError:
        raise Exception("No long URL in your request, nothing to do.")

    if len(request_data['url']) > app.config['max_url_length']:
        raise Exception("URL exceeds maximum length.")

    supported_actions = filter(lambda f: not f.startswith("_"), dir(Actions))
    unsupported_actions = set(request_data.get('actions', [])).difference(supported_actions)
    app.logger.debug("unsupported_actions=%s", repr(unsupported_actions))
    if len(unsupported_actions) > 0:
        raise Exception("These actions are unsupported: %s" % " ".join(unsupported_actions))
    
    # Look up the user's specified ID generation function, failing if they
    # specify one that doesn't exist. If they don't specify one, fall back
    # to the default in the config.
    id_generators = filter(lambda f: not f.startswith("_"), dir(IDGenerators))
    if request_data.get('id_generator', app.config['default_id_generator']) not in id_generators:
        raise Exception("No ID generator called %s" % ex)

@app.route('/add/', methods = ['POST'])
def add():
    app.logger.debug("route=add request_data=%s", repr(request.data))

    # Validate auth token.
    if not validate_auth_token():
        return json.dumps({"error": "Bad auth token."}), 403

    request_data = json.loads(request.data)

    # Validate the request data.
    try:
        validate_add(request_data)
    except Exception as ex:
        return json.dumps({"error": str(ex)}), 400
    
    # Look up the user's specified ID generation function. If they
    # don't specify one, fall back to the default in the config.
    id_gen_func = getattr(IDGenerators, request_data.get('id_generator', app.config['default_id_generator']))

    # Call the ID generating function, with any args the user may have supplied.
    # Use the auth token submitted with this request as a random seed for the
    # ID generator functions.
    short_id = id_gen_func(request.headers.get('x-authtoken'), **request_data.get('id_generator_args', {}))
    app.logger.debug("short_id=%s", short_id)
    
    # Build the URL metadata that will be put in the persistent store.
    url_metadata = {
            'url': request_data['url']
        ,   'actions': request_data.get('actions', None)
        ,   'created': int(time.time())
        ,   'short_id': short_id
        }
    app.logger.debug("url_metadata=%s", repr(url_metadata))

    # Save the URL metadata in the persistent store.
    storage.put(short_id, url_metadata)

    # Build the new short URL and send it back to the user.
    new_url = "%s%s" % (request.url_root, short_id)
    app.logger.debug("new_url=%s", new_url)
    return json.dumps({'url': new_url}), 201

@app.route('/<path:short>')
@app.route('/<action>/<path:short>')
def lookup(short, action = None):
    app.logger.debug("route=lookup short=%s action=%s", short, action)

    # Look up the url metadata from persistent storage.
    url_metadata = storage.get(short)
    app.logger.debug("url_metadata=%s", url_metadata)

    # If no action is provided, check if only one action is provided for
    # this URL. If there is, use it. Otherwise, use the default action.
    if action is None:
        try:
            if len(url_metadata['actions']) == 1:
                action = url_metadata['actions'][0]
        except (KeyError, TypeError):
            pass

        if action is None:
            action = app.config['default_action']

    # When actions=None, any action is allowed.
    # Alternatively, the requested action must be in the list specified
    # for this URL when it was created.
    if url_metadata['actions'] is None or action in url_metadata['actions']:
        app.logger.debug("final_action=%s short=%s", action, short)
        action_func = getattr(Actions, action)
        return action_func(url_metadata)
    else:
        return "Denied.", 403 # TODO template

@app.route('/favicon.ico')
def favicon():
    return "", 404
