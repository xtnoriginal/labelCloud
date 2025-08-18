class UnifiedAnnotationController:
    def __init__(self):
        self.items = []  # Can hold both BBox and Point objects
        self.active_index = None
        self.view: "GUI" = None
    
    def set_view(self, view: "GUI") -> None:
        self.view = view

    def add_item(self, item):
        self.items.append(item)
        self.active_index = len(self.items) - 1

    def get_active_item(self):
        if self.active_index is not None and 0 <= self.active_index < len(self.items):
            return self.items[self.active_index]
        return None
    

    def has_active_item(self):
        return self.active_index is not None and 0 <= self.active_index < len(self.items)

    def set_active_item(self, index):
        if 0 <= index < len(self.items):
            self.active_index = index


    def reset(self):
        self.items = []
        self.active_index = None
        # self.view.status_manager.update_status(
        #     "No point selected.", mode=Mode.DEFAULT
        # )   


    def update_label_list(self) -> None:
        """Updates the list of drawn labels and highlights the active label.

        Should be always called if the bounding boxes changed.
        :return: None
        """
        self.view.label_list.blockSignals(True)  # To brake signal loop
        self.view.label_list.clear()
        for item in self.items:
            self.view.label_list.addItem(item.get_classname())
        if self.has_active_item():
            self.view.label_list.setCurrentRow(self.active_index)
            current_item = self.view.label_list.currentItem()
            if current_item:
                current_item.setSelected(True)
        self.view.label_list.blockSignals(False)


