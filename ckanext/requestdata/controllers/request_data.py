from ckan.lib import base
from ckan.common import c, _
from ckan import logic
from ckanext.requestdata import emailer
from ckanext.requestdata import utils
from ckan.plugins import toolkit
from ckan.controllers.admin import get_sysadmins

try:
    # CKAN 2.7 and later
    from ckan.common import config
except ImportError:
    # CKAN 2.6 and earlier
    from pylons import config
import ckan.model as model
import ckan.plugins as p
import json

NotFound = logic.NotFound
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
abort = base.abort
BaseController = base.BaseController


def _get_email_configuration(
        user_name, data_owner, dataset_name, email, message, organization,
        data_maintainers, only_org_admins=False):
    schema = logic.schema.update_configuration_schema()
    avaiable_terms = ['{name}', '{data_maintainers}', '{dataset}',
                      '{organization}', '{message}', '{email}']
    new_terms = [user_name, data_maintainers, dataset_name, organization,
                 message, email]

    try:
        is_user_sysadmin = \
            utils.get_action('user_show', {'id': c.user}).get('sysadmin')
    except NotFound:
        pass

    for key in schema:
        # get only email configuration
        if 'email_header' in key:
            email_header = config.get(key)
        elif 'email_body' in key:
            email_body = config.get(key)
        elif 'email_footer' in key:
            email_footer = config.get(key)
    if '{message}' not in email_body and not email_body and not email_footer:
        email_body += message
        return email_body
    for i in range(0, len(avaiable_terms)):
        if avaiable_terms[i] == '{dataset}' and new_terms[i]:
            url = toolkit.url_for(
                                    controller='package',
                                    action='read',
                                    id=new_terms[i], qualified=True)
            new_terms[i] = '<a href="' + url + '">' + new_terms[i] + '</a>'
        elif avaiable_terms[i] == '{organization}' and is_user_sysadmin:
            new_terms[i] = config.get('ckan.site_title')
        elif avaiable_terms[i] == '{data_maintainers}':
            if len(new_terms[i]) == 1:
                new_terms[i] = new_terms[i][0]
            else:
                maintainers = ''
                for j, term in enumerate(new_terms[i][:]):
                    maintainers += term

                    if j == len(new_terms[i]) - 2:
                        maintainers += ' and '
                    elif j < len(new_terms[i]) - 1:
                        maintainers += ', '

                new_terms[i] = maintainers

        email_header = email_header.replace(avaiable_terms[i], new_terms[i])
        email_body = email_body.replace(avaiable_terms[i], new_terms[i])
        email_footer = email_footer.replace(avaiable_terms[i], new_terms[i])

    if only_org_admins:
        owner_org = utils.get_action('package_show', {'id': dataset_name}).get('owner_org')
        url = toolkit.url_for('requestdata_organization_requests',
                              id=owner_org, qualified=True)
        email_body += _('<br><br> This dataset\'s maintainer does not exist.\
        Go to your organisation\'s <a href="' + url + '">Requested Data</a>\
         page to see the new request. Please also edit the dataset and assign\
          a new maintainer.')
    else:
        url = \
            toolkit.url_for('requestdata_my_requests',
                            id=data_owner, qualified=True)
        email_body += _('<br><br><strong> Please accept or decline the request\
        as soon as you can by visiting the \
        <a href="' + url + '">My Requests</a> page.</strong>')

    organizations =\
        utils.get_action('organization_list_for_user', {'id': data_owner})

    package = utils.get_action('package_show', {'id': dataset_name})

    if not only_org_admins:
        for org in organizations:
            if org['name'] in organization\
                    and package['owner_org'] == org['id']:
                url = \
                    toolkit.url_for('requestdata_organization_requests',
                                    id=org['name'], qualified=True)
                email_body += _('<br><br> Go to <a href="' + url + '">\
                    Requested data</a> page in organization admin.')
    site_url = config.get('ckan.site_url')
    site_title = config.get('ckan.site_title')
    newsletter_url = config.get('ckanext.requestdata.newsletter_url', site_url)
    twitter_url = \
        config.get('ckanext.requestdata.twitter_url', 'https://twitter.com')
    contact_email = config.get('ckanext.requestdata.contact_email', '')

    email_footer += _("""
        <br/><br/>
        <small>
          <p>
            <a href=" """ + site_url + """ ">""" + site_title + """</a>
          </p>
          <p>
            <a href=" """ + newsletter_url + """ ">\
            Sign up for our newsletter</a> | \
            <a href=" """ + twitter_url + """ ">Follow us on Twitter</a>\
             | <a href="mailto:""" + contact_email + """ ">Contact us</a>
          </p>
        </small>

    """)

    result = email_header + '<br><br>' + email_body + '<br><br>' + email_footer

    return result


class RequestDataController(BaseController):

    def send_request(self):
        '''Send mail to resource owner.

        :param data: Contact form data.
        :type data: object

        :rtype: json
        '''
        context = {'model': model, 'session': model.Session,
                   'user': c.user, 'auth_user_obj': c.userobj}
        maintainer_field_name = utils.get_maintainer_field_name()
        try:
            if p.toolkit.request.method == 'POST':
                data = dict(toolkit.request.POST)
                utils.get_action('requestdata_request_create', data)
        except NotAuthorized:
            abort(403, _('Unauthorized to update this dataset.'))
        except ValidationError as e:
            error = {
                'success': False,
                'error': {
                    'fields': e.error_dict
                }
            }

            return json.dumps(error)

        data_dict = {'id': data['package_id']}
        package = utils.get_action('package_show', data_dict)
        sender_name = data.get('sender_name', '')
        user_obj = context['auth_user_obj']
        data_dict = {
            'id': user_obj.id,
            'permission': 'read'
        }

        organizations = utils.get_action('organization_list_for_user', data_dict)

        orgs = []
        for i in organizations:
            orgs.append(i['display_name'])
        org = ','.join(orgs)
        dataset_name = package['name']
        dataset_title = package['title']
        email = user_obj.email
        message = data['message_content']
        creator_user_id = package['creator_user_id']
        data_owner =\
            utils.get_action('user_show', {'id': creator_user_id}).get('name')
        if len(get_sysadmins()) > 0:
            sysadmin = get_sysadmins()[0].name
            context_sysadmin = {
                'model': model,
                'session': model.Session,
                'user': sysadmin,
                'auth_user_obj': c.userobj
            }
            to = package[maintainer_field_name]
            if to is None:
                message = {
                    'success': False,
                    'error': {
                        'fields': {
                            'email': _('Dataset maintainer email not found.')
                        }
                    }
                }

                return json.dumps(message)
            maintainers = to.split(',')
            data_dict = {
                'users': []
            }
            users_email = []
            only_org_admins = False
            data_maintainers = []
            # Get users objects from maintainers list
            for id in maintainers:
                try:
                    user =\
                        toolkit.get_action('user_show')(context_sysadmin,
                                                        {'id': id})
                    data_dict['users'].append(user)
                    users_email.append(user['email'])
                    data_maintainers.append(user['fullname'] or user['name'])
                except NotFound:
                    pass
            mail_subject =\
                config.get('ckan.site_title') + _(': New data request "') + dataset_title + '"'

            if len(users_email) == 0:
                admins = self._org_admins_for_dataset(dataset_name)

                for admin in admins:
                    users_email.append(admin.get('email'))
                    data_maintainers.append(admin.get('fullname'))
                only_org_admins = True

            content = _get_email_configuration(
                sender_name, data_owner, dataset_name, email,
                message, org, data_maintainers,
                only_org_admins=only_org_admins)

            response_message = \
                emailer.send_email(content, users_email, mail_subject)

            # notify package creator that new data request was made
            utils.get_action('requestdata_notification_create', data_dict)
            data_dict = {
                'package_id': data['package_id'],
                'flag': 'request'
            }

            action_name = 'requestdata_increment_request_data_counters'
            utils.get_action(action_name, data_dict)

            return json.dumps(response_message)
        else:
            message = {
                'success': True,
                'message': _('Request sent, but email message was not sent.')
            }

            return json.dumps(message)

    def _org_admins_for_dataset(self, dataset_name):
        package = utils.get_action('package_show', {'id': dataset_name})
        owner_org = package['owner_org']
        admins = []

        org = utils.get_action('organization_show', {'id': owner_org})

        for user in org['users']:
            if user['capacity'] == 'admin':
                db_user = model.User.get(user['id'])
                data = {
                    'email': db_user.email,
                    'fullname': db_user.fullname or db_user.name
                }
                admins.append(data)

        return admins

    def read_request(self, package_id, request_id):
            context = {
                'model': model,
                'session': model.Session,
                'user': c.user
            }

            maintainer_field_name = utils.get_maintainer_field_name()

            data_request = toolkit.get_action('requestdata_request_show')(context, {'id': request_id, 'package_id': package_id})
            pkg_dict = toolkit.get_action('package_show')(context, {'id': package_id})
            

            maintainers = []

            if pkg_dict.get(maintainer_field_name):
                maintainers = pkg_dict.get(maintainer_field_name).split(',')


            data_maintainers = []
            # Get users objects from maintainers list
            for id in maintainers:
                try:
                    user =\
                        toolkit.get_action('user_show')({'skip_auth': True},
                                                        {'id': id})
                    data_maintainers.append({'id': user['id'], 'fullname': user.get('fullname') or user.get('name')})
                except NotFound:
                    pass
            
            pkg_dict['maintainers'] = data_maintainers

            extra_vars = {
                'data_request': data_request,
                'pkg_dict': pkg_dict
            }

            return base.render('requestdata/read_data_request.html',
                        extra_vars)
