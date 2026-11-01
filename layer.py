# ============================================================
# LAYER MODEL
# ============================================================


class Layer:

    def __init__(
        self,
        name
    ):

        self.name = name

        # Is this layer rendered?
        self.visible = True

        # ==================================================
        # VIEWPORT TRANSFORM
        # ==================================================

        self.x = 0
        self.y = 0

        self.scale = 1.0
        self.opacity = 1.0

        # ==================================================
        # TIMELINE MEDIA
        # ==================================================

        self.clips = []

    # ======================================================
    # ADD CLIP
    # ======================================================

    def add_clip(
        self,
        clip
    ):

        self.clips.append(
            clip
        )

    # ======================================================
    # REMOVE CLIP
    # ======================================================

    def remove_clip(
        self,
        clip
    ):

        if clip in self.clips:

            self.clips.remove(
                clip
            )

    # ======================================================
    # GET ACTIVE CLIP
    # ======================================================

    def get_clip_at_time(
        self,
        project_time
    ):

        # Search backwards so that if clips overlap
        # on one layer, the most recently added clip
        # takes priority.

        for clip in reversed(
            self.clips
        ):

            if clip.contains_time(
                project_time
            ):

                return clip

        return None