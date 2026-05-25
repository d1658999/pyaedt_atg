# PyAEDT Automatic Electromagnetic Setup GUI Tool

This utility provides a user-friendly, responsive PySide6 desktop interface to automate the initial configuration of Cadence Allegro PCB layout designs (`.brd`) or Ansys Electronics Desktop projects (`.aedt`/`.aedb`) before starting HFSS EM simulations. 

It streamlines four key tasks:
1. **Layout Cutout Creation** (reducing board size to only focus on critical nets).
2. **Auto-Configuration of Ports and RLCs** (placing excitations on terminations and replacing RLCs with component ports).
3. **Broadband Frequency Sweep Setup** (setting up simulation setups and frequency ranges with custom adaptive solution profiles).
4. **EM Simulation Execution** (running the HFSS 3D Layout analysis directly from the GUI without freezing the interface).

---

## 🛠️ Prerequisites & System Setup

### 1. Ansys Electronics Desktop (AEDT)
The tool supports **Ansys Electronics Desktop versions from 2023 R1 (v231) up to 2025 R2 (v252)** (default: 2025 R1).
- Default Installation Path format: `C:\Program Files\ANSYS Inc\v[ver_code]\AnsysEM` (e.g. `v251` for 2025 R1).
- The application dynamically configures the corresponding environment variable (e.g. `ANSYSEM_ROOT231` for version 2023.1) based on the user-selected version in the dropdown.

### 2. Python Virtual Environment & Dependencies
Dependencies are installed inside the virtual environment (`.venv`). Make sure the following libraries are installed:
```bash
# Activate your virtual environment
.venv\Scripts\activate

# Install required dependencies
pip install PySide6 pyaedt pyedb pyedb[dotnet]
```

---

## 🚀 Running the GUI Tool

To launch the desktop interface, execute `main_gui.py` using the virtual environment's python interpreter:

```bash
.venv\Scripts\python main_gui.py
```

---

## 📖 Step-by-Step GUI Workflow

The GUI is divided into a **Control Panel** (left) and an **Interactive Browser** (right). Below is the recommended sequence:

### Step 1: Import Project
1. Go to the **1. Import** tab in the control panel.
2. Click **Browse** and select a `.brd` board file, `.aedb` folder, or `.aedt` project.
3. Choose the Ansys Version (default: `2025.1`).
4. Click **Load Board/Project**. 
   > [!NOTE]
   > Translating a `.brd` file to EDB format (`.aedb`) can take 1–3 minutes depending on the board complexity. The interface remains fully responsive during this process due to background worker threads.

### Step 2: Select Signal Nets
1. Once loaded, the **Nets Browser** on the right lists all nets in the design.
2. Use the search filter at the top (e.g. search for `ANT6` or `ANT7`) to quickly locate signal nets.
3. Select one or more nets by clicking on them. Use `Ctrl` or `Shift` for multi-selection.

### Step 3: Configure Layout Cutout & Stackup
1. Switch to the **2. Cutout** tab on the left.

**Import Stackup (Optional)**:
- Click **Browse** in the "Import Stackup" section to select a stackup `.xml` file.
- Click **Import Stackup** to apply it. The tool automatically parses and registers all materials defined in the XML (such as dielectric properties for `DS-8502SQ`, `SOLDERMASK`, `AIR` and conductor properties for `copper - 5E7`) into the EDB design database before importing the stackup layers. The **Stackup Layers Viewer** below will automatically update to display all layers, types, materials, dielectric fill, and thicknesses in order, confirming a successful import.

**Layout Cutout**:
- Set the **Cutout Type** (default is **Conforming**; options: `Conforming`, `ConvexHull`, `Bounding`).
- Set the **Expansion Factor** (default is **0.1** representing 10% expansion, which is used to calculate the expansion size dynamically for all cutout strategies).
- Verify the output folder path (defaults to `[original_path]_cutout.aedb`).
- Click **Run Layout Cutout**.
- When complete, a prompt will ask if you want to automatically load this new cutout project. Click **Yes** to load it and configure ports.

### Step 4: Auto-Setup Ports & RLCs
1. Go to the **3. Ports** tab.
2. Specify the ground reference net (default: `GND`).
3. Click **Auto-Setup Ports & RLCs**.
   > [!NOTE]
   > The tool automatically:
   > - Places terminal ports on non-RLC termination points (e.g., connector or IC pins).
   > - Matches reference ground pins on the **same placement layer** as the signal pin to maintain high-quality reference paths.
   > - Deactivates all Resistors, Capacitors, and Inductors connected to the signal path and replaces them with component ports.

### Step 5: Configure Sweep & Adaptive Solutions
1. Switch to the **4. Sweep** tab.
2. The tab is divided into two logical sections:
   - **Adaptive Solutions (Top Group)**:
     - Set the **Setup Name** (default `Setup1`).
     - Choose the **Solution Freq Type**:
       - **Broadband (Default)**: Enter `Low Frequency` (default `0.5GHz`), `High Frequency` (default `5GHz`), `Maximum Number of Passes` (default `10`), and `Maximum Delta S` (default `0.02`).
       - **Single**: Enter `Frequency` (default `5GHz`), `Maximum Number of Passes` (default `10`), and `Maximum Delta S` (default `0.02`).
       - **Multi-frequencies**: Use the interactive table to define each adaptive frequency entry with its own `Frequency`, `Units` (GHz/MHz/kHz/Hz), and `Max Delta S`. Click **Add** to insert a row or **Remove** to delete the selected row. Set the shared `Maximum Number of Passes` (default `10`).
   - **Frequency Sweep Range (Bottom Group)**:
     - Set the **Sweep Name** (default `Sweep1`).
     - Define the **Start Frequency** (default `0.5GHz`), **Stop Frequency** (default `5GHz`), and **Frequency Step** (default `0.01GHz`).
3. Click **Apply Sweep Setup** to create/configure the settings inside AEDT.

### Step 6: Run EM Analysis
1. Switch to the **5. Analyze** tab.

**EM Analysis**:
1. Verify the **Setup Name** (default: `Setup1`) and **Sweep Name** (default: `Sweep1`).
2. Set the **CPU Cores** (default: `4`) for parallel processing.
3. Check/uncheck **Run Non-Graphical Mode** as needed.
4. Check **Export Touchstone (e.g. .s10p, .s16p) after analysis** to automatically export S-parameter matrix data upon completion. The tool automatically detects the number of simulation ports and uses the correct Touchstone extension (e.g., `.s10p` or `.s16p` for 10 and 16 ports, respectively). Optionally specify a custom output path, or leave blank for an auto-generated filename.
5. Click **▶ Run EM Analysis**.
6. A confirmation dialog will appear — click **Yes** to start.
   > [!NOTE]
   > The simulation runs in a background thread so the **GUI remains fully responsive**. Progress and solver output are streamed in real-time to the **Execution Log** panel. A status indicator on the Analyze tab shows whether the analysis is running, succeeded, or failed.
   > 
   > EM simulations can take anywhere from minutes to hours depending on design complexity and frequency resolution.
   >
   > If Touchstone export is enabled, the `.sNp` file (with the extension resolved to the actual port count, e.g. `.s10p` or `.s16p`) will be saved automatically after the simulation completes. The file path is displayed in the status indicator and the Execution Log.

---

## ⚡ Automatic Port Configuration Rules

When you trigger **Auto-Setup Ports & RLCs**:

1. **Non-RLC Termination Excitations**:
   - Places circuit ports directly on the connector and IC pins connected to active signal nets.
   - Selects the best ground reference pin using a **3-tier priority order**:
     1. **Same component** — GND pins within the same component (e.g., a connector's own GND pin). This produces short, clean port references and avoids long diagonal lines crossing other components.
     2. **Same placement layer** — GND pins on the same layer (e.g. `TOP` layer signals map to `TOP` layer ground pins).
     3. **Global fallback** — Any GND pin in the design if no local match exists.
   - Generates non-clashing terminal/reference names (e.g. `Port_J10601_1` and `Port_J10601_1_ref`) to support multiple ports sharing the same physical reference pin without database conflicts.
2. **RLC Replacement**:
   - All Resistors, Inductors, and Capacitors on the active signal path are deactivated in EDB and replaced with component ports across their layout footprint pads.

---

## 🛠️ Troubleshooting & Tips

- **Lock Files**: If you run into database write errors, ensure Ansys Electronics Desktop is closed for the project you are loading, as it may place file locks on the `.aedb` folder. The tool automatically attempts to clear stale lock files before configuring sweeps.
- **Environment Variables**: If the tool cannot find AEDT, verify that `C:\Program Files\ANSYS Inc\v251\AnsysEM` exists and matches the version selected in the dropdown.
- **Log Console**: Any errors or detailed output from PyAEDT/PyEDB will be printed directly in the **Execution Log** text window at the bottom left.
- **Long Simulations**: EM analyses can run for extended periods. The GUI stays interactive — you can scroll logs, switch tabs, or review settings while the simulation runs in the background.
