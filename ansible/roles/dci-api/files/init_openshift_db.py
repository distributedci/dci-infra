#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2015 Red Hat, Inc
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
This module will initialize the database with the admin user and group based
on openshift environment variable.
"""

import os
import sys

import sqlalchemy
import sqlalchemy_utils.functions
from sqlalchemy import exc as sa_exc

from dci.server import app
from dci.server import auth2
from dci.server import dci_config
from dci.server.db import models_core


if not os.environ.get('DCI_LOGIN') or not os.environ.get('DCI_PASSWORD'):
    print("Environment variables missing: DCI_LOGIN='%s', DCI_PASSWORD='%s'" %
          (os.environ.get('DCI_LOGIN', ''),
           os.environ.get('DCI_PASSWORD', '')))
    sys.exit(1)

DCI_LOGIN = os.environ.get('DCI_LOGIN')
DCI_PASSWORD = os.environ.get('DCI_PASSWORD')
DCI_PASSWORD_HASH = auth2.hash_password(os.environ.get('DCI_PASSWORD'))


def init_db(db_conn):
    def db_insert_with_name(model_item, **kwargs):
        query = sqlalchemy.sql.select([model_item]).where(
            model_item.c.name == kwargs['name'])
        try:
            result = db_conn.execute(query).fetchone()
        except sa_exc.DBAPIError as e:
            print(str(e))
            sys.exit(1)

        if result is None:
            query = model_item.insert().values(**kwargs)
            return db_conn.execute(query).inserted_primary_key[0]
        else:
            result = dict(result)
            query = model_item.update().where(
                model_item.c.name == result['name']).values(**kwargs)
            try:
                db_conn.execute(query)
            except sa_exc.DBAPIError as e:
                print(str(e))
                sys.exit(1)
            return result['id']

    # Create team admin
    team_admin_id = db_insert_with_name(models_core.TEAMS, name='admin')

    # Create admin role
    role_admin_id = db_insert_with_name(models_core.ROLES, name='admin')

    # Create admin user
    user_admin_id = db_insert_with_name(models_core.USERS,
                                        name=DCI_LOGIN,
                                        password=DCI_PASSWORD_HASH,
                                        team_id=team_admin_id)

    # Create one user_roles entry
    query = models_core.JOIN_USERS_ROLES.insert().values(user_id=user_admin_id,
                                                         role_id=role_admin_id)
    try:
        db_conn.execute(query)
    except sa_exc.IntegrityError:
        # Safely ignore this exception because the user_roles entry already
        # exists.
        pass


def main():
    conf = dci_config.generate_conf()
    db_uri = conf['SQLALCHEMY_DATABASE_URI']
    if sqlalchemy_utils.functions.database_exists(db_uri):
        sqlalchemy_utils.functions.drop_database(db_uri)
    sqlalchemy_utils.functions.create_database(db_uri)
    engine = sqlalchemy.create_engine(db_uri)
    models_core.metadata.create_all(engine)
    with engine.begin() as conn:
        init_db(conn)

if __name__ == '__main__':
    main()
