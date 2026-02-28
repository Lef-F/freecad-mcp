class FreeCADMCPAddonWorkbench(Workbench):
    MenuText = "MCP Addon"
    ToolTip = "Addon for MCP Communication"

    def Initialize(self):
        import os
        self.__class__.Icon = os.path.join(os.path.dirname(__file__), "mcp_workbench.svg")

        from rpc_server import rpc_server

        commands = [
            "Start_RPC_Server",
            "Stop_RPC_Server",
            "Toggle_Remote_Connections",
            "Configure_Allowed_IPs",
        ]
        self.appendToolbar("FreeCAD MCP", commands)
        self.appendMenu("FreeCAD MCP", commands)

    def Activated(self):
        pass

    def Deactivated(self):
        pass

    def ContextMenu(self, recipient):
        pass

    def GetClassName(self):
        return "Gui::PythonWorkbench"


Gui.addWorkbench(FreeCADMCPAddonWorkbench())
