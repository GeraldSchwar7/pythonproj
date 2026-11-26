# ============================================================
# EDITOR CONTROLLER
# Central interface for editor actions.
# ============================================================


class EditorController:

    def __init__(self, workspace):

        self.workspace = workspace

    # ========================================================
    # GET SELECTED CLIP
    # ========================================================

    def get_selected_clip(self):

        timeline = self.workspace.timeline

        if hasattr(timeline, "selected_clip"):
            return timeline.selected_clip

        return None

    # ========================================================
    # TOOL SELECTION
    # ========================================================

    def select_tool(
        self,
        tool_name
    ):

        valid_tools = {
            "Select",
            "Move",
            "Copy",
            "Resize",
            "Cut",
            "Camera View"
        }

        if tool_name not in valid_tools:
            return

        self.workspace.tools.activate_tool(
            tool_name
        )

        self.workspace.timeline.set_tool(
            tool_name
        )

    # ========================================================
    # GET SELECTED LAYER
    # ========================================================

    def get_selected_layer(self):

        return self.workspace.timeline.selected_layer

    def copy_selected(self):
        timeline = self.workspace.timeline
        clip = self.get_selected_clip()
        if clip is None or not hasattr(timeline, "duplicate_clip"):
            return None

        return timeline.duplicate_clip(clip)

    def cut_selected(self):
        timeline = self.workspace.timeline
        clip = self.get_selected_clip()
        if clip is None or not hasattr(timeline, "split_clip_at_playhead"):
            return False

        return timeline.split_clip_at_playhead(clip)

    # ========================================================
    # DELETE
    # ========================================================

    def delete_selected(self):

        # Timeline clip gets priority.
        clip = self.get_selected_clip()

        if clip is not None:

            print(
                "EditorController: deleting clip:",
                clip
            )

            # We'll connect this to your exact timeline
            # delete method below.
            if hasattr(
                self.workspace.timeline,
                "delete_clip"
            ):
                self.workspace.timeline.delete_clip(
                    clip
                )

            return

        # Otherwise check layers.

        layer = self.get_selected_layer()

        if layer is not None:

            print(
                "EditorController: deleting layer:",
                layer
            )

            self.workspace.timeline.delete_layer(layer)

            return

        print(
            "EditorController: nothing selected"
        )

    # ========================================================
    # USING THE TOOLS
    # ========================================================
