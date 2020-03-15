from utils import error
from struct import unpack, pack
from lark import Lark, Token
from constants import OPCODES, SPECIAL_VARS, SAVEMAP_VARS, MODELS


class Compiler:
    def __init__(self, file):
        super(Compiler, self).__init__()
        self.out = bytearray()
        self.opcodes = {**{v[0]: (k, v[1], v[2]) for k, v in OPCODES.items() if v}}
        self.constants = {**{v: k for k, v in SPECIAL_VARS.items() if v},
                          **{v: k for k, v in SAVEMAP_VARS.items() if v},
                          **{v: k for k, v in MODELS.items() if v}}
        self.file = file
        self.pos = 0
        self.stack = []

    def error(self, msg):
        error(msg)
        exit(1)

    def emit(self, value):
        self.out += pack('<H', value)
        self.pos += 2

    def emit_value(self, value):
        if isinstance(value, Token) and not str(value).isdecimal():
            if str(value) in self.constants:
                self.emit(int(self.constants[str(value)]))
        else:
            self.emit(int(value))

    def emit_opcode(self, opcode):
        opcode = self.opcodes[opcode]
        self.emit(opcode[0])

    def opcode(self, opcode, args):
        self.compile_tree(args.children, opcode)
        self.emit_opcode(opcode)
        if self.opcodes[opcode][2] > 0:
            self.emit_value(args.children[0].children[0])

    def compile_tree(self, tree, parent = None):
        for item in tree:
            if item == 'End':
                self.emit_opcode('Return')
            elif item == 'EndIf':
                pass  # Mark end of if
            elif item.data == 'if_stmt':
                pass  # Same as Opcode
            elif item.data == 'goto_stmt':
                pass  # GoTo children[0]
            elif item.data == 'label':
                pass  # Label children[0]
            elif item.data == 'expr_add':
                self.opcode('Add', item)
            elif item.data == 'value':
                if parent and self.opcodes[parent][2] > 0:
                    continue

                self.emit_opcode('Value')
                value = item.children[0]
                if len(value) > 2 and value[:2] == '0x':
                    value = unpack('>H', bytes.fromhex(item.children[0][2:]))[0]

                self.emit_value(value)
            elif item.data == 'opcode':
                opcode = item.children[0]
                args = item.children[1]
                self.opcode(opcode, args)

    def compile(self):
        with open('world_script.lark') as f:
            grammar = f.read()

        parser = Lark(grammar, start='program', parser='lalr', lexer='standard')
        tree = parser.parse(self.file.read())
        self.compile_tree(tree.children)

        return self.out
