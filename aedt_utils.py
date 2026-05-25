import os
import sys
import math
import shutil

try:
    import ansys.aedt.core as pyaedt
except ImportError:
    import pyaedt

import pyedb
from pyedb import Edb

class EdbHelper:
    def __init__(self, file_path, version="2025.1"):
        self.file_path = file_path
        self.version = version
        self.edb_path = None
        self.edb = None
        self.temp_dir = None
        
        # Setup environment variable for Ansys
        os.environ["ANSYSEM_ROOT251"] = r"C:\Program Files\ANSYS Inc\v251\AnsysEM"
        
        self.initialize_edb()

    def initialize_edb(self):
        """Initialize the EDB connection. Translates BRD files if necessary."""
        ext = os.path.splitext(self.file_path)[1].lower()
        if ext == ".brd":
            # Translate BRD to AEDB
            self.edb_path = self.file_path.replace(".brd", "_translated.aedb")
            if os.path.exists(self.edb_path):
                shutil.rmtree(self.edb_path, ignore_errors=True)
            print(f"Translating {self.file_path} to EDB folder {self.edb_path}...")
            self.edb = Edb(edbpath=self.file_path, version=self.version)
            self.edb_path = self.edb.edbpath
        elif ext == ".aedb":
            self.edb_path = self.file_path
            print(f"Opening EDB folder {self.edb_path}...")
            self.edb = Edb(edbpath=self.file_path, version=self.version)
        elif ext == ".aedt":
            # For AEDT projects, EDB is stored in the matching .aedb folder in the same directory.
            self.edb_path = self.file_path.replace(".aedt", ".aedb")
            print(f"Opening EDB folder {self.edb_path} matching AEDT project {self.file_path}...")
            self.edb = Edb(edbpath=self.edb_path, version=self.version)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Must be .brd, .aedb, or .aedt.")

    def get_nets(self):
        """Get all net names in the design."""
        if not self.edb:
            return []
        return sorted(list(self.edb.nets.nets.keys()))

    def get_components(self):
        """Get list of components with their metadata."""
        if not self.edb:
            return []
        
        comp_list = []
        for name, comp in self.edb.components.instances.items():
            nets = getattr(comp, 'nets', [])
            comp_type = getattr(comp, 'type', 'Other')
            numpins = getattr(comp, 'numpins', 0)
            layer = getattr(comp, 'placement_layer', 'TOP')
            
            comp_list.append({
                'name': name,
                'type': comp_type,
                'numpins': numpins,
                'layer': layer,
                'nets': nets
            })
        return sorted(comp_list, key=lambda x: x['name'])

    def create_cutout(self, signal_nets, reference_nets, extent_type="ConvexHull", expansion_size=0.05, output_path=None):
        """Create a layout cutout and save to a new AEDB folder.
        
        Args:
            signal_nets: List of signal net names.
            reference_nets: List of reference net names.
            extent_type: Cutout type (Conforming, ConvexHull, Bounding).
            expansion_size: Expansion size in millimeters (default: 0.05 mm).
            output_path: Path to save the cutout AEDB.
        """
        if not self.edb:
            raise RuntimeError("EDB is not loaded.")
        
        if not output_path:
            output_path = self.edb_path.replace(".aedb", "_cutout.aedb")
            
        if os.path.exists(output_path):
            shutil.rmtree(output_path, ignore_errors=True)
            
        print(f"Creating cutout ({extent_type}, {expansion_size}mm margin)...")
        # Convert expansion_size from mm to meters for PyEDB
        expansion_size_meters = expansion_size * 0.001
        
        # Run pyedb cutout
        res = self.edb.cutout(
            signal_nets=signal_nets,
            reference_nets=reference_nets,
            extent_type=extent_type,
            expansion_size=expansion_size_meters,
            output_aedb_path=output_path,
            open_cutout_at_end=False
        )
        print(f"Cutout created successfully at: {output_path}")
        return output_path

    def auto_setup_ports(self, signal_nets, reference_net="GND", port_mode="component_port"):
        """
        Auto configure ports for non-RLC termination points and RLC components.
        - port_mode:
          - "component_port": place circuit ports on non-RLC termination points, and also deactivate RLC components and replace them with component ports.
        """
        if not self.edb:
            raise RuntimeError("EDB is not loaded.")
            
        # Get all GND pins in layout for distance calculation
        gnd_pins = []
        for name, comp in self.edb.components.instances.items():
            for p_name, pin in comp.pins.items():
                if pin.net_name.lower() == reference_net.lower():
                    gnd_pins.append(pin)
                    
        print(f"Found {len(gnd_pins)} ground pins in design.")
        created_ports = []
        
        # 1. Place ports on non-RLC termination points (ICs, Connectors, etc.)
        print("\nConfiguring ports on non-RLC termination points...")
        for comp_name, comp in self.edb.components.instances.items():
            comp_type = getattr(comp, 'type', 'Other')
            numpins = getattr(comp, 'numpins', 0)
            
            # Check if it is a non-RLC component (not Resistor, Capacitor, Inductor)
            is_rlc = comp_type in ['Resistor', 'Capacitor', 'Inductor']
            if is_rlc:
                continue
                
            for pin_name, pin in comp.pins.items():
                if pin.net_name in signal_nets:
                    print(f"Found termination pin: {comp_name}.{pin_name} on net {pin.net_name}")
                    # Find best GND reference pin using priority order:
                    # 1st: GND pins within the SAME component (shortest, cleanest reference)
                    # 2nd: GND pins on the same placement layer in the design
                    # 3rd: Any GND pin in the design (fallback)
                    ref_pin = None
                    min_dist = float('inf')
                    sig_pos = pin.position
                    ref_source = ""
                    
                    # Priority 1: Same-component GND pins
                    same_comp_gnd = [p for p in comp.pins.values()
                                     if p.net_name.lower() == reference_net.lower() and p != pin]
                    if same_comp_gnd:
                        for gp in same_comp_gnd:
                            try:
                                gp_pos = gp.position
                                dist = math.hypot(gp_pos[0] - sig_pos[0], gp_pos[1] - sig_pos[1])
                                if dist < min_dist:
                                    min_dist = dist
                                    ref_pin = gp
                            except Exception:
                                continue
                        if ref_pin:
                            ref_source = "same-component"
                    
                    # Priority 2: Same-layer GND pins in the design
                    if not ref_pin and gnd_pins:
                        same_layer_gnd = [gp for gp in gnd_pins if gp.placement_layer == pin.placement_layer]
                        if same_layer_gnd:
                            for gp in same_layer_gnd:
                                try:
                                    gp_pos = gp.position
                                    dist = math.hypot(gp_pos[0] - sig_pos[0], gp_pos[1] - sig_pos[1])
                                    if dist < min_dist:
                                        min_dist = dist
                                        ref_pin = gp
                                except Exception:
                                    continue
                            if ref_pin:
                                ref_source = "same-layer"
                    
                    # Priority 3: Any GND pin (global fallback)
                    if not ref_pin and gnd_pins:
                        for gp in gnd_pins:
                            try:
                                gp_pos = gp.position
                                dist = math.hypot(gp_pos[0] - sig_pos[0], gp_pos[1] - sig_pos[1])
                                if dist < min_dist:
                                    min_dist = dist
                                    ref_pin = gp
                            except Exception:
                                continue
                        if ref_pin:
                            ref_source = "global-fallback"
                                
                    if ref_pin:
                        port_name = f"Port_{comp_name}_{pin_name}"
                        # Make sure port name is unique
                        idx = 1
                        orig_name = port_name
                        while port_name in list(self.edb.excitations.keys()):
                            port_name = f"{orig_name}_{idx}"
                            idx += 1
                            
                        self.edb.excitation_manager.create_port_on_pins(
                            refdes=comp_name,
                            pins=pin,
                            reference_pins=ref_pin,
                            port_name=port_name
                        )
                        if port_name in list(self.edb.excitations.keys()):
                            created_ports.append(port_name)
                            print(f"Created termination port {port_name} referencing {ref_source} GND pin {ref_pin.component_name}.{ref_pin.name} (layer: {ref_pin.placement_layer}, dist: {min_dist*1000:.3f} mm)")
                    else:
                        print(f"Warning: No ground reference found for termination pin {comp_name}.{pin_name}")

        # 2. Configure RLC components (always replace them with component ports)
        print("\nConfiguring component ports on RLC components...")
        for comp_name, comp in self.edb.components.instances.items():
            comp_type = getattr(comp, 'type', 'Other')
            is_rlc = comp_type in ['Resistor', 'Capacitor', 'Inductor']
            if not is_rlc:
                continue
                
            comp_nets = getattr(comp, 'nets', [])
            connected_signals = [n for n in comp_nets if n in signal_nets]
            if not connected_signals:
                continue
                
            pins = list(comp.pins.values())
            if len(pins) != 2:
                continue
                
            # Deactivate component and replace it with a port across its pins
            res = self.edb.components.add_port_on_rlc_component(component=comp_name, circuit_ports=True)
            if res:
                created_ports.append(comp_name)
                print(f"Created component port on RLC component {comp_name}")

        # Save EDB changes
        self.edb.save()
        return created_ports

    def setup_broadband_sweep(self, start_freq="0.5GHz", stop_freq="5GHz", step_freq="0.01GHz", setup_name="Setup1", sweep_name="Sweep1", non_graphical=True, solution_type="Broadband", max_passes=10, max_delta_s=0.02, low_freq="0.5GHz", high_freq="5GHz", single_freq="5GHz", multi_freqs="0.5,5,10", multi_deltas=""):
        """Open design in PyAEDT HFSS 3D Layout and set up simulation and frequency sweep."""
        if not self.edb_path:
            raise RuntimeError("EDB path is not set.")
            
        print(f"Launching HFSS 3D Layout (non-graphical={non_graphical}) to configure frequency sweep...")
        
        # Close Edb connection first to release file lock
        self.close()
        
        # Clean up stale .aedt and .aedt.lock files to avoid locks
        aedt_file = self.edb_path.replace(".aedb", ".aedt")
        aedt_lock = aedt_file + ".lock"
        for f in [aedt_file, aedt_lock]:
            if os.path.exists(f):
                try:
                    os.remove(f)
                    print(f"Removed stale file: {f}")
                except Exception as e:
                    print(f"Could not remove stale file {f}: {e}")
        
        try:
            from ansys.aedt.core import Hfss3dLayout
            
            # Open project in HFSS 3D Layout
            h3d = Hfss3dLayout(project=self.edb_path, version=self.version, non_graphical=non_graphical)
            
            # Check if setup exists, create if not
            setup = None
            for s in h3d.setups:
                if s.name == setup_name:
                    setup = s
                    break
            
            if not setup:
                setup = h3d.create_setup(name=setup_name)
                print(f"Created setup: {setup_name}")
            else:
                print(f"Using existing setup: {setup_name}")
                
            # Configure adaptive settings based on solution_type
            adaptive_settings = setup.props.get('AdaptiveSettings', {})
            adaptive_settings['DoAdaptive'] = True
            
            if solution_type == "Single":
                adaptive_settings['AdaptType'] = 'kSingle'
                sf = single_freq if "Hz" in single_freq else f"{single_freq}GHz"
                adaptive_settings['SingleFrequencyDataList'] = {
                    'AdaptiveFrequencyData': [
                        {
                            'AdaptiveFrequency': sf,
                            'MaxDelta': str(max_delta_s),
                            'MaxPasses': int(max_passes),
                            'Expressions': []
                        }
                    ]
                }
                print(f"Setting adaptive solution type to Single at {sf} (passes: {max_passes}, delta: {max_delta_s})")
                
            elif solution_type == "Multi-frequencies":
                adaptive_settings['AdaptType'] = 'kMultiFrequencies'
                freq_list = []
                for val in multi_freqs.split(','):
                    val = val.strip()
                    if val:
                        vf = val if "Hz" in val else f"{val}GHz"
                        freq_list.append(vf)
                if not freq_list:
                    freq_list = ["0.5GHz", "5GHz", "10GHz"]
                
                # Parse per-frequency delta S values
                delta_list = []
                if multi_deltas:
                    delta_list = [d.strip() for d in multi_deltas.split(',') if d.strip()]
                
                adaptive_settings['MultiFrequencyDataList'] = {
                    'AdaptiveFrequencyData': [
                        {
                            'AdaptiveFrequency': freq,
                            'MaxDelta': delta_list[i] if i < len(delta_list) else str(max_delta_s),
                            'MaxPasses': int(max_passes),
                            'Expressions': []
                        } for i, freq in enumerate(freq_list)
                    ]
                }
                print(f"Setting adaptive solution type to Multi-frequencies at {freq_list} (passes: {max_passes}, deltas: {delta_list if delta_list else max_delta_s})")
                
            else:  # Broadband (default)
                adaptive_settings['AdaptType'] = 'kBroadBand'
                lf = low_freq if "Hz" in low_freq else f"{low_freq}GHz"
                hf = high_freq if "Hz" in high_freq else f"{high_freq}GHz"
                adaptive_settings['BroadbandFrequencyDataList'] = {
                    'AdaptiveFrequencyData': [
                        {
                            'AdaptiveFrequency': lf,
                            'MaxDelta': str(max_delta_s),
                            'MaxPasses': int(max_passes),
                            'Expressions': []
                        },
                        {
                            'AdaptiveFrequency': hf,
                            'MaxDelta': str(max_delta_s),
                            'MaxPasses': int(max_passes),
                            'Expressions': []
                        }
                    ]
                }
                print(f"Setting adaptive solution type to Broadband at {lf}, {hf} (passes: {max_passes}, delta: {max_delta_s})")

            setup.props['AdaptiveSettings'] = adaptive_settings
            setup.update()
            
            # Create frequency sweep using LIN (Linear Step) format
            sweep = setup.add_sweep(name=sweep_name, sweep_type="Interpolating")
            sweep.props['Sweeps'] = {
                'Variable': 'Freq',
                'Data': f"LIN {start_freq} {stop_freq} {step_freq}",
                'OffsetF1': False,
                'Synchronize': 0
            }
            sweep.update()
            print(f"Created/configured frequency sweep: {sweep_name} ({start_freq} to {stop_freq} step {step_freq})")
            
            h3d.save_project()
            h3d.close_project()
            print("Setup configuration completed and project saved.")
            
            # Re-initialize Edb connection
            self.initialize_edb()
            return True
        except Exception as e:
            print("Error configuring sweep via PyAEDT:")
            import traceback
            traceback.print_exc()
            # Try to re-initialize Edb anyway
            try:
                self.initialize_edb()
            except:
                pass
            return False

    def import_stackup_xml(self, xml_path):
        """Import a stackup definition from an XML file into the current EDB design.
        
        Args:
            xml_path: Absolute path to the stackup XML file.
        
        Returns:
            True if stackup was imported successfully, False otherwise.
        """
        if not self.edb:
            raise RuntimeError("EDB is not loaded.")
        
        if not os.path.exists(xml_path):
            raise FileNotFoundError(f"Stackup XML file not found: {xml_path}")
        
        print(f"Importing stackup from XML: {xml_path}")
        try:
            # Parse and import materials from XML first to ensure layer materials are defined
            try:
                import xml.etree.ElementTree as ET
                tree = ET.parse(xml_path)
                root = tree.getroot()
                
                # Helper to find tag ignoring namespace
                def find_all_by_local_name(parent, local_name):
                    elements = []
                    for elem in parent.iter():
                        tag = elem.tag
                        if '}' in tag:
                            tag = tag.split('}', 1)[1]
                        if tag == local_name:
                            elements.append(elem)
                    return elements

                materials_elements = find_all_by_local_name(root, "Material")
                print(f"Found {len(materials_elements)} Material definitions in stackup XML. Registering...")
                for mat_elem in materials_elements:
                    name = mat_elem.get("Name")
                    if not name:
                        continue
                    
                    # Skip if already exists
                    if name in self.edb.materials.materials:
                        continue
                    
                    # Parse permittivity (default 1.0)
                    permittivity = 1.0
                    perm_elems = find_all_by_local_name(mat_elem, "Permittivity")
                    if perm_elems:
                        double_elems = find_all_by_local_name(perm_elems[0], "Double")
                        if double_elems and double_elems[0].text:
                            permittivity = float(double_elems[0].text)
                            
                    # Parse dielectric loss tangent (default 0.0)
                    loss_tangent = 0.0
                    lt_elems = find_all_by_local_name(mat_elem, "DielectricLossTangent")
                    if lt_elems:
                        double_elems = find_all_by_local_name(lt_elems[0], "Double")
                        if double_elems and double_elems[0].text:
                            loss_tangent = float(double_elems[0].text)
                            
                    # Parse conductivity (default None)
                    conductivity = None
                    cond_elems = find_all_by_local_name(mat_elem, "Conductivity")
                    if cond_elems:
                        double_elems = find_all_by_local_name(cond_elems[0], "Double")
                        if double_elems and double_elems[0].text:
                            conductivity = float(double_elems[0].text)
                            
                    if conductivity is not None:
                        try:
                            self.edb.materials.add_conductor_material(name, conductivity)
                            print(f"  Added conductor material: {name} (conductivity={conductivity})")
                        except Exception as e:
                            print(f"  Error adding conductor material {name}: {e}")
                    else:
                        try:
                            self.edb.materials.add_dielectric_material(name, permittivity, loss_tangent)
                            print(f"  Added dielectric material: {name} (permittivity={permittivity}, loss_tangent={loss_tangent})")
                        except Exception as e:
                            print(f"  Error adding dielectric material {name}: {e}")
            except Exception as e:
                print(f"Error parsing/adding materials from XML: {e}")

            # Now load the stackup XML
            self.edb.stackup.load_from_xml(file_path=xml_path)
            self.edb.save()
            print("Stackup imported and EDB saved successfully.")
            
            # Print imported layer summary
            layers = list(self.edb.stackup.layers.keys())
            print(f"Stackup layers ({len(layers)}): {', '.join(layers)}")
            return True
        except Exception as e:
            print(f"Error importing stackup XML:")
            import traceback
            traceback.print_exc()
            return False

    def get_stackup_info(self):
        """Retrieve stackup layers details for display in the GUI.
        
        Returns:
            list of dicts containing name, type, material, dielectric_fill, thickness
        """
        if not self.edb:
            return []
        
        layers_info = []
        try:
            layer_objs = list(self.edb.stackup.layers.values())
            # Sort by upper_elevation descending (TOP first, BOTTOM last)
            try:
                layer_objs.sort(key=lambda x: getattr(x, 'upper_elevation', 0), reverse=True)
            except Exception:
                pass
            
            for layer in layer_objs:
                thickness = getattr(layer, 'thickness', 0.0)
                if thickness < 1e-3:
                    thickness_str = f"{thickness * 1e6:.2f} µm"
                else:
                    thickness_str = f"{thickness * 1e3:.4f} mm"
                
                # Get dielectric fill material if available
                dielectric_fill = getattr(layer, 'dielectric_fill', '')
                if dielectric_fill is None:
                    dielectric_fill = ''
                elif hasattr(dielectric_fill, 'name'):
                    dielectric_fill = dielectric_fill.name
                    
                layers_info.append({
                    "name": getattr(layer, 'name', 'Unknown'),
                    "type": getattr(layer, 'type', 'Unknown'),
                    "material": getattr(layer, 'material', 'Unknown'),
                    "dielectric_fill": str(dielectric_fill),
                    "thickness": thickness_str,
                    "thickness_val": thickness
                })
        except Exception as e:
            print(f"Error getting stackup info: {e}")
            import traceback
            traceback.print_exc()
            
        return layers_info

    def export_touchstone(self, setup_name="Setup1", sweep_name="Sweep1",
                          output_path="", non_graphical=True):
        """Export Touchstone (.sNp) file from a completed simulation.
        
        Args:
            setup_name: Name of the setup to export from.
            sweep_name: Name of the sweep to export from.
            output_path: Output file path. Auto-generated if empty.
            non_graphical: If True, run in non-graphical mode.
        
        Returns:
            Path to the exported Touchstone file, or None on failure.
        """
        aedt_file = self.edb_path.replace(".aedb", ".aedt")
        if not os.path.exists(aedt_file):
            print(f"AEDT project file not found: {aedt_file}")
            return None
        
        # Close EDB to release file lock
        self.close()
        
        try:
            from ansys.aedt.core import Hfss3dLayout
            
            h3d = Hfss3dLayout(project=aedt_file, version=self.version,
                               non_graphical=non_graphical)
            
            # Automatically detect how many ports exist in the simulation design
            num_ports = 0
            try:
                if h3d.ports:
                    num_ports = len(h3d.ports)
                elif h3d.excitation_names:
                    num_ports = len(h3d.excitation_names)
            except Exception as e:
                print(f"Warning: could not detect port count via h3d: {e}")
                
            ext = f".s{num_ports}p" if num_ports > 0 else ".sNp"
            print(f"Detected {num_ports} ports. Using Touchstone extension: {ext}")
            
            if not output_path:
                project_dir = os.path.dirname(aedt_file)
                project_name = os.path.splitext(os.path.basename(aedt_file))[0]
                output_path = os.path.join(project_dir, f"{project_name}{ext}")
            else:
                base, orig_ext = os.path.splitext(output_path)
                if orig_ext.lower().startswith('.s') and orig_ext.lower().endswith('p'):
                    output_path = base + ext
            
            print(f"Exporting Touchstone to: {output_path}")
            
            result = h3d.export_touchstone(
                setup=setup_name,
                sweep=sweep_name,
                output_file=output_path
            )
            
            h3d.save_project()
            h3d.close_project()
            
            if result and os.path.exists(output_path):
                print(f"Touchstone exported successfully: {output_path}")
                self.initialize_edb()
                return output_path
            else:
                # Try to find generated sNp file by pattern
                project_dir = os.path.dirname(aedt_file)
                for f in os.listdir(project_dir):
                    f_ext = os.path.splitext(f)[1].lower()
                    if f_ext.startswith('.s') and f_ext.endswith('p'):
                        found_path = os.path.join(project_dir, f)
                        print(f"Found exported Touchstone file: {found_path}")
                        self.initialize_edb()
                        return found_path
                
                print("Touchstone export completed but file not found at expected path.")
                self.initialize_edb()
                return None
                
        except Exception as e:
            print("Error exporting Touchstone:")
            import traceback
            traceback.print_exc()
            try:
                self.initialize_edb()
            except:
                pass
            return None

    def run_analysis(self, setup_name="Setup1", sweep_name="Sweep1", num_cores=4,
                     non_graphical=True, export_touchstone=False, export_path=""):
        """Open design in PyAEDT HFSS 3D Layout and run the EM simulation.
        
        This method is designed to be called from a background thread so the
        GUI stays responsive during long-running simulations.
        
        Args:
            setup_name: Name of the setup to analyze (default: Setup1).
            sweep_name: Name of the sweep for Touchstone export (default: Sweep1).
            num_cores: Number of CPU cores to use for simulation (default: 4).
            non_graphical: If True, run Ansys in non-graphical mode (default: True).
            export_touchstone: If True, export Touchstone (.sNp) after analysis.
            export_path: Output path for the Touchstone file. Auto-generated if empty.
        
        Returns:
            dict with 'success' (bool) and optionally 'touchstone_path' (str).
        """
        if not self.edb_path:
            raise RuntimeError("EDB path is not set.")
        
        # The AEDT project file should already exist after sweep setup
        aedt_file = self.edb_path.replace(".aedb", ".aedt")
        if not os.path.exists(aedt_file):
            raise RuntimeError(
                f"AEDT project file not found: {aedt_file}\n"
                "Please run 'Apply Sweep Setup' first to create the AEDT project."
            )
        
        print(f"Launching HFSS 3D Layout for EM analysis (non-graphical={non_graphical}, cores={num_cores})...")
        
        # Close Edb connection first to release file lock
        self.close()
        
        # Remove stale lock file
        aedt_lock = aedt_file + ".lock"
        if os.path.exists(aedt_lock):
            try:
                os.remove(aedt_lock)
                print(f"Removed stale lock file: {aedt_lock}")
            except Exception as e:
                print(f"Could not remove lock file {aedt_lock}: {e}")
        
        result = {'success': False, 'touchstone_path': None}
        
        try:
            from ansys.aedt.core import Hfss3dLayout
            
            # Open project in HFSS 3D Layout
            h3d = Hfss3dLayout(project=aedt_file, version=self.version, non_graphical=non_graphical)
            
            # Verify the setup exists
            setup_found = False
            for s in h3d.setups:
                if s.name == setup_name:
                    setup_found = True
                    break
            
            if not setup_found:
                available = [s.name for s in h3d.setups]
                h3d.close_project()
                raise RuntimeError(
                    f"Setup '{setup_name}' not found in the project.\n"
                    f"Available setups: {available}"
                )
            
            print(f"Starting EM analysis on setup '{setup_name}' with {num_cores} cores...")
            print("This may take a significant amount of time depending on design complexity.")
            print("=" * 60)
            
            # Run analysis
            h3d.analyze_setup(name=setup_name, cores=num_cores)
            
            print("=" * 60)
            print(f"EM analysis on setup '{setup_name}' completed successfully!")
            result['success'] = True
            
            # Auto-export Touchstone if requested
            if export_touchstone:
                # Automatically detect how many ports exist in the simulation design
                num_ports = 0
                try:
                    if h3d.ports:
                        num_ports = len(h3d.ports)
                    elif h3d.excitation_names:
                        num_ports = len(h3d.excitation_names)
                except Exception as e:
                    print(f"Warning: could not detect port count via h3d: {e}")
                    
                ext = f".s{num_ports}p" if num_ports > 0 else ".sNp"
                print(f"Detected {num_ports} ports. Using Touchstone extension: {ext}")
                
                if not export_path:
                    project_dir = os.path.dirname(aedt_file)
                    project_name = os.path.splitext(os.path.basename(aedt_file))[0]
                    export_path = os.path.join(project_dir, f"{project_name}{ext}")
                else:
                    base, orig_ext = os.path.splitext(export_path)
                    if orig_ext.lower().startswith('.s') and orig_ext.lower().endswith('p'):
                        export_path = base + ext
                
                print(f"Exporting Touchstone to: {export_path}")
                try:
                    ts_result = h3d.export_touchstone(
                        setup=setup_name,
                        sweep=sweep_name,
                        output_file=export_path
                    )
                    if ts_result:
                        print(f"Touchstone exported successfully: {export_path}")
                        result['touchstone_path'] = export_path
                    else:
                        print("Touchstone export returned no result. Check output directory.")
                except Exception as ts_e:
                    print(f"Warning: Touchstone export failed: {ts_e}")
            
            h3d.save_project()
            h3d.close_project()
            print("Project saved and closed.")
            
            # Re-initialize Edb connection
            self.initialize_edb()
            return result
            
        except Exception as e:
            print("Error during EM analysis:")
            import traceback
            traceback.print_exc()
            # Try to re-initialize Edb anyway
            try:
                self.initialize_edb()
            except:
                pass
            return result

    def close(self):
        """Close Edb connection."""
        if self.edb:
            try:
                self.edb.close()
                print("Edb connection closed.")
            except:
                pass
            self.edb = None

