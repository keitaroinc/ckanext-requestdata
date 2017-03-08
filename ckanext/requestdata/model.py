import logging
import datetime

from sqlalchemy import Table
from sqlalchemy import Column
from sqlalchemy import types
from sqlalchemy import Index

from sqlalchemy.engine.reflection import Inspector
from ckan.model.meta import metadata, mapper, Session, engine
from ckan.model.types import make_uuid
from ckan.model.domain_object import DomainObject

log = logging.getLogger(__name__)

request_data_table = None


def setup():
    if request_data_table is None:
        define_request_data_table()
        log.debug('Requestdata table defined in memory.')

        if not request_data_table.exists():
            request_data_table.create()
    else:
        log.debug('Requestdata table already exists.')
        inspector = Inspector.from_engine(engine)

        index_names =\
            [index['name'] for index in
                inspector.get_indexes('ckanext_requestdata')]

        if 'ckanext_requestdata_id_idx' not in index_names:
            log.debug('Creating index for ckanext_requestdata.')
            Index('ckanext_requestdata_id_idx',
                  request_data_table.c.ckanext_event_id).create()


class ckanextRequestdata(DomainObject):
    @classmethod
    def get(self, key, value):
        '''Finds a single entity in the table.

        :param key: Name of the column.
        :type key: string
        :param value: Value of the column.
        :type value: string

        '''

        kwds = {key: value}

        query = Session.query(self).autoflush(False)
        query = query.filter_by(**kwds).first()

        return query

    @classmethod
    def search(self, limit, order='created_at', **kwds):
        '''Finds entities in the table that satisfy certain criteria.

        :param limit: Number of records to return.
        :type limit: number
        :param order: Order rows by specified column.
        :type order: string

        '''

        query = Session.query(self).autoflush(False)
        query = query.filter_by(**kwds)
        query = query.order_by(order)
        query = query.limit(limit)

        return query.all()


def define_request_data_table():
    global request_data_table

    request_data_table = Table('ckanext_requestdata', metadata,
                               Column('id', types.UnicodeText,
                                      primary_key=True,
                                      default=make_uuid),
                               Column('sender_name', types.UnicodeText,
                                      nullable=False),
                               Column('organization', types.UnicodeText,
                                      nullable=False),
                               Column('email_address', types.UnicodeText,
                                      nullable=False),
                               Column('message_content', types.UnicodeText,
                                      nullable=False),
                               Column('package_name', types.UnicodeText,
                                      nullable=False),
                               Column('state', types.UnicodeText,
                                      nullable=False),
                               Column('data_shared', types.Boolean,
                                      default=False),
                               Column('created_at', types.DateTime,
                                      default=datetime.datetime.utcnow),
                               Index('ckanext_requestdata_id_idx', 'id'))

    mapper(
        ckanextRequestdata,
        request_data_table
    )