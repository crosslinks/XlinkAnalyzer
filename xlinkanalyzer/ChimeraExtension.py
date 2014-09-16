from chimera.extension import EMO, manager

class XlinkAnalyzer_EMO(EMO):

    def name(self):
        return 'Xlink Analyzer'
    def description(self):
        return 'Xlink Analyzer modeling visualization'
    def categories(self):
        return ['Utilities']
    def icon(self):
        return None
    def activate(self):
        self.module('gui').show_dialog()
        return None

manager.registerExtension(XlinkAnalyzer_EMO(__file__))
