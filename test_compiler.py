from unittest import TestCase
from io import StringIO

from compiler import Compiler
from lark import Lark


class CompilerTest(TestCase):
    @staticmethod
    def assert_compiled(input, output, offset: int = 0):
        file_mock = StringIO(input)
        compiler = Compiler(file_mock, offset)
        compiled = bytes(compiler.compile()).hex()
        expected = output.replace(' ', '')
        assert compiled == expected, 'Actual output doesn\'t match expected output:\n'

    def test_end(self):
        CompilerTest.assert_compiled('End', '0302')

    def test_simple_func(self):
        CompilerTest.assert_compiled('PlayLayerAnimation(0x06)', '1001 0600 4a03')
        CompilerTest.assert_compiled('SetEntityAltitudeOffset(-400)', '1001 9001 1500 0b03')

    def test_comment(self):
        CompilerTest.assert_compiled('LoadModel(0) # loads a model', '1001 0000 0003')

    def test_nested_func(self):
        CompilerTest.assert_compiled('WriteTo(TempByte(2), SpecialByte(15))', '1901 0200 1b01 0f00 e000')

    def test_model_func(self):
        CompilerTest.assert_compiled('RunModelFunction($Highwind, 20)', '1001 0300 1802')
        CompilerTest.assert_compiled('RunModelFunction(SpecialByte($PlayerEntityModelId), 29)', '1b01 0800 2102')

    def test_constants(self):
        CompilerTest.assert_compiled('SetEntityDirection(SpecialByte($EntityDirection) + 128)',
                                     '1b01 0400 1001 8000 4000 0403')

    def test_goto(self):
        CompilerTest.assert_compiled('@LABEL_1\nLoadModel(0)\nGoTo @LABEL_1',
                                     '1001 0000 0003 0001 0002 0000')
        CompilerTest.assert_compiled('LoadModel(0)\n@LABEL_1\nLoadModel(1)\nGoTo @LABEL_1',
                                     '1001 0000 0003 0001 1001 0100 0003 0001 0002 0300')
        CompilerTest.assert_compiled('GoTo @LABEL_1\nLoadModel(0)\n@LABEL_1\nLoadModel(1)',
                                     '0002 0600 0001 1001 0000 0003 0001 1001 0100 0003')

    def test_savemap_and_math(self):
        CompilerTest.assert_compiled('WriteTo(SavemapBit(0x0F29, 3), 1)', '1401 2b1c 1001 0100 e000')
        CompilerTest.assert_compiled('WriteTo(SavemapByte(0x0C14), SavemapByte(0x0C14) - 1)',
                                     '1801 8003 1801 8003 1001 0100 4100 e000')
        CompilerTest.assert_compiled('SetEntityAltitudeOffset(SavemapWord(0x0C16) - 3685 >> 1)',
                                     '1c01 9003 1001 650e 4100 1001 0100 5100 0b03')
        CompilerTest.assert_compiled('WriteTo(TempByte(0), SpecialByte($Random8BitNumber) * 9 >> 8)',
                                     '1901 0000 1b01 1000 1001 0900 3000 1001 0800 5100 e000')

    def test_conditions(self):
        CompilerTest.assert_compiled('If GetDistanceToModel($GoldSaucer) <= 100 Then\nUnknown30d()\nEndIf',
                                     '1001 0e00 1900 1001 6400 6200 0102 0a00 0001 0d03')
        CompilerTest.assert_compiled('If SavemapWord($GameProgress) == 1596 Then\n'
                                     'If GetDistanceToPoint(9) <= 256 Then\n'
                                     '  EnterFieldLevel(52, 0)\n'
                                     'EndIf\nEndIf\nLoadModel(0)\nEnd',
                                     '1c01 0000 1001 3c06 7000 0102 1600 0001 1001 0900 1800 1001 0001 6200 0102 '
                                     '1600 0001 1001 3400 1001 0000 1803 0001 1001 0000 0003 0302')

    def test_reset(self):
        CompilerTest.assert_compiled('If SavemapByte(0x0C15) < 5 Then\n'
                                     '  PlaySound(433)\n'
                                     'EndIf\n'
                                     'PlaySound(434)\n'
                                     'End',
                                     '1801 8803 1001 0500 6000 0102 0b00 0001 1001 b101 1d03 0001 1001 b201 1d03 0302')

    def test_complex(self):
        CompilerTest.assert_compiled('''
            If SpecialByte($PlayerEntityModelId) == $Buggy Then
              If Not(SavemapBit($YuffieFlags, 1)) Then
                PlayerControlsEnabled(0)
                RunModelFunction($Buggy, 18)
                GoTo @LABEL_1
              EndIf
              If Not(SavemapBit($YuffieFlags, 2)) Then
                PlayerControlsEnabled(0)
                RunModelFunction($Buggy, 18)
              EndIf
            EndIf
            @LABEL_1
            End''', '1b01 0800 1001 0600 7000 0102 622a 0001 1401 790e 1700 0102 542a 0001 1001 0000 0703 0001 '
                    '1001 0600 1602 0002 622a 0001 1401 7a0e 1700 0102 622a 0001 1001 0000 0703 0001 '
                    '1001 0600 1602 0302', 0x2a3d)


class ParserTest(TestCase):
    @staticmethod
    def parse(prog):
        with open('world_script.lark') as f:
            grammar = f.read()

        parser = Lark(grammar, start='program', parser='lalr', lexer='standard')
        t = parser.parse(prog)
        # print(t.pretty())
        return t.children

    def test_end(self):
        lines = ParserTest.parse("End")

        assert lines[0] == 'End'

    def test_simple_func(self):
        lines = ParserTest.parse("TestFunc()")

        assert lines[0].data == 'opcode'
        assert lines[0].children[0] == 'TestFunc'

    def test_simple_prog(self):
        lines = ParserTest.parse("""
            TestFunc1()
            TestFunc2()
            
            End
        """)

        assert lines[0].data == 'opcode'
        assert lines[0].children[0] == 'TestFunc1'
        assert lines[1].data == 'opcode'
        assert lines[1].children[0] == 'TestFunc2'
        assert lines[2] == 'End'

    def test_func_params(self):
        lines = ParserTest.parse("""
            TestFunc1(123)
            TestFunc1(4, 6)
            TestFunc2(-256)
        """)

        assert lines[0].children[1].data == 'arguments'
        assert len(lines[0].children[1].children) == 1
        assert lines[0].children[1].children[0].data == 'value'
        assert lines[0].children[1].children[0].children[0] == '123'
        assert len(lines[1].children[1].children) == 2
        assert lines[1].children[1].children[1].children[0] == '6'
        assert lines[2].children[1].children[0].data == 'expr_neg'
        assert lines[2].children[1].children[0].children[0].data == 'value'
        assert lines[2].children[1].children[0].children[0].children[0] == '256'

    def test_nested_func(self):
        lines = ParserTest.parse("""
            TestFunc1(TestFunc2())
        """)

        assert lines[0].data == 'opcode'
        assert lines[0].children[0] == 'TestFunc1'
        assert lines[0].children[1].data == 'arguments'
        assert lines[0].children[1].children[0].data == 'opcode'
        assert lines[0].children[1].children[0].children[0] == 'TestFunc2'

    def test_complex_if(self):
        lines = ParserTest.parse("""
            If GetDistanceToModel(SpecialByte($PlayerEntityModelId)) <= 75 Then
            WriteTo(Frames(10))
            EndIf
            TestFunc(123)
            GoTo @LABEL_1
            @LABEL_1
        """)
