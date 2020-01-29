"""Multinet uploader for nested JSON files."""
import json
from io import StringIO
from flasgger import swag_from
from dataclasses import dataclass
from collections import OrderedDict

from multinet import db, util
from multinet.errors import ValidationFailed
from multinet.util import decode_data
from multinet.validation import ValidationFailure

from flask import Blueprint, request

# Import types
from typing import Any, List, Sequence

bp = Blueprint("d3_json", __name__)
bp.before_request(util.require_db)


@dataclass
class InvalidStructure(ValidationFailure):
    """Invalid structure in a D3 JSON file."""


@dataclass
class InvalidLinkKeys(ValidationFailure):
    """Invalid link keys in a D3 JSON file."""


@dataclass
class InconsistentLinkKeys(ValidationFailure):
    """Inconsistent link keys in a D3 JSON file."""


@dataclass
class NodeDuplicates(ValidationFailure):
    """Duplicate nodes in a D3 JSON file."""


def validate_d3_json(data: dict) -> Sequence[ValidationFailure]:
    """Perform any necessary d3 json validation, and return appropriate errors."""
    data_errors: List[ValidationFailure] = []

    # Check the structure of the uploaded file is what we expect
    if "nodes" not in data.keys() or "links" not in data.keys():
        data_errors.append(InvalidStructure())

    # Check that links are in source -> target form
    if not all(
        "source" in row.keys() and "target" in row.keys() for row in data["links"]
    ):
        data_errors.append(InvalidLinkKeys())

    # Check that the keys for each dictionary match
    if not all(data["links"][0].keys() == row.keys() for row in data["links"]):
        data_errors.append(InconsistentLinkKeys())

    # Check for duplicated nodes
    ids = set(row["id"] for row in data["nodes"])
    if len(data["nodes"]) != len(ids):
        data_errors.append(NodeDuplicates())

    return data_errors


@bp.route("/<workspace>/<table>", methods=["POST"])
@swag_from("swagger/d3_json.yaml")
def upload(workspace: str, table: str) -> Any:
    """Store a d3 json-encoded graph into the database as a node and edge table.

    `workspace` - the target workspace
    `table` - the target table
    `data` - the json data, passed in the request body. The json data should contain
    nodes: [] and links: []
    """
    # Get data from the request and load it as json
    body = decode_data(request.data)
    data = json.load(StringIO(body), object_pairs_hook=OrderedDict)

    # Check file structure
    errors = validate_d3_json(data)
    if len(errors) > 0:
        raise ValidationFailed(errors)

    # Change column names from the d3 format to the arango format
    nodes = data["nodes"]
    for node in nodes:
        node["_key"] = node["id"]
        del node["id"]

    links = data["links"]
    for link in links:
        link["_from"] = f"{table}_nodes/{link['source']}"
        link["_to"] = f"{table}_nodes/{link['target']}"
        del link["source"]
        del link["target"]

    # Create or retrieve the workspace
    space = db.db(workspace)
    if space.has_collection(f"{table}_nodes"):
        nodes_coll = space.collection(f"{table}_nodes")
    else:
        nodes_coll = space.create_collection(f"{table}_nodes", edge=False)

    if space.has_collection(f"{table}_links"):
        links_coll = space.collection(f"{table}_links")
    else:
        links_coll = space.create_collection(f"{table}_links", edge=True)

    # Insert data
    nodes_coll.insert_many(nodes)
    links_coll.insert_many(links)

    return dict(nodecount=len(nodes), edgecount=len(links))
