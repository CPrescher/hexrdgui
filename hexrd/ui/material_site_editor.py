import numpy as np

from PySide2.QtCore import QObject, QSignalBlocker, Signal
from PySide2.QtWidgets import QSizePolicy, QTableWidgetItem

from hexrd.material import Material

from hexrd.ui.periodic_table_dialog import PeriodicTableDialog
from hexrd.ui.scientificspinbox import ScientificDoubleSpinBox
from hexrd.ui.ui_loader import UiLoader


COLUMNS = {
    'symbol': 0,
    'occupancy': 1,
    'thermal_factor': 2
}

DEFAULT_U = Material.DFLT_U[0]

OCCUPATION_MIN = 0
OCCUPATION_MAX = 1000

THERMAL_FACTOR_MIN = -1.e7
THERMAL_FACTOR_MAX = 1.e7

U_TO_B = 8 * np.pi ** 2
B_TO_U = 1 / U_TO_B


class MaterialSiteEditor(QObject):

    site_modified = Signal()

    def __init__(self, site, parent=None):
        super().__init__(parent)

        loader = UiLoader()
        self.ui = loader.load_file('material_site_editor.ui', parent)

        self._site = site

        self.occupancy_spinboxes = []
        self.thermal_factor_spinboxes = []

        self.update_gui()

        self.setup_connections()

    def setup_connections(self):
        self.ui.select_atom_types.pressed.connect(self.select_atom_types)
        self.ui.thermal_factor_type.currentIndexChanged.connect(
            self.update_thermal_factor_header)
        self.ui.thermal_factor_type.currentIndexChanged.connect(
            self.update_gui)
        for w in self.site_settings_widgets:
            w.valueChanged.connect(self.update_config)
        self.ui.total_occupancy.valueChanged.connect(
            self.update_occupancy_validity)

    def select_atom_types(self):
        dialog = PeriodicTableDialog(self.atom_types, self.ui)
        if not dialog.exec_():
            return

        self.atom_types = dialog.selected_atoms

    @property
    def site(self):
        return self._site

    @site.setter
    def site(self, v):
        self._site = v
        self.update_gui()

    @property
    def atoms(self):
        return self.site['atoms']

    @property
    def total_occupancy(self):
        return self.site['total_occupancy']

    @total_occupancy.setter
    def total_occupancy(self, v):
        self.site['total_occupancy'] = v

    @property
    def fractional_coords(self):
        return self.site['fractional_coords']

    @property
    def thermal_factor_type(self):
        return self.ui.thermal_factor_type.currentText()

    def U(self, val):
        # Take a thermal factor from a spin box and convert it to U
        type = self.thermal_factor_type
        if type == 'U':
            multiplier = 1
        elif type == 'B':
            multiplier = B_TO_U
        else:
            raise Exception(f'Unknown type: {type}')

        return val * multiplier

    def B(self, val):
        # Take a thermal factor from a spin box and convert it to B
        type = self.thermal_factor_type
        if type == 'U':
            multiplier = U_TO_B
        elif type == 'B':
            multiplier = 1
        else:
            raise Exception(f'Unknown type: {type}')

        return val * multiplier

    def thermal_factor(self, atom):
        # Given an atom, return the thermal factor in either B or U
        type = self.thermal_factor_type
        if type == 'U':
            multiplier = 1
        elif type == 'B':
            multiplier = U_TO_B
        else:
            raise Exception(f'Unknown type: {type}')

        return atom['U'] * multiplier

    @property
    def atom_types(self):
        return [x['symbol'] for x in self.site['atoms']]

    @atom_types.setter
    def atom_types(self, v):
        if v == self.atom_types:
            # No changes needed...
            return

        # Reset all the occupancies
        atoms = self.atoms
        atoms.clear()
        atoms += [{'symbol': x, 'U': DEFAULT_U} for x in v]
        self.reset_occupancies()

        self.update_table()
        self.emit_site_modified_if_valid()

    def create_symbol_label(self, v):
        w = QTableWidgetItem(v)
        return w

    def create_occupancy_spinbox(self, v):
        sb = ScientificDoubleSpinBox(self.ui.table)
        sb.setKeyboardTracking(False)
        sb.setMinimum(OCCUPATION_MIN)
        sb.setMaximum(OCCUPATION_MAX)
        sb.setValue(v)
        sb.valueChanged.connect(self.update_config)

        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sb.setSizePolicy(size_policy)

        self.occupancy_spinboxes.append(sb)
        return sb

    def create_thermal_factor_spinbox(self, v):
        sb = ScientificDoubleSpinBox(self.ui.table)
        sb.setKeyboardTracking(False)
        sb.setMinimum(THERMAL_FACTOR_MIN)
        sb.setMaximum(THERMAL_FACTOR_MAX)
        sb.setValue(v)
        sb.valueChanged.connect(self.update_config)

        size_policy = QSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        sb.setSizePolicy(size_policy)

        self.thermal_factor_spinboxes.append(sb)
        return sb

    def clear_table(self):
        self.occupancy_spinboxes.clear()
        self.thermal_factor_spinboxes.clear()
        self.ui.table.clearContents()

    def update_gui(self):
        widgets = self.site_settings_widgets
        blockers = [QSignalBlocker(w) for w in widgets]  # noqa: F841

        self.ui.total_occupancy.setValue(self.total_occupancy)
        for i, w in enumerate(self.fractional_coords_widgets):
            w.setValue(self.fractional_coords[i])

        self.update_table()

    def update_table(self):
        blocker = QSignalBlocker(self.ui.table)  # noqa: F841

        atoms = self.site['atoms']
        self.clear_table()
        self.ui.table.setRowCount(len(atoms))
        for i, atom in enumerate(atoms):
            w = self.create_symbol_label(atom['symbol'])
            self.ui.table.setItem(i, COLUMNS['symbol'], w)

            w = self.create_occupancy_spinbox(atom['occupancy'])
            self.ui.table.setCellWidget(i, COLUMNS['occupancy'], w)

            w = self.create_thermal_factor_spinbox(self.thermal_factor(atom))
            self.ui.table.setCellWidget(i, COLUMNS['thermal_factor'], w)

        self.update_occupancy_validity()

    def update_thermal_factor_header(self):
        w = self.ui.table.horizontalHeaderItem(COLUMNS['thermal_factor'])
        w.setText(self.thermal_factor_type)

    def update_config(self):
        self.total_occupancy = self.ui.total_occupancy.value()
        for i, w in enumerate(self.fractional_coords_widgets):
            self.fractional_coords[i] = w.value()

        for atom, spinbox in zip(self.atoms, self.occupancy_spinboxes):
            atom['occupancy'] = spinbox.value()

        for atom, spinbox in zip(self.atoms, self.thermal_factor_spinboxes):
            atom['U'] = self.U(spinbox.value())

        self.update_occupancy_validity()

        self.emit_site_modified_if_valid()

    def reset_occupancies(self):
        total = self.total_occupancy
        atoms = self.atoms
        num_atoms = len(atoms)
        for atom in atoms:
            atom['occupancy'] = total / num_atoms

        self.update_occupancy_validity()

    @property
    def site_valid(self):
        return self.occupancies_valid

    @property
    def occupancies_valid(self):
        total_occupancy = sum(x['occupancy'] for x in self.atoms)
        tol = 1.e-6
        return abs(total_occupancy - self.site['total_occupancy']) < tol

    def update_occupancy_validity(self):
        valid = self.occupancies_valid
        color = 'white' if valid else 'red'
        msg = '' if valid else 'Sum of occupancies must equal total occupancy'

        for w in self.occupancy_spinboxes + [self.ui.total_occupancy]:
            w.setStyleSheet(f'background-color: {color}')
            w.setToolTip(msg)

    def emit_site_modified_if_valid(self):
        if not self.site_valid:
            return

        self.site_modified.emit()

    @property
    def fractional_coords_widgets(self):
        return [
            self.ui.coords_x,
            self.ui.coords_y,
            self.ui.coords_z
        ]

    @property
    def site_settings_widgets(self):
        return [
            self.ui.total_occupancy
        ] + self.fractional_coords_widgets
