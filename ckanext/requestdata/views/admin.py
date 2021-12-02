# encoding: utf-8

import logging
import json
import csv
from io import StringIO
from collections import Counter

from flask import Blueprint, make_response

from ckan.plugins import toolkit
from ckan import model
from ckan.common import c, _, config, request
import ckan.lib.base as base
import ckan.lib.helpers as h
import ckan.logic as logic
from ckan.views.admin import before_request as admin_before_request

from ckanext.requestdata import helpers
import ckanext.requestdata.utils as utils
import ckanext.requestdata.helpers as requestdata_helper


NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
abort = base.abort

log = logging.getLogger(__name__)

admin = Blueprint(u'requestdata_admin', __name__, url_prefix=u'/ckan-admin')


@admin.before_request
def before_request():
    return admin_before_request()


def email():
    '''
        Handles creating the email template in admin dashboard.

        :returns template
    '''
    data = request.form
    if 'save' in data:
        try:
            data_dict = request.form
            del data_dict['save']
            data = utils.get_action('config_option_update', data_dict)
            h.flash_success(_('Successfully updated.'))
        except logic.ValidationError as e:
            errors = e.error_dict
            error_summary = e.error_summary
            vars = {'data': data, 'errors': errors,
                    'error_summary': error_summary}
            return base.render('admin/email.html', extra_vars=vars)

        h.redirect_to('requestdata_admin.email')

    schema = logic.schema.update_configuration_schema()
    data = {}
    for key in schema:
        data[key] = config.get(key)

    vars = {'data': data, 'errors': {}}
    return toolkit.render('admin/email.html', extra_vars=vars)


def requests_data():
    '''
        Handles creating template for 'Requested Data' page in the
        admin dashboard.

        :returns: template

    '''
    try:
        requests = utils.get_action('requestdata_request_list_for_sysadmin', {})
    except NotAuthorized:
        abort(403, _('Not authorized to see this page.'))

    maintainer_field_name = utils.get_maintainer_field_name()
    organizations = []
    tmp_orgs = []
    filtered_maintainers = []
    filtered_organizations = []
    organizations_for_filters = {}
    reverse = True
    q_organizations = []
    request_params = request.args
    order = 'last_request_created_at'

    for item in request_params:
        if item == 'filter_by_maintainers':
            x = request_params[item]
            params = x.split('|')
            org = params[0].split(':')[1]
            maintainers = params[1].split(':')[1].split(',')
            maintainers_ids = []

            if maintainers[0] != '*all*':
                for i in maintainers:
                    try:
                        user = utils.get_action('user_show', {'id': i})
                        maintainers_ids.append(user['id'])
                    except NotFound:
                        pass

                data = {
                    'org': org,
                    'maintainers': maintainers_ids
                }

                filtered_maintainers.append(data)
        elif item == 'filter_by_organizations':
            filtered_organizations = request_params[item].split(',')
        elif item == 'order_by':
            x = request_params[item]
            params = x.split('|')
            q_organization = params[1].split(':')[1]
            order = params[0]

            if 'asc' in order:
                reverse = False
                order = 'title'
                current_order_name = _('Alphabetical (A-Z)')
            elif 'desc' in order:
                reverse = True
                order = 'title'
                current_order_name = _('Alphabetical (Z-A)')
            elif 'most_recent' in order:
                reverse = True
                order = 'last_request_created_at'
                current_order_name = _('Most Recent')
            elif 'shared' in order:
                current_order_name = _('Sharing Rate')
            elif 'requests' in order:
                current_order_name = _('Requests Rate')

            data = {
                'org': q_organization,
                'order': order,
                'reverse': reverse,
                'current_order_name': current_order_name
            }

            q_organizations.append(data)

            for x in requests:
                package = utils.get_action('package_show', {'id': x['package_id']})
                count = utils.get_action('requestdata_request_data_counters_get',
                                         {'package_id': x['package_id']})
                if count:
                    x['shared'] = count.shared
                    x['requests'] = count.requests
                x['title'] = package['title']
                data_dict = {'id': package['owner_org']}
                current_org = utils.get_action('organization_show', data_dict)
                x['name'] = current_org['name']

    # Group requests by organization
    for item in requests:
        try:
            package = \
                utils.get_action('package_show', {'id': item['package_id']})
            package_maintainer_ids = package[maintainer_field_name].split(',')
            data_dict = {'id': package['owner_org']}
            org = utils.get_action('organization_show', data_dict)
            item['title'] = package['title']
        except NotFound as e:
            # package was not found, possibly deleted
            continue

        if org['id'] in organizations_for_filters:
            organizations_for_filters[org['id']]['requests'] += 1
        else:
            organizations_for_filters[org['id']] = {
                'name': org['name'],
                'title': org['title'],
                'requests': 1
            }

        if len(filtered_organizations) > 0\
                and org['name'] not in filtered_organizations:
            continue
        maintainers = []
        name = ''
        username = ''
        for id in package_maintainer_ids:
            try:
                user = utils.get_action('user_show', {'id': id})
                id = user['id']
                username = user['name']
                name = user['fullname'] or user['name']
                payload = {
                    'id': id,
                    'name': name,
                    'username': username,
                    'fullname': name
                }
                maintainers.append(payload)

                if not name:
                    name = username
            except NotFound:
                pass
        item['maintainers'] = maintainers
        counters = utils.get_action('requestdata_request_data_counters_get_by_org',
                                    {'org_id': org['id']})

        if org['id'] not in tmp_orgs:
            data = {
                'title': org['title'],
                'name': org['name'],
                'id': org['id'],
                'requests_new': [],
                'requests_open': [],
                'requests_archive': [],
                'maintainers': [],
                'counters': counters
            }

            if item['state'] == 'new':
                data['requests_new'].append(item)
            elif item['state'] == 'open':
                data['requests_open'].append(item)
            elif item['state'] == 'archive':
                data['requests_archive'].append(item)

            payload = {'id': id, 'name': name, 'username': username}
            data['maintainers'].append(payload)

            organizations.append(data)
        else:
            current_org = \
                next(item for item in organizations
                     if item['id'] == org['id'])

            payload = {'id': id, 'name': name, 'username': username}
            current_org['maintainers'].append(payload)

            if item['state'] == 'new':
                current_org['requests_new'].append(item)
            elif item['state'] == 'open':
                current_org['requests_open'].append(item)
            elif item['state'] == 'archive':
                current_org['requests_archive'].append(item)

        tmp_orgs.append(org['id'])

    for org in organizations:
        copy_of_maintainers = org['maintainers']
        org['maintainers'] = \
            dict((item['id'], item)
                 for item in org['maintainers']).values()

        # Count how many requests each maintainer has
        for main in org['maintainers']:
            c = Counter(item for dct in copy_of_maintainers
                        for item in dct.items())
            main['count'] = c[('id', main['id'])]

        # Sort maintainers by number of requests
        org['maintainers'] = \
            sorted(org['maintainers'],
                   key=lambda k: k['count'],
                   reverse=True)

        total_organizations = \
            org['requests_new'] + \
            org['requests_open'] +\
            org['requests_archive']

        for i, r in enumerate(total_organizations):
            maintainer_found = False

            package = utils.get_action('package_show', {'id': r['package_id']})
            package_maintainer_ids = package[maintainer_field_name].split(',')
            is_hdx = requestdata_helper.is_hdx_portal()

            if is_hdx:
                # Quick fix for hdx portal
                maintainer_ids = []
                for maintainer_name in package_maintainer_ids:
                    try:
                        main_ids = utils.get_action('user_show', {'id': maintainer_name})
                        maintainer_ids.append(main_ids['id'])
                    except NotFound:
                        pass
            data_dict = {'id': package['owner_org']}
            organ = utils.get_action('organization_show', data_dict)

            # Check if current request is part of a filtered maintainer
            for x in filtered_maintainers:
                if x['org'] == organ['name']:
                    for maint in x['maintainers']:
                        if is_hdx:
                            if maint in maintainer_ids:
                                maintainer_found = True
                        else:
                            if maint in package_maintainer_ids:
                                maintainer_found = True

                    if not maintainer_found:
                        if r['state'] == 'new':
                            org['requests_new'].remove(r)
                        elif r['state'] == 'open':
                            org['requests_open'].remove(r)
                        elif r['state'] == 'archive':
                            org['requests_archive'].remove(r)

        org['requests_archive'] = \
            helpers.group_archived_requests_by_dataset(
                org['requests_archive'])

        q_org = [x for x in q_organizations if x.get('org') == org['name']]

        if q_org:
            q_org = q_org[0]
            order = q_org.get('order')
            reverse = q_org.get('reverse')
            current_order_name = q_org.get('current_order_name')
        else:
            order = 'last_request_created_at'
            reverse = True
            current_order_name = _('Most Recent')

        org['current_order_name'] = current_order_name

        if order == 'last_request_created_at':
            for dataset in org['requests_archive']:
                created_at = \
                    dataset.get('requests_archived')[0].get('created_at')
                data = {
                    'last_request_created_at': created_at
                }
                dataset.update(data)

        org['requests_archive'] = \
            sorted(org['requests_archive'],
                   key=lambda x: x[order],
                   reverse=reverse)

    organizations_for_filters = \
        sorted(organizations_for_filters.items(),
               key=lambda x_y: x_y[1]['requests'], reverse=True)

    total_requests_counters =\
        utils.get_action('requestdata_request_data_counters_get_all', {})
    extra_vars = {
        'organizations': organizations,
        'organizations_for_filters': organizations_for_filters,
        'total_requests_counters': total_requests_counters
    }

    return toolkit.render('admin/all_requests_data.html', extra_vars)


def download_requests_data():
    '''
        Handles creating csv or json file from all of the Requested Data

        :returns: json or csv file
    '''

    file_format = request.args.get('format')
    requests = \
        utils.get_action('requestdata_request_list_for_sysadmin', {})
    s = StringIO()

    print(file_format)

    if 'json' in file_format.lower():
        json.dump(requests, s, indent=4)
        resp = make_response(s.getvalue())
        resp.headers['Content-Type'] = u'application/json'
        resp.headers['Content-Disposition'] = u'attachment;filename="data_requests.json"'
        return resp

    if 'csv' in file_format.lower():
        writer = csv.writer(s, delimiter=',')
        header = True
        for k in requests:
            if header:
                writer.writerow(k.keys())
                header = False
            writer.writerow(k.values())
        resp = make_response(s.getvalue())

        resp.headers['Content-Type'] = u'text/csv'
        resp.headers['Content-Disposition'] = u'attachment;filename="data_requests.csv"'
        return resp


admin.add_url_rule(u'/email', view_func=email,
                   methods=[u'GET', u'POST'])
admin.add_url_rule(u'/requests_data', view_func=requests_data,
                   methods=[u'GET', u'POST'])
admin.add_url_rule(u'/requests_data/download', view_func=download_requests_data,
                   methods=[u'GET', u'POST'])


def get_blueprints():
    return [admin]
