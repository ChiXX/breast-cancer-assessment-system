import pytest
import os
import json
import pickle
import numpy as np
from unittest.mock import MagicMock, patch

# Assume the script will be in mcp/scripts/build_index.py
# or mcp/data/build_index.py. The user spec says mcp/data/build_index.py
# but the metadata said scripts/build_index.py.
# I'll try to import it once I know where it is.
# For now, I'll just write the test logic.

def test_build_index_creates_files():
    """
    Test that build_index.py creates index.faiss and doc_map.pkl
    """
    # Import the function from the script
    from mcp.data.build_index import build_index
    
    # Mock dashscope to avoid real API calls
    with patch('dashscope.TextEmbedding.call') as mock_call:
        mock_call.return_value = MagicMock(
            status_code=200,
            output={'embeddings': [{'embedding': [0.1] * 1024}] * 15} # Match sample data count approx
        )
        
        # Clean up existing files if any
        if os.path.exists("mcp/data/vector_store/index.faiss"):
            os.remove("mcp/data/vector_store/index.faiss")
        if os.path.exists("mcp/data/vector_store/doc_map.pkl"):
            os.remove("mcp/data/vector_store/doc_map.pkl")
            
        # Run the function
        build_index()
        
        # Check if output files exist
        assert os.path.exists("mcp/data/vector_store/index.faiss")
        assert os.path.exists("mcp/data/vector_store/doc_map.pkl")
        
        # Verify content of doc_map
        with open("mcp/data/vector_store/doc_map.pkl", "rb") as f:
            doc_map = pickle.load(f)
            assert len(doc_map) > 0
            # Check for a specific ID from the json
            assert "QA-H-001" in [doc['id'] for doc in doc_map.values()]
