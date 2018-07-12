import re
from pylons import config
from ckan import logic, model
from ckan.plugins import toolkit
from ckan.common import c


def match_uuidv4(val):
    return re.match('^[a-f0-9]{8}-?[a-f0-9]{4}-?4[a-f0-9]{3}-?[89ab][a-f0-9]{3}-?[a-f0-9]{12}\Z', val, re.I) is not None


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


def _user_show_override(user_show):
    def _user_show(context, data_dict):
        if data_dict.get('id'):
            print ' -> user_show: id=', data_dict['id']
            if looks_like_an_email(data_dict['id']):
                print ' -> looks like an email'
                user = model.User.by_email(data_dict['id'])
                print ' -> got user: ', user
                if user:
                    if type(user) == list:
                        user = user[0]
                    data_dict['id'] = user.id
            else:
                print ' -> doe NOT look like an email'
        print ' -> pass to CKAN user show: ', data_dict
        user_dict = user_show(context, data_dict)
        print user_dict
        return user_dict

    return _user_show



def get_action(action, data_dict):
    if action == 'user_show':
        # special handling for user_show to enable search by email as well
        user_show = toolkit.get_action('user_show')
        return _user_show_override(user_show)(_get_context(), data_dict)
    return toolkit.get_action(action)(_get_context(), data_dict)
