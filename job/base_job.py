class BaseJob:
    """
    Lớp cơ sở cho Job quản lý các tool.
    """
    def __init__(self, tools):
        self.tools = tools

    def run(self, frame):
        results = {}
        for tool in self.tools:
            if tool.enabled:
                results[tool.name] = tool.run(frame)
        return results
