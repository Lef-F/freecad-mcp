class FreeCADMCPAddonWorkbench(Workbench):
    MenuText = "MCP Addon"
    ToolTip = "Addon for MCP Communication"

    def Initialize(self):
        import os
        from rpc_server import rpc_server

        # __file__ is not available in FreeCAD's exec() scope; derive the addon dir
        # from rpc_server's __file__ instead (rpc_server/rpc_server.py → FreeCADMCP/)
        addon_dir = os.path.dirname(os.path.dirname(rpc_server.__file__))
        self.__class__.Icon = os.path.join(addon_dir, "mcp_workbench.svg")

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
