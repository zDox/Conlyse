class PageManager:
    def __init__(self):
        self.pages = {}

    def add_page(self, page_id, content):
        self.pages[page_id] = content

    def get_page(self, page_id):
        return self.pages.get(page_id, None)

    def remove_page(self, page_id):
        if page_id in self.pages:
            del self.pages[page_id]