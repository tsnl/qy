#
# Mailbox:
# - contains multiple reports
#

class Mailbox(object):
    def __init__(self):
        super().__init__()
        self.reports = []

    def __str__(self):
        return '\n'.join(map(str, self.reports))
