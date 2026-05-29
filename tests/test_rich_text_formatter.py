from rich_text_formatter import KeyAction, RichTextFormatter, TypeAction


def _shortcuts(actions):
    return [a.shortcut for a in actions if isinstance(a, KeyAction)]


def _typed(actions):
    return [a.text for a in actions if isinstance(a, TypeAction)]


def test_list_exit_to_paragraph_uses_docs_two_enter_rule():
    formatter = RichTextFormatter(platform="win")

    actions = formatter.parse("- one\nafter")

    assert _shortcuts(actions) == ["Control+Shift+8", "Enter", "Enter"]
    assert _typed(actions) == ["one", "after"]


def test_empty_list_item_is_treated_as_list_item():
    formatter = RichTextFormatter(platform="win")

    actions = formatter.parse("- one\n-\nafter")

    # One Enter to create the empty list item, then Enter+Enter to exit list.
    assert _shortcuts(actions) == ["Control+Shift+8", "Enter", "Enter", "Enter"]
    assert _typed(actions) == ["one", "after"]
