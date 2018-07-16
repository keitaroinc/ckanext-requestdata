from ckan.plugins.toolkit import _
from ckan.plugins.toolkit import get_action
from ckan import logic
from ckanext.requestdata import utils


def request_create(context, data_dict):
    user = context['user']

    if user:
        return {'success': True}
    else:
        message = _('Only registered users can request data.')

        return {'success': False, 'msg': message}


def request_show(context, data_dict):
    if utils.is_allowed_public_view():
        return {'success': True}
    if _user_has_access_to_request(context, data_dict):
        return {'success': True}
    else:
        message = _('You don\'t have access to this request data.')

        return {'success': False, 'msg': message}


def request_list_for_current_user(context, data_dict):
    return {'success': True}


def request_list_for_organization(context, data_dict):
    if utils.is_allowed_public_view():
        return {'success': True}
    current_user_id = context['auth_user_obj'].id

    payload = {'id': data_dict['org_id']}

    try:
        organization = get_action('organization_show')(context, payload)
    except logic.NotFound:
        raise logic.ValidationError(_('Organization not found.'))

    for user in organization['users']:

        # Checks whether the current logged in user is admin on the
        # organization
        if user['id'] == current_user_id and user['capacity'] == 'admin':
            return {'success': True}

    return {'success': False}


def requestdata_request_list_for_organization_update(context, data_dict):
    current_user_id = context['auth_user_obj'].id

    payload = {'id': data_dict['org_id']}

    try:
        organization = get_action('organization_show')(context, payload)
    except logic.NotFound:
        raise logic.ValidationError(_('Organization not found.'))

    for user in organization['users']:

        # Checks whether the current logged in user is admin on the
        # organization
        if user['id'] == current_user_id and user['capacity'] == 'admin':
            return {'success': True}

    return {'success': False}


def request_patch(context, data_dict):
    if _user_has_access_to_request(context, data_dict):
        return {'success': True}
    else:
        message = _('You don\'t have access to this request data.')

        return {'success': False, 'msg': message}


def request_list_for_sysadmin(context, data_dict):
    model = context['model']
    user = model.User.get(context['user'])
    is_sysadmin = user.sysadmin

    if is_sysadmin:
        return {'success': True}
    else:
        message = _('You don\'t have access to this request data.')

        return {'success': False, 'msg': message}


def _user_has_access_to_request(context, data_dict):
    current_user_id = context['auth_user_obj'].id

    payload = {'id': data_dict['package_id']}
    package = get_action('package_show')(context, payload)
    creator_user_id = package['creator_user_id']

    # Checks whether the current logged in user is the creator of the package
    if current_user_id == creator_user_id:
        return True
    else:
        payload = {'id': package['owner_org']}
        organization = get_action('organization_show')(context, payload)

        for user in organization['users']:

            # Checks whether the current logged in user is admin on the
            # organization that the package belongs to
            if user['id'] == current_user_id and user['capacity'] == 'admin':
                return True

    return False
