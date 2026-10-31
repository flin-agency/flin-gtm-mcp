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
        assert len(tools) == 34
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

        assert len((await session.list_prompts()).prompts) == 3
        assert len((await session.list_resources()).resources) == 2
        assert len((await session.list_resource_templates()).resourceTemplates) == 2
        guide = await session.read_resource("gtm://best-practices")
        assert "untrusted" in guide.contents[0].text
        prompt = await session.get_prompt("audit_container", {"container_path": "accounts/1/containers/2"})
        assert "gtm_get_live_version" in prompt.messages[0].content.text
        bad = await session.call_tool("gtm_get_folder_entities", {"path": "accounts/1:publish"})
        assert bad.isError
        bad = await session.call_tool("gtm_lookup_container", {"tag_id": "GTM-A", "destination_id": "AW-1"})
        assert bad.isError
