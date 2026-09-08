from runtrail.toolkit.local_function_tool import LocalFunctionTool


def test_call_invokes_the_wrapped_function_with_kwargs():
    tool = LocalFunctionTool("add", lambda a, b: a + b)

    assert tool.call(a=2, b=3) == 5
    assert tool.name == "add"
