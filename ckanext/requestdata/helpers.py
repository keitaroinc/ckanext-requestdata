import timeago
import datetime
import itertools
from operator import itemgetter
import json

from paste.deploy.converters import asbool

from ckan import model, logic
from ckan.common import c, _, request, config
from ckan.lib import base
from ckan.plugins import toolkit
from ckan.model.user import User
from ckan.lib.helpers import check_access as helper_check_access
from ckanext.requestdata.utils import is_allowed_public_view, looks_like_ckan_id

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError


def _get_context():
    return {
        'model': model,
        'session': model.Session,
        'user': c.user or c.author,
        'auth_user_obj': c.userobj
    }


def _get_action(action, data_dict):
    return toolkit.get_action(action)(_get_context(), data_dict)


def time_ago_from_datetime(date):
    '''Returns a 'time ago' string from an instance of datetime or datetime
    formated string.

    Example: 2 hours ago

    :param date: The parameter which will be formated.
    :type idate: datetime or string

    :rtype: string

    '''

    now = datetime.datetime.now()

    if isinstance(date, datetime.date):
        date = date.strftime("%Y-%m-%d %H:%M:%S")
    elif isinstance(date, str):
        date = date[:-7]

    return timeago.format(date, now)


def get_package_title(package_id):
    try:
        package = _get_action('package_show', {'id': package_id})
    except NotAuthorized:
        base.abort(403, _('Not authorized to see this package.'))
    except NotFound:
        base.abort(403, _('Package not found.'))

    return package['title']


def get_notification():
    '''Returns a boolean which indicates if notification was seen or not

      :rtype: bool

      '''

    notification = _get_action('requestdata_notification_for_current_user', {})
    return notification


def get_request_counters(id):
    '''
        Returns a counters for particular request data

       :param package_id: The id of the package the request belongs to.
       :type package_id: string

     '''

    package_id = id
    data_dict = {'package_id': package_id}
    counters = _get_action('requestdata_request_data_counters_get', data_dict)
    return counters


def convert_id_to_email(ids):
    ids = ids.split(',')
    emails = []

    for id in ids:
        user = User.get(id)

        if user:
            emails.append(user.email)
        else:
            emails.append(id)

    return ','.join(emails)


def group_archived_requests_by_dataset(requests):
    sorted_requests = sorted(requests, key=itemgetter('package_id'))
    grouped_requests = []

    for key, group in itertools.groupby(sorted_requests,
                                        key=lambda x: x['package_id']):

        requests = list(group)
        item_shared = requests[0].get('shared')
        item_requests = requests[0].get('requests')

        data = {
            'package_id': key,
            'title': requests[0].get('title'),
            'maintainers': requests[0].get('maintainers'),
            'requests_archived': requests,
            'shared': item_shared,
            'requests': item_requests
        }

        grouped_requests.append(data)

    return grouped_requests


def has_query_param(param):
    # Checks if the provided parameter is part of the current URL query params

    params = request.args

    if param in params:
        return True

    return False


def convert_str_to_json(data):
    try:
        return json.loads(data)
    except Exception:
        return _('string cannot be parsed')


def is_hdx_portal():
    return asbool(config.get('hdx_portal', False))


def is_current_user_a_maintainer(maintainers):
    if c.user:
        current_user = _get_action('user_show', {'id': c.user})
        user_id = current_user.get('id')
        user_name = current_user.get('name')

        if user_id in maintainers or user_name in maintainers:
            return True

    return False


def get_orgs_for_user(user_id):
    try:
        orgs = _get_action('organization_list_for_user', {'id': user_id})

        return orgs
    except Exception:
        return []


def role_in_org(user_id, org_name):
    try:
        org = _get_action('organization_show', {'id': org_name})
    except NotFound:
        return ''

    for user in org.get('users', []):
        if user.get('id') == user_id:
            return user.get('capacity')


def check_ckan_version(min_version=None, max_version=None):
    return toolkit.check_ckan_version(min_version, max_version)

def enable_visibility():
    """Check whether to enable the visibility dropdown in dataset/new.

    The default is to disable. This value is controlled by the CKAN configuration value
    ``ckanext.requestdata.enable_visibility``.

    Returns ``True`` if visibility is enabled in the configuration, otherwise ``False``.
    """
    visibility = config.get('ckanext.requestdata.enable_visibility', False)
    if not visibility:
        return False
    if isinstance(visibility, str):
        return visibility.lower() in ['true', 'yes', 't', '1']
    return False


def requestdata_check_access(action, data_dict, allow_public_if_set=False):
    if allow_public_if_set and is_allowed_public_view():
        return True
    return helper_check_access(action, data_dict)


def is_allowed_to_take_actions(user, organization):
    if not user:
        return False
    context = {'ignore_auth': True}
    try:
        user = toolkit.get_action('user_show')(context, {'id': user})
        if user.get('sysadmin'):
           return True
    except toolkit.NotFound:
        return False
    
    user_orgs = toolkit.get_action('organization_list_for_user')(context, {
        'id': user['id'],
        'permission': 'admin',
    })
    
    if user_orgs:
        for org in user_orgs:
            if looks_like_ckan_id(organization) and organization == org['id']:
                return True
            elif organization == org['name']:
                return True

    return False