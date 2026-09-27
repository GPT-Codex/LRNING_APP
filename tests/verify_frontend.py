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

        # 2. Subjects & Curriculum Page
        page.goto('http://127.0.0.1:5000/subjects')
        page.wait_for_selector('h1')
        page.screenshot(path='subjects_curriculum.png')

        # 3. Question Form (Two-Step Dependent Dropdown)
        page.goto('http://127.0.0.1:5000/questions/new')
        page.wait_for_selector('h1')
        page.select_option('#subject_id', index=1)
        page.wait_for_timeout(300)
        page.screenshot(path='exam_workspace.png')

        # 4. Exam Taker Landing
        page.goto('http://127.0.0.1:5000/exam-taker/')
        page.wait_for_selector('h1')
        page.screenshot(path='exam_taker_landing.png')

        # 5. Exam Taker Setup Wizard
        page.goto('http://127.0.0.1:5000/exam-taker/setup')
        page.wait_for_selector('h1')
        page.screenshot(path='exam_taker_setup.png')

        # 6. Question Bank
        page.goto('http://127.0.0.1:5000/questions/')
        page.wait_for_selector('h1')
        page.screenshot(path='question_bank.png')

        # 7. Analytics
        page.goto('http://127.0.0.1:5000/analytics/')
        page.wait_for_selector('h1')
        page.screenshot(path='analytics.png')

        browser.close()
        print("Frontend verification screenshots generated successfully.")

if __name__ == '__main__':
    run_verification()
