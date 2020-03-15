from utils import error
from struct import pack
from lark import Lark
from constants import OPCODES


class Compiler:
    def __init__(self, file):
        super(Compiler, self).__init__()
        self.out = bytearray()
        self.opcodes = {**{v[0]: (k, v[1], v[3]) for k, v in OPCODES.items() if v}}
        self.file = file
        self.pos = 0
        self.stack = []

    def error(self, msg):
        error(msg)
        exit(1)

    def opcode(self, op):
        opcode, stack_length, returns_value = self.opcodes[op]
        for i in range(0, stack_length):
            item = self.stack.pop()
            if item:
                self.emit(item[0])
                self.emit(item[1])

        # Dummy stack item for as a return value
        if returns_value:
            self.stack.append(None)

        return opcode

    def emit(self, value):
        self.out += pack('<H', value)
        self.pos += 2

    def compile_tree(self, tree):
        for item in tree:
            if item == 'End':
                self.emit(self.opcode('Return'))

    def compile(self):
        with open('world_script.lark') as f:
            grammar = f.read()

        parser = Lark(grammar, start='program', parser='lalr', lexer='standard')
        tree = parser.parse(self.file.read())
        self.compile_tree(tree.children)

        return self.out
