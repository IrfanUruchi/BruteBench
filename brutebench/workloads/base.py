class Workload:
    name = "base"

    def setup(self):
        """Prepare workload (optional)"""
        pass

    def run(self):
        """Execute workload"""
        raise NotImplementedError

    def teardown(self):
        """Cleanup after run (optional)"""
        pass

    def execute(self):
        """Standard execution pipeline"""
        self.setup()
        result = self.run()
        self.teardown()
        return result