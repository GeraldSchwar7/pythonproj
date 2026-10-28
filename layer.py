# ============================================================
# LAYER MODEL
# ============================================================

class Layer:

    def __init__(self, name, image=None):

        self.name = name
        self.image = image

        self.visible = True

        self.x = 0
        self.y = 0

        self.scale = 1.0
        self.opacity = 1.0

        self.clips = []
        

