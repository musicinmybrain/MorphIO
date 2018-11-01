import os

import numpy as np
from nose import tools as nt
from nose.tools import assert_equal, assert_raises
from numpy.testing import assert_array_equal

from morphio import (Morphology, RawDataError, SectionType, SomaError, SomaType,
                     ostream_redirect, set_maximum_warnings)
from utils import (_test_swc_exception, assert_substring, assert_string_equal, captured_output,
                   strip_color_codes, tmp_swc_file, strip_all)

_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")


def test_read_single_neurite():
    with tmp_swc_file('''# A simple neuron consisting of a point soma
                         # and a single branch neurite.
                         1 1 0 4 0 3.0 -1
                         2 3 0 0 2 0.5 1
                         3 3 0 0 3 0.5 2
                         4 3 0 0 4 0.5 3
                         5 3 0 0 5 0.5 4''') as tmp_file:

        n = Morphology(tmp_file.name)

    assert_array_equal(n.soma.points, [[0, 4, 0]])
    assert_array_equal(n.soma.diameters, [6.0])
    nt.eq_(len(n.root_sections), 1)
    nt.eq_(n.root_sections[0].id, 0)
    assert_array_equal(n.soma.points,
                       [[0, 4, 0]])
    nt.eq_(len(n.root_sections), 1)
    assert_array_equal(n.root_sections[0].points,
                       np.array([[0, 0, 2],
                                 [0, 0, 3],
                                 [0, 0, 4],
                                 [0, 0, 5]]))


def test_read_simple():
    simple = Morphology(os.path.join(_path, 'simple.swc'))
    assert_equal(len(simple.root_sections), 2)
    assert_equal(simple.root_sections[0].id, 0)
    assert_equal(simple.root_sections[1].id, 3)

    assert_array_equal(simple.root_sections[0].points, [[0, 0, 0], [0, 5, 0]])

    assert_equal(len(simple.root_sections[0].children), 2)
    assert_equal(simple.root_sections[0].children[0].id, 1)
    assert_equal(simple.root_sections[0].children[1].id, 2)
    # assert_array_equal(simple.root_sections[0].children[0].points, [[0, 5, 0], [-5, 5, 0]])
    # assert_array_equal(simple.root_sections[1].points, [[0, 0, 0], [0, -4, 0]])


def test_repeated_id():
    _test_swc_exception('''# A simple neuron with a repeated id
                       1 1 0 0 1 0.5 -1
                       2 3 0 0 2 0.5 1
                       3 3 0 0 3 0.5 2
                       4 3 0 0 4 0.5 3
                       4 3 0 0 4 0.5 3 # <-- repeated id
                       5 3 0 0 5 0.5 4
                       ''',
                        RawDataError,
                        'Repeated ID: 4\nID already appears here:',
                        ':6:warning')


def test_neurite_followed_by_soma():
    # Capturing the output to keep the unit test suite stdout clean
    with captured_output() as (_, err):
        with ostream_redirect(stdout=True, stderr=True):
            _test_swc_exception('''# An orphan neurite with a soma child
                           1 3 0 0 1 0.5 -1
                           2 3 0 0 2 0.5 1
                           3 3 0 0 3 0.5 2
                           4 3 0 0 4 0.5 3
                           5 3 0 0 5 0.5 4
                           6 1 0 0 0 3.0 5 # <-- soma child''',
                                SomaError,
                                'Found a soma point with a neurite as parent',
                                ':7:error')


def test_read_split_soma():
    with tmp_swc_file('''# A simple neuron consisting of a two-branch soma
                         # with a single branch neurite on each branch.
                         #
                         # initial soma point
                         1 1 1 0 1 4.0 -1
                         # first neurite
                         2 3 0 0 2 0.5 1
                         3 3 0 0 3 0.5 2
                         4 3 0 0 4 0.5 3
                         5 3 0 0 5 0.5 4
                         # soma branch, off initial point
                         6 1 2 0 0 4.0 1
                         7 1 3 0 0 4.0 1
                         # second neurite, off soma branch
                         8 3 0 0 6 0.5 1
                         9 3 0 0 7 0.5 8
                         10 3 0 0 8 0.5 9
                         11 3 0 0 9 0.5 10
                         ''') as tmp_file:
        n = Morphology(tmp_file.name)

    assert_array_equal(n.soma.points,
                       [[1, 0, 1],
                        [2, 0, 0],
                        [3, 0, 0]])

    nt.assert_equal(len(n.root_sections), 2)
    assert_array_equal(n.root_sections[0].points,
                       [[0, 0, 2],
                        [0, 0, 3],
                        [0, 0, 4],
                        [0, 0, 5]])

    assert_array_equal(n.root_sections[1].points,
                       [[0, 0, 6],
                        [0, 0, 7],
                        [0, 0, 8],
                        [0, 0, 9]])

    nt.eq_(len(list(n.iter())), 2)


def test_weird_indent():

    with tmp_swc_file("""

                 # this is the same as simple.swc

# but with a questionable styling

     1 1  0  0 0 1. -1
 2 3  0  0 0 1.  1

 3 3  0  5 0 1.  2
 4 3 -5  5 0 0.  3



 5 3  6  5 0 0.  3
     6 2  0  0 0 1.  1
 7 2  0 -4 0 1.  6

 8 2  6 -4 0         0.  7
 9 2 -5      -4 0 0.  7 # 3 0 0
""") as tmp_file:
        n = Morphology(tmp_file.name)

    simple = Morphology(os.path.join(_path, 'simple.swc'))
    assert_array_equal(simple.points,
                       n.points)


def test_cyclic():
    _test_swc_exception("""1 1  0  0 0 1. -1
                           2 3  0  0 0 1.  1
                           3 3  0  5 0 1.  2
                           4 3 -5  5 0 0.  3
                           5 3  6  5 0 0.  3
                           6 2  0  0 0 1.  6  # <-- cyclic point
                           7 2  0 -4 0 1.  6
                           8 2  6 -4 0 0.  7
                           9 2 -5 -4 0 0.  7""",
                        RawDataError,
                        'Parent ID can not be itself',
                        ':6:error')


def test_simple_reversed():
    with tmp_swc_file('''# This is the same as 'simple.swc',
                         # except w/ leaf nodes before their parents
                         1 1  0  0 0 1. -1
                         2 3 -5  5 0 0.  7
                         3 3  6  5 0 0.  7
                         4 2  6 -4 0 0.  9
                         5 2 -5 -4 0 0.  9
                         6 3  0  0 0 1.  1
                         7 3  0  5 0 1.  6
                         8 2  0  0 0 1.  1
                         9 2  0 -4 0 1.  8 ''') as tmp_file:
        n = Morphology(tmp_file.name)
    assert_array_equal(n.soma.points,
                       [[0, 0, 0]])
    nt.assert_equal(len(n.root_sections), 2)
    assert_array_equal(n.root_sections[0].points,
                       [[0, 0, 0],
                        [0, 5, 0]])
    assert_array_equal(n.root_sections[1].points,
                       [[0, 0, 0],
                        [0, -4, 0]])
    assert_array_equal(n.root_sections[1].children[0].points,
                       [[0, -4, 0],
                        [6, -4, 0]])
    assert_array_equal(n.root_sections[1].children[1].points,
                       [[0, -4, 0],
                        [-5, -4, 0]])


def test_soma_type():
    '''The ordering of IDs is not required'''
    # 1 point soma
    with tmp_swc_file('''1 1 0 0 0 3.0 -1''') as tmp_file:
        assert_equal(Morphology(tmp_file.name).soma_type,
                     SomaType.SOMA_SINGLE_POINT)

    # 2 point soma
    with tmp_swc_file('''1 1 0 0 0 3.0 -1
                         2 1 0 0 0 3.0  1''') as tmp_file:
        assert_equal(Morphology(tmp_file.name).soma_type,
                     SomaType.SOMA_UNDEFINED)

    # > 3 points soma
    with tmp_swc_file('''1 1 0 0 0 3.0 -1
                         2 1 0 0 0 3.0  1
                         3 1 0 0 0 3.0  2
                         4 1 0 0 0 3.0  3
                         5 1 0 0 0 3.0  4''') as tmp_file:
        assert_equal(Morphology(tmp_file.name).soma_type,
                     SomaType.SOMA_CYLINDERS)

    # 3 points soma can be of type SOMA_CYLINDERS or SOMA_NEUROMORPHO_THREE_POINT_CYLINDERS
    # depending on the point layout

    # SOMA_NEUROMORPHO_THREE_POINT_CYLINDERS are characterized by
    # one soma point with 2 children
    with tmp_swc_file('''1 1 0  0 0 3.0 -1
    2 1 0 -3 0 3.0  1
    3 1 0  3 0 3.0  1 # PID is 1''') as tmp_file:
        assert_equal(Morphology(tmp_file.name).soma_type,
                     SomaType.SOMA_NEUROMORPHO_THREE_POINT_CYLINDERS)

    with captured_output() as (_, err):
        with ostream_redirect(stdout=True, stderr=True):

            with tmp_swc_file('''1 1 0  0 0 3.0 -1
                                 2 1 1 -3 0 3.0  1
                                 3 1 0  0 0 3.0  1 # PID is 1''') as tmp_file:
                assert_equal(Morphology(tmp_file.name).soma_type,
                             SomaType.SOMA_NEUROMORPHO_THREE_POINT_CYLINDERS)
                assert_string_equal(
                    err.getvalue(),
                    '''The soma does not conform the three point soma spec
                       The only valid neuro-morpho soma is:
                       1 1 x   y   z r -1
                       2 1 x (y-r) z r  1
                       3 1 x (y+r) z r  1

                       Got:
                       1 1 0 0 0 3 -1
                       2 1 1.000000 (exp. 0.000000) -3.000000 0.000000 3.000000 1
                       3 1 0.000000 0.000000 (exp. 3.000000) 0.000000 3.000000 1
                       ''')

# If this configuration is not respected -> SOMA_CYLINDERS
    with tmp_swc_file('''1 1 0 0 0 3.0 -1
                         2 1 0 0 0 3.0  1
                         3 1 0 0 0 3.0  2 # PID is 2''') as tmp_file:
        assert_equal(Morphology(tmp_file.name).soma_type,
                     SomaType.SOMA_CYLINDERS)


def test_read_weird_ids():
    '''The ordering of IDs is not required'''
    with tmp_swc_file('''1 1 0 0 0 3.0 -1
                         2 3 0 0 2 0.5 1
                         3 3 0 0 3 0.5 2
                         4 3 0 0 4 0.5 3
                         5 3 0 0 5 0.5 4''') as tmp_file:

        normal = Morphology(tmp_file.name)

    with tmp_swc_file('''10000 3 0 0 5 0.5 100 # neurite 4th point
                         3 3 0 0 3 0.5 47      # neurite 2nd point
                         10 1 0 0 0 3.0 -1     # soma
                         47 3 0 0 2 0.5 10     # neurite 1st point
                         100 3 0 0 4 0.5 3     # neurite 3rd point
                         ''') as tmp_file:
        weird = Morphology(tmp_file.name)

    assert_equal(normal, weird)


def test_equality():
    filename = os.path.join(_path, 'simple.swc')
    nt.ok_(not (Morphology(filename) is Morphology(filename)))
    nt.ok_(Morphology(filename) == Morphology(filename))


def test_multiple_soma():
    with assert_raises(SomaError) as obj:
        Morphology(os.path.join(_path, 'multiple_soma.swc'))
    assert_substring(
        ''.join(['Multiple somata found: \n\n',
                 os.path.join(_path, 'multiple_soma.swc:2:error\n\n\n'),
                 os.path.join(_path, 'multiple_soma.swc:11:error')]),
        strip_color_codes(str(obj.exception)))


def test_disconnected_neurite():
    with captured_output() as (_, err):
        with ostream_redirect(stdout=True, stderr=True):
            n = Morphology(os.path.join(_path, 'disconnected_neurite.swc'))
            assert_equal(
                _path + '''/disconnected_neurite.swc:10:warning
Found a disconnected neurite.
Neurites are not supposed to have parentId: -1
(although this is normal if this neuron has no soma)''',
                strip_color_codes(err.getvalue().strip()))