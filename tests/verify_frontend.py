from playwright.sync_api import sync_playwright

def run_verification():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()

        # 1. Dashboard
        page.goto('http://127.0.0.1:5000/')
        page.wait_for_selector('h1')
        page.screenshot(path='dashboard.png')

        # 2. Exams List and Exam Workspace
        page.goto('http://127.0.0.1:5000/exams/')
        page.wait_for_selector('h1')
        page.locator('a[title="Edit in Workspace"]').first.click()
        page.wait_for_selector('.workspace-container')
        page.screenshot(path='exam_workspace.png')

        # 3. Question Bank
        page.goto('http://127.0.0.1:5000/questions/')
        page.wait_for_selector('h1')
        page.screenshot(path='question_bank.png')

        # 4. Question Detail
        page.locator('text=Inspect & History').first.click()
        page.wait_for_selector('.timeline')
        page.screenshot(path='question_detail.png')

        # 5. Review Session
        page.goto('http://127.0.0.1:5000/review/')
        page.wait_for_selector('h1')
        if page.locator('text=Practice Active Recall').count() > 0:
            page.locator('text=Practice Active Recall').first.click()
            page.wait_for_selector('.review-card')
            page.screenshot(path='review_session.png')

        # 6. Analytics
        page.goto('http://127.0.0.1:5000/analytics/')
        page.wait_for_selector('#scoreTrendChart')
        page.screenshot(path='analytics.png')

        browser.close()
        print("Frontend verification screenshots generated successfully.")

if __name__ == '__main__':
    run_verification()
