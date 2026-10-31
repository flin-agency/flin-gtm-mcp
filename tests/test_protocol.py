import sys

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def test_real_stdio_handshake_tools_and_validation():
    params = StdioServerParameters(
        command=sys.executable, args=["-m", "flin_gtm_mcp"], env={"FLIN_GTM_CREDENTIALS_FILE": ""}
    )
    async with stdio_client(params) as (read, write), ClientSession(read, write) as session:
        await session.initialize()
        response = await session.list_tools()
        tools = {tool.name: tool for tool in response.tools}
        assert len(tools) == 20
        assert "gtm_get_live_version" in tools
        for name, tool in tools.items():
            assert tool.annotations.destructiveHint is False
            if name != "gtm_authenticate":
                assert tool.annotations.readOnlyHint is True
        assert all(
            not any(x in name for x in ("publish", "delete", "update", "create")) for name in tools
        )
        status = await session.call_tool("gtm_auth_status", {})
        assert not status.isError
        bad = await session.call_tool("gtm_get_tag", {"path": "https://evil.example"})
        assert bad.isError
        missing_auth = await session.call_tool("gtm_list_accounts", {})
        assert missing_auth.isError
