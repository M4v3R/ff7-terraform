from sys import exit
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
            if len(value) > 2 and value[:2] == '0x':
                self.emit(int(value, 0))
            elif str(value) in self.constants:
                self.emit(int(self.constants[str(value)]))
        else:
            self.emit(int(value))

    def emit_opcode(self, opcode):
        opcode = self.opcodes[opcode]
        self.emit(opcode[0])

    def emit_expression(self, item):
        expressions = {
            'expr_lt': 0x60, 'expr_gt': 0x61, 'expr_le': 0x62,'expr_ge': 0x63, 'expr_eq': 0x70,
            'expr_add': 0x40, 'expr_sub': 0x41, 'expr_mul': 0x30,
            'expr_shl': 0x50, 'expr_shr': 0x51, 'expr_and': 0x80, 'expr_or': 0xa0,
        }
        opcode = OPCODES[expressions[item.data]]
        self.opcode(opcode[0], item)

    def opcode(self, opcode, args):
        self.compile_tree(args.children, opcode)
        self.emit_opcode(opcode)
        if self.opcodes[opcode][0] == 0x114:  # SavemapBit
            address = int(args.children[0].children[0], 0)
            bit = int(args.children[1].children[0], 0)
            self.emit_value((address - 0xBA4) * 8 + bit)
        elif self.opcodes[opcode][0] in [0x118, 0x11c]:  # SavemapByte/SavemapWord
            address = int(args.children[0].children[0], 0)
            self.emit_value((address - 0xBA4) * 8)
        elif self.opcodes[opcode][2] > 0:
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
            elif len(item.data) > 4 and item.data[:5] == 'expr_':
                self.emit_expression(item)
            elif item.data == 'value':
                if parent and self.opcodes[parent][2] > 0:
                    continue

                self.emit_opcode('Value')
                self.emit_value(item.children[0])
            elif item.data == 'opcode':
                opcode = item.children[0]
                args = item.children[1]
                self.opcode(opcode, args)

    def compile(self):
        with open('world_script.lark') as f:
            grammar = f.read()

        parser = Lark(grammar, start='program', parser='lalr', lexer='standard')
        tree = parser.parse(self.file.read())
        print(tree.pretty())
        self.compile_tree(tree.children)

        return self.out
