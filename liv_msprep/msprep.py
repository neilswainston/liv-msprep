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
_SAMPLE_PLATE_TYPE = 'opentrons_24_aluminumblock_nest_1.5ml_snapcap'
_DEST_PLATE_TYPE = 'thermo_96_wellplate_450ul'

_SRC_PLATE_LAST = 'D6'
_NUM_REPS = 3


def run(protocol):
    '''Run protocol.'''

    # Setup:
    p300_single, p300_multi, reag_plt, src_plt, dest_plt = _setup(protocol)
    num_src = src_plt.wells().index(src_plt[_SRC_PLATE_LAST]) + 1
    num_repl_wells = len(src_plt.wells()) * _NUM_REPS
    pool_col_idx = num_repl_wells // len(dest_plt.rows())

    # Plate:
    for src_idx, src_well in enumerate(src_plt.wells()[:num_src]):
        repl_idxs = range(src_idx,
                          num_repl_wells,
                          len(src_plt.wells()))

        p300_single.distribute(
            75,
            src_well,
            [dest_plt.wells()[idx] for idx in repl_idxs],
            # air_gap=20,
            disposal_volume=0,
            trash=False)

    protocol.pause('Put %s in vacuum drier.\n' % dest_plt)

    # Resuspend:
    for col_idx in range(_NUM_REPS):
        repl_idxs = range(col_idx, pool_col_idx, _NUM_REPS)
        repl_wells = [dest_plt.columns()[idx] for idx in repl_idxs]

        p300_multi.transfer(
            40,
            reag_plt['A1'],
            repl_wells,
            mix_after=(3, 40)
        )

    protocol.pause(
        'Centrifuge %s (remove bubbles and any particulates).\n' % dest_plt)

    p300_single.reset_tipracks()

    # Pool:
    for col_idx in range(_NUM_REPS):
        repl_idxs = range(col_idx, pool_col_idx, _NUM_REPS)
        repl_wells = [dest_plt.columns()[idx] for idx in repl_idxs]

        p300_multi.consolidate(
            40,
            repl_wells,
            dest_plt.columns()[pool_col_idx + col_idx])


def _setup(protocol):
    '''Setup.'''
    # Add temp deck:
    temp_deck = protocol.load_module('tempdeck', 10)
    temp_deck.set_temperature(4)

    # Setup tip racks:
    tip_racks_200 = \
        [protocol.load_labware('opentrons_96_filtertiprack_200ul', 11)]

    # Add pipette:
    p300_single = protocol.load_instrument(
        'p300_single', 'left', tip_racks=tip_racks_200)

    p300_multi = protocol.load_instrument(
        'p300_multi', 'right', tip_racks=tip_racks_200)

    # Add plates:
    reag_plt = protocol.load_labware(_REAGENT_PLATE_TYPE, 9, 'reagent')
    src_plt = temp_deck.load_labware(_SAMPLE_PLATE_TYPE, 'source')
    dest_plt = protocol.load_labware(_DEST_PLATE_TYPE, 8, 'destination')

    return p300_single, p300_multi, reag_plt, src_plt, dest_plt


def main():
    '''main method.'''
    filename = os.path.realpath(__file__)

    with open(filename) as protocol_file:
        runlog, _ = simulate.simulate(protocol_file, filename)
        print(simulate.format_runlog(runlog))


if __name__ == '__main__':
    main()
