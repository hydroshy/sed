
import json

class Tool:
    def __init__(self, name, config=None):
        self.name = name
        self.config = config or {}

    def to_dict(self):
        return {'name': self.name, 'config': self.config}

    @staticmethod
    def from_dict(d):
        return Tool(d['name'], d.get('config', {}))

class Job:
    def __init__(self, name, tools=None):
        self.name = name
        self.tools = tools or []  # List[Tool]

    def add_tool(self, tool):
        self.tools.append(tool)

    def remove_tool(self, index):
        if 0 <= index < len(self.tools):
            del self.tools[index]

    def edit_tool(self, index, new_tool):
        if 0 <= index < len(self.tools):
            self.tools[index] = new_tool

    def to_dict(self):
        return {'name': self.name, 'tools': [t.to_dict() for t in self.tools]}

    @staticmethod
    def from_dict(d):
        tools = [Tool.from_dict(td) for td in d.get('tools', [])]
        return Job(d['name'], tools)

class JobManager:
    def __init__(self):
        self.jobs = []  # List[Job]
        self.current_job = None
        self.available_tools = [Tool('OCR'), Tool('EdgeDetection')]

    def add_job(self, job):
        self.jobs.append(job)
        self.current_job = job

    def remove_job(self, index):
        if 0 <= index < len(self.jobs):
            del self.jobs[index]
            if self.jobs:
                self.current_job = self.jobs[0]
            else:
                self.current_job = None

    def save_job(self, path):
        if self.current_job:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.current_job.to_dict(), f, ensure_ascii=False, indent=2)

    def load_job(self, path):
        with open(path, 'r', encoding='utf-8') as f:
            d = json.load(f)
            job = Job.from_dict(d)
            self.add_job(job)
            return job

    def get_tool_list(self):
        return self.available_tools

    def get_job_list(self):
        return self.jobs

    def get_current_job(self):
        return self.current_job
