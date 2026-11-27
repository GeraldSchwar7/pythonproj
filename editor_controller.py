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
            "Paste",
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
        if clip is None or not hasattr(timeline, "copy_clip_to_clipboard"):
            return None

        return timeline.copy_clip_to_clipboard(clip)

    def paste_at_position(self, timeline_x, timeline_y):
        return self.workspace.timeline.paste_clip_at_position(
            timeline_x,
            timeline_y
        )

    def cut_selected(self, split_time=None):
        timeline = self.workspace.timeline
        clip = self.get_selected_clip()
        if clip is None:
            return False

        if split_time is None:
            return timeline.split_clip_at_playhead(clip)

        return timeline.split_clip_at_time(clip, split_time)

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
