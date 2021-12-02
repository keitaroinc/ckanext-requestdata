import six

from ckan.plugins import toolkit

from ckanext.requestdata.logic import validators


not_missing = toolkit.get_validator('not_missing')
not_empty = toolkit.get_validator('not_empty')
package_id_exists = toolkit.get_validator('package_id_exists')
email_validator = validators.email_validator
state_validator = validators.state_validator
boolean_validator = validators.boolean_validator
counters_validator = validators.request_counter_validator


def request_create_schema():
    return {
        'sender_name': [not_empty, six.text_type],
        'email_address': [not_empty, email_validator],
        'message_content': [not_empty, six.text_type],
        'package_id': [not_empty, package_id_exists]
    }


def request_show_schema():
    return {
        'id': [not_empty, six.text_type],
        'package_id': [not_empty, package_id_exists]
    }


def request_patch_schema():
    return {
        'id': [not_empty, six.text_type],
        'package_id': [not_empty, package_id_exists, six.text_type],
        'state': [state_validator],
        'data_shared': [boolean_validator],
        'rejected': [boolean_validator]
    }


def request_list_for_organization_schema():
    return {
        'org_id': [not_empty]
    }


def notification_create_schema():
    return {
        'users': [not_empty]
    }


def notification_change_schema():
    return{
        'user_id': [not_empty, six.text_type]
    }


def increment_request_counters_schema():
    return{
        'package_id': [not_empty],
        'flag': [counters_validator]
    }
