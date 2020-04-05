from sys import exit
from utils import error
from struct import pack
from lark import Lark, Token, Tree
from constants import OPCODES, SPECIAL_VARS, SAVEMAP_VARS, FIELD_IDS, MODELS


class Compiler:
    def __init__(self, file, offset = 0):
        super(Compiler, self).__init__()
        self.out = bytearray()
        self.opcodes = {**{v[0]: (k, v[1], v[2], v[3]) for k, v in OPCODES.items() if v}}
        self.constants = {**{v: k for k, v in SPECIAL_VARS.items() if v},
                          **{v: k for k, v in SAVEMAP_VARS.items() if v},
                          **{v: k for k, v in FIELD_IDS.items() if v},
                          **{v: k for k, v in MODELS.items() if v}}
        self.file = file
        self.offset = offset
        self.pos = 0
        self.stack = []
        self.jumps = []
        self.labels = []
        self.ifs = []
        self.line = 0

    def error(self, msg):
        error(msg + ' while parsing ' + self.file.name + ' on line ' + str(self.line))
        exit(1)

    def emit(self, value):
        self.out += pack('<H', value)
        self.pos += 1

    def parse_value(self, value):
        if isinstance(value, Token) and not str(value).isdecimal():
            if len(value) > 2 and value[:2] == '0x':
                return int(value, 0)
            elif str(value) in self.constants:
                return int(self.constants[str(value)])
        else:
            return int(value)

    def emit_value(self, value):
        self.emit(self.parse_value(value))

    def emit_opcode(self, opcode):
        opcode = self.opcodes[opcode]
        self.emit(opcode[0])

    def emit_expression(self, item):
        expressions = {
            'expr_lt': 0x60, 'expr_gt': 0x61, 'expr_le': 0x62,'expr_ge': 0x63, 'expr_eq': 0x70,
            'expr_neg': 0x15, 'expr_add': 0x40, 'expr_sub': 0x41, 'expr_mul': 0x30,
            'expr_shl': 0x50, 'expr_shr': 0x51, 'expr_and': 0xb0, 'expr_or': 0xc0,
        }
        opcode = OPCODES[expressions[item.data]]
        self.opcode(opcode[0], item)

    def opcode(self, opcode, args):
        if self.opcodes[opcode][0] == 0x204:  # RunModelFunction:
            value = args.children.pop()
            self.compile_tree(args.children, opcode)
            self.emit(0x204 + int(value.children[0]))
            return

        self.compile_tree(args.children, opcode)
        self.emit_opcode(opcode)
        if self.opcodes[opcode][0] == 0x114:  # SavemapBit
            address = self.parse_value(args.children[0].children[0])
            bit = int(args.children[1].children[0], 0)
            self.emit_value((address - 0xBA4) * 8 + bit)
        elif self.opcodes[opcode][0] in [0x118, 0x11c]:  # SavemapByte/SavemapWord
            address = self.parse_value(args.children[0].children[0])
            self.emit_value(address - 0xBA4)
        elif self.opcodes[opcode][0] == 0x201:  # If
            self.ifs.append(self.pos)
            self.emit_value(0xCDAB)  # Placeholder value
        elif self.opcodes[opcode][2] > 0:
            self.emit_value(args.children[0].children[0])

    def compile_tree(self, tree, parent: str = None):
        for index, item in enumerate(tree):
            if parent is None and item != 'ResetStack':
                self.line += 1

            if item == 'End':
                self.emit_opcode('Return')
            elif item == 'EndIf':
                if len(self.ifs) == 0:
                    self.error("EndIf without a matching If")

                pos = self.ifs.pop()
                self.jumps.append((pos, 'if', pos))
                self.labels.append((self.pos, 'if', pos))
            elif item == 'ResetStack':
                self.emit_opcode(OPCODES[0x100][0])
            elif isinstance(item, Token) and item[0] == '#':
                continue
            elif item.data == 'newline':
                if index == 0 or not isinstance(tree[index - 1], Tree) or tree[index - 1].data != 'newline':
                    self.line -= 1

                continue
            elif item.data == 'if_stmt':
                opcode = OPCODES[0x201][0]
                self.opcode(opcode, item)
            elif item.data == 'goto_stmt':
                self.emit_opcode(OPCODES[0x200][0])
                self.jumps.append((self.pos, 'label', int(item.children[0])))
                self.emit_value(0xCDAB)  # Placeholder value
            elif item.data == 'label':
                self.labels.append((self.pos, 'label', int(item.children[0])))
            elif len(item.data) > 4 and item.data[:5] == 'expr_':
                self.emit_expression(item)
            elif item.data == 'value' or item.data == 'variable':
                if parent and self.opcodes[parent][2] > 0:
                    continue

                self.emit_opcode(OPCODES[0x110][0])
                self.emit_value(item.children[0])
            elif item.data == 'opcode':
                opcode = item.children[0]
                args = item.children[1]
                if not opcode in self.opcodes:
                    self.error('Unknown opcode: ' + opcode)

                self.opcode(opcode, args)

    def apply_jumps(self):
        for jump in self.jumps:
            label = None
            for l in self.labels:
                if l[1] == jump[1] and l[2] == jump[2]:
                    label = l
                    break
            if label is None:
                self.error("Label #%d not found" % jump[2])

            value = pack('<H', label[0] + self.offset)
            self.out[jump[0] * 2] = value[0]
            self.out[jump[0] * 2 + 1] = value[1]

    def add_resets(self, tree):
        new_children = []
        for item in tree.children:
            if isinstance(item, Tree):
                if item.data == 'if_stmt':
                    new_children.append('ResetStack')
                elif item.data == 'opcode':
                    if item.children[0] in self.opcodes:
                        opcode = self.opcodes[item.children[0]]
                        if opcode[1] > 0:
                            new_children.append('ResetStack')
            new_children.append(item)
        tree.children = new_children

    def compile(self):
        with open('world_script.lark') as f:
            grammar = f.read()

        parser = Lark(grammar, start='program', parser='lalr', lexer='standard')
        try:
            tree = parser.parse(self.file.read())
        except Exception as e:
            print("Parse error while parsing " + self.file.name + ":")
            print(e)
            exit(1)
        
        self.add_resets(tree)
        self.compile_tree(tree.children)
        self.apply_jumps()

        return self.out
