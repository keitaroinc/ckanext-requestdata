import re
from ckan import model
from ckan.plugins import toolkit
from ckan.common import c

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config


def match_uuidv4(val):
    return re.match(r'^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', val, re.I) is not None


def looks_like_ckan_id(val):
    # CKAN id's are UUIDv4 values
    return match_uuidv4(val)


def looks_like_an_email(val):
    # very basic check - one "@" and at least one dot after it.
    return re.match('^[^@]+@[^@]+\\.[^@]+', val, re.I) is not None


def get_maintainer_field_name():
    return config.get('ckanext.requestdata.maintainer_field', 'maintainer')


def _get_context():
    return {
        'model': model,
        'session': model.Session,
        'user': c.user or c.author,
        'auth_user_obj': c.userobj
    }


def get_action(action, data_dict):
    return toolkit.get_action(action)(_get_context(), data_dict)


def use_standard_package_type():
    return _parse_bool(config.get('ckanext.requestdata.use_standard_package_type', 'false'))


def _parse_bool(val):
    if not val:
        return False
    return str(val).lower() in ("yes", "true", "t", "1")