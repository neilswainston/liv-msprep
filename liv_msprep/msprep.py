'''
(c) University of Liverpool 2020

Licensed under the MIT License.

To view a copy of this license, visit <http://opensource.org/licenses/MIT/>..

@author: neilswainston
'''
# pylint: disable=invalid-name
# pylint: disable=undefined-loop-variable
import os.path

from opentrons import simulate

metadata = {'apiLevel': '2.3',
            'author': 'Neil Swainston <neil.swainston@liverpool.ac.uk>'}


_REAGENT_PLATE_TYPE = 'agilent_1_reservoir_290ml'
_SAMPLE_PLATE_TYPE = 'opentrons_24_aluminumblock_nest_1.5ml_screwcap'
_DEST_PLATE_TYPE = '4titude_96_wellplate_200ul'

_SAMPLE_PLATE_LAST = 'A2'
_NUM_REPS = 4


def run(protocol):
    '''Run protocol.'''
    # Setup:
    p300_single, p300_multi, reag_plt, src_plt, int_plt, dest_plt = \
        _setup(protocol)

    # Plate:
    for src_idx, src_well in enumerate(src_plt.wells()):
        p300_single.distribute(
            75,
            src_well,
            int_plt.wells()[src_idx * _NUM_REPS:(src_idx + 1) * _NUM_REPS])

        if src_well == src_plt[_SAMPLE_PLATE_LAST]:
            break

    protocol.pause('Put %s in vacuum drier.\n' % src_plt)

    # Resuspend:
    for col in range(_get_num_cols()):
        p300_multi.transfer(
            40,
            reag_plt['A1'],
            int_plt.columns()[col],
            mix_after=(3, 40))

    protocol.pause(
        'Centrifuge %s (remove bubbles and any particulates).\n' % src_plt)

    # Pool:
    for dest_idx, dest_well in enumerate(dest_plt.wells()):
        p300_single.consolidate(
            40,
            int_plt.wells()[dest_idx * _NUM_REPS:(dest_idx + 1) * _NUM_REPS],
            dest_well)

        if dest_well == dest_plt[_SAMPLE_PLATE_LAST]:
            break


def _setup(protocol):
    '''Setup.'''
    # Add temp deck:
    temp_deck = protocol.load_module('tempdeck', 7)
    temp_deck.set_temperature(4)

    # Setup tip racks:
    tip_racks_200 = \
        [protocol.load_labware('opentrons_96_filtertiprack_200ul', 4)]

    # Add pipette:
    p300_single = protocol.load_instrument(
        'p300_single', 'left', tip_racks=tip_racks_200)

    p300_multi = protocol.load_instrument(
        'p300_multi', 'right', tip_racks=tip_racks_200)

    # Add plates:
    reag_plt = protocol.load_labware(_REAGENT_PLATE_TYPE, 5, 'reagent')
    src_plt = temp_deck.load_labware(_SAMPLE_PLATE_TYPE, 'source')
    int_plt = protocol.load_labware(_DEST_PLATE_TYPE, 8, 'intermidiate')
    dest_plt = protocol.load_labware(_DEST_PLATE_TYPE, 6, 'destination')

    return p300_single, p300_multi, reag_plt, src_plt, int_plt, dest_plt


def _get_num_cols():
    '''Get number of sample columns.'''
    return int(_SAMPLE_PLATE_LAST[1:])


def main():
    '''main method.'''
    filename = os.path.realpath(__file__)

    with open(filename) as protocol_file:
        runlog, _ = simulate.simulate(protocol_file, filename)
        print(simulate.format_runlog(runlog))


if __name__ == '__main__':
    main()
