
def test_commands():
    tool = ChoiceTool()

    INPUTS = [
        ("Add to list medium: watercolor, oil", "add", "medium", "watercolor, oil"),
        ("Clear list medium", "clear", "medium", None),
        ("Challenge me", "challenge", None, None),
        ("Hey, what's up", None)
    ]

    for input in INPUTS:
        m = tool.get_command_for(input[0])
        if input[1] is None:
            assert m is None
        else:
            assert m is not None
            assert m[0] == input[1]
            assert m[1] == input[2]
            assert m[2] == input[3]
