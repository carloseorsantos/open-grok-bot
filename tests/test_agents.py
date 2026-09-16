from src.agents.orchestrator import ChiefOfStaff
from src.agents.specialists import (
    create_researcher_bot,
    create_web_navigator_bot,
    create_outbound_bot,
    create_code_analyst_bot
)


def test_specialists_creation():
    researcher = create_researcher_bot()
    assert researcher.name == "Researcher"
    assert "search_web" in researcher.tools

    navigator = create_web_navigator_bot()
    assert navigator.name == "Web Navigator"
    assert "browser_navigate" in navigator.tools

    outbound = create_outbound_bot()
    assert outbound.name == "Sales Outbound"
    assert "search_web" in outbound.tools

    coder = create_code_analyst_bot()
    assert coder.name == "Code & Data Analyst"
    assert "run_python_code" in coder.tools
    assert "write_file" in coder.tools


def test_chief_of_staff_tools():
    cos = ChiefOfStaff()
    expected_tools = [
        "get_currency_quote",
        "search_web",
        "search_news",
        "generate_image",
        "run_python_code",
        "browser_navigate",
        "browser_screenshot",
        "save_memory",
        "get_memory",
        "list_memories",
        "create_routine",
        "delete_routine",
        "list_routines",
        "delegate_to_outbound",
        "delegate_to_code_analyst"
    ]
    for tool_name in expected_tools:
        assert tool_name in cos.tools, f"Tool {tool_name} missing from ChiefOfStaff.tools"

    schema_names = [s["function"]["name"] for s in cos.tools_schema]
    for tool_name in expected_tools:
        assert tool_name in schema_names, f"Tool {tool_name} missing from ChiefOfStaff.tools_schema"
