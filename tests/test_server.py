def test_server_imports_with_supported_mcp_sdk():
    from bahi_mcp.server import mcp

    assert callable(mcp.run)
