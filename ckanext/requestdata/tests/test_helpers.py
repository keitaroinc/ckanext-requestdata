# encoding: utf-8
import nose
import json
from datetime import datetime, timedelta
from ckanext.requestdata import helpers as h
import ckan.plugins as p
from ckan.tests import helpers, factories
from ckan import logic
from ckan.common import request

ok_ = nose.tools.ok_
eq_ = nose.tools.eq_
raises = nose.tools.raises
assert_equals = nose.tools.assert_equals
assert_not_equal = nose.tools.assert_not_equal


class ActionBase(object):

    @classmethod
    def setup_class(self):
        self.app = helpers._get_test_app()
        if not p.plugin_loaded('requestdata'):
            p.load('requestdata')

    def setup(self):
        helpers.reset_db()

    @classmethod
    def teardown_class(self):
        if p.plugin_loaded('requestdata'):
            p.unload('requestdata')


class TestHelpers(ActionBase):

    def test_time_ago_from_datetime_valid(self):
        d = datetime.today() - timedelta(days=1)
        eq_(h.time_ago_from_datetime(d), '1 day ago')

    def test_time_ago_from_datetime_valid_string_result(self):
        d = datetime.today() - timedelta(days=2)
        assert isinstance(h.time_ago_from_datetime(d), str)

    def test_convert_id_to_emails_valid(self):
        user = factories.User()
        users = [{'name': user['name']}]
        ids = user['id']
        response = h.convert_id_to_email(ids)
        email = '@ckan.org'
        assert email in response

    def test_convert_id_to_emails_invalid(self):
        ids = '231'
        response = h.convert_id_to_email(ids)
        email = 'test_user_05@ckan.org'
        assert_not_equal(email, response)

    def test_convert_str_to_json_invalid(self):
        str = "test: 123"
        res = h.convert_str_to_json(str)
        assert_equals("string cannot be parsed", res)

    def test_convert_str_to_json_valid(self):
        str = "{'test': 2}"
        res = h.convert_str_to_json(json.dumps(str))
        assert_not_equal(res, "string cannot be parsed")

    def test_group_archived_requests_valid(self):
        id2 = 2
        id3 = 3
        id55 = 55
        requests = [{
            'package_id': id55,
            'title': 'test5',
            'maintainers': 'm',
            'requests_archived': 'r',
            'shared': '',
            'requests': 'r'
        }, {
            'package_id': id3,
            'title': 'test3',
            'maintainers': '',
            'requests_archived': '',
            'shared': '',
            'requests': ''
        }, {
            'package_id': id2,
            'title': 'test2',
            'maintainers': 't',
            'requests_archived': 'r',
            'shared': 't',
            'requests': 'r'
        }]

        res = h.group_archived_requests_by_dataset(requests)
        assert_equals(res[0]['package_id'], id2)
        assert_equals(res[1]['package_id'], id3)
        assert_equals(res[2]['package_id'], id55)
