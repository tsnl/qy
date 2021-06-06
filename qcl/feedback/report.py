import textwrap


class Report(object):
    def __init__(self, title, desc, notes):
        super().__init__()
        self.title = title
        self.desc = desc
        self.notes = notes

    def __str__(self):
        header = f"{self.title}\n{self.desc}\n"
        body_chunks = [str(note) for note in self.notes]
        body_chunks = list(map(
            lambda txt: "- " + textwrap.indent(txt, '  ')[2:],
            body_chunks
        ))
        return header + '\n'.join(body_chunks)
