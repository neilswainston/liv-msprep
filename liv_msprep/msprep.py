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
_SAMPLE_PLATE_TYPE = 'opentrons_24_aluminumblock_nest_2ml_snapcap'
_DEST_PLATE_TYPE = 'thermo_96_wellplate_450ul'

_SRC_PLATE_LAST = 'B1'
_NUM_REPS = 3


def run(protocol):
    '''Run protocol.'''

    # Setup:
    p300_single, p300_multi, reag_plt, src_plt, dest_plt = _setup(protocol)

    num_src = src_plt.wells().index(src_plt[_SRC_PLATE_LAST]) + 1
    num_repl_wells = len(src_plt.wells()) * _NUM_REPS
    pool_col_idx = num_repl_wells // len(dest_plt.rows())

    # Plate:
    protocol.comment('\nPlate')
    _plate(p300_single, src_plt, dest_plt, num_src, num_repl_wells)

    protocol.pause('Put %s in vacuum drier.\n' % dest_plt)

    # Resuspend:
    protocol.comment('\nResuspend')
    _resuspend(p300_multi, reag_plt, dest_plt, num_src, pool_col_idx)
    p300_multi.reset_tipracks()

    # Mix:
    protocol.comment('\nMix')
    _mix(p300_multi, dest_plt, num_src, pool_col_idx)
    p300_multi.reset_tipracks()

    protocol.pause(
        'Centrifuge %s (remove bubbles and any particulates).\n' % dest_plt)

    # Pool:
    protocol.comment('\nPool')
    _pool(protocol, p300_multi, dest_plt, num_src, pool_col_idx)


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
        'p300_single', 'right', tip_racks=tip_racks_200)

    p300_multi = protocol.load_instrument(
        'p300_multi', 'left', tip_racks=tip_racks_200)

    # Add plates:
    reag_plt = protocol.load_labware(_REAGENT_PLATE_TYPE, 9, 'reagent')
    src_plt = temp_deck.load_labware(_SAMPLE_PLATE_TYPE, 'source')
    dest_plt = protocol.load_labware(_DEST_PLATE_TYPE, 8, 'destination')

    return p300_single, p300_multi, reag_plt, src_plt, dest_plt


def _plate(pipette, src_plt, dest_plt, num_src, num_repl_wells):
    '''Plate.'''
    for src_idx, src_well in enumerate(src_plt.wells()[:num_src]):
        repl_idxs = range(src_idx,
                          num_repl_wells,
                          len(src_plt.wells()))

        pipette.distribute(
            75,
            src_well,
            [dest_plt.wells()[idx] for idx in repl_idxs],
            disposal_volume=0,
            trash=False)


def _resuspend(pipette, reag_plt, dest_plt, num_src, pool_col_idx):
    '''Resuspend.'''
    pipette.pick_up_tip()

    for col_idx in range(min(num_src // len(dest_plt.rows()) + 1, _NUM_REPS)):
        repl_idxs = range(col_idx, pool_col_idx, _NUM_REPS)
        repl_wells = [dest_plt.columns()[idx][0] for idx in repl_idxs]

        pipette.distribute(
            40,
            reag_plt['A1'],
            [wells.top() for wells in repl_wells],
            disposal_volume=0,
            new_tip='never'
        )

        # Blow-out over last column:
        pipette.blow_out(repl_wells[-1].top())

    pipette.drop_tip()


def _mix(pipette, dest_plt, num_src, pool_col_idx):
    '''Mix.'''
    for col_idx in range(min(num_src // len(dest_plt.rows()) + 1, _NUM_REPS)):
        repl_idxs = range(col_idx, pool_col_idx, _NUM_REPS)
        repl_wells = [dest_plt.columns()[idx][0] for idx in repl_idxs]

        pipette.pick_up_tip()

        for well in repl_wells:
            pipette.mix(5, 15, well.bottom(0.5))

        pipette.return_tip()


def _pool(protocol, pipette, dest_plt, num_src, pool_col_idx):
    '''Pool.'''
    old_aspirate, old_dispense, _ = \
        _set_flow_rate(protocol, pipette, aspirate=50, dispense=100)

    for col_idx in range(min(num_src // len(dest_plt.rows()) + 1, _NUM_REPS)):
        repl_idxs = range(col_idx, pool_col_idx, _NUM_REPS)
        repl_wells = [dest_plt.columns()[idx]
                      for idx in repl_idxs]

        dest_well = dest_plt.columns()[pool_col_idx + col_idx]

        pipette.consolidate(
            35,
            repl_wells,
            dest_well)

        # Blow-out over last column:
        pipette.blow_out(dest_well[0].top())

    _set_flow_rate(protocol, pipette, aspirate=old_aspirate,
                   dispense=old_dispense)


def _set_flow_rate(protocol, pipette, aspirate=None, dispense=None,
                   blow_out=None):
    '''Set flow rates.'''
    old_aspirate = pipette.flow_rate.aspirate
    old_dispense = pipette.flow_rate.dispense
    old_blow_out = pipette.flow_rate.blow_out

    if aspirate and aspirate != old_aspirate:
        protocol.comment('Updating aspirate from %i to %i'
                         % (old_aspirate, aspirate))
        pipette.flow_rate.aspirate = aspirate

    if dispense and dispense != old_dispense:
        protocol.comment('Updating dispense from %i to %i'
                         % (old_dispense, dispense))
        pipette.flow_rate.dispense = dispense

    if blow_out and blow_out != old_blow_out:
        protocol.comment('Updating blow_out from %i to %i'
                         % (old_blow_out, blow_out))
        pipette.flow_rate.blow_out = blow_out

    return old_aspirate, old_dispense, old_blow_out


def main():
    '''main method.'''
    filename = os.path.realpath(__file__)

    with open(filename) as protocol_file:
        runlog, _ = simulate.simulate(protocol_file, filename)
        print(simulate.format_runlog(runlog))


if __name__ == '__main__':
    main()
