from flask import Blueprint

from ckan.lib import base
from ckan.common import c, _, request
from ckan import logic
import ckan.model as model
import ckan.lib.helpers as h
from ckan.plugins import toolkit

import ckan.views.dataset as dataset

import ckan.lib.navl.dictization_functions as dict_fns
from ckanext.requestdata.helpers import has_query_param
from ckanext.requestdata.utils import use_standard_package_type

get_action = logic.get_action
NotAuthorized = logic.NotAuthorized
ValidationError = logic.ValidationError
clean_dict = logic.clean_dict

redirect = h.redirect_to
abort = base.abort
tuplize_dict = logic.tuplize_dict
parse_params = logic.parse_params


requestdata_dataset = Blueprint(u'requestdata_dataset_blueprint',
                                __name__,
                                url_prefix=u'/dataset',
                                url_defaults={u'package_type': u'dataset'}
)


class CreateView(dataset.CreateView):
    def get(self, package_type, data=None, errors=None, error_summary=None):

        # Handle metadata-only datasets
        if has_query_param('metadata'):
            package_type = package_type if use_standard_package_type() else 'requestdata-metadata-only'

        return super(CreateView, self).get(package_type, data,
                                           errors, error_summary)

    def post(self, package_type):

        # Handle metadata-only datasets
        if has_query_param('metadata'):
            package_type = package_type if use_standard_package_type() else 'requestdata-metadata-only'

            data_dict = dataset.clean_dict(
                dataset.dict_fns.unflatten(
                    dataset.tuplize_dict(dataset.parse_params(request.form))))
            context = self._prepare()
            data_dict['type'] = package_type

            try:
                package = get_action('package_create')(context, data_dict)

                url = h.url_for(u'{0}.read'.format(package_type), id=package['name'])

                return redirect(url)
            except NotAuthorized:
                abort(403, _('Unauthorized to create a dataset.'))
            except ValidationError as e:
                errors = e.error_dict
                error_summary = e.error_summary

                form_vars = {'errors': errors, 'dataset_type': package_type, 'action': 'new',
                             'error_summary': error_summary, 'stage': ['active'], 'data': data_dict}

                extra_vars = {
                    'form_vars': form_vars,
                    'form_snippet': 'package/new_package_form.html',
                    'dataset_type': package_type
                }

                return toolkit.render('package/new.html',
                                      extra_vars=extra_vars)
        else:
            return super(CreateView, self).post(package_type)


requestdata_dataset.add_url_rule(u'/new', view_func=CreateView.as_view(str(u'new')))


def get_blueprints():
    return [requestdata_dataset]
