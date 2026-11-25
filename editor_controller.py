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
    # DELETE
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

    # ========================================================
    # GET SELECTED LAYER
    # ========================================================

    def get_selected_layer(self):

        return self.workspace.timeline.selected_layer

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