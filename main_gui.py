import os
import sys
import traceback
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QLabel, QLineEdit, QPushButton, 
                             QFileDialog, QComboBox, QCheckBox, QListWidget, 
                             QTableWidget, QTableWidgetItem, QTextEdit, 
                             QSplitter, QGroupBox, QFormLayout, QMessageBox, 
                             QProgressBar, QTabWidget, QHeaderView, QSpacerItem,
                             QSizePolicy, QAbstractItemView)
from PySide6.QtCore import Qt, QThread, Signal, Slot
from PySide6.QtGui import QFont, QColor, QPalette, QIcon

from aedt_utils import EdbHelper

class LogRedirector:
    def __init__(self, signal):
        self.signal = signal

    def write(self, text):
        if text.strip():
            self.signal.emit(text.strip())

    def flush(self):
        pass


class WorkerThread(QThread):
    finished_signal = Signal(object)
    error_signal = Signal(str)
    log_signal = Signal(str)

    def __init__(self, task_type, helper_args, task_args):
        super().__init__()
        self.task_type = task_type
        self.helper_args = helper_args
        self.task_args = task_args

    def run(self):
        try:
            # Setup logs redirection
            sys.stdout = LogRedirector(self.log_signal)
            sys.stderr = LogRedirector(self.log_signal)

            if self.task_type == "load":
                # Initialize helper
                file_path = self.helper_args['file_path']
                version = self.helper_args['version']
                helper = None
                try:
                    helper = EdbHelper(file_path, version)
                    nets = helper.get_nets()
                    components = helper.get_components()
                    self.finished_signal.emit({"nets": nets, "components": components, "helper": helper})
                except Exception as e:
                    if helper:
                        try:
                            helper.close()
                        except:
                            pass
                    raise e

            elif self.task_type == "cutout":
                helper = self.task_args['helper']
                signal_nets = self.task_args['signal_nets']
                reference_nets = self.task_args['reference_nets']
                extent_type = self.task_args['extent_type']
                expansion_size = self.task_args['expansion_size']
                output_path = self.task_args['output_path']

                new_aedb = helper.create_cutout(
                    signal_nets=signal_nets,
                    reference_nets=reference_nets,
                    extent_type=extent_type,
                    expansion_size=expansion_size,
                    output_path=output_path
                )
                self.finished_signal.emit({"new_aedb": new_aedb})

            elif self.task_type == "ports":
                helper = self.task_args['helper']
                signal_nets = self.task_args['signal_nets']
                reference_net = self.task_args['reference_net']
                port_mode = self.task_args['port_mode']

                created_ports = helper.auto_setup_ports(
                    signal_nets=signal_nets,
                    reference_net=reference_net,
                    port_mode=port_mode
                )
                self.finished_signal.emit({"created_ports": created_ports})

            elif self.task_type == "sweep":
                helper = self.task_args['helper']
                start_freq = self.task_args['start_freq']
                stop_freq = self.task_args['stop_freq']
                step_freq = self.task_args['step_freq']
                setup_name = self.task_args['setup_name']
                sweep_name = self.task_args['sweep_name']
                solution_type = self.task_args['solution_type']
                max_passes = self.task_args['max_passes']
                max_delta_s = self.task_args['max_delta_s']
                low_freq = self.task_args['low_freq']
                high_freq = self.task_args['high_freq']
                single_freq = self.task_args['single_freq']
                multi_freqs = self.task_args['multi_freqs']
                multi_deltas = self.task_args.get('multi_deltas', '')
                non_graphical = self.task_args['non_graphical']

                res = helper.setup_broadband_sweep(
                    start_freq=start_freq,
                    stop_freq=stop_freq,
                    step_freq=step_freq,
                    setup_name=setup_name,
                    sweep_name=sweep_name,
                    non_graphical=non_graphical,
                    solution_type=solution_type,
                    max_passes=max_passes,
                    max_delta_s=max_delta_s,
                    low_freq=low_freq,
                    high_freq=high_freq,
                    single_freq=single_freq,
                    multi_freqs=multi_freqs,
                    multi_deltas=multi_deltas
                )
                self.finished_signal.emit({"success": res})

            elif self.task_type == "import_stackup":
                helper = self.task_args['helper']
                xml_path = self.task_args['xml_path']
                res = helper.import_stackup_xml(xml_path=xml_path)
                self.finished_signal.emit({"success": res})

            elif self.task_type == "analyze":
                helper = self.task_args['helper']
                setup_name = self.task_args['setup_name']
                sweep_name = self.task_args.get('sweep_name', 'Sweep1')
                num_cores = self.task_args['num_cores']
                non_graphical = self.task_args['non_graphical']
                do_export = self.task_args.get('export_touchstone', False)
                export_path = self.task_args.get('export_path', '')

                res = helper.run_analysis(
                    setup_name=setup_name,
                    sweep_name=sweep_name,
                    num_cores=num_cores,
                    non_graphical=non_graphical,
                    export_touchstone=do_export,
                    export_path=export_path
                )
                self.finished_signal.emit(res)

        except Exception as e:
            err_msg = traceback.format_exc()
            self.error_signal.emit(err_msg)
        finally:
            # Restore stdout/stderr
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__


class MainWindow(QMainWindow):
    log_signal = Signal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("PyAEDT Auto Configuration Tool")
        self.resize(1200, 800)
        
        self.helper = None
        self.file_path = ""
        self.nets = []
        self.components = []

        self.setup_ui()
        self.apply_dark_theme()
        
        # Connect console logger signal
        self.log_signal.connect(self.append_log)

    def setup_ui(self):
        # Central widget
        central_widget = QWidget(self)
        self.setCentralWidget(central_widget)

        # Main Layout (Horizontal split)
        main_layout = QHBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        # Splitter between controls (left) and data lists (right)
        splitter = QSplitter(Qt.Horizontal)
        main_layout.addWidget(splitter)

        # ----------------- Left Panel (Controls) -----------------
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(10)
        
        # Tab Widget for different modules
        self.control_tabs = QTabWidget()
        left_layout.addWidget(self.control_tabs)

        # Tab 1: File Loading
        load_tab = QWidget()
        load_layout = QFormLayout(load_tab)
        self.file_edit = QLineEdit()
        self.file_edit.setPlaceholderText("Select .brd, .aedb or .aedt file...")
        self.browse_btn = QPushButton("Browse")
        self.browse_btn.setObjectName("browse_btn")
        self.browse_btn.clicked.connect(self.browse_file)
        
        file_row = QHBoxLayout()
        file_row.addWidget(self.file_edit)
        file_row.addWidget(self.browse_btn)
        
        self.version_combo = QComboBox()
        self.version_combo.addItems(["2026.2", "2026.1", "2025.4", "2025.3", "2025.2", "2025.1", "2024.4","2024.3", "2024.2", "2024.1", "2023.4","2023.3","2023.2", "2023.1", "2022.4","2022.3","2022.2"])
        self.version_combo.setCurrentText("2025.1")
        
        self.load_btn = QPushButton("Load Board/Project")
        self.load_btn.clicked.connect(self.load_project)
        
        load_layout.addRow("File Path:", file_row)
        load_layout.addRow("Ansys Version:", self.version_combo)
        load_layout.addRow(self.load_btn)
        self.control_tabs.addTab(load_tab, "1. Import")

        # Tab 2: Layout Cutout
        cutout_tab = QWidget()
        cutout_tab_layout = QVBoxLayout(cutout_tab)
        cutout_tab_layout.setContentsMargins(6, 6, 6, 6)
        cutout_tab_layout.setSpacing(8)

        # 2a. Import Stackup XML (Optional)
        stackup_group = QGroupBox("Import Stackup (Optional)")
        stackup_h_layout = QHBoxLayout(stackup_group)
        self.stackup_path_edit = QLineEdit()
        self.stackup_path_edit.setPlaceholderText("Select stackup .xml file...")
        self.stackup_browse_btn = QPushButton("Browse")
        self.stackup_browse_btn.setObjectName("browse_btn")
        self.stackup_browse_btn.clicked.connect(self.browse_stackup_xml)
        self.stackup_import_btn = QPushButton("Import Stackup")
        self.stackup_import_btn.clicked.connect(self.run_import_stackup)
        self.stackup_import_btn.setEnabled(False)
        stackup_h_layout.addWidget(self.stackup_path_edit, 3)
        stackup_h_layout.addWidget(self.stackup_browse_btn, 0)
        stackup_h_layout.addWidget(self.stackup_import_btn, 0)
        cutout_tab_layout.addWidget(stackup_group)

        # 2b. Layout Cutout Settings
        cutout_group = QGroupBox("Layout Cutout Settings")
        self.cutout_layout = QFormLayout(cutout_group)
        
        self.extent_type_combo = QComboBox()
        self.extent_type_combo.addItems(["Conforming", "ConvexHull", "Bounding"])
        self.extent_type_combo.currentTextChanged.connect(self.on_cutout_type_changed)
        
        self.expansion_edit = QLineEdit("0.1")
        self.expansion_edit.setPlaceholderText("Expansion factor (e.g. 0.1 for 10%)...")
        
        self.output_path_edit = QLineEdit()
        self.output_path_edit.setPlaceholderText("Defaults to [filename]_cutout.aedb")
        
        self.cutout_btn = QPushButton("Run Layout Cutout")
        self.cutout_btn.clicked.connect(self.run_cutout)
        self.cutout_btn.setEnabled(False)

        self.cutout_layout.addRow("Cutout Type:", self.extent_type_combo)
        self.cutout_layout.addRow("Expansion Factor:", self.expansion_edit)
        self.cutout_layout.addRow("Output Path:", self.output_path_edit)
        self.cutout_layout.addRow(self.cutout_btn)
        cutout_tab_layout.addWidget(cutout_group)

        # 2c. Stackup Layers Viewer
        stackup_view_group = QGroupBox("Stackup Layers Viewer")
        stackup_view_layout = QVBoxLayout(stackup_view_group)
        self.stackup_table = QTableWidget()
        self.stackup_table.setColumnCount(5)
        self.stackup_table.setHorizontalHeaderLabels(["Layer Name", "Type", "Material", "Dielectric Fill", "Thickness"])
        self.stackup_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.stackup_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        stackup_view_layout.addWidget(self.stackup_table)
        cutout_tab_layout.addWidget(stackup_view_group)

        self.control_tabs.addTab(cutout_tab, "2. Cutout")

        # Tab 3: Port Setup
        port_tab = QWidget()
        port_layout = QFormLayout(port_tab)
        
        self.ref_net_edit = QLineEdit("GND")
        self.ref_net_edit.setPlaceholderText("Reference ground net name...")
        
        self.ports_btn = QPushButton("Auto-Setup Ports & RLCs")
        self.ports_btn.clicked.connect(self.run_port_setup)
        self.ports_btn.setEnabled(False)

        port_layout.addRow("Reference Net (GND):", self.ref_net_edit)
        port_layout.addRow(self.ports_btn)
        self.control_tabs.addTab(port_tab, "3. Ports")

        # Tab 4: Sweep Config
        sweep_tab = QWidget()
        sweep_main_layout = QVBoxLayout(sweep_tab)
        sweep_main_layout.setContentsMargins(6, 6, 6, 6)
        sweep_main_layout.setSpacing(10)
        
        # 4a. Adaptive Solutions Group Box
        adaptive_group = QGroupBox("Adaptive Solutions")
        adaptive_form = QFormLayout(adaptive_group)
        
        self.setup_name_edit = QLineEdit("Setup1")
        self.solution_type_combo = QComboBox()
        self.solution_type_combo.addItems(["Broadband", "Single", "Multi-frequencies"])
        
        adaptive_form.addRow("Setup Name:", self.setup_name_edit)
        adaptive_form.addRow("Solution Freq Type:", self.solution_type_combo)
        
        # --- Adaptive Solutions: Broadband group ---
        self.broadband_group = QWidget()
        bb_layout = QFormLayout(self.broadband_group)
        bb_layout.setContentsMargins(0, 4, 0, 4)
        self.low_freq_edit = QLineEdit("0.5GHz")
        self.high_freq_edit = QLineEdit("5GHz")
        self.bb_max_passes_edit = QLineEdit("10")
        self.bb_max_delta_s_edit = QLineEdit("0.02")
        bb_layout.addRow("Low Frequency:", self.low_freq_edit)
        bb_layout.addRow("High Frequency:", self.high_freq_edit)
        bb_layout.addRow("Maximum Number of Passes:", self.bb_max_passes_edit)
        bb_layout.addRow("Maximum Delta S:", self.bb_max_delta_s_edit)
        
        # --- Adaptive Solutions: Single group ---
        self.single_group = QWidget()
        single_layout = QFormLayout(self.single_group)
        single_layout.setContentsMargins(0, 4, 0, 4)
        self.single_freq_edit = QLineEdit("5GHz")
        self.single_max_passes_edit = QLineEdit("10")
        self.single_max_delta_s_edit = QLineEdit("0.02")
        single_layout.addRow("Frequency:", self.single_freq_edit)
        single_layout.addRow("Maximum Number of Passes:", self.single_max_passes_edit)
        single_layout.addRow("Maximum Delta S:", self.single_max_delta_s_edit)
        
        # --- Adaptive Solutions: Multi-frequencies group ---
        self.multi_group = QWidget()
        multi_outer = QVBoxLayout(self.multi_group)
        multi_outer.setContentsMargins(0, 4, 0, 4)
        multi_outer.setSpacing(6)
        
        # Frequency table matching Ansys UI (Frequency | Units | Max Delta S)
        self.multi_freq_table = QTableWidget(3, 3)
        self.multi_freq_table.setHorizontalHeaderLabels(["Frequency", "Units", "Max Delta S"])
        self.multi_freq_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.multi_freq_table.verticalHeader().setVisible(False)
        self.multi_freq_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.multi_freq_table.setMaximumHeight(140)
        # Default rows: 0.5GHz, 5GHz, 10GHz with delta 0.02
        default_multi = [("0.5", "GHz", "0.02"), ("5", "GHz", "0.02"), ("10", "GHz", "0.02")]
        for r, (freq, unit, delta) in enumerate(default_multi):
            self.multi_freq_table.setItem(r, 0, QTableWidgetItem(freq))
            unit_combo = QComboBox()
            unit_combo.addItems(["GHz", "MHz", "kHz", "Hz"])
            unit_combo.setCurrentText(unit)
            self.multi_freq_table.setCellWidget(r, 1, unit_combo)
            self.multi_freq_table.setItem(r, 2, QTableWidgetItem(delta))
        
        multi_outer.addWidget(self.multi_freq_table)
        
        # Add / Remove buttons row
        multi_btn_row = QHBoxLayout()
        multi_btn_row.addStretch()
        self.multi_add_btn = QPushButton("Add")
        self.multi_add_btn.setFixedWidth(80)
        self.multi_add_btn.clicked.connect(self.multi_freq_add_row)
        self.multi_remove_btn = QPushButton("Remove")
        self.multi_remove_btn.setFixedWidth(80)
        self.multi_remove_btn.clicked.connect(self.multi_freq_remove_row)
        multi_btn_row.addWidget(self.multi_add_btn)
        multi_btn_row.addWidget(self.multi_remove_btn)
        multi_outer.addLayout(multi_btn_row)
        
        # Max Passes for Multi-frequencies
        multi_passes_row = QHBoxLayout()
        multi_passes_row.addWidget(QLabel("Maximum Number of Passes:"))
        self.multi_max_passes_edit = QLineEdit("10")
        multi_passes_row.addWidget(self.multi_max_passes_edit)
        multi_outer.addLayout(multi_passes_row)
        
        self.solution_type_combo.currentTextChanged.connect(self.on_solution_type_changed)
        
        # Add sub-groups to Adaptive Solutions layout
        adaptive_form.addRow(self.broadband_group)
        adaptive_form.addRow(self.single_group)
        adaptive_form.addRow(self.multi_group)
        
        sweep_main_layout.addWidget(adaptive_group)
        
        # 4b. Frequency Sweep Group Box
        sweep_group = QGroupBox("Frequency Sweep Range")
        sweep_range_form = QFormLayout(sweep_group)
        
        self.sweep_name_edit = QLineEdit("Sweep1")
        self.start_freq_edit = QLineEdit("0.5GHz")
        self.stop_freq_edit = QLineEdit("5GHz")
        self.step_freq_edit = QLineEdit("0.01GHz")
        
        sweep_range_form.addRow("Sweep Name:", self.sweep_name_edit)
        sweep_range_form.addRow("Start Frequency:", self.start_freq_edit)
        sweep_range_form.addRow("Stop Frequency:", self.stop_freq_edit)
        sweep_range_form.addRow("Frequency Step:", self.step_freq_edit)
        
        sweep_main_layout.addWidget(sweep_group)
        
        self.non_graphical_check = QCheckBox("Run Non-Graphical Mode")
        self.non_graphical_check.setChecked(True)
        
        self.sweep_btn = QPushButton("Apply Sweep Setup")
        self.sweep_btn.clicked.connect(self.run_sweep_setup)
        self.sweep_btn.setEnabled(False)
        
        sweep_main_layout.addWidget(self.non_graphical_check)
        sweep_main_layout.addWidget(self.sweep_btn)
        sweep_main_layout.addStretch()
        
        # Call toggle to initialize correct visibility
        self.on_solution_type_changed(self.solution_type_combo.currentText())
        self.control_tabs.addTab(sweep_tab, "4. Sweep")

        # Tab 5: Analyze (Run EM Simulation)
        analyze_tab = QWidget()
        analyze_main_layout = QVBoxLayout(analyze_tab)
        analyze_main_layout.setContentsMargins(6, 6, 6, 6)
        analyze_main_layout.setSpacing(8)

        # --- Analysis Settings ---
        analysis_group = QGroupBox("EM Analysis")
        analyze_layout = QFormLayout(analysis_group)

        self.analyze_setup_edit = QLineEdit("Setup1")
        self.analyze_setup_edit.setPlaceholderText("Setup name to analyze...")

        self.analyze_sweep_edit = QLineEdit("Sweep1")
        self.analyze_sweep_edit.setPlaceholderText("Sweep name for Touchstone export...")

        self.num_cores_edit = QLineEdit("4")
        self.num_cores_edit.setPlaceholderText("Number of CPU cores...")

        self.analyze_non_graphical_check = QCheckBox("Run Non-Graphical Mode")
        self.analyze_non_graphical_check.setChecked(True)

        analyze_layout.addRow("Setup Name:", self.analyze_setup_edit)
        analyze_layout.addRow("Sweep Name:", self.analyze_sweep_edit)
        analyze_layout.addRow("CPU Cores:", self.num_cores_edit)
        analyze_layout.addRow(self.analyze_non_graphical_check)
        analyze_main_layout.addWidget(analysis_group)

        # --- Touchstone Export ---
        touchstone_group = QGroupBox("Touchstone Export")
        ts_layout = QFormLayout(touchstone_group)
        self.export_touchstone_check = QCheckBox("Export Touchstone (e.g. .s10p, .s16p) after analysis")
        self.export_touchstone_check.setChecked(True)
        self.export_path_edit = QLineEdit()
        self.export_path_edit.setPlaceholderText("Auto-generated suffix based on port count (e.g. .s10p) if left blank")
        ts_layout.addRow(self.export_touchstone_check)
        ts_layout.addRow("Output Path:", self.export_path_edit)
        analyze_main_layout.addWidget(touchstone_group)

        # Status label
        self.analyze_status_label = QLabel("")
        self.analyze_status_label.setWordWrap(True)
        self.analyze_status_label.setStyleSheet("color: #a0aec0; font-style: italic; padding: 4px;")
        analyze_main_layout.addWidget(self.analyze_status_label)

        self.analyze_btn = QPushButton("▶  Run EM Analysis")
        self.analyze_btn.setObjectName("analyze_btn")
        self.analyze_btn.clicked.connect(self.run_analyze)
        self.analyze_btn.setEnabled(False)
        analyze_main_layout.addWidget(self.analyze_btn)

        analyze_main_layout.addStretch()
        self.control_tabs.addTab(analyze_tab, "5. Analyze")

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        # Log Console
        log_group = QGroupBox("Execution Log")
        log_layout = QVBoxLayout(log_group)
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        log_layout.addWidget(self.log_console)
        left_layout.addWidget(log_group)

        splitter.addWidget(left_widget)

        # ----------------- Right Panel (Data Browsers) -----------------
        right_tab_widget = QTabWidget()
        
        # Tab 1: Net List Browser
        net_widget = QWidget()
        net_layout = QVBoxLayout(net_widget)
        
        search_layout = QHBoxLayout()
        self.net_search_edit = QLineEdit()
        self.net_search_edit.setPlaceholderText("Search net names (e.g. ANT6, ANT7)...")
        self.net_search_edit.textChanged.connect(self.filter_nets)
        search_layout.addWidget(self.net_search_edit)
        net_layout.addLayout(search_layout)
        
        self.net_list_widget = QListWidget()
        self.net_list_widget.setSelectionMode(QListWidget.MultiSelection)
        net_layout.addWidget(self.net_list_widget)
        right_tab_widget.addTab(net_widget, "Nets Browser")

        # Tab 2: Components Browser
        comp_widget = QWidget()
        comp_layout = QVBoxLayout(comp_widget)
        
        comp_search_layout = QHBoxLayout()
        self.comp_search_edit = QLineEdit()
        self.comp_search_edit.setPlaceholderText("Search component reference designators...")
        self.comp_search_edit.textChanged.connect(self.filter_components)
        comp_search_layout.addWidget(self.comp_search_edit)
        comp_layout.addLayout(comp_search_layout)

        self.comp_table = QTableWidget()
        self.comp_table.setColumnCount(5)
        self.comp_table.setHorizontalHeaderLabels(["Name", "Type", "Pins", "Layer", "Connected Nets"])
        self.comp_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        comp_layout.addWidget(self.comp_table)
        right_tab_widget.addTab(comp_widget, "Components Browser")

        # Tab 3: User Guide
        guide_widget = QWidget()
        guide_layout = QVBoxLayout(guide_widget)
        guide_text = QTextEdit()
        guide_text.setReadOnly(True)
        guide_text.setHtml("""
        <h2 style="color:#4cc9f0;">PyAEDT Automatic Configuration GUI Tool</h2>
        <p>This utility automates the setup of Cadence Allegro PCB layouts (<code>.brd</code>) or Ansys designs (<code>.aedb</code>/<code>.aedt</code>) for HFSS 3D Layout electromagnetic simulations.</p>

        <h3 style="color:#7209b7;">Workflow Overview</h3>
        <table border="0" cellspacing="4" cellpadding="4">
        <tr><td style="color:#4cc9f0; font-weight:bold; vertical-align:top;">Step 1</td>
            <td><b>Import</b> &mdash; Click <i>Browse</i> to select a <code>.brd</code>, <code>.aedb</code>, or <code>.aedt</code> file, choose the Ansys version, and click <i>Load Board/Project</i>. Translation of <code>.brd</code> files may take 1&ndash;3 minutes for large designs.</td></tr>
        <tr><td style="color:#4cc9f0; font-weight:bold; vertical-align:top;">Step 2</td>
            <td><b>Select Nets</b> &mdash; Use the <i>Nets Browser</i> on the right panel to search and select signal nets (e.g. <code>ANT6</code>, <code>ANT7</code>). Selected nets are shared across Cutout, Port, and Sweep steps.</td></tr>
        <tr><td style="color:#4cc9f0; font-weight:bold; vertical-align:top;">Step 3</td>
            <td><b>Layout Cutout &amp; Stackup</b> &mdash; In the <i>2. Cutout</i> tab:<br/><br/>
            &bull; <b>Import Stackup (Optional):</b> Click <i>Browse</i> to select a stackup <code>.xml</code> file and click <i>Import Stackup</i>. The tool automatically parses and registers all materials defined in the XML (such as <code>DS-8502SQ</code>, <code>SOLDERMASK</code>, <code>copper - 5E7</code>) into the EDB database, then loads the stackup layers. The <b>Stackup Layers Viewer</b> below will update to display all layers confirming successful import.<br/>
            &bull; <b>Layout Cutout:</b> Choose the cutout type (default: <b>Conforming</b>; options: <code>Conforming</code>, <code>ConvexHull</code>, <code>Bounding</code>), set the expansion factor (default: <b>0.1</b> representing 10% for all cutout types), and click <i>Run Layout Cutout</i>. A reduced EDB is created and you can auto-load it.</td></tr>
        <tr><td style="color:#4cc9f0; font-weight:bold; vertical-align:top;">Step 4</td>
            <td><b>Auto-Setup Ports &amp; RLCs</b> &mdash; In the <i>3. Ports</i> tab, specify the ground reference net (default: <code>GND</code>) and click <i>Auto-Setup Ports &amp; RLCs</i>.<br/><br/>
            The tool automatically:<br/>
            &bull; Places excitation ports on non-RLC termination pins (ICs, connectors).<br/>
            &bull; Selects the <b>best GND reference pin</b> using a priority order: <b>same component</b> first (for short, clean port paths), then same placement layer, then global fallback.<br/>
            &bull; Deactivates all RLC components on the signal path and replaces them with <b>component ports</b>.</td></tr>
        <tr><td style="color:#4cc9f0; font-weight:bold; vertical-align:top;">Step 5</td>
            <td><b>Sweep &amp; Adaptive Solutions</b> &mdash; In the <i>4. Sweep</i> tab, the settings are grouped into two sections:<br/><br/>
            &bull; <b>Adaptive Solutions (Top Section):</b> Set the adaptive setup name, choose the solution frequency type (<b>Broadband</b>, <b>Single</b>, or <b>Multi-frequencies</b>), and configure the corresponding adaptive settings (adaptive frequencies, maximum passes, and maximum delta S).<br/>
            &bull; <b>Frequency Sweep Range (Bottom Section):</b> Define the sweep name and the sweep frequency range (Start Frequency, Stop Frequency, and Frequency Step).<br/><br/>
            Click <i>Apply Sweep Setup</i> to configure the HFSS 3D Layout simulation.</td></tr>
        <tr><td style="color:#4cc9f0; font-weight:bold; vertical-align:top;">Step 6</td>
            <td><b>Run EM Analysis</b> &mdash; In the <i>5. Analyze</i> tab:<br/><br/>
            <b>EM Analysis:</b> Set the setup name, sweep name, CPU cores, and click <i>Run EM Analysis</i>.<br/>
            &bull; Check <b>Export Touchstone (e.g. .s10p, .s16p)</b> to automatically export S-parameter matrix data after the simulation completes. The tool will auto-detect the number of ports in the design and set the appropriate Touchstone extension (e.g. <code>.s10p</code> or <code>.s16p</code>).<br/>
            &bull; The <b>GUI remains fully responsive</b> while the simulation runs in the background.<br/>
            &bull; Progress and results are reported in real-time in the <b>Execution Log</b> panel.<br/>
            &bull; Upon completion, a status indicator shows whether the analysis succeeded or failed.</td></tr>
        </table>

        <h3 style="color:#7209b7;">Tips</h3>
        <ul>
            <li>Close Ansys Electronics Desktop before loading a project to avoid file lock issues.</li>
            <li>Check the <b>Execution Log</b> panel at the bottom left for detailed progress and error messages.</li>
            <li>The tool is configured for <b>Ansys Electronics Desktop 2025 R1 (v251)</b> by default, and supports versions from 2023 R1 (v231) up to 2025 R2 (v252).</li>
            <li>EM simulations can take minutes to hours. The GUI stays interactive throughout.</li>
            <li>To compile this tool into a standalone <code>.exe</code> executable, run the <code>build_exe.bat</code> script in the project root folder.</li>
        </ul>
        """)
        guide_layout.addWidget(guide_text)
        right_tab_widget.addTab(guide_widget, "User Guide")

        splitter.addWidget(right_tab_widget)
        
        # Adjust splitter sizes
        splitter.setSizes([500, 700])

    def apply_dark_theme(self):
        # Premium Dark Theme Styling QSS
        qss = """
        QMainWindow {
            background-color: #0f1013;
        }
        QWidget {
            color: #e2e8f0;
            font-family: "Segoe UI", -apple-system, BlinkMacSystemFont, Roboto, Helvetica, sans-serif;
            font-size: 13px;
        }
        QGroupBox {
            font-weight: bold;
            font-size: 14px;
            border: 1px solid #272930;
            border-radius: 8px;
            margin-top: 15px;
            padding: 12px;
            background-color: #16171d;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            subcontrol-position: top left;
            left: 12px;
            padding: 0 6px;
            color: #4cc9f0;
        }
        QTabWidget::pane {
            border: 1px solid #272930;
            border-radius: 8px;
            background-color: #16171d;
            top: -1px;
        }
        QTabBar::tab {
            background-color: #101116;
            border: 1px solid #272930;
            border-bottom: none;
            padding: 8px 16px;
            border-top-left-radius: 6px;
            border-top-right-radius: 6px;
            margin-right: 4px;
            color: #a0aec0;
            font-weight: 500;
        }
        QTabBar::tab:selected {
            background-color: #16171d;
            color: #4cc9f0;
            border: 1px solid #272930;
            border-bottom: 1px solid #16171d;
            font-weight: bold;
        }
        QTabBar::tab:hover:!selected {
            background-color: #1a1c23;
            color: #e2e8f0;
        }
        QLineEdit, QComboBox {
            background-color: #1c1e24;
            border: 1px solid #2d3139;
            border-radius: 6px;
            padding: 8px;
            color: #e2e8f0;
        }
        QLineEdit:focus, QComboBox:focus {
            border: 1px solid #4cc9f0;
            background-color: #20222a;
        }
        QComboBox::drop-down {
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 25px;
            border-left-width: 0px;
        }
        QPushButton {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7209b7, stop:1 #4cc9f0);
            color: #ffffff;
            font-weight: bold;
            border: none;
            border-radius: 6px;
            padding: 9px 18px;
        }
        QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #f72585, stop:1 #7209b7);
        }
        QPushButton:pressed {
            background: #7209b7;
        }
        QPushButton:disabled {
            background: #272930;
            color: #718096;
        }
        /* Secondary Outline Button Styling for Browse */
        QPushButton#browse_btn {
            background: #1c1e24;
            border: 1px solid #2d3139;
            color: #e2e8f0;
        }
        QPushButton#browse_btn:hover {
            background: #272930;
            border-color: #4cc9f0;
        }
        QListWidget, QTableWidget {
            background-color: #13141a;
            border: 1px solid #272930;
            border-radius: 8px;
            padding: 6px;
            gridline-color: #1f2026;
            selection-background-color: #2d3748;
            selection-color: #4cc9f0;
        }
        QListWidget::item, QTableWidget::item {
            padding: 6px;
            border-radius: 4px;
        }
        QListWidget::item:hover, QTableWidget::item:hover {
            background-color: #1a1c23;
        }
        QListWidget::item:selected, QTableWidget::item:selected {
            background-color: #2d3748;
            color: #4cc9f0;
            font-weight: bold;
        }
        QTableWidget QHeaderView::section {
            background-color: #16171d;
            color: #4cc9f0;
            padding: 6px;
            border: 1px solid #272930;
            font-weight: bold;
        }
        QTextEdit {
            background-color: #0b0c0f;
            border: 1px solid #21232a;
            border-radius: 8px;
            font-family: "Consolas", "Fira Code", Courier, monospace;
            font-size: 12px;
            color: #39ff14; /* Matrix neon green style for logs */
            padding: 8px;
        }
        QProgressBar {
            border: 1px solid #272930;
            border-radius: 6px;
            text-align: center;
            background-color: #13141a;
            color: #ffffff;
            font-weight: bold;
            height: 18px;
        }
        QProgressBar::chunk {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7209b7, stop:1 #4cc9f0);
            border-radius: 5px;
        }
        QScrollBar:vertical {
            background-color: #101116;
            width: 10px;
            margin: 0px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background-color: #2d3139;
            min-height: 20px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical:hover {
            background-color: #4cc9f0;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QScrollBar:horizontal {
            background-color: #101116;
            height: 10px;
            margin: 0px;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal {
            background-color: #2d3139;
            min-width: 20px;
            border-radius: 5px;
        }
        QScrollBar::handle:horizontal:hover {
            background-color: #4cc9f0;
        }
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
            width: 0px;
        }
        QCheckBox {
            spacing: 8px;
        }
        QCheckBox::indicator {
            width: 18px;
            height: 18px;
            border: 1px solid #2d3139;
            border-radius: 4px;
            background-color: #1c1e24;
        }
        QCheckBox::indicator:unchecked:hover {
            border-color: #4cc9f0;
        }
        QCheckBox::indicator:checked {
            background-color: #4cc9f0;
            border-color: #4cc9f0;
        }
        QCheckBox::indicator:checked:hover {
            background-color: #7209b7;
            border-color: #7209b7;
        }
        QMessageBox {
            background-color: #16171d;
            border: 1px solid #272930;
        }
        QMessageBox QLabel {
            color: #e2e8f0;
            background-color: transparent;
        }
        QMessageBox QPushButton {
            background: #272930;
            color: #e2e8f0;
            border: 1px solid #2d3139;
            border-radius: 6px;
            padding: 6px 14px;
            font-weight: bold;
        }
        QMessageBox QPushButton:hover {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #7209b7, stop:1 #4cc9f0);
            color: #ffffff;
            border: none;
        }
        """
        self.setStyleSheet(qss)

    # ----------------- Actions & Logic -----------------
    
    @Slot(str)
    def append_log(self, message):
        self.log_console.append(message)
        # Scroll to bottom
        self.log_console.ensureCursorVisible()

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Layout/Project File", "", 
            "Ansys/Cadence Files (*.brd *.aedb *.aedt)"
        )
        if file_path:
            self.file_edit.setText(file_path)

    def load_project(self):
        file_path = self.file_edit.text().strip()
        if not file_path:
            QMessageBox.warning(self, "Warning", "Please select a valid file path.")
            return

        if self.helper:
            self.append_log("Closing previous EDB connection...")
            try:
                self.helper.close()
            except Exception as e:
                self.append_log(f"Error closing previous connection: {e}")
            self.helper = None

        self.log_console.clear()
        self.append_log(f"Loading board: {file_path}")
        self.progress_bar.setVisible(True)
        self.load_btn.setEnabled(False)
        self.browse_btn.setEnabled(False)

        # Launch background thread to load project
        helper_args = {
            'file_path': file_path,
            'version': self.version_combo.currentText()
        }
        self.worker = WorkerThread("load", helper_args, None)
        self.worker.finished_signal.connect(self.on_load_finished)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.log_signal.connect(self.append_log)
        self.worker.start()

    def on_load_finished(self, data):
        self.progress_bar.setVisible(False)
        self.load_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)

        self.helper = data['helper']
        self.nets = data['nets']
        self.components = data['components']

        # Populate nets list
        self.net_list_widget.clear()
        self.net_list_widget.addItems(self.nets)

        # Populate components table
        self.comp_table.setRowCount(len(self.components))
        for row, comp in enumerate(self.components):
            self.comp_table.setItem(row, 0, QTableWidgetItem(comp['name']))
            self.comp_table.setItem(row, 1, QTableWidgetItem(comp['type']))
            self.comp_table.setItem(row, 2, QTableWidgetItem(str(comp['numpins'])))
            self.comp_table.setItem(row, 3, QTableWidgetItem(comp['layer']))
            self.comp_table.setItem(row, 4, QTableWidgetItem(", ".join(comp['nets'])))

        self.append_log(f"Successfully loaded EDB design: {self.helper.edb_path}")
        self.append_log(f"Total Nets: {len(self.nets)}")
        self.append_log(f"Total Components: {len(self.components)}")

        # Enable control buttons
        self.cutout_btn.setEnabled(True)
        self.ports_btn.setEnabled(True)
        self.sweep_btn.setEnabled(True)
        self.analyze_btn.setEnabled(True)
        self.stackup_import_btn.setEnabled(True)

        # Update stackup layers viewer
        self.update_stackup_table()

        # Default cutout path suggestion
        self.output_path_edit.setText(self.helper.edb_path.replace(".aedb", "_cutout.aedb"))

    def on_worker_error(self, error_trace):
        self.progress_bar.setVisible(False)
        self.load_btn.setEnabled(True)
        self.browse_btn.setEnabled(True)
        self.cutout_btn.setEnabled(self.helper is not None)
        self.ports_btn.setEnabled(self.helper is not None)
        self.sweep_btn.setEnabled(self.helper is not None)
        self.analyze_btn.setEnabled(self.helper is not None)
        self.stackup_import_btn.setEnabled(self.helper is not None)

        self.append_log(f"\n[ERROR] Task Execution Failed:\n{error_trace}")
        QMessageBox.critical(self, "Error", f"An error occurred during execution. Please check the log console.")

    def filter_nets(self, search_text):
        for i in range(self.net_list_widget.count()):
            item = self.net_list_widget.item(i)
            item.setHidden(search_text.lower() not in item.text().lower())

    def filter_components(self, search_text):
        for row in range(self.comp_table.rowCount()):
            item = self.comp_table.item(row, 0)
            self.comp_table.setRowHidden(row, search_text.lower() not in item.text().lower())

    def on_cutout_type_changed(self, text):
        label = self.cutout_layout.labelForField(self.expansion_edit)
        self.expansion_edit.setText("0.1")
        self.expansion_edit.setPlaceholderText("Expansion factor (e.g. 0.1 for 10%)...")
        if label and isinstance(label, QLabel):
            label.setText("Expansion Factor:")

    def run_cutout(self):
        selected_nets = [item.text() for item in self.net_list_widget.selectedItems()]
        if not selected_nets:
            QMessageBox.warning(self, "Warning", "Please select one or more signal nets to perform cutout.")
            return

        ref_net = self.ref_net_edit.text().strip()
        if ref_net not in self.nets:
            QMessageBox.warning(self, "Warning", f"Reference net '{ref_net}' not found in the design.")
            return

        try:
            expansion = float(self.expansion_edit.text().strip())
        except ValueError:
            QMessageBox.warning(self, "Warning", "Please enter a valid float for expansion margin.")
            return

        output_path = self.output_path_edit.text().strip()
        if not output_path:
            output_path = self.helper.edb_path.replace(".aedb", "_cutout.aedb")

        self.append_log(f"\n[CUTOUT] Starting cutout for signal nets: {selected_nets}")
        self.progress_bar.setVisible(True)
        self.cutout_btn.setEnabled(False)

        helper_args = {'file_path': self.helper.file_path, 'version': self.helper.version}
        task_args = {
            'helper': self.helper,
            'signal_nets': selected_nets,
            'reference_nets': [ref_net],
            'extent_type': self.extent_type_combo.currentText(),
            'expansion_size': expansion,
            'output_path': output_path
        }

        self.worker = WorkerThread("cutout", helper_args, task_args)
        self.worker.finished_signal.connect(self.on_cutout_finished)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.log_signal.connect(self.append_log)
        self.worker.start()

    def on_cutout_finished(self, data):
        self.progress_bar.setVisible(False)
        self.cutout_btn.setEnabled(True)

        new_aedb = data['new_aedb']
        self.append_log(f"[CUTOUT] Layout cutout successfully created at: {new_aedb}")
        
        reply = QMessageBox.question(
            self, "Cutout Complete", 
            "Cutout complete! Would you like to load the cutout design into the tool now to configure ports?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            self.file_edit.setText(new_aedb)
            self.load_project()

    @Slot(str)
    def on_solution_type_changed(self, text):
        self.broadband_group.setVisible(text == "Broadband")
        self.single_group.setVisible(text == "Single")
        self.multi_group.setVisible(text == "Multi-frequencies")

    def multi_freq_add_row(self):
        """Add a new row to the Multi-frequencies adaptive table."""
        row = self.multi_freq_table.rowCount()
        self.multi_freq_table.insertRow(row)
        self.multi_freq_table.setItem(row, 0, QTableWidgetItem("1"))
        unit_combo = QComboBox()
        unit_combo.addItems(["GHz", "MHz", "kHz", "Hz"])
        self.multi_freq_table.setCellWidget(row, 1, unit_combo)
        self.multi_freq_table.setItem(row, 2, QTableWidgetItem("0.02"))

    def multi_freq_remove_row(self):
        """Remove the selected row(s) from the Multi-frequencies adaptive table."""
        selected_rows = sorted(set(idx.row() for idx in self.multi_freq_table.selectedIndexes()), reverse=True)
        if not selected_rows:
            # Remove last row if nothing selected
            if self.multi_freq_table.rowCount() > 1:
                self.multi_freq_table.removeRow(self.multi_freq_table.rowCount() - 1)
            return
        for row in selected_rows:
            if self.multi_freq_table.rowCount() > 1:  # Keep at least one row
                self.multi_freq_table.removeRow(row)

    def run_port_setup(self):
        selected_nets = [item.text() for item in self.net_list_widget.selectedItems()]
        if not selected_nets:
            QMessageBox.warning(self, "Warning", "Please select one or more signal nets in the Nets Browser tab.")
            return

        ref_net = self.ref_net_edit.text().strip()
        if ref_net not in self.nets:
            QMessageBox.warning(self, "Warning", f"Reference net '{ref_net}' not found in the design.")
            return

        self.append_log(f"\n[PORTS] Running auto port and RLC assignment for: {selected_nets} referencing {ref_net}...")
        self.progress_bar.setVisible(True)
        self.ports_btn.setEnabled(False)

        helper_args = {'file_path': self.helper.file_path, 'version': self.helper.version}
        task_args = {
            'helper': self.helper,
            'signal_nets': selected_nets,
            'reference_net': ref_net,
            'port_mode': 'component_port'
        }

        self.worker = WorkerThread("ports", helper_args, task_args)
        self.worker.finished_signal.connect(self.on_ports_finished)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.log_signal.connect(self.append_log)
        self.worker.start()

    def on_ports_finished(self, data):
        self.progress_bar.setVisible(False)
        self.ports_btn.setEnabled(True)

        created_ports = data['created_ports']
        self.append_log(f"[PORTS] Port setup complete. Total ports created: {len(created_ports)}")
        for port in created_ports:
            self.append_log(f" - Created Port: {port}")
            
        QMessageBox.information(
            self, "Port Setup Complete", 
            f"Successfully configured ports/RLCs on the design!\nTotal ports created: {len(created_ports)}"
        )

    def _collect_multi_freq_data(self):
        """Collect multi-frequency entries from the table as a comma-separated string."""
        entries = []
        for r in range(self.multi_freq_table.rowCount()):
            freq_item = self.multi_freq_table.item(r, 0)
            if not freq_item:
                continue
            freq_val = freq_item.text().strip()
            unit_combo = self.multi_freq_table.cellWidget(r, 1)
            unit = unit_combo.currentText() if unit_combo else "GHz"
            if freq_val:
                entries.append(f"{freq_val}{unit}")
        return ",".join(entries)

    def _collect_multi_freq_deltas(self):
        """Collect per-frequency max delta S values from the table."""
        deltas = []
        for r in range(self.multi_freq_table.rowCount()):
            delta_item = self.multi_freq_table.item(r, 2)
            if delta_item:
                deltas.append(delta_item.text().strip())
            else:
                deltas.append("0.02")
        return ",".join(deltas)

    def run_sweep_setup(self):
        self.append_log("\n[SWEEP] Starting frequency sweep configuration...")
        self.progress_bar.setVisible(True)
        self.sweep_btn.setEnabled(False)

        solution_type = self.solution_type_combo.currentText()

        # Collect max_passes and max_delta_s from the active solution-type group
        if solution_type == "Broadband":
            max_passes = self.bb_max_passes_edit.text().strip()
            max_delta_s = self.bb_max_delta_s_edit.text().strip()
        elif solution_type == "Single":
            max_passes = self.single_max_passes_edit.text().strip()
            max_delta_s = self.single_max_delta_s_edit.text().strip()
        else:  # Multi-frequencies
            max_passes = self.multi_max_passes_edit.text().strip()
            max_delta_s = "0.02"  # per-freq deltas handled separately

        helper_args = {'file_path': self.helper.file_path, 'version': self.helper.version}
        task_args = {
            'helper': self.helper,
            'start_freq': self.start_freq_edit.text().strip(),
            'stop_freq': self.stop_freq_edit.text().strip(),
            'step_freq': self.step_freq_edit.text().strip(),
            'setup_name': self.setup_name_edit.text().strip(),
            'sweep_name': self.sweep_name_edit.text().strip(),
            'solution_type': solution_type,
            'max_passes': max_passes,
            'max_delta_s': max_delta_s,
            'low_freq': self.low_freq_edit.text().strip(),
            'high_freq': self.high_freq_edit.text().strip(),
            'single_freq': self.single_freq_edit.text().strip(),
            'multi_freqs': self._collect_multi_freq_data(),
            'multi_deltas': self._collect_multi_freq_deltas(),
            'non_graphical': self.non_graphical_check.isChecked()
        }

        self.worker = WorkerThread("sweep", helper_args, task_args)
        self.worker.finished_signal.connect(self.on_sweep_finished)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.log_signal.connect(self.append_log)
        self.worker.start()

    def on_sweep_finished(self, data):
        self.progress_bar.setVisible(False)
        self.sweep_btn.setEnabled(True)

        success = data['success']
        if success:
            self.append_log("[SWEEP] Sweep setup configuration completed successfully!")
            QMessageBox.information(self, "Sweep Config Complete", "Frequency sweep configured successfully in HFSS 3D Layout!")
        else:
            self.append_log("[SWEEP] Failed to configure sweep via PyAEDT. Please check logs.")
            QMessageBox.critical(self, "Error", "Failed to configure sweep. Check logs for details.")

    def run_analyze(self):
        """Launch EM analysis on the configured setup in a background thread."""
        if not self.helper:
            QMessageBox.warning(self, "Warning", "Please load a project first.")
            return

        setup_name = self.analyze_setup_edit.text().strip()
        if not setup_name:
            QMessageBox.warning(self, "Warning", "Please enter a setup name to analyze.")
            return

        try:
            num_cores = int(self.num_cores_edit.text().strip())
            if num_cores < 1:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Warning", "Please enter a valid positive integer for CPU cores.")
            return

        # Confirm before starting long-running operation
        reply = QMessageBox.question(
            self, "Start EM Analysis",
            f"Start EM simulation on setup '{setup_name}' with {num_cores} cores?\n\n"
            "This may take a long time depending on design complexity.\n"
            "The GUI will remain responsive during the analysis.",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply != QMessageBox.Yes:
            return

        sweep_name = self.analyze_sweep_edit.text().strip() or "Sweep1"
        do_export = self.export_touchstone_check.isChecked()
        export_path = self.export_path_edit.text().strip()

        self.append_log(f"\n[ANALYZE] Starting EM analysis on setup '{setup_name}' with {num_cores} cores...")
        if do_export:
            self.append_log(f"[ANALYZE] Touchstone export enabled. Sweep: {sweep_name}")
        self.progress_bar.setVisible(True)
        self.analyze_btn.setEnabled(False)
        self.analyze_status_label.setText("⏳ EM simulation is running... GUI remains responsive.")
        self.analyze_status_label.setStyleSheet("color: #4cc9f0; font-style: italic; padding: 4px;")

        helper_args = {'file_path': self.helper.file_path, 'version': self.helper.version}
        task_args = {
            'helper': self.helper,
            'setup_name': setup_name,
            'sweep_name': sweep_name,
            'num_cores': num_cores,
            'non_graphical': self.analyze_non_graphical_check.isChecked(),
            'export_touchstone': do_export,
            'export_path': export_path
        }

        self.worker = WorkerThread("analyze", helper_args, task_args)
        self.worker.finished_signal.connect(self.on_analyze_finished)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.log_signal.connect(self.append_log)
        self.worker.start()

    def on_analyze_finished(self, data):
        self.progress_bar.setVisible(False)
        self.analyze_btn.setEnabled(True)

        success = data.get('success', False)
        touchstone_path = data.get('touchstone_path', None)

        if success:
            msg = "✅ EM analysis completed successfully!"
            if touchstone_path:
                msg += f"\n📁 Touchstone: {touchstone_path}"
            self.analyze_status_label.setText(msg)
            self.analyze_status_label.setStyleSheet("color: #39ff14; font-weight: bold; padding: 4px;")
            self.append_log("[ANALYZE] EM analysis completed successfully!")
            if touchstone_path:
                self.append_log(f"[ANALYZE] Touchstone exported: {touchstone_path}")
            QMessageBox.information(self, "Analysis Complete",
                f"EM simulation finished successfully!" +
                (f"\n\nTouchstone exported to:\n{touchstone_path}" if touchstone_path else ""))
        else:
            self.analyze_status_label.setText("❌ EM analysis failed. Check logs for details.")
            self.analyze_status_label.setStyleSheet("color: #f72585; font-weight: bold; padding: 4px;")
            self.append_log("[ANALYZE] EM analysis failed. Please check logs.")
            QMessageBox.critical(self, "Error", "EM analysis failed. Check logs for details.")

    # --- Stackup Import ---
    def browse_stackup_xml(self):
        """Open file dialog to select a stackup XML file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Stackup XML File", "",
            "XML Files (*.xml);;All Files (*)"
        )
        if file_path:
            self.stackup_path_edit.setText(file_path)

    def run_import_stackup(self):
        """Import a stackup XML file into the current EDB design."""
        if not self.helper:
            QMessageBox.warning(self, "Warning", "Please load a project first.")
            return

        xml_path = self.stackup_path_edit.text().strip()
        if not xml_path:
            QMessageBox.warning(self, "Warning", "Please select a stackup XML file.")
            return

        if not os.path.exists(xml_path):
            QMessageBox.warning(self, "Warning", f"File not found: {xml_path}")
            return

        self.append_log(f"\n[STACKUP] Importing stackup from: {xml_path}")
        self.progress_bar.setVisible(True)
        self.stackup_import_btn.setEnabled(False)

        helper_args = {'file_path': self.helper.file_path, 'version': self.helper.version}
        task_args = {
            'helper': self.helper,
            'xml_path': xml_path
        }

        self.worker = WorkerThread("import_stackup", helper_args, task_args)
        self.worker.finished_signal.connect(self.on_stackup_import_finished)
        self.worker.error_signal.connect(self.on_worker_error)
        self.worker.log_signal.connect(self.append_log)
        self.worker.start()

    def on_stackup_import_finished(self, data):
        self.progress_bar.setVisible(False)
        self.stackup_import_btn.setEnabled(True)

        success = data['success']
        if success:
            self.append_log("[STACKUP] Stackup imported successfully!")
            QMessageBox.information(self, "Stackup Import", "Stackup XML imported successfully into the design!")
            self.update_stackup_table()
        else:
            self.append_log("[STACKUP] Stackup import failed. Check logs for details.")
            QMessageBox.critical(self, "Error", "Stackup import failed. Check logs for details.")

    def update_stackup_table(self):
        """Update the stackup layers table in the Cutout tab."""
        if not self.helper:
            self.stackup_table.setRowCount(0)
            return

        try:
            layers = self.helper.get_stackup_info()
            self.stackup_table.setRowCount(len(layers))
            for row, layer in enumerate(layers):
                self.stackup_table.setItem(row, 0, QTableWidgetItem(layer['name']))
                self.stackup_table.setItem(row, 1, QTableWidgetItem(layer['type']))
                self.stackup_table.setItem(row, 2, QTableWidgetItem(layer['material']))
                self.stackup_table.setItem(row, 3, QTableWidgetItem(layer['dielectric_fill']))
                self.stackup_table.setItem(row, 4, QTableWidgetItem(layer['thickness']))
        except Exception as e:
            self.append_log(f"[STACKUP] Failed to update stackup view: {e}")

    def closeEvent(self, event):
        """Ensure that EDB connections are cleanly closed upon exit."""
        if self.helper:
            try:
                self.helper.close()
            except:
                pass
            self.helper = None
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
