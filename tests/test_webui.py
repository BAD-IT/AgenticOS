from playwright.sync_api import Page, expect

def test_webui_layout(page: Page):
    """Verify the 3-panel DWM-style layout loads correctly."""
    page.goto("http://localhost:8000/ui/index.html")
    expect(page).to_have_title("Agentic OS")
    expect(page.locator("#left-panel")).to_be_visible()
    expect(page.locator("#center-panel")).to_be_visible()
    expect(page.locator("#right-panel")).to_be_visible()

def test_webui_quick_command(page: Page):
    """Verify that native JS intercepts quick commands without server hit."""
    page.goto("http://localhost:8000/ui/index.html")
    cli_input = page.locator("#cli-input")
    cli_input.fill("/time")
    cli_input.press("Enter")
    chat_history = page.locator("#chat-history")
    expect(chat_history).to_contain_text("Local system time")

def test_webui_workspace_switch(page: Page):
    """Verify that Alt+3 successfully switches workspace logic."""
    page.goto("http://localhost:8000/ui/index.html")
    
    # Dynamically create workspaces 2 and 3 before switching
    page.locator("#add-workspace-btn").click()
    page.locator("#add-workspace-btn").click()
    
    page.keyboard.press("Alt+3")
    status_bar = page.locator("#status")
    expect(status_bar).to_contain_text("Agentic OS - Workspace 3")
