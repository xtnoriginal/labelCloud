class UnifiedAnnotationController:
    def __init__(self):
        self.items = []  # Can hold both BBox and Point objects
        self.active_index = None

    def add_item(self, item):
        self.items.append(item)
        self.active_index = len(self.items) - 1

    def get_active_item(self):
        if self.active_index is not None and 0 <= self.active_index < len(self.items):
            return self.items[self.active_index]
        return None

    def set_active_item(self, index):
        if 0 <= index < len(self.items):
            self.active_index = index
