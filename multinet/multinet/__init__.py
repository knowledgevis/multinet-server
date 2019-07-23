"""Defines the MultiNet Girder plugin."""

from girder import plugin, logprint
from girder.api import access
from girder.api.rest import Resource, getBodyJson
from girder.api.describe import Description, autoDescribeRoute

import csv
import re
import json
from io import StringIO
import logging
from graphql import graphql
import cherrypy
import newick
import uuid

from .schema import schema
from . import db


def graphql_query(query, variables=None):
    """Perform a GraphQL query using optional variable definitions."""
    result = graphql(schema, query, variables=variables or {})
    if result:
        errors = [error.message for error in result.errors] if result.errors else []
        logprint('Errors in request: %s' % len(errors), level=logging.WARNING)
        for error in errors[:10]:
            logprint(error, level=logging.WARNING)
    else:
        errors = []
    return dict(data=result.data, errors=errors, query=query)


def graph_validation(query):
    print('query', query)
    node_tables = json.loads(re.findall('node_tables: (\\[.+\\])', query)[0])
    edge_table = re.findall('edge_table: \"(.+)\"', query)[0]
    workspace = re.findall('workspace: \"(.+)\"', query)[0]

    workspace = db.db(workspace)
    print(node_tables, edge_table, workspace)

    edge_table = workspace.collection(edge_table)
    res = list(edge_table.find({}))
    # Find all docs with _from
    # With those results, check if any of those aren't
    # in node_tables
    # If so, throw error
    print(res)
    for table in node_tables:
        print('table', table)
        if workspace.has_collection(table):
            print('YEET')
        else:
            print('NOS')


class MultiNet(Resource):
    """Define the MultiNet API within Girder."""

    def __init__(self, port):
        """
        Initialize the plugin.

        `port` - the port where Arango is running.
        """
        super(MultiNet, self).__init__()
        self.resourceName = 'multinet'
        self.arango_port = port
        self.route('POST', ('graphql',), self.graphql)
        self.route('POST', ('csv', ':workspace', ':table'), self.bulk)

        # Newick tree operations.
        self.route('POST', ('newick', ':workspace', ':table'), self.tree)

    @access.public
    @autoDescribeRoute(
        Description('Receive GraphQL queries')
        .param('query', 'GraphQL query text', paramType='body', required=True)
    )
    def graphql(self, params):
        """
        Perform a GraphQL query.

        The body of the request is a JSON object containing a required `query`
        property containing the text of the query itself, and an options
        `variables` property, containing variable definitions for the body of
        `query`.
        """
        logprint('Executing GraphQL Request', level=logging.INFO)

        # Grab the GraphQL parameters from the request body.
        body = getBodyJson()
        query = body['query']
        variables = body.get('variables')

        print(graph_validation(query))

        logprint('request: %s' % query, level=logging.DEBUG)
        logprint('variables: %s' % variables, level=logging.DEBUG)

        return graphql_query(query, variables)

    @access.public
    @autoDescribeRoute(
        Description('Store CSV data in database')
        .param('workspace', 'Target workspace', required=True)
        .param('table', 'Target table', required=True)
        .param('data', 'CSV data', paramType='body', required=True)
    )
    def bulk(self, params, workspace=None, table=None):
        """
        Append CSV rows to a particular table in a particular workspace.

        `workspace` - the target workspace.
        `table` - the target table.
        `data` - CSV text, passed in the request body.
        """
        logprint('Bulk Loading', level=logging.INFO)
        rows = csv.DictReader(StringIO(cherrypy.request.body.read().decode('utf8')))
        workspace = db.db(workspace)

        # Set the collection, paying attention to whether the data contains
        # _from/_to fields.
        coll = None
        if workspace.has_collection(table):
            coll = workspace.collection(table)
        else:
            edges = '_from' in rows.fieldnames and '_to' in rows.fieldnames
            coll = workspace.create_collection(table, edge=edges)

        # Insert the data into the collection.
        results = coll.insert_many(rows)
        return dict(count=len(results))

    @access.public
    @autoDescribeRoute(
        Description('Store tree in database from nexus/newick files. '
                    'Two tables will be created with the given table name, '
                    '<table>_edges and <table>_nodes')
        .param('workspace', 'Target workspace', required=True)
        .param('table', 'Target table', required=True)
        .param('data', 'Tree data', paramType='body', required=True)
    )
    def tree(self, params, workspace=None, table=None, schema=None):
        """
        Store a newick tree into the database in coordinated node and edge tables.

        `workspace` - the target workspace.
        `table` - the target table.
        `data` - the newick data, passed in the request body.
        """
        logprint('Bulk Loading', level=logging.INFO)
        tree = newick.loads(cherrypy.request.body.read().decode('utf8'))
        workspace = db.db(workspace)
        edgetable_name = '%s_edges' % table
        nodetable_name = '%s_nodes' % table
        if workspace.has_collection(edgetable_name):
            edgetable = workspace.collection(edgetable_name)
        else:
            # Note that edge=True must be set or the _from and _to keys
            # will be ignored below.
            edgetable = workspace.create_collection(edgetable_name, edge=True)
        if workspace.has_collection(nodetable_name):
            nodetable = workspace.collection(nodetable_name)
        else:
            nodetable = workspace.create_collection(nodetable_name)

        edgecount = 0
        nodecount = 0

        def read_tree(parent, node):
            nonlocal nodecount
            nonlocal edgecount
            key = node.name or uuid.uuid4().hex
            if not nodetable.has(key):
                nodetable.insert({'_key': key})
            nodecount = nodecount + 1
            for desc in node.descendants:
                read_tree(key, desc)
            if parent:
                edgetable.insert({
                    '_from': '%s/%s' % (nodetable_name, parent),
                    '_to': '%s/%s' % (nodetable_name, key),
                    'length': node.length
                })
                edgecount += 1

        read_tree(None, tree[0])

        return dict(edgecount=edgecount, nodecount=nodecount)


class GirderPlugin(plugin.GirderPlugin):
    """Girder plugin infrastructure for MultiNet API."""

    DISPLAY_NAME = 'MultiNet'

    def load(self, info):
        """Load the plugin at Girder startup."""
        info['apiRoot'].multinet = MultiNet(port=8080)
