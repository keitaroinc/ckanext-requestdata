from ckan.lib import base
from ckan import logic, model
from ckan.plugins import toolkit
from ckan.common import c, _, request
from ckan.controllers import organization
from collections import Counter
from ckanext.requestdata import helpers
import ckanext.requestdata.utils as utils


get_action = logic.get_action
NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError

abort = base.abort
render = base.render
BaseController = base.BaseController



class OrganizationController(organization.OrganizationController):

    def requested_data(self, id):
        '''Handles creating template for 'Requested Data' page in the
        organization's dashboard.
        :param id: The organization's id.
        :type id: string
        :returns: template
        '''

        try:
            requests = utils.get_action('requestdata_request_list_for_organization',
                                   {'org_id': id})

        except NotAuthorized:
            abort(403, _('Not authorized to see this page.'))


        maintainer_field_name = utils.get_maintainer_field_name()
        users_cache = {}  # temporay cache, to avoid making unnecessary calls to 'user_show'

        group_type = self._ensure_controller_matches_group_type(id)
        context = {
            'model': model,
            'session': model.Session,
            'user': c.user
        }
        c.group_dict = self._get_group_dict(id)
        group_type = c.group_dict['type']
        request_params = request.params.dict_of_lists()
        filtered_maintainers = []
        reverse = True
        order = 'last_request_created_at'
        q_organization = ''
        current_order_name = _('Most Recent')

        for item in request_params:
            if item == 'filter_by_maintainers':
                for x in request_params[item]:
                    params = x.split('|')
                    org = params[0].split(':')[1]
                    maintainers = params[1].split(':')[1].split(',')
                    maintainers_ids = []

                    if maintainers[0] != '*all*':
                        for i in maintainers:
                            try:
                                user = user_cache.get(i) or utils.get_action('user_show', {'id': i})
                                users_cache[i] = user
                                maintainers_ids.append(user['id'])
                            except NotFound:
                                pass

                        data = {
                            'org': org,
                            'maintainers': maintainers_ids
                        }

                        filtered_maintainers.append(data)
            elif item == 'order_by':
                params = request_params[item][0].split('|')
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
                elif 'shared' in order:
                    current_order_name = _('Sharing Rate')
                elif 'requests' in order:
                    current_order_name = _('Requests Rate')

                for x in requests:
                    package = \
                        utils.get_action('package_show', {'id': x['package_id']})
                    count = \
                        utils.get_action('requestdata_request_data_counters_get',
                                    {'package_id': x['package_id']})
                    x['title'] = package['title']
                    x['shared'] = count.shared
                    x['requests'] = count.requests
                    data_dict = {'id': package['owner_org']}
                    current_org = utils.get_action('organization_show', data_dict)
                    x['name'] = current_org['name']

        maintainers = []
        for item in requests:
            package = utils.get_action('package_show', {'id': item['package_id']})
            package_maintainer_ids = package[maintainer_field_name].split(',')
            item['title'] = package['title']
            package_maintainers = []

            for maint_id in package_maintainer_ids:
                try:
                    user = users_cache.get(maint_id) or utils.get_action('user_show', {'id': maint_id})
                    users_cache[maint_id] = user
                    username = user['name']
                    name = user['fullname']

                    if not name:
                        name = username

                    payload = {
                               'id': user['id'],
                               'name': name,
                               'username': username,
                               'fullname': name}
                    maintainers.append(payload)
                    package_maintainers.append(payload)
                except NotFound:
                    pass
            item['maintainers'] = package_maintainers

        copy_of_maintainers = maintainers
        maintainers = dict((item['id'], item) for item in maintainers).values()
        organ = utils.get_action('organization_show', {'id': id})

        # Count how many requests each maintainer has
        for main in maintainers:
            count = Counter(
                item for dct in copy_of_maintainers for item in dct.items())
            main['count'] = count[('id', main['id'])]

        # Sort maintainers by number of requests
        maintainers = sorted(
            maintainers, key=lambda k: k['count'], reverse=True)

        for i, r in enumerate(requests[:]):
            maintainer_found = False

            package = utils.get_action('package_show', {'id': r['package_id']})
            package_maintainer_ids = package[maintainer_field_name].split(',')
            is_hdx = helpers.is_hdx_portal()

            if is_hdx:
                # Quick fix for hdx portal
                maintainer_ids = []
                for maintainer_name in package_maintainer_ids:
                    try:
                        main_ids = users_cache.get(maintainer_name) or utils.get_action('user_show', {'id': maintainer_name})
                        users_cache[maintainer_name] = main_ids
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
                        requests.remove(r)

        requests_new = []
        requests_open = []
        requests_archive = []

        for item in requests:
            if item['state'] == 'new':
                requests_new.append(item)
            elif item['state'] == 'open':
                requests_open.append(item)
            elif item['state'] == 'archive':
                requests_archive.append(item)

        grouped_requests_archive =\
            helpers.group_archived_requests_by_dataset(requests_archive)

        if order == 'last_request_created_at':
            for dataset in grouped_requests_archive:
                created_at =\
                    dataset.get('requests_archived')[0].get('created_at')
                data = {
                    'last_request_created_at': created_at
                }
                dataset.update(data)

        if organ['name'] == q_organization:
            grouped_requests_archive = sorted(grouped_requests_archive,
                                              key=lambda x: x[order],
                                              reverse=reverse)

        counters =\
            utils.get_action('requestdata_request_data_counters_get_by_org',
                        {'org_id': organ['id']})

        extra_vars = {
            'requests_new': requests_new,
            'requests_open': requests_open,
            'requests_archive': grouped_requests_archive,
            'maintainers': maintainers,
            'org_name': organ['name'],
            'current_order_name': current_order_name,
            'counters': counters
        }

        self._setup_template_variables(context, {'id': id},
                                       group_type=group_type)

        return render('requestdata/organization_requested_data.html',
                      extra_vars)
