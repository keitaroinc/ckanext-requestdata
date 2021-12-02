import six

import ckan.plugins as plugins
import ckan.plugins.toolkit as toolkit
from ckan.logic import get_action, auth_allow_anonymous_access

from ckanext.requestdata.model import setup as model_setup
from ckanext.requestdata.logic import actions
from ckanext.requestdata.logic import auth
from ckanext.requestdata import helpers
from ckanext.requestdata.logic import validators
from ckan.lib.plugins import DefaultTranslation
from ckan.lib import helpers as core_helpers

import ckanext.requestdata.utils as utils
import ckanext.requestdata.views.user as user_blueprint
import ckanext.requestdata.views.dataset as dataset_blueprint
import ckanext.requestdata.views.request_data as request_data_blueprint
import ckanext.requestdata.views.admin as admin_blueprint


class RequestdataPlugin(plugins.SingletonPlugin, toolkit.DefaultDatasetForm,
                        DefaultTranslation):
    plugins.implements(plugins.IConfigurer)
    # plugins.implements(plugins.IRoutes, inherit=True)
    plugins.implements(plugins.IConfigurable)
    plugins.implements(plugins.IActions)
    plugins.implements(plugins.IAuthFunctions)
    plugins.implements(plugins.ITemplateHelpers)
    plugins.implements(plugins.IDatasetForm)
    plugins.implements(plugins.IPackageController, inherit=True)
    plugins.implements(plugins.ITranslation)
    plugins.implements(plugins.IBlueprint)

    # IConfigurer

    def update_config(self, config_):
        toolkit.add_template_directory(config_, 'templates')
        toolkit.add_public_directory(config_, 'public')
        toolkit.add_resource('fanstatic', 'requestdata')

    def update_config_schema(self, schema):
        ignore_missing = toolkit.get_validator('ignore_missing')

        email_body = {}
        email_body.update({'email_header': [ignore_missing, six.text_type],
                           'email_body': [ignore_missing, six.text_type],
                           'email_footer': [ignore_missing, six.text_type]})

        schema.update(email_body)

        return schema

    # IRoutes

    def before_map(self, map):

        package_controller =\
            'ckanext.requestdata.controllers.package:PackageController'
        user_controller =\
            'ckanext.requestdata.controllers.user:UserController'
        request_data_controller = 'ckanext.requestdata.controllers.'\
            'request_data:RequestDataController'
        admin_controller = \
            'ckanext.requestdata.controllers.admin:AdminController'
        organization_controller = 'ckanext.requestdata.controllers.'\
            'organization:OrganizationController'
        search_controller =\
            'ckanext.requestdata.controllers.search:SearchController'

        map.connect('/dataset/new',
                    controller=package_controller,
                    action='create_metadata_package')

        map.connect('requestdata_my_requests',
                    '/user/my_requested_data/{id}',
                    controller=user_controller,
                    action='my_requested_data', ckan_icon='list')

        map.connect('requestdata_handle_new_request_action',
                    '/user/my_requested_data/{username}/' +
                    '{request_action:reply|reject}',
                    controller=user_controller,
                    action='handle_new_request_action')

        map.connect('requestdata_handle_open_request_action',
                    '/user/my_requested_data/{username}/' +
                    '{request_action:shared|notshared}',
                    controller=user_controller,
                    action='handle_open_request_action')

        map.connect('requestdata_send_request', '/request_data',
                    controller=request_data_controller,
                    action='send_request')

        map.connect('requestdata_read_data_request',
                    '/request_data/dataset/{package_id}/request/{request_id}',
                    controller=request_data_controller,
                    action='read_request')

        is_ckan_greater_than_27 = helpers.check_ckan_version(min_version='2.7')
        if is_ckan_greater_than_27:
            envelope_icon = 'envelope-o'
        else:
            envelope_icon = 'envelope-alt'
        map.connect('ckanadmin_email', '/ckan-admin/email',
                    controller=admin_controller,
                    action='email', ckan_icon=envelope_icon)

        map.connect('ckanadmin_requests_data', '/ckan-admin/requests_data',
                    controller=admin_controller,
                    action='requests_data', ckan_icon='list')

        map.connect('download_requests_data',
                    '/ckan-admin/requests_data/download',
                    controller=admin_controller,
                    action='download_requests_data')

        map.connect('requestdata_organization_requests',
                    '/organization/requested_data/{id}',
                    controller=organization_controller,
                    action='requested_data', ckan_icon='list')

        map.connect('simple_search', '/dataset', controller=search_controller,
                    action='search_datasets')

        map.connect('search', '/search', controller=search_controller,
                    action='search_datasets')

        return map

    # IConfigurable

    def configure(self, config):

        # Setup requestdata model
        model_setup()

    # IActions

    def get_actions(self):
        package_create = get_action('package_create')
        package_update = get_action('package_update')
        package_show = get_action('package_show')
        user_show = get_action('user_show')
        return {
            'requestdata_request_create': actions.request_create,
            'requestdata_request_show': actions.request_show,
            'requestdata_request_list_for_current_user':
            actions.request_list_for_current_user,
            'requestdata_request_list_for_organization':
            actions.request_list_for_organization,
            'requestdata_request_list_for_sysadmin':
            actions.request_list_for_sysadmin,
            'requestdata_request_patch': actions.request_patch,
            'requestdata_request_update': actions.request_update,
            'requestdata_request_delete': actions.request_delete,
            'requestdata_notification_create': actions.notification_create,
            'requestdata_notification_for_current_user':
            actions.notification_for_current_user,
            'requestdata_notification_change': actions.notification_change,
            'requestdata_increment_request_data_counters':
            actions.increment_request_data_counters,
            'requestdata_request_data_counters_get':
            actions.request_data_counters_get,
            'requestdata_request_data_counters_get_all':
            actions.request_data_counters_get_all,
            'requestdata_request_data_counters_get_by_org':
            actions.request_data_counters_get_by_org,
            # 'package_create':
            # get_package_action_override(package_create, validate_request_for_metadata),
            # 'package_update':
            # get_package_action_override(package_update, validate_request_for_metadata),
            'package_show':
            package_show_override(package_show),
            'user_show': actions.user_show_override(user_show)
        }

    # IAuthFunctions

    def get_auth_functions(self):
        requestdata_request_list_for_organization = auth.request_list_for_organization
        requestdata_request_show = auth.request_show
        if utils.is_allowed_public_view():
            requestdata_request_list_for_organization = auth_allow_anonymous_access(requestdata_request_list_for_organization)
            requestdata_request_show = auth_allow_anonymous_access(requestdata_request_show)

        return {
            'requestdata_request_create': auth.request_create,
            'requestdata_request_show': requestdata_request_show,
            'requestdata_request_list_for_current_user':
            auth.request_list_for_current_user,
            'requestdata_request_list_for_organization':
            requestdata_request_list_for_organization,
            'requestdata_request_list_for_organization_update':
            auth.requestdata_request_list_for_organization_update,
            'requestdata_request_patch': auth.request_patch,
            'requestdata_request_list_for_sysadmin':
            auth.request_list_for_sysadmin
        }

    # ITemplateHelpers

    def get_helpers(self):
        return {
            'requestdata_time_ago_from_datetime':
                helpers.time_ago_from_datetime,
            'requestdata_get_package_title':
                helpers.get_package_title,
            'requestdata_get_notification':
                helpers.get_notification,
            'requestdata_get_request_counters':
                helpers.get_request_counters,
            'requestdata_convert_id_to_email':
                helpers.convert_id_to_email,
            'requestdata_has_query_param':
                helpers.has_query_param,
            'requestdata_convert_str_to_json': helpers.convert_str_to_json,
            'requestdata_is_hdx_portal':
                helpers.is_hdx_portal,
            'requestdata_is_current_user_a_maintainer':
                helpers.is_current_user_a_maintainer,
            'requestdata_get_orgs_for_user':
                helpers.get_orgs_for_user,
            'requestdata_role_in_org':
                helpers.role_in_org,
            'requestdata_check_ckan_version':
                helpers.check_ckan_version,
            'requestdata_enable_visibility':
                helpers.enable_visibility,
            'requestdata_check_access':
                helpers.requestdata_check_access,
            'requestdata_is_allowed_to_take_actions':
                helpers.is_allowed_to_take_actions,
        }

    # IDatasetForm

    def _modify_package_schema(self, schema):
        not_empty = toolkit.get_validator('not_empty')
        convert_to_extras = toolkit.get_converter('convert_to_extras')
        members_in_org_validator = validators.members_in_org_validator

        schema.update({
            'maintainer': [not_empty, members_in_org_validator,
                           convert_to_extras]
        })

        return schema

    def create_package_schema(self):
        schema = super(RequestdataPlugin, self).create_package_schema()
        schema = self._modify_package_schema(schema)

        return schema

    def update_package_schema(self):
        schema = super(RequestdataPlugin, self).update_package_schema()
        schema = self._modify_package_schema(schema)

        return schema

    def show_package_schema(self):
        schema = super(RequestdataPlugin, self).show_package_schema()
        not_empty = toolkit.get_validator('not_empty')
        convert_from_extras = toolkit.get_converter('convert_from_extras')

        schema.update({
            'maintainer': [not_empty, convert_from_extras]
        })

        return schema

    def is_fallback(self):
        # Return True to register this plugin as the default handler for
        # package types not handled by any other IDatasetForm plugin.
        return False

    def package_types(self):
        return ['requestdata-metadata-only']

    # IPackageController

    def before_search(self, search_params):
        fq = search_params.get('fq', '')

        if 'dataset_type:dataset' in fq:
            fq = fq.replace('dataset_type:dataset',
                            'dataset_type: (dataset OR '
                            'requestdata-metadata-only)')
            search_params.update({'fq': fq})

        return search_params

    # IBlueprint

    def get_blueprint(self):
        return user_blueprint.get_blueprints() + \
               dataset_blueprint.get_blueprints() + \
               request_data_blueprint.get_blueprints() + \
               admin_blueprint.get_blueprints()


def package_show_override(package_show):
    def _package_show(context, data_dict):
        result = package_show(context, data_dict)
        result['title'] = core_helpers.dataset_display_name(result)
        result['notes'] = core_helpers.get_translated(result, 'notes')
        from ckan.views.admin import _get_sysadmins
        sysadmins = [a.name for a in _get_sysadmins()]
        sysadmin = sysadmins[0]
        sysadmin_context = {'user': sysadmin, 'ignore_auth': True}

        maintainer_field_name = utils.get_maintainer_field_name()
        if result.get(maintainer_field_name):
            maintainers = result[maintainer_field_name]

            maintainer_emails = []

            for maintainer_email in maintainers.split(','):
                maintainer_email = maintainer_email.strip()
                if utils.looks_like_ckan_id(maintainer_email):
                    try:
                        user = get_action('user_show')(sysadmin_context, {'id': maintainer_email})
                        maintainer_email = user['email']
                    except:
                        raise
                maintainer_emails.append(maintainer_email)

            result[maintainer_field_name] = ','.join(maintainer_emails)

        return result

    return _package_show
