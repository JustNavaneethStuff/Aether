def test_prompt_template_render_logic() -> None:
    content = "Hello {{name}}, your task is {{task}}."
    variables = {"name": "Agent", "task": "research"}
    for key, value in variables.items():
        content = content.replace(f"{{{{{key}}}}}", str(value))
    assert content == "Hello Agent, your task is research."
