from playwright.sync_api import sync_playwright, expect
import time

def verify_renju_game():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        # 1. Login
        print("Navigating to home page...")
        page.goto("http://localhost:5000")

        print("Logging in...")
        page.fill("#username", "Verifier")
        page.click("#login-btn")

        # Wait for lobby
        expect(page.locator("#lobby-screen")).to_be_visible()
        print("Lobby visible.")

        # 2. Create PvC Room
        print("Creating PvC Room...")
        page.fill("#room-name", "VerifyRoom")
        page.select_option("#game-type", "pvc")
        page.click("#create-room-btn")

        # Wait for game screen
        expect(page.locator("#game-screen")).to_be_visible()
        print("Game screen visible.")

        # 3. Make a move (Black plays first, so user plays)
        # Board is generated. Click center (7, 7)
        # Grid is 15x15.
        # cell selector: .cell[data-x='7'][data-y='7']
        print("Making a move at 7,7...")
        cell = page.locator(".cell[data-x='7'][data-y='7']")
        cell.click()

        # 4. Wait for move to appear
        # Black stone should appear
        expect(cell.locator(".stone.black")).to_be_visible()
        print("Black stone verified.")

        # 5. Wait for Computer move (White stone)
        # It might take a moment.
        # We look for any white stone.
        print("Waiting for computer move...")
        expect(page.locator(".stone.white")).to_be_visible(timeout=5000)
        print("White stone verified.")

        # 6. Screenshot
        print("Taking screenshot...")
        page.screenshot(path="verification/renju_game.png")
        print("Screenshot saved to verification/renju_game.png")

        browser.close()

if __name__ == "__main__":
    verify_renju_game()
