"""Tests functions in the Neick Uploader Flask Blueprint."""
import newick
import os
import pytest

from multinet.errors import ValidationFailed, DecodeFailed
from multinet.validation import DuplicateKey
from multinet.uploaders.newick import validate_newick, decode_data

TEST_DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "data"))


def test_validate_newick():
    """Test the validate_newick() function."""
    duplicate_keys_file_path = os.path.join(
        TEST_DATA_DIR, "basic_newick_duplicates.tree"
    )

    # Test duplicate keys
    with open(duplicate_keys_file_path) as test_file:
        test_file = test_file.read()

    body = newick.loads(test_file)

    with pytest.raises(ValidationFailed) as v_error:
        validate_newick(body)

    validation_resp = v_error.value.errors
    assert DuplicateKey(key="A").dict() in validation_resp

    # Test unicode decode errors
    test_data = (
        b"\xff\xfe(\x00B\x00,\x00(\x00A\x00,"
        b"\x00C\x00,\x00E\x00)\x00,\x00D\x00)\x00;\x00\n\x00"
    )
    pytest.raises(DecodeFailed, decode_data, test_data)
