import os
from flask import Flask, request
import json
import hashlib
import time
import uuid
import logging

app = Flask(__name__)

class Actions:
    @staticmethod
    def redirect(url_metadata):
        # Location header
        pass
    
    @staticmethod
    def proxy(url_metadata):
        # Fetch and serve
        pass
    
    @staticmethod
    def preview(url_metadata):
        # TODO template etc
        pass

class IDGenerators:
    @staticmethod
    def uuid():
        return uuid.uuid4()

# Some default config settings.
default_config = {
        'max_url_length': 1024
    ,   'default_id_generator': 'uuid'
    ,   'log_level': 'DEBUG'
    }

# Load config from the environment, falling back to the defaults.
for k, v in default_config.iteritems():
    app.config[k] = os.environ.get(k, v)

# Set up logging.
app.logger.setLevel(getattr(logging, app.config['log_level']))
app.logger.addHandler(logging.StreamHandler())

def check_config():
    """Returns a bool indicating whether we have enough configuration
    to serve a request."""

    keys_desired = set(['API_SECRET', 'AWS_ACCESS', 'AWS_SECRET'])

    app.logger.info("Verifying config contains these keys: %s", " ".join(keys_desired))

    keys_provided = set(os.environ.keys())
    keys_missing = keys_desired.difference(keys_provided)
    
    if len(keys_missing) > 0:
        app.logger.info("Config is missing at least one key: %s", " ".join(keys_missing))
        return False
    else:
        app.logger.info("Config passes basic check.")
        return True

@app.route('/')
def root():
    if check_config():
        return 'OK'
    else:
        return 'Config not OK, check logs.'

def validate_auth_token():
    # The secret token is appended to the complete JSON request body and a
    # sha1 hash is computed. If this matches what the user supplied, it
    # proves they know the shared secret and are allowed to create URLs.
    # We accept some variants, like a trailing newline, to try to be nicer
    # to the user.
    auth_tokens = []
    auth_tokens.append(hashlib.sha1(request.data + os.environ['API_SECRET']).hexdigest())
    auth_tokens.append(hashlib.sha1(request.data + os.environ['API_SECRET'] + "\n").hexdigest())
    app.logger.debug("auth_tokens=%s", repr(auth_tokens))
    return request.headers.get('x-authtoken', None) in auth_tokens

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
    
    # Build the URL metadata that will be put in the persistent store.
    url_metadata = {
            'url': request_data['url']
        ,   'actions': request_data.get('actions', None)
        ,   'created': int(time.time())
        }

    app.logger.debug("url_metadata=%s", repr(url_metadata))

    # Look up the user's specified ID generation function. If they
    # don't specify one, fall back to the default in the config.
    id_gen_func = getattr(IDGenerators, request_data.get('id_generator', app.config['default_id_generator']))

    # Call the ID generating function, with any args the user may have supplied.
    short_id = id_gen_func(**request_data.get('id_generator_args', {}))
    app.logger.debug("short_id=%s", short_id)

    # Save the URL metadata in the persistent store.
    # TODO

    # Build the new short URL and send it back to the user.
    new_url = "%s%s" % (request.url_root, short_id)
    app.logger.debug("new_url=%s", new_url)
    return json.dumps({'url': new_url}), 201

@app.route('/<path:short>')
@app.route('/<action>/<path:short>')
def lookup(short, action = None):
    app.logger.debug("route=lookup short=%s action=%s", short, action)
    # Look up long URL from short path ID
    # If not action:
    # Look up default action, according to the rules the URL was created with.
    # Verify that the requested action is allowed for this URL.
    # Do something based on the action:
    # redirect: Send Location header.
    # proxy: Request the remote content and serve it to the user.
    # preview: Show the user a page with the long URL and let them take themselves there.
    return "lookup"


