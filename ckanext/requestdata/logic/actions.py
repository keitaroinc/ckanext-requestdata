import datetime

from ckan.plugins import toolkit
from ckan.logic import check_access, NotFound
import ckan.lib.navl.dictization_functions as df
from ckan.model.user import User
from ckanext.requestdata.logic import schema
from ckanext.requestdata.model import ckanextRequestdata,\
    ckanextUserNotification, ckanextMaintainers, ckanextRequestDataCounters
from ckanext.requestdata import helpers
from ckanext.requestdata import utils


def request_create(context, data_dict):
    '''Create new request data.

    :param sender_name: The name of the sender who request data.
    :type sender_name: string

    :param organization: The sender's organization.
    :type organization: string

    :param email_address: The sender's email_address.
    :type email_address: string

    :param message_content: The content of the message.
    :type message_content: string

    :param package_id: The id of the package the data belongs to.
    :type package_id: string

    :returns: the newly created request data
    :rtype: dictionary

    '''

    check_access('requestdata_request_create', context, data_dict)

    data, errors = df.validate(data_dict, schema.request_create_schema(),
                               context)

    if errors:
        print(errors)
        raise toolkit.ValidationError(errors)

    maintainer_field_name = utils.get_maintainer_field_name()
    sender_name = data.get('sender_name')
    organization = data.get('organization')
    email_address = data.get('email_address')
    message_content = data.get('message_content')
    package_id = data.get('package_id')

    package = toolkit.get_action('package_show')(context, {'id': package_id})

    sender_user_id = User.get(context['user']).id

    maintainers = package[maintainer_field_name].split(',')

    data = {
        'sender_name': sender_name,
        'sender_user_id': sender_user_id,
        'organization': organization,
        'email_address': email_address,
        'message_content': message_content,
        'package_id': package_id
    }

    requestdata = ckanextRequestdata(**data)
    requestdata.save()
    maintainers_list = []
    is_hdx = helpers.is_hdx_portal()

    for id in maintainers:
        try:
            if is_hdx:
                main_ids = toolkit.get_action('user_show')(context, {'id': id})
                user = User.get(main_ids['id'])
            else:
                if utils.looks_like_an_email(id):
                    user = User.by_email(id)
                    if isinstance(user, list):
                        user = user[0]
                else:
                    user = User.get(id)
            data = ckanextMaintainers()
            data.request_data_id = requestdata.id
            if user:
                data.email = user.email
                data.maintainer_id = user.id
            else:
                data.email = id
                data.maintainer_id = id
            maintainers_list.append(data)
        except NotFound:
            data = ckanextMaintainers()
            data.maintainer_id = id
            data.email = id
            maintainers_list.append(data)

    out = ckanextMaintainers.insert_all(maintainers_list, requestdata.id)

    return out


@toolkit.side_effect_free
def request_show(context, data_dict):
    '''Return the metadata of a requestdata.

    :param id: The id of a requestdata.
    :type id: string

    :rtype: dictionary

    '''

    data, errors = df.validate(data_dict, schema.request_show_schema(),
                               context)

    if errors:
        raise toolkit.ValidationError(errors)

    check_access('requestdata_request_show', context, data_dict)

    id = data.get('id')

    requestdata = ckanextRequestdata.get(id=id)

    if requestdata is None:
        raise NotFound(toolkit._('Request with provided \'id\' cannot be found'))

    out = requestdata.as_dict()

    return out


@toolkit.side_effect_free
def request_list_for_sysadmin(context, data_dict):
    '''Returns a list of all requests.

    :rtype: list of dictionaries

    '''

    check_access('requestdata_request_list_for_sysadmin',
                 context, data_dict)

    requests = ckanextRequestdata.search()

    out = []

    for item in requests:
        out.append(item.as_dict())

    return out


@toolkit.side_effect_free
def request_list_for_organization(context, data_dict):
    '''Returns a list of requests for specified organization.

    :param org_id: The organization id.
    :type org_id: string

    :rtype: list of dictionaries

    '''

    data, errors = df.validate(data_dict,
                               schema.request_list_for_organization_schema(),
                               context)

    if errors:
        raise toolkit.ValidationError(errors)

    check_access('requestdata_request_list_for_organization',
                 context, data_dict)

    org_id = data.get('org_id')
    org = toolkit.get_action('organization_show')(context, {'id': org_id})

    data_dict = {
        'fq': 'organization:' + org['name'],
        'rows': 1000000,
        'include_private': True
    }

    packages = toolkit.get_action('package_search')(context, data_dict)
    total_requests = []
    for package in packages['results']:
        data = {
            'package_id': package['id']
        }
        requests = ckanextRequestdata.search(**data)
        for item in requests:
            total_requests.append(item.as_dict())

    return total_requests


@toolkit.side_effect_free
def request_list_for_current_user(context, data_dict):
    '''Returns a list of requests.

    :param id: The id of a requestdata.
    :type id: string

    :rtype: list of dictionaries

    '''

    check_access('requestdata_request_list_for_current_user',
                 context, data_dict)

    model = context['model']
    user_id = model.User.get(context['user']).id

    requests = ckanextRequestdata.search_by_maintainers(user_id)
    out = []

    for item in requests:
        out.append(item)

    return out


def request_patch(context, data_dict):
    '''Patch a request.

    :param id: The id of a request.
    :type id: string

    :returns: A patched request
    :rtype: dictionary

    '''

    request_patch_schema = schema.request_patch_schema()
    fields = request_patch_schema.keys()

    # Exclude fields from the schema that are not in data_dict
    for field in fields:
        if field not in data_dict.keys() and\
           (field != 'id' and field != 'package_id'):
            request_patch_schema.pop(field)

    data, errors = df.validate(data_dict, request_patch_schema, context)

    if errors:
        raise toolkit.ValidationError(errors)

    check_access('requestdata_request_patch', context, data_dict)

    id = data.get('id')
    package_id = data.get('package_id')

    payload = {
        'id': id,
        'package_id': package_id
    }

    request = ckanextRequestdata.get(**payload)

    if request is None:
        raise NotFound

    request_patch_schema.pop('id')
    request_patch_schema.pop('package_id')

    fields = request_patch_schema.keys()

    for field in fields:
        setattr(request, field, data.get(field))

    request.modified_at = datetime.datetime.now()

    request.save()

    out = request.as_dict()

    return out


def request_update(self):
    pass


def request_delete(self):
    pass


def notification_create(context, data_dict):
    '''Create new notification data.

    :param package_id: The id of the package the data belongs to.
    :type package_id: string

    :returns: the newly created notification data
    :rtype: dictionary

    '''
    not_seen = False
    notifications = []
    maintainers = data_dict['users']
    for m in maintainers:
        data = {
            'package_maintainer_id': m['id'],
            'seen': not_seen
        }
        user_notification = ckanextUserNotification(**data)
        user_exist = ckanextUserNotification.get(package_maintainer_id=m['id'])
        if user_exist is None:
            user_notification.save()
            notifications.append(user_notification)
        else:
            user_exist.seen = not_seen
            user_exist.commit()
            notifications.append(user_exist)
    return notifications


@toolkit.side_effect_free
def notification_for_current_user(context, data_dict):
    '''Returns a notification for logged in user

    :rtype: boolean

    '''

    model = context['model']
    user_id = model.User.get(context['user']).id
    notification = ckanextUserNotification.get(package_maintainer_id=user_id)
    if notification is None:
        # do not display notification
        return True
    else:
        is_notified = notification.seen
        return is_notified


@toolkit.side_effect_free
def notification_change(context, data_dict):
    '''
        Change the notification status to seen
    :param context:

    :param user_id: The id of logged in user
    :type String

    :return:
    '''

    data, errors = df.validate(data_dict,
                               schema.notification_change_schema(),
                               context)
    if errors:
        raise toolkit.ValidationError(errors)

    user_id = data.get('user_id')
    notification = ckanextUserNotification.get(package_maintainer_id=user_id)
    if notification is not None:
        notification.seen = True
        notification.commit()
        return notification


def increment_request_data_counters(context, data_dict):
    '''
       Increment the counter for the requested data depending on the flag

       :param package_id: The id of the package the data belongs to.
       :type package_id: string

       :param flag: The flag that indicates which counter to increment
       :type String

       :return:
     '''
    data, errors = df.validate(data_dict,
                               schema.increment_request_counters_schema(),
                               context)
    if errors:
        raise toolkit.ValidationError(errors)

    flag = data.get('flag')
    package_id = data.get('package_id')
    package = toolkit.get_action('package_show')(context, {'id': package_id})
    data = {
        'package_id': package_id,
        'org_id': package['owner_org']
    }

    data_request = ckanextRequestDataCounters.get(package_id=package_id)
    if data_request is None:
        new_request = ckanextRequestDataCounters(**data)
        new_request.requests = 1
        new_request.save()
        return new_request
    else:
        if flag == 'request':
            data_request.requests += 1
        elif flag == 'replied':
            data_request.replied += 1
        elif flag == 'declined':
            data_request.declined += 1
        elif flag == 'shared':
            data_request.shared += 1
        elif flag == 'shared and replied':
            data_request.shared += 1
            data_request.replied += 1

        data_request.save()
        return data_request


@toolkit.side_effect_free
def request_data_counters_get(context, data_dict):
    '''
        Returns a counters for particular request data

       :param package_id: The id of the package the request belongs to.
       :type package_id: string

     '''

    package_id = data_dict['package_id']
    counters = ckanextRequestDataCounters.get(package_id=package_id)
    return counters


@toolkit.side_effect_free
def request_data_counters_get_all(context, data_dict):
    '''
        Returns a counters for particular request data

       :param package_id: The id of the package the request belongs to.
       :type package_id: string

     '''

    counters = ckanextRequestDataCounters.search()
    return counters


@toolkit.side_effect_free
def request_data_counters_get_by_org(context, data_dict):
    '''
        Return counters for requests that belong to particular organization

       :param org_id: The id of the organizatiion the request belongs to.
       :type org_id: string

     '''

    data = {'org_id': data_dict['org_id']}

    counters = ckanextRequestDataCounters.search_by_organization(**data)

    return counters


def user_show_override(user_show):
    def _user_show(context, data_dict):
        if data_dict.get('id'):
            if utils.looks_like_an_email(data_dict['id']):
                user = User.by_email(data_dict['id'])
                if user:
                    if isinstance(user, list):
                        user = user[0]
                    data_dict['id'] = user.id
        user_dict = user_show(context, data_dict)
        return user_dict

    return _user_show
