import json

import requests
from dcos.api import errors, util

try:
    from urllib import urlencode, quote
except ImportError:
    from urllib.parse import urlencode, quote

logger = util.get_logger(__name__)


def create_client(config):
    """Creates a Marathon client with the supplied configuration.

    :param config: Configuration dictionary
    :type config: config.Toml
    :returns: Marathon client
    :rtype: dcos.api.marathon.Client
    """
    return Client(config['marathon.host'], config['marathon.port'])


class Client(object):
    """Class for talking to the Marathon server.

    :param host: Host for the Marathon server.
    :type host: str
    :param port: Port for the Marathon server.
    :type port: int
    """

    def __init__(self, host, port):
        self._url_pattern = "http://{host}:{port}/{path}"
        self._host = host
        self._port = port

    def _create_url(self, path, query_params=None):
        """Creates the url from the provided path

        :param path: Url path
        :type path: str
        :param query_params: Query string parameters
        :type query_params: dict
        :returns: Constructed url
        :rtype: str
        """

        url = self._url_pattern.format(
            host=self._host,
            port=self._port,
            path=path)

        if query_params is not None:
            query_string = urlencode(query_params)
            url = (url + '?{}').format(query_string)

        return url

    def _sanitize_app_id(self, app_id):
        """
        :param app_id: Raw application ID
        :type app_id: str
        :returns: Sanitized application ID
        :rtype: str
        """

        return quote('/' + app_id.strip('/'))

    def _response_to_error(self, response):
        """
        :param response: HTTP resonse object
        :type response: requests.Response
        :returns: The error embedded in the response JSON
        :rtype: Error
        """

        message = response.json().get('message')
        if message is None:
            logger.error(
                'Marathon server did not return a message: %s',
                response.json())
            return Error('Unknown error from Marathon')

        return Error('Error: {}'.format(response.json()['message']))

    def get_app(self, app_id, version=None):
        """Returns a representation of the requested application version. If
        version is None the return the latest version.

        :param app_id: The ID of the application
        :type app_id: str
        :param version: Application version as a ISO8601 datetime
        :type version: str
        :returns: The requested Marathon application
        :rtype: (dict, Error)
        """

        app_id = self._sanitize_app_id(app_id)
        if version is None:
            url = self._create_url('v2/apps{}'.format(app_id))
        else:
            url = self._create_url(
                'v2/apps{}/versions/{}'.format(app_id, version))

        logger.info('Getting %r', url)

        response = requests.get(url)

        logger.info('Got (%r): %r', response.status_code, response.json())

        if response.status_code == 200:
            # Looks like Marathon return different JSON for versions
            if version is None:
                return (response.json()['app'], None)
            else:
                return (response.json(), None)
        else:
            return (None, self._response_to_error(response))

    def get_app_versions(self, app_id, max_count=None):
        """Asks Marathon for all the versions of the Application up to a
        maximum count.

        :param app_id: The ID of the application
        :type app_id: str
        :param max_count: The maximum number of version to fetch
        :type max_count: int
        :returns: A list of all the version of the application
        :rtype: (list of str, Error)
        """

        app_id = self._sanitize_app_id(app_id)

        url = self._create_url('v2/apps{}/versions'.format(app_id))

        logger.info('Getting %r', url)

        response = requests.get(url)

        logger.info('Got (%r): %r', response.status_code, response.json())

        if response.status_code == 200:
            if max_count is None:
                return (response.json()['versions'], None)
            else:
                return (response.json()['versions'][:max_count], None)
        else:
            return (None, self._response_to_error(response))

    def get_apps(self):
        """Get a list of known applications.

        :returns: List of known applications.
        :rtype: (list of dict, Error)
        """

        url = self._create_url('v2/apps')
        response = requests.get(url)

        if response.status_code == 200:
            apps = response.json()['apps']
            return (apps, None)
        else:
            return (None, self._response_to_error(response))

    def add_app(self, app_resource):
        """Add a new application.

        :param app_resource: Application resource
        :type app_resource: dict, bytes or file
        :returns: Status of trying to start the application
        :rtype: Error
        """

        url = self._create_url('v2/apps')

        # The file type exists only in Python 2, preventing type(...) is file.
        if hasattr(app_resource, 'read'):
            app_json = json.load(app_resource)
        else:
            app_json = app_resource

        logger.info("Posting %r to %r", app_json, url)
        response = requests.post(url, json=app_json)

        if response.status_code == 201:
            return None
        else:
            return self._response_to_error(response)

    def scale_app(self, app_id, instances, force=None):
        """Scales an application to the requested number of instances.

        :param app_id: The ID of the application to scale.
        :type app_id: str
        :param instances: The requested number of instances.
        :type instances: int
        :param force: Whether to override running deployments.
        :type force: bool
        :returns: The resulting deployment ID.
        :rtype: (bool, Error)
        """

        if force is None:
            force = False

        app_id = self._sanitize_app_id(app_id)

        params = None
        if force:
            params = {'force': True}

        url = self._create_url('v2/apps{}'.format(app_id), params)
        response = requests.put(url, json={'instances': int(instances)})

        if response.status_code == 200:
            deployment = response.json()['deploymentId']
            return (deployment, None)
        else:
            return (None, self._response_to_error(response))

    def suspend_app(self, app_id, force=None):
        """Scales an application to zero instances.

        :param app_id: The ID of the application to suspend.
        :type app_id: str
        :param force: Whether to override running deployments.
        :type force: bool
        :returns: The resulting deployment ID.
        :rtype: (bool, Error)
        """

        return self.scale_app(app_id, 0, force)

    def remove_app(self, app_id, force=None):
        """Completely removes the requested application.

        :param app_id: The ID of the application to suspend.
        :type app_id: str
        :param force: Whether to override running deployments.
        :type force: bool
        :returns: Error if it failed to remove the app; None otherwise.
        :rtype: Error
        """

        if force is None:
            force = False

        app_id = self._sanitize_app_id(app_id)

        params = None
        if force:
            params = {'force': True}

        url = self._create_url('v2/apps{}'.format(app_id), params)
        response = requests.delete(url)

        if response.status_code == 200:
            return None
        else:
            return self._response_to_error(response)


class Error(errors.Error):
    """ Class for describing erros while talking to the Marathon server.

    :param message: Error message
    :type message: str
    """

    def __init__(self, message):
        self._message = message

    def error(self):
        """Return error message

        :returns: The error message
        :rtype: str
        """

        return self._message
